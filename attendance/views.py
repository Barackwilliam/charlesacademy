# attendance/views.py
import datetime
import json

from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from dashboard.models import SchoolSettings
from students.models import Student
from teachers.models import Teacher
from classes.models import ClassRoom, Subject
from .models import StudentAttendance, TeacherAttendance


# ──────────────────────────────────────────────────────────────────
# ADMIN — mark student attendance
# ──────────────────────────────────────────────────────────────────

@login_required
def mark_student_attendance(request):
    today = datetime.date.today()

    selected_class   = request.GET.get('class_id', '')
    selected_subject = request.GET.get('subject_id', '')
    selected_date    = request.GET.get('date', str(today))
    search_query     = request.GET.get('search', '')

    try:
        attendance_date = datetime.date.fromisoformat(selected_date)
    except (ValueError, TypeError):
        attendance_date = today

    # Students queryset
    students_qs = Student.objects.all().select_related('classroom')
    if selected_class:
        students_qs = students_qs.filter(classroom__id=selected_class)
    if search_query:
        students_qs = students_qs.filter(
            Q(full_name__icontains=search_query) |
            Q(registration_number__icontains=search_query)
        )

    # Subject object
    subject_obj = None
    if selected_subject:
        try:
            subject_obj = Subject.objects.get(id=selected_subject)
        except Subject.DoesNotExist:
            pass

    # POST — save
    if request.method == 'POST':
        saved_class   = request.POST.get('class_id', '')
        saved_subject = request.POST.get('subject_id', '')
        saved_date    = request.POST.get('attendance_date', str(today))
        saved_search  = request.POST.get('search', '')

        try:
            save_date = datetime.date.fromisoformat(saved_date)
        except (ValueError, TypeError):
            save_date = today

        save_subject_obj = None
        if saved_subject:
            try:
                save_subject_obj = Subject.objects.get(id=saved_subject)
            except Subject.DoesNotExist:
                pass

        save_students = Student.objects.all()
        if saved_class:
            save_students = save_students.filter(classroom__id=saved_class)
        if saved_search:
            save_students = save_students.filter(
                Q(full_name__icontains=saved_search) |
                Q(registration_number__icontains=saved_search)
            )

        count = 0
        for student in save_students:
            status = request.POST.get(f'student_{student.id}')
            if status in ('PRESENT', 'ABSENT', 'LATE'):
                StudentAttendance.objects.update_or_create(
                    student=student,
                    date=save_date,
                    subject=save_subject_obj,
                    defaults={'status': status}
                )
                count += 1

        messages.success(request, f"Attendance saved for {save_date.strftime('%B %d, %Y')} — {count} record(s) ✓")
        return redirect(
            f"{request.path}?class_id={saved_class}&subject_id={saved_subject}&date={saved_date}&search={saved_search}"
        )

    # Build existing attendance as JSON for JS pre-fill
    existing_json = '{}'
    if students_qs.exists():
        em = {
            str(r.student_id): r.status
            for r in StudentAttendance.objects.filter(
                student__in=students_qs,
                date=attendance_date,
                subject=subject_obj
            )
        }
        existing_json = json.dumps(em)

    # Subjects dropdown
    if selected_class:
        subjects = Subject.objects.filter(classroom__id=selected_class)
    else:
        subjects = Subject.objects.all().select_related('classroom')

    context = {
        'students': students_qs,
        'today': attendance_date,
        'classes': ClassRoom.objects.all(),
        'subjects': subjects,
        'selected_class': selected_class,
        'selected_subject': selected_subject,
        'selected_date': str(attendance_date),
        'search_query': search_query,
        'existing_json': existing_json,
        'subject_obj': subject_obj,
        'is_teacher_view': False,
    }
    return render(request, 'attendance/mark_student_attendance.html', context)


# ──────────────────────────────────────────────────────────────────
# TEACHER — mark attendance (own classes only)
# ──────────────────────────────────────────────────────────────────

