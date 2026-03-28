from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Max
from datetime import date
from decimal import Decimal
from encrypted_model_fields.fields import EncryptedCharField
import logging

logger = logging.getLogger(__name__)

COURSE_HOURS_MAP = {
    "A": 9, "A+B": 9, "A1": 9, "A1+A+B": 9, "A1+B": 9,
    "АЗИЯ": 5, "БАЗА": 10, "БАЗА индив": 10,
    "КОНТР": 16, "КОНТР индив": 16,
    "МИНИ": 5, "МИНИ индив": 5,
    "ПРО": 16, "ПРО индив": 16,
    "ПРОБНОЕ": 2, "ПРОБНОЕ индив": 2,
    "РАЗОВОЕ": 1, "РАЗОВОЕ индив": 1,
    "СЕКЦИЯ": 4, "СЕРТИФИКАТ": None,
    "СТАНДАРТ": 9, "СТАНДАРТ индив": 9,
    "ЭКСТРА": 13, "ЭКСТРА индив": 13,
    "VIP": 16,
}

COURSE_NAME_CHOICES = [(name, name) for name in COURSE_HOURS_MAP.keys()]
SCHOOL_NAME_CHOICES = [("НУР", "НУР"), ("ДВИЖ", "ДВИЖ")]


class AdultStudentManager(models.Manager):
    def get_next_sequence_number(self, year):
        with transaction.atomic():
            agg = self.filter(statement_year=year).aggregate(max_seq=Max('sequence_number'))
            return (agg['max_seq'] or 0) + 1


class AdultStudent(models.Model):
    HOURS_BY_COURSE = COURSE_HOURS_MAP 
    COURSE_NAME_CHOICES = [(name, name) for name in COURSE_HOURS_MAP.keys()]
    
    objects = AdultStudentManager()

    sequence_number = models.PositiveIntegerField(
        verbose_name="Порядковый номер в году", editable=False
    )
    statement_year = models.PositiveSmallIntegerField(
        verbose_name="Год ведомости", editable=False, db_index=True
    )
    
    fio = EncryptedCharField(max_length=255, verbose_name="ФИО")
    phone_number = EncryptedCharField(max_length=20, verbose_name="Номер телефона", db_index=True)
    
    course_name = models.CharField(
        max_length=50, choices=COURSE_NAME_CHOICES, verbose_name="Название курса"
    )
    total_hours = models.IntegerField(verbose_name="Всего часов", null=True, blank=True)
    rolled_back_hours = models.IntegerField(default=0, verbose_name="Откатанные часы")
    first_visit_date = models.DateField(verbose_name="Первое посещение", blank=True, null=True)
    
    date_of_buyback = models.DateField(verbose_name="Дата покупки", blank=True, null=True)
    summ_of_payback = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма платежа"
    )
    comment_for_payback = models.TextField(
        blank=True, null=True, verbose_name="Комментарий по оплате"
    )
    
    is_refund = models.BooleanField(default=False, verbose_name="Возврат средств")
    summ_of_refund = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма возврата", default=Decimal('0.00'), blank=True
    )

    school_name = models.CharField(
        max_length=10, choices=SCHOOL_NAME_CHOICES, verbose_name="Школа", blank=True, null=True
    )
    documents = models.BooleanField(default=False, verbose_name="Документы")
    internal_examination = models.BooleanField(default=False, verbose_name="Внутренний экзамен")
    gai_examination = models.BooleanField(default=False, verbose_name="Экзамен в ГАИ")
    transferred_the_certificate = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Свидетельство передано/дата/комментарии"
    )
    is_in_office = models.BooleanField(default=False, verbose_name="В офисе")
    is_manually_closed = models.BooleanField(default=False, verbose_name="Ведомость закрыта вручную")

    class Meta:
        verbose_name = "Взрослый студент"
        verbose_name_plural = "Взрослые студенты"
        unique_together = ('sequence_number', 'statement_year')
        ordering = ['-statement_year', '-sequence_number']

    def clean(self):
        super().clean()
        if self.total_hours is not None and self.rolled_back_hours > self.total_hours:
            raise ValidationError({
                'rolled_back_hours': "Откатанные часы не могут превышать общее количество."
            })

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        if is_new:
            if not self.date_of_buyback:
                self.date_of_buyback = timezone.now().date()
            
            self.statement_year = self.date_of_buyback.year
            
            if not getattr(self, '_imported', False) and not self.sequence_number:
                self.sequence_number = AdultStudent.objects.get_next_sequence_number(self.statement_year)

            if self.rolled_back_hours > 0 and not self.first_visit_date:
                self.first_visit_date = timezone.now().date()
            
            self.full_clean() 

        super().save(*args, **kwargs)

    @property
    def remaining_hours(self):
        if self.total_hours is None:
            return None
        return max(0, self.total_hours - self.rolled_back_hours)

    @property
    def statement_number(self):
        if self.statement_year == timezone.now().year:
            return str(self.sequence_number)
        return f"{self.sequence_number}-{str(self.statement_year)[-2:]}"

    @property
    def is_course(self):
        return self.total_hours is not None and self.total_hours >= 5

    @property
    def is_trial(self):
        return self.course_name in ["ПРОБНОЕ", "ПРОБНОЕ индив"]
    
    @property
    def is_statement_closed(self):
        if self.is_manually_closed:
            return True
        if self.total_hours and self.rolled_back_hours >= (self.total_hours - 1):
            return True
        return False

    def __str__(self):
        return f"{self.statement_number} — {self.fio} — {self.course_name}"


