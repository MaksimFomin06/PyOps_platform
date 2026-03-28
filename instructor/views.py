from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta

from internal_accounting.models import AdultStudent, Child
from .models import SessionLog
from .forms import SessionLogForm


def instructor_dashboard(request):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    total_sessions = SessionLog.objects.count()
    pending_sessions = SessionLog.objects.filter(status='pending').count()
    confirmed_today = SessionLog.objects.filter(
        status='confirmed',
        session_date=today
    ).count()
    
    today_sessions = SessionLog.objects.filter(
        session_date=today
    ).select_related('student', 'child_student')[:20]
    
    pending_list = SessionLog.objects.filter(
        status='pending'
    ).select_related('student', 'child_student').order_by('-created_at')[:10]
    
    context = {
        'today': today,
        'week_start': week_start,
        'week_end': week_end,
        'total_sessions': total_sessions,
        'pending_sessions': pending_sessions,
        'confirmed_today': confirmed_today,
        'today_sessions': today_sessions,
        'pending_list': pending_list,
    }
    
    return render(request, 'instructor/dashboard.html', context)


def add_session(request):
    if request.method == 'POST':
        print("=== POST ЗАПРОС ПОЛУЧЕН ===")
        print(f"POST данные: {request.POST}")
        print(f"FILES: {request.FILES}")
        
        form = SessionLogForm(request.POST)
        
        if form.is_valid():
            print("✅ Форма валидна")
            session = form.save(commit=False)
            
            if session.student_type == 'adult' and form.cleaned_data.get('selected_student_id'):
                session.student = AdultStudent.objects.get(
                    pk=form.cleaned_data['selected_student_id']
                )
                print(f"Студент взрослый: {session.student.fio}")
            elif session.student_type == 'child' and form.cleaned_data.get('selected_child_id'):
                session.child_student = Child.objects.get(
                    pk=form.cleaned_data['selected_child_id']
                )
                print(f"Студент детский: {session.child_student.fio}")
            
            session.save()
            print(f"✅ Занятие сохранено: {session.id}")
            
            messages.success(
                request,
                f'Занятие добавлено и ожидает подтверждения! '
                f'{session.student_fio} — {session.hours_count}ч.'
            )
            return redirect('instructor:session_list')
        else:
            print("❌ Форма НЕ валидна")
            print(f"Ошибки формы: {form.errors}")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
                messages.error(request, f'{field}: {errors}')
    else:
        print("=== GET ЗАПРОС ===")
        form = SessionLogForm()
    
    context = {
        'form': form,
        'title': 'Добавить занятие',
    }
    
    return render(request, 'instructor/session_form.html', context)


def session_list(request):
    status = request.GET.get('status', '')
    instructor_id = request.GET.get('instructor')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    student_fio = request.GET.get('student_fio')
    student_type = request.GET.get('student_type', '')
    
    sessions = SessionLog.objects.all().select_related(
        'student', 'child_student'
    )
    
    if status:
        sessions = sessions.filter(status=status)
    if instructor_id:
        sessions = sessions.filter(instructor=instructor_id)
    if date_from:
        sessions = sessions.filter(session_date__gte=date_from)
    if date_to:
        sessions = sessions.filter(session_date__lte=date_to)
    if student_fio:
        sessions = sessions.filter(
            Q(student_fio__icontains=student_fio) |
            Q(statement_number__icontains=student_fio)
        )
    if student_type:
        sessions = sessions.filter(student_type=student_type)
    
    sessions = sessions.order_by('-session_date', '-created_at')
    
    stats = {
        'total': sessions.count(),
        'pending': sessions.filter(status='pending').count(),
        'confirmed': sessions.filter(status='confirmed').count(),
        'rejected': sessions.filter(status='rejected').count(),
    }
    
    context = {
        'sessions': sessions,
        'stats': stats,
        'current_status': status,
        'current_instructor': instructor_id,
        'date_from': date_from,
        'date_to': date_to,
        'student_fio': student_fio,
        'current_student_type': student_type,
    }
    
    return render(request, 'instructor/session_list.html', context)


def session_detail(request, pk):
    session = get_object_or_404(
        SessionLog.objects.select_related('student', 'child_student'),
        pk=pk
    )
    
    context = {
        'session': session,
    }
    
    return render(request, 'instructor/session_detail.html', context)


def confirm_session(request, pk):
    session = get_object_or_404(SessionLog, pk=pk)
    
    if request.method == 'POST':
        confirmed_by = request.POST.get('confirmed_by', 'Администратор')
        session.confirm(confirmed_by)
        
        messages.success(
            request,
            f'Занятие подтверждено! {session.student_fio} +{session.hours_count}ч.'
        )
        return redirect('instructor:session_list')
    
    context = {
        'session': session,
    }
    
    return render(request, 'instructor/session_confirm.html', context)