@login_required
def teacher_mark_attendance(request):
    try:
        teacher = Teacher.objects.get(email__iexact=request.user.email)
    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect('teacher_dashboard')

    assigned_classes  = teacher.classes.all()
    assigned_subjects = teacher.subjects.all()
    today = datetime.date.today()

    selected_class   = request.GET.get('class_id', '')
    selected_subject = request.GET.get('subject_id', '')
    selected_date    = request.GET.get('date', str(today))
    search_query     = request.GET.get('search', '')

    try:
        attendance_date = datetime.date.fromisoformat(selected_date)
    except (ValueError, TypeError):
        attendance_date = today

    students_qs = Student.objects.none()
    if selected_class:
        if assigned_classes.filter(id=selected_class).exists():
            students_qs = Student.objects.filter(
                classroom__id=selected_class
            ).select_related('classroom')
            if search_query:
                students_qs = students_qs.filter(
                    Q(full_name__icontains=search_query) |
                    Q(registration_number__icontains=search_query)
                )

    subject_obj = None
    if selected_subject:
        try:
            subject_obj = Subject.objects.get(id=selected_subject)
        except Subject.DoesNotExist:
            pass

    if request.method == 'POST':
        saved_class   = request.POST.get('class_id', '')
        saved_subject = request.POST.get('subject_id', '')
        saved_date    = request.POST.get('attendance_date', str(today))
        saved_search  = request.POST.get('search', '')

        if not assigned_classes.filter(id=saved_class).exists():
            messages.error(request, "You can only mark attendance for your assigned classes.")
            return redirect('attendance:teacher_mark_attendance')

        try:
            save_date = datetime.date.fromisoformat(saved_date)
        except (ValueError, TypeError):
            save_date = today

        save_subject_obj = None
        if saved_subject:
            try:
                save_subject_obj = Subject.objects.get(id=saved_subject)
            except Subject.DoesNotExist:
                pass

        save_students = Student.objects.filter(classroom__id=saved_class)
        if saved_search:
            save_students = save_students.filter(
                Q(full_name__icontains=saved_search) |
                Q(registration_number__icontains=saved_search)
            )

        count = 0
        for student in save_students:
            status = request.POST.get(f'student_{student.id}')
            if status in ('PRESENT', 'ABSENT', 'LATE'):
                StudentAttendance.objects.update_or_create(
                    student=student,
                    date=save_date,
                    subject=save_subject_obj,
                    defaults={'status': status}
                )
                count += 1

        messages.success(request, f"Attendance saved — {count} record(s) ✓")
        return redirect(
            f"{request.path}?class_id={saved_class}&subject_id={saved_subject}&date={saved_date}&search={saved_search}"
        )

    # Existing attendance as JSON
    existing_json = '{}'
    if students_qs.exists():
        em = {
            str(r.student_id): r.status
            for r in StudentAttendance.objects.filter(
                student__in=students_qs,
                date=attendance_date,
                subject=subject_obj
            )
        }
        existing_json = json.dumps(em)

    # Subjects: only teacher's subjects for selected class
    if selected_class:
        subjects = assigned_subjects.filter(classroom__id=selected_class)
    else:
        subjects = assigned_subjects

    context = {
        'teacher': teacher,
        'students': students_qs,
        'today': attendance_date,
        'classes': assigned_classes,
        'subjects': subjects,
        'selected_class': selected_class,
        'selected_subject': selected_subject,
        'selected_date': str(attendance_date),
        'search_query': search_query,
        'existing_json': existing_json,
        'subject_obj': subject_obj,
        'is_teacher_view': True,
    }
    return render(request, 'attendance/mark_student_attendance.html', context)


# ──────────────────────────────────────────────────────────────────
# ADMIN — mark teacher attendance
# ──────────────────────────────────────────────────────────────────

@login_required
def mark_teacher_attendance(request):
    teachers = Teacher.objects.all()
    today = datetime.date.today()

    if request.method == 'POST':
        count = 0
        for teacher in teachers:
            status = request.POST.get(f'teacher_{teacher.id}')
            if status in ('PRESENT', 'ABSENT', 'LATE'):
                TeacherAttendance.objects.update_or_create(
                    teacher=teacher,
                    date=today,
                    defaults={'status': status}
                )
                count += 1
        messages.success(request, f"Teacher attendance saved — {count} record(s) ✓")
        return redirect('attendance:teacher_attendance_list')

    # Pre-fill existing
    existing_today = {
        str(ta.teacher_id): ta.status
        for ta in TeacherAttendance.objects.filter(date=today)
    }

    return render(request, 'attendance/mark_teacher_attendance.html', {
        'teachers': teachers,
        'today': today,
        'existing_json': json.dumps(existing_today),
    })


# ──────────────────────────────────────────────────────────────────
# List views
# ──────────────────────────────────────────────────────────────────

@login_required
def attendance_list(request):
    attendances = StudentAttendance.objects.select_related('student', 'subject').all()
    return render(request, 'attendance/attendance_list.html', {'attendances': attendances})


@login_required
def student_attendance_list(request):
    records = StudentAttendance.objects.select_related(
        'student', 'subject', 'student__classroom'
    ).order_by('-date')
    return render(request, 'attendance/student_attendance_list.html', {'records': records})


@login_required
def teacher_attendance_list(request):
    records = TeacherAttendance.objects.select_related('teacher').order_by('-date')
    return render(request, 'attendance/teacher_attendance_list.html', {'records': records})


@login_required
def monthly_student_report(request):
    month = request.GET.get('month')
    records = StudentAttendance.objects.select_related('student', 'subject').all()
    if month:
        records = records.filter(date__month=month)
    return render(request, 'attendance/monthly_report.html', {
        'records': records, 'month': month
    })


@login_required
def my_attendance(request):
    try:
        student = request.user.student_profile
        records = StudentAttendance.objects.filter(
            student=student
        ).select_related('subject').order_by('-date')
    except Exception:
        records = []
    return render(request, 'attendance/my_attendance.html', {'records': records})
