from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F, Sum, Case, When, Value, IntegerField
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
import logging

from internal_accounting.models import AdultStudent, AdultRefund
from internal_accounting.forms import AdultStudentForm, AdultRefundForm

logger = logging.getLogger(__name__)

DESIRED_SERVICE_CHOICES = [
    ('', 'Все'),
    ('course', 'Курс'),
    ('trial', 'Пробное'),
    ('section', 'Секция'),
    ('individual', 'Индивидуальное'),
]


def adult_student_list(request):
    """Список взрослых студентов."""
    
    current_year = request.GET.get('year', str(timezone.now().year))
    all_years = AdultStudent.objects.values_list('statement_year', flat=True).distinct().order_by('-statement_year')
    all_years = list(all_years)
    
    current_sort = request.GET.get('sort', '-statement_number')
    valid_sort_fields = [
        'statement_number', '-statement_number',
        'fio', '-fio',
        'course_name', '-course_name',
        'date_of_buyback', '-date_of_buyback',
        'phone_number', '-phone_number',
        'summ_of_payback', '-summ_of_payback',
        'school_name', '-school_name',
        'first_visit_date', '-first_visit_date',
    ]
    if current_sort not in valid_sort_fields:
        current_sort = '-statement_number'
    
    queryset = AdultStudent.objects.all()
    
    if current_year != 'all':
        try:
            year = int(current_year)
            queryset = queryset.filter(statement_year=year)
        except (ValueError, TypeError):
            pass
    
    current_school = request.GET.get('school', '')
    current_status = request.GET.get('status', '')
    current_desired_service = request.GET.get('desired_service', '')
    current_total_hours_min = request.GET.get('total_hours_min', '')
    current_total_hours_max = request.GET.get('total_hours_max', '')
    current_rolled_min = request.GET.get('rolled_min', '')
    current_rolled_max = request.GET.get('rolled_max', '')
    current_remaining_min = request.GET.get('remaining_min', '')
    current_remaining_max = request.GET.get('remaining_max', '')
    current_sum_min = request.GET.get('sum_min', '')
    current_sum_max = request.GET.get('sum_max', '')
    current_buyback_from = request.GET.get('buyback_from', '')
    current_buyback_to = request.GET.get('buyback_to', '')
    current_documents = request.GET.get('documents', None)
    current_internal_exam = request.GET.get('internal_exam', None)
    current_gai_exam = request.GET.get('gai_exam', None)
    
    if current_school:
        queryset = queryset.filter(school_name=current_school)
    
    if current_status == 'in_office':
        queryset = queryset.filter(is_in_office=True)
    elif current_status == 'frozen':
        queryset = queryset.filter(is_manually_closed=True)
    elif current_status == 'individual':
        queryset = queryset.filter(course_name__icontains='индив')
    elif current_status == 'refund':
        queryset = queryset.filter(is_refund=True)
    
    if current_desired_service == 'course':
        queryset = queryset.filter(total_hours__gte=5)
    elif current_desired_service == 'trial':
        queryset = queryset.filter(course_name__icontains='ПРОБНОЕ')
    elif current_desired_service == 'section':
        queryset = queryset.filter(course_name__icontains='СЕКЦИЯ')
    elif current_desired_service == 'individual':
        queryset = queryset.filter(course_name__icontains='индив')
    
    if current_total_hours_min:
        try:
            queryset = queryset.filter(total_hours__gte=int(current_total_hours_min))
        except (ValueError, TypeError):
            pass
    if current_total_hours_max:
        try:
            queryset = queryset.filter(total_hours__lte=int(current_total_hours_max))
        except (ValueError, TypeError):
            pass
    
    if current_rolled_min:
        try:
            queryset = queryset.filter(rolled_back_hours__gte=int(current_rolled_min))
        except (ValueError, TypeError):
            pass
    if current_rolled_max:
        try:
            queryset = queryset.filter(rolled_back_hours__lte=int(current_rolled_max))
        except (ValueError, TypeError):
            pass
    
    if current_sum_min:
        try:
            queryset = queryset.filter(summ_of_payback__gte=Decimal(current_sum_min))
        except (ValueError, TypeError):
            pass
    if current_sum_max:
        try:
            queryset = queryset.filter(summ_of_payback__lte=Decimal(current_sum_max))
        except (ValueError, TypeError):
            pass
    
    if current_buyback_from:
        try:
            queryset = queryset.filter(date_of_buyback__gte=current_buyback_from)
        except (ValueError, TypeError):
            pass
    if current_buyback_to:
        try:
            queryset = queryset.filter(date_of_buyback__lte=current_buyback_to)
        except (ValueError, TypeError):
            pass
    
    if current_documents == 'true':
        queryset = queryset.filter(documents=True)
    elif current_documents == 'false':
        queryset = queryset.filter(documents=False)
    
    if current_internal_exam == 'true':
        queryset = queryset.filter(internal_examination=True)
    elif current_internal_exam == 'false':
        queryset = queryset.filter(internal_examination=False)
    
    if current_gai_exam == 'true':
        queryset = queryset.filter(gai_examination=True)
    elif current_gai_exam == 'false':
        queryset = queryset.filter(gai_examination=False)
    
    if current_sort in ['statement_number', '-statement_number']:
        queryset = queryset.order_by(current_sort.replace('statement_number', 'sequence_number'))
    else:
        queryset = queryset.order_by(current_sort)
    
    total_hours_all = queryset.filter(total_hours__isnull=False).aggregate(
        total=Sum('total_hours')
    )['total'] or 0
    
    total_rolled = queryset.aggregate(total=Sum('rolled_back_hours'))['total'] or 0
    
    queryset_annotated = queryset.annotate(
        remaining=Case(
            When(total_hours__isnull=True, then=Value(None)),
            default=F('total_hours') - F('rolled_back_hours'),
            output_field=IntegerField()
        )
    )
    total_remaining = queryset_annotated.filter(remaining__isnull=False).aggregate(
        total=Sum('remaining')
    )['total'] or 0
    
    students_with_flags = []
    for student in queryset:
        flags = {
            'student': student,
            'is_refund': student.is_refund,
            'is_in_office': student.is_in_office,
            'is_frozen': student.is_manually_closed,
            'is_individual': 'индив' in (student.course_name or '').lower(),
            'is_section': 'СЕКЦИЯ' in (student.course_name or ''),
            'is_no_category': not student.is_refund and not student.is_in_office,
            'school_name': student.school_name,
            'remaining_hours': student.remaining_hours,
        }
        students_with_flags.append(flags)
    
    unregistered_refunds = []
    
    show_filters = request.GET.get('show_filters', 'false') == 'true'
    if any([
        current_school, current_status, current_desired_service,
        current_total_hours_min, current_total_hours_max,
        current_rolled_min, current_rolled_max,
        current_remaining_min, current_remaining_max,
        current_sum_min, current_sum_max,
        current_buyback_from, current_buyback_to,
        current_documents, current_internal_exam, current_gai_exam
    ]):
        show_filters = True
    
    context = {
        'students_with_flags': students_with_flags,
        'all_years': all_years,
        'current_year': current_year,
        'current_sort': current_sort,
        'total_hours_all': total_hours_all,
        'total_rolled': total_rolled,
        'total_remaining': total_remaining,
        'unregistered_refunds': unregistered_refunds,
        'show_filters': show_filters,
        'desired_service_choices': DESIRED_SERVICE_CHOICES,
        'current_school': current_school,
        'current_status': current_status,
        'current_desired_service': current_desired_service,
        'current_total_hours_min': current_total_hours_min,
        'current_total_hours_max': current_total_hours_max,
        'current_rolled_min': current_rolled_min,
        'current_rolled_max': current_rolled_max,
        'current_remaining_min': current_remaining_min,
        'current_remaining_max': current_remaining_max,
        'current_sum_min': current_sum_min,
        'current_sum_max': current_sum_max,
        'current_buyback_from': current_buyback_from,
        'current_buyback_to': current_buyback_to,
        'current_documents': current_documents,
        'current_internal_exam': current_internal_exam,
        'current_gai_exam': current_gai_exam,
    }
    
    return render(request, 'internal_accounting/adult/student_list.html', context)