def reject_session(request, pk):
    session = get_object_or_404(SessionLog, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('rejected_reason', 'Без причины')
        rejected_by = request.POST.get('rejected_by', 'Администратор')
        session.reject(reason, rejected_by)
        
        messages.warning(
            request,
            f'Занятие отклонено: {reason}'
        )
        return redirect('instructor:session_list')
    
    context = {
        'session': session,
    }
    
    return render(request, 'instructor/session_reject.html', context)


def bulk_confirm(request):
    if request.method == 'POST':
        session_ids = request.POST.getlist('session_ids')
        confirmed_by = request.POST.get('confirmed_by', 'Администратор')
        
        confirmed_count = 0
        for session_id in session_ids:
            try:
                session = SessionLog.objects.get(pk=session_id, status='pending')
                session.confirm(confirmed_by)
                confirmed_count += 1
            except SessionLog.DoesNotExist:
                continue
        
        messages.success(request, f'Подтверждено занятий: {confirmed_count}')
        return redirect('instructor:session_list')
    
    pending_sessions = SessionLog.objects.filter(status='pending').select_related(
        'student', 'child_student'
    )[:50]
    
    context = {
        'pending_sessions': pending_sessions,
    }
    
    return render(request, 'instructor/bulk_confirm.html', context)


def search_student(request):
    query = request.GET.get('q', '').strip()
    student_type = request.GET.get('type', 'adult')
    
    print(f"🔍 Поиск: query='{query}', type='{student_type}'")
    
    results = []
    
    if not query:
        return JsonResponse({'results': results})
    
    if student_type == 'adult':
        students = AdultStudent.objects.all()
        print(f"📊 Всего взрослых в базе: {students.count()}")
        
        for s in students:
            if (query.lower() in s.fio.lower() or 
                query in str(s.sequence_number) or
                query in str(s.phone_number)):
                
                print(f"✅ Найдено: {s.fio}")
                results.append({
                    'id': s.id,
                    'fio': s.fio,
                    'statement_number': s.statement_number,
                    'course': s.course_name,
                    'total_hours': s.total_hours,
                    'rolled_hours': s.rolled_back_hours,
                    'remaining': s.remaining_hours,
                    'type': 'adult',
                })
    else:
        students = Child.objects.all()
        print(f"📊 Всего детей в базе: {students.count()}")
        
        for s in students:
            if (query.lower() in s.fio.lower() or 
                query in str(s.sequence_number) or
                query in str(s.phone_number)):
                
                print(f"✅ Найдено: {s.fio}")
                results.append({
                    'id': s.id,
                    'fio': s.fio,
                    'statement_number': s.statement_number,
                    'course': s.course_name,
                    'total_hours': s.total_hours,
                    'rolled_hours': s.rolled_back_hours,
                    'remaining': s.remaining_hours,
                    'type': 'child',
                })
    
    print(f"📤 Возвращаю: {len(results)} результатов")
    return JsonResponse({'results': results})


def instructor_sessions(request, instructor_id):
    sessions = SessionLog.objects.filter(
        instructor=instructor_id
    ).select_related('student', 'child_student').order_by('-session_date')[:100]
    
    stats = {
        'total': sessions.count(),
        'pending': sessions.filter(status='pending').count(),
        'confirmed': sessions.filter(status='confirmed').count(),
        'rejected': sessions.filter(status='rejected').count(),
    }
    
    context = {
        'instructor': instructor_id,
        'sessions': sessions,
        'stats': stats,
    }
    
    return render(request, 'instructor/instructor_sessions.html', context)


def admin_panel(request):
    pending_sessions = SessionLog.objects.filter(
        status='pending'
    ).select_related('student', 'child_student').order_by('-created_at')
    
    confirmed_sessions = SessionLog.objects.filter(
        status='confirmed'
    ).select_related('student', 'child_student').order_by('-confirmed_at')[:50]
    
    rejected_sessions = SessionLog.objects.filter(
        status='rejected'
    ).select_related('student', 'child_student').order_by('-created_at')[:50]
    
    stats = {
        'pending': pending_sessions.count(),
        'confirmed_today': SessionLog.objects.filter(
            status='confirmed',
            confirmed_at__date=date.today()
        ).count(),
        'rejected_today': SessionLog.objects.filter(
            status='rejected',
            created_at__date=date.today()
        ).count(),
    }
    
    context = {
        'pending_sessions': pending_sessions,
        'confirmed_sessions': confirmed_sessions,
        'rejected_sessions': rejected_sessions,
        'stats': stats,
    }
    
    return render(request, 'instructor/admin_panel.html', context)