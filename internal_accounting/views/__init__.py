from .adult_views import (
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

from .child_views import (
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

__all__ = [
    'adult_student_list', 'adult_student_detail', 'adult_student_visits',
    'adult_add_student', 'adult_edit_student', 'adult_delete_student',
    'adult_refund_add', 'adult_export_excel', 'adult_import_students',
    'child_student_list', 'child_student_detail', 'child_student_visits',
    'child_add_student', 'child_edit_student', 'child_delete_student',
    'child_refund_add', 'child_export_excel', 'child_import_students',
]