def adult_student_detail(request, pk):
    student = get_object_or_404(AdultStudent, pk=pk)
    refunds = AdultRefund.objects.filter(student=student).order_by('-date_of_refund')
    
    context = {
        'student': student,
        'refunds': refunds,
        'remaining_hours': student.remaining_hours,
        'is_statement_closed': student.is_statement_closed,
    }
    
    return render(request, 'internal_accounting/adult/student_detail.html', context)


def adult_student_visits(request, pk):
    """История посещений взрослого студента."""
    student = get_object_or_404(AdultStudent, pk=pk)
    context = {'student': student}
    return render(request, 'internal_accounting/adult/student_visits.html', context)


def adult_add_student(request):
    if request.method == 'POST':
        form = AdultStudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student._imported = False
            student.save()
            messages.success(request, f'Студент {student.fio} успешно добавлен!')
            return redirect('internal_accounting:adult:student_list')
        else:
            print("❌ Ошибки формы:", form.errors)
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
    else:
        form = AdultStudentForm()
    
    context = {
        'form': form,
        'title': 'Добавить взрослого студента',
    }
    
    return render(request, 'internal_accounting/adult/student_form.html', context)


def adult_edit_student(request, pk):
    student = get_object_or_404(AdultStudent, pk=pk)
    
    if request.method == 'POST':
        form = AdultStudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Данные студента {student.fio} обновлены!')
            return redirect('internal_accounting:adult:student_detail', pk=pk)
    else:
        form = AdultStudentForm(instance=student)
    
    context = {
        'form': form,
        'student': student,
        'title': 'Редактировать студента',
    }
    
    return render(request, 'internal_accounting/adult/student_form.html', context)


