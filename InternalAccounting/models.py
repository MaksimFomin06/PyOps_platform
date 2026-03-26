from django.db import models

class Statements(models.Model):
    direction = models.CharField()
    statement_number = models.IntegerField()
    student_fio = models.CharField()
    course_name = models.CharField()
    phone_number = models.models.PhoneNumberField(_(""))
    comment = models.CharField()
    course_cost = models.DecimalField()
    school = models.CharField()
    date_of_purchase = models.DateField()
    statement_year = models.IntegerField