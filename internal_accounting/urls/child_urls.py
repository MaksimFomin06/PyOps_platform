from django.urls import path
from internal_accounting.views import (
    child_student_list,
    child_student_detail,
    child_student_visits,
    child_add_student,
    child_edit_student,
    child_delete_student,
    child_refund_add,
    child_export_excel,
    child_import_students,
)

app_name = 'child'

urlpatterns = [
    path('', child_student_list, name='student_list'),
    path('<int:pk>/', child_student_detail, name='student_detail'),
    path('<int:pk>/visits/', child_student_visits, name='student_visits'), # Нет пути из student_detail
    path('add/', child_add_student, name='add_student'),
    path('<int:pk>/edit/', child_edit_student, name='edit_student'),
    path('<int:pk>/delete/', child_delete_student, name='delete_student'),
    path('refund/add/', child_refund_add, name='refund_add'),
    path('export/', child_export_excel, name='export_excel'),
    path('import/', child_import_students, name='import_students'),
]