class AdultRefund(models.Model):
    student = models.ForeignKey(
        AdultStudent, 
        on_delete=models.CASCADE, 
        related_name='refunds',
        verbose_name="Студент"
    )
    fio_snapshot = models.CharField(max_length=255, verbose_name="ФИО (на момент возврата)")
    course_name_snapshot = models.CharField(max_length=255, verbose_name="Курс (на момент возврата)")
    
    summ_of_refund = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма возврата"
    )
    date_of_refund = models.DateField(
        verbose_name="Дата возврата", default=date.today
    )
    comment_for_refund = models.TextField(
        blank=True, null=True, verbose_name="Комментарий по возврату"
    )

    class Meta:
        verbose_name = "Возврат средств (взрослый)"
        verbose_name_plural = "Возвраты средств (взрослые)"
        ordering = ['-date_of_refund']

    def _update_student_comment(self, student, action='add'):
        comment = (student.comment_for_payback or "").strip()
        prefix = "ВОЗВРАТ-"
        refund_entry = f"{prefix}{self.summ_of_refund}-{self.date_of_refund}"

        parts = comment.split()
        cleaned_parts = [part for part in parts if not part.startswith(prefix)]
        cleaned_comment = " ".join(cleaned_parts).strip()

        if action == 'add':
            new_comment = f"{cleaned_comment} {refund_entry}".strip()
        else:
            new_comment = cleaned_comment

        student.comment_for_payback = new_comment if new_comment else ""

    def save(self, *args, **kwargs):
        if self._state.adding and self.student_id:
            with transaction.atomic():
                student = AdultStudent.objects.select_for_update().get(pk=self.student_id)
                
                self.fio_snapshot = student.fio
                self.course_name_snapshot = student.course_name
                
                student.summ_of_payback -= self.summ_of_refund
                student.is_refund = True
                student.summ_of_refund = self.summ_of_refund
                
                self._update_student_comment(student, action='add')
                
                student.save(update_fields=[
                    'summ_of_payback', 'is_refund', 'summ_of_refund', 'comment_for_payback'
                ])
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.student_id:
            with transaction.atomic():
                try:
                    student = AdultStudent.objects.select_for_update().get(pk=self.student_id)
                    
                    student.summ_of_payback += self.summ_of_refund
                    if student.refunds.count() <= 1:
                         student.is_refund = False
                         student.summ_of_refund = Decimal('0.00')
                    
                    self._update_student_comment(student, action='remove')
                    
                    student.save(update_fields=[
                        'summ_of_payback', 'is_refund', 'summ_of_refund', 'comment_for_payback'
                    ])
                except AdultStudent.DoesNotExist:
                    logger.warning(f"Студент для возврата {self.id} не найден.")

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Возврат {self.fio_snapshot} от {self.date_of_refund}"


class ChildStudentManager(models.Manager):
    def get_next_sequence_number(self, year):
        with transaction.atomic():
            agg = self.filter(statement_year=year).aggregate(max_seq=Max('sequence_number'))
            return (agg['max_seq'] or 0) + 1


class Child(models.Model):
    HOURS_BY_COURSE = COURSE_HOURS_MAP 
    COURSE_NAME_CHOICES = [(name, name) for name in COURSE_HOURS_MAP.keys()]
    
    objects = ChildStudentManager()

    sequence_number = models.PositiveIntegerField(
        verbose_name="Порядковый номер в году", editable=False
    )
    statement_year = models.PositiveSmallIntegerField(
        verbose_name="Год ведомости", editable=False, db_index=True
    )
    
    fio = EncryptedCharField(max_length=255, verbose_name="ФИО ребенка")
    phone_number = EncryptedCharField(max_length=20, verbose_name="Номер телефона родителя", db_index=True)
    parent_name = EncryptedCharField(max_length=255, verbose_name="ФИО родителя/законного представителя", blank=True, null=True)
    
    course_name = models.CharField(
        max_length=50, choices=COURSE_NAME_CHOICES, verbose_name="Название курса"
    )
    total_hours = models.IntegerField(verbose_name="Всего часов", null=True, blank=True)
    rolled_back_hours = models.IntegerField(default=0, verbose_name="Откатанные часы")
    first_visit_date = models.DateField(verbose_name="Первое посещение", blank=True, null=True)
    
    date_of_buyback = models.DateField(verbose_name="Дата покупки", blank=True, null=True)
    summ_of_payback = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма платежа"
    )
    comment_for_payback = models.TextField(
        blank=True, null=True, verbose_name="Комментарий по оплате"
    )
    
    is_refund = models.BooleanField(default=False, verbose_name="Возврат средств")
    summ_of_refund = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма возврата", default=Decimal('0.00'), blank=True
    )

    is_in_office = models.BooleanField(default=False, verbose_name="В офисе")
    is_manually_closed = models.BooleanField(default=False, verbose_name="Ведомость закрыта вручную")

    class Meta:
        verbose_name = "Детский студент"
        verbose_name_plural = "Детские студенты"
        unique_together = ('sequence_number', 'statement_year')
        ordering = ['-statement_year', '-sequence_number']

    def clean(self):
        super().clean()
        if self.total_hours is not None and self.rolled_back_hours > self.total_hours:
            raise ValidationError({
                'rolled_back_hours': "Откатанные часы не могут превышать общее количество."
            })

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        if is_new:
            if not self.date_of_buyback:
                self.date_of_buyback = timezone.now().date()
            
            self.statement_year = self.date_of_buyback.year
            
            if not getattr(self, '_imported', False) and not self.sequence_number:
                self.sequence_number = Child.objects.get_next_sequence_number(self.statement_year)

            if self.rolled_back_hours > 0 and not self.first_visit_date:
                self.first_visit_date = timezone.now().date()
            
            self.full_clean() 

        super().save(*args, **kwargs)

    @property
    def remaining_hours(self):
        if self.total_hours is None:
            return None
        return max(0, self.total_hours - self.rolled_back_hours)

    @property
    def statement_number(self):
        if self.statement_year == timezone.now().year:
            return str(self.sequence_number)
        return f"{self.sequence_number}-{str(self.statement_year)[-2:]}"

    @property
    def is_course(self):
        return self.total_hours is not None and self.total_hours >= 5

    @property
    def is_trial(self):
        return self.course_name in ["ПРОБНОЕ", "ПРОБНОЕ индив"]
    
    @property
    def is_statement_closed(self):
        if self.is_manually_closed:
            return True
        if self.total_hours and self.rolled_back_hours >= (self.total_hours - 1):
            return True
        return False

    def __str__(self):
        return f"{self.statement_number} — {self.fio} — {self.course_name}"


class ChildRefund(models.Model):
    student = models.ForeignKey(
        Child, 
        on_delete=models.CASCADE, 
        related_name='refunds',
        verbose_name="Студент"
    )
    fio_snapshot = models.CharField(max_length=255, verbose_name="ФИО ребенка (на момент возврата)")
    course_name_snapshot = models.CharField(max_length=255, verbose_name="Курс (на момент возврата)")
    
    summ_of_refund = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма возврата"
    )
    date_of_refund = models.DateField(
        verbose_name="Дата возврата", default=date.today
    )
    comment_for_refund = models.TextField(
        blank=True, null=True, verbose_name="Комментарий по возврату"
    )

    class Meta:
        verbose_name = "Возврат средств (детский)"
        verbose_name_plural = "Возвраты средств (детские)"
        ordering = ['-date_of_refund']

    def _update_student_comment(self, student, action='add'):
        comment = (student.comment_for_payback or "").strip()
        prefix = "ВОЗВРАТ-"
        refund_entry = f"{prefix}{self.summ_of_refund}-{self.date_of_refund}"

        parts = comment.split()
        cleaned_parts = [part for part in parts if not part.startswith(prefix)]
        cleaned_comment = " ".join(cleaned_parts).strip()

        if action == 'add':
            new_comment = f"{cleaned_comment} {refund_entry}".strip()
        else:
            new_comment = cleaned_comment

        student.comment_for_payback = new_comment if new_comment else ""

    def save(self, *args, **kwargs):
        if self._state.adding and self.student_id:
            with transaction.atomic():
                student = Child.objects.select_for_update().get(pk=self.student_id)
                
                self.fio_snapshot = student.fio
                self.course_name_snapshot = student.course_name
                
                student.summ_of_payback -= self.summ_of_refund
                student.is_refund = True
                student.summ_of_refund = self.summ_of_refund
                
                self._update_student_comment(student, action='add')
                
                student.save(update_fields=[
                    'summ_of_payback', 'is_refund', 'summ_of_refund', 'comment_for_payback'
                ])
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.student_id:
            with transaction.atomic():
                try:
                    student = Child.objects.select_for_update().get(pk=self.student_id)
                    
                    student.summ_of_payback += self.summ_of_refund
                    if student.refunds.count() <= 1:
                         student.is_refund = False
                         student.summ_of_refund = Decimal('0.00')
                    
                    self._update_student_comment(student, action='remove')
                    
                    student.save(update_fields=[
                        'summ_of_payback', 'is_refund', 'summ_of_refund', 'comment_for_payback'
                    ])
                except Child.DoesNotExist:
                    logger.warning(f"Ребенок для возврата {self.id} не найден.")

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Возврат {self.fio_snapshot} от {self.date_of_refund}"