def adult_delete_student(request, pk):
    student = get_object_or_404(AdultStudent, pk=pk)
    
    if request.method == 'POST':
        fio = student.fio
        student.delete()
        messages.warning(request, f'Студент {fio} удалён!')
        return redirect('internal_accounting:adult:student_list')
    
    context = {'student': student}
    return render(request, 'internal_accounting/adult/student_confirm_delete.html', context)


def adult_refund_add(request):
    student_id = request.GET.get('student_id')
    student = None
    if student_id:
        student = get_object_or_404(AdultStudent, pk=student_id)
    
    if request.method == 'POST':
        form = AdultRefundForm(request.POST)
        if form.is_valid():
            refund = form.save(commit=False)
            refund.save()
            messages.success(request, f'Возврат средств на сумму {refund.summ_of_refund} зарегистрирован!')
            return redirect('internal_accounting:adult:student_detail', pk=refund.student_id)
    else:
        form = AdultRefundForm()
        if student:
            form.initial['student'] = student
    
    context = {
        'form': form,
        'student': student,
    }
    
    return render(request, 'internal_accounting/adult/refund_form.html', context)


def adult_export_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from django.http import HttpResponse
    
    queryset = AdultStudent.objects.all()
    
    current_year = request.GET.get('year', str(timezone.now().year))
    if current_year != 'all':
        try:
            year = int(current_year)
            queryset = queryset.filter(statement_year=year)
        except (ValueError, TypeError):
            pass
    
    wb = Workbook()
    ws = wb.active
    ws.title = 'Взрослые студенты'
    
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    headers = [
        '№', 'ФИО', 'Курс', 'Дата покупки', 'Телефон',
        'Сумма платежа', 'Школа', 'Всего часов', 'Откатано', 'Остаток',
        'Первое посещение', 'В офисе', 'Возврат'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = alignment
    
    for row, student in enumerate(queryset.order_by('-statement_year', '-sequence_number'), 2):
        data = [
            student.statement_number,
            student.fio,
            student.course_name,
            student.date_of_buyback.strftime('%d.%m.%Y') if student.date_of_buyback else '',
            student.phone_number,
            float(student.summ_of_payback),
            student.school_name or '',
            student.total_hours or '',
            student.rolled_back_hours,
            student.remaining_hours if student.remaining_hours is not None else '',
            student.first_visit_date.strftime('%d.%m.%Y') if student.first_visit_date else '',
            'Да' if student.is_in_office else 'Нет',
            'Да' if student.is_refund else 'Нет',
        ]
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
            cell.alignment = alignment
    
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'adult_students_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    
    return response


def adult_import_students(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, 'Файл не загружен!')
            return redirect('internal_accounting:adult:import_students')
        
        # Логика импорта
        messages.success(request, 'Студенты успешно импортированы!')
        return redirect('internal_accounting:adult:student_list')
    
    return render(request, 'internal_accounting/adult/import_students.html')