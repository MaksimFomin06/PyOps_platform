from django.db import models
from django.utils import timezone
from internal_accounting.models import AdultStudent, Child


class SessionLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('rejected', 'Отклонено'),
    ]
    
    DIRECTION_CHOICES = [
        ('adult', 'Взрослое'),
        ('child', 'Детское'),
    ]
    
    INSTRUCTOR_CHOICES = [
        ('1', 'Инструктор 1'),
        ('2', 'Инструктор 2'),
        ('3', 'Инструктор 3'),
        ('4', 'Инструктор 4'),
        ('5', 'Инструктор 5'),
    ]
    
    student_type = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        verbose_name="Направление"
    )
    student = models.ForeignKey(
        AdultStudent, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Студент (взрослый)",
        related_name='instructor_sessions'
    )
    child_student = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Студент (детский)",
        related_name='instructor_sessions'
    )
    
    instructor = models.CharField(
        max_length=10,
        choices=INSTRUCTOR_CHOICES,
        verbose_name="Инструктор"
    )
    
    session_date = models.DateField(verbose_name="Дата занятия")
    
    hours_count = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Количество часов"
    )
    hour_times = models.TextField(
        blank=True,
        null=True,
        verbose_name="Время занятий"
    )
    
    statement_number = models.CharField(
        max_length=50,
        verbose_name="Номер ведомости",
        editable=False
    )
    course_name = models.CharField(
        max_length=100,
        verbose_name="Курс",
        editable=False
    )
    student_fio = models.CharField(
        max_length=255,
        verbose_name="ФИО студента",
        editable=False
    )
    total_hours = models.IntegerField(
        verbose_name="Всего часов у студента",
        editable=False,
        null=True
    )
    rolled_back_hours_before = models.IntegerField(
        verbose_name="Откатано до занятия",
        editable=False,
        default=0
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Подтверждено"
    )
    confirmed_by = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Подтвердил"
    )
    rejected_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Причина отклонения"
    )
    
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий инструктора")
    admin_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий админа")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    
    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Журнал занятий"
        ordering = ['-session_date', '-created_at']
        indexes = [
            models.Index(fields=['session_date']),
            models.Index(fields=['status']),
            models.Index(fields=['instructor']),
        ]
    
    def __str__(self):
        return f"{self.session_date} — {self.student_fio} — {self.hours_count}ч."
    
    def save(self, *args, **kwargs):
        if self.student:
            self.statement_number = self.student.statement_number
            self.course_name = self.student.course_name
            self.student_fio = self.student.fio
            self.total_hours = self.student.total_hours
            self.rolled_back_hours_before = self.student.rolled_back_hours
        elif self.child_student:
            self.statement_number = self.child_student.statement_number
            self.course_name = self.child_student.course_name
            self.student_fio = self.child_student.fio
            self.total_hours = self.child_student.total_hours
            self.rolled_back_hours_before = self.child_student.rolled_back_hours
        
        super().save(*args, **kwargs)
    
    def confirm(self, confirmed_by_name):
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.confirmed_by = confirmed_by_name
        self.save()
        
        if self.student:
            self.student.rolled_back_hours = (self.student.rolled_back_hours or 0) + self.hours_count
            if self.student.rolled_back_hours > 0 and not self.student.first_visit_date:
                self.student.first_visit_date = self.session_date
            self.student.save()
        elif self.child_student:
            self.child_student.rolled_back_hours = (self.child_student.rolled_back_hours or 0) + self.hours_count
            if self.child_student.rolled_back_hours > 0 and not self.child_student.first_visit_date:
                self.child_student.first_visit_date = self.session_date
            self.child_student.save()
    
    def reject(self, reason, rejected_by_name):
        self.status = 'rejected'
        self.rejected_reason = reason
        self.admin_comment = f"Отклонено: {reason} ({rejected_by_name})"
        self.save()
    
    @property
    def remaining_hours_after(self):
        if self.total_hours:
            return self.total_hours - (self.rolled_back_hours_before + self.hours_count)
        return None
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_confirmed(self):
        return self.status == 'confirmed'
    
    @property
    def is_rejected(self):
        return self.status == 'rejected'