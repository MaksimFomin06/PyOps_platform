from django.urls import path
from internal_accounting.views import (
    adult_student_list,
    adult_student_detail,
    adult_student_visits,
    adult_add_student,
    adult_edit_student,
    adult_delete_student,
    adult_refund_add,
    adult_export_excel,
    adult_import_students,
)

app_name = 'adult'

urlpatterns = [
    path('', adult_student_list, name='student_list'),
    path('<int:pk>/', adult_student_detail, name='student_detail'),
    path('<int:pk>/visits/', adult_student_visits, name='student_visits'), # Нет пути из student_detail
    path('add/', adult_add_student, name='add_student'),
    path('<int:pk>/edit/', adult_edit_student, name='edit_student'),
    path('<int:pk>/delete/', adult_delete_student, name='delete_student'),
    path('refund/add/', adult_refund_add, name='refund_add'),
    path('export/', adult_export_excel, name='export_excel'),
    path('import/', adult_import_students, name='import_students'),
]