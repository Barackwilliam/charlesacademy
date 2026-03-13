# teachers/views.py
import datetime
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import Teacher
from .utils import send_teacher_credentials
from accounts.decorators import role_required
from classes.models import Subject, ClassRoom
from dashboard.models import SchoolSettings
from students.models import Student
from exams.models import Exam, Result
from attendance.models import StudentAttendance

User = get_user_model()


# ──────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────

def _get_teacher(request):
    """Return Teacher for the logged-in user, or None."""
    try:
        return Teacher.objects.get(email__iexact=request.user.email)
    except Teacher.DoesNotExist:
        return None


# ──────────────────────────────────────────────────────────────────
# ADMIN — list teachers
# ──────────────────────────────────────────────────────────────────

@login_required
@role_required(['ADMIN'])
def teacher_list(request):
    settings_obj = SchoolSettings.objects.first()
    teachers = Teacher.objects.prefetch_related('classes', 'subjects').all()
    return render(request, 'teachers/teacher_list.html', {
        'teachers': teachers,
        'school_settings': settings_obj,
    })


# ──────────────────────────────────────────────────────────────────
# ADMIN — add teacher
# ──────────────────────────────────────────────────────────────────

@login_required
@role_required(['ADMIN'])
def add_teacher(request):
    settings_obj = SchoolSettings.objects.first()
    classes  = ClassRoom.objects.all()
    subjects = Subject.objects.select_related('classroom').all()

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        phone      = request.POST.get('phone', '').strip()

        if not all([email, first_name, last_name, phone]):
            messages.error(request, "All fields are required.")
            return render(request, 'teachers/add_teacher.html', {
                'classes': classes, 'subjects': subjects, 'school_settings': settings_obj,
            })

        if Teacher.objects.filter(email__iexact=email).exists():
            messages.error(request, "A teacher with this email already exists.")
            return render(request, 'teachers/add_teacher.html', {
                'classes': classes, 'subjects': subjects, 'school_settings': settings_obj,
            })

        if User.objects.filter(username__iexact=email).exists():
            messages.error(request, "A user account with this email already exists.")
            return render(request, 'teachers/add_teacher.html', {
                'classes': classes, 'subjects': subjects, 'school_settings': settings_obj,
            })

        # Create Teacher
        teacher = Teacher.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
        )

        # Assign classes & subjects
        selected_classes  = request.POST.getlist('classes')
        selected_subjects = request.POST.getlist('subjects')
        if selected_classes:
            teacher.classes.set(selected_classes)
        if selected_subjects:
            teacher.subjects.set(selected_subjects)

        # Create User account
        password = f"{first_name.lower()}@123"
        User.objects.create_user(
            username=email,
            email=email,
            password=password,
            role='TEACHER',
            first_name=first_name,
            last_name=last_name,
        )

        # Send credentials email
        email_sent = send_teacher_credentials(teacher, password, request)

        if email_sent:
            messages.success(request,
                f"✅ Teacher {teacher.full_name} added! Credentials sent to {email}."
            )
        else:
            messages.warning(request,
                f"⚠️ Teacher added. Email failed. "
                f"Username: {email} | Password: {password}"
            )

        return redirect('teacher_list')

    return render(request, 'teachers/add_teacher.html', {
        'classes': classes,
        'subjects': subjects,
        'school_settings': settings_obj,
    })


# ──────────────────────────────────────────────────────────────────
# ADMIN — edit teacher
# ──────────────────────────────────────────────────────────────────

@login_required
@role_required(['ADMIN'])
def edit_teacher(request, id):
    settings_obj = SchoolSettings.objects.first()
    teacher  = get_object_or_404(Teacher, id=id)
    classes  = ClassRoom.objects.all()
    subjects = Subject.objects.select_related('classroom').all()

    if request.method == 'POST':
        old_email  = teacher.email
        new_email  = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        phone      = request.POST.get('phone', '').strip()

        teacher.first_name   = first_name
        teacher.last_name    = last_name
        teacher.email        = new_email
        teacher.phone        = phone
        teacher.is_available = request.POST.get('is_available') == 'on'
        teacher.save()

        teacher.classes.set(request.POST.getlist('classes', []))
        teacher.subjects.set(request.POST.getlist('subjects', []))

        # Update user account
        try:
            user = User.objects.get(username__iexact=old_email)
            user.username   = new_email
            user.email      = new_email
            user.first_name = first_name
            user.last_name  = last_name
            if old_email != new_email:
                new_password = f"{first_name.lower()}@123"
                user.set_password(new_password)
                send_teacher_credentials(teacher, new_password, request)
            user.save()
        except User.DoesNotExist:
            # Create account if missing
            password = f"{first_name.lower()}@123"
            User.objects.create_user(
                username=new_email, email=new_email,
                password=password, role='TEACHER',
                first_name=first_name, last_name=last_name,
            )
            send_teacher_credentials(teacher, password, request)

        messages.success(request, f"Teacher {teacher.full_name} updated successfully!")
        return redirect('teacher_list')

    context = {
        'teacher': teacher,
        'classes': classes,
        'subjects': subjects,
        'school_settings': settings_obj,
        'assigned_class_ids':   list(teacher.classes.values_list('id', flat=True)),
        'assigned_subject_ids': list(teacher.subjects.values_list('id', flat=True)),
    }
    return render(request, 'teachers/edit_teacher.html', context)


# ──────────────────────────────────────────────────────────────────
# TEACHER — dashboard
# ──────────────────────────────────────────────────────────────────

@login_required
def teacher_dashboard(request):
    if request.user.role != 'TEACHER':
        return redirect('dashboard')

    settings_obj = SchoolSettings.objects.first()
    teacher = _get_teacher(request)
    if not teacher:
        messages.error(request, "Teacher profile not found. Contact admin.")
        return redirect('login')

    assigned_classes  = teacher.classes.all()
    assigned_subjects = teacher.subjects.all()
    today = datetime.date.today()

    total_students = Student.objects.filter(classroom__in=assigned_classes).count()

    today_attendance_count = StudentAttendance.objects.filter(
        student__classroom__in=assigned_classes,
        date=today
    ).count()

    recent_results = Result.objects.filter(
        exam__classroom__in=assigned_classes
    ).select_related('student', 'exam', 'subject').order_by('-id')[:8]

    upcoming_exams = Exam.objects.filter(
        classroom__in=assigned_classes,
        date__gte=today
    ).order_by('date')[:5]

    context = {
        'school_settings': settings_obj,
        'teacher': teacher,
        'assigned_classes': assigned_classes,
        'assigned_subjects': assigned_subjects,
        'total_students': total_students,
        'today_attendance_count': today_attendance_count,
        'recent_results': recent_results,
        'upcoming_exams': upcoming_exams,
    }
    return render(request, 'teachers/dashboard.html', context)


# ──────────────────────────────────────────────────────────────────
# TEACHER — register student
# ──────────────────────────────────────────────────────────────────

@login_required
def teacher_register_student(request):
    if request.user.role != 'TEACHER':
        return redirect('dashboard')

    teacher = _get_teacher(request)
    if not teacher:
        messages.error(request, "Teacher profile not found.")
        return redirect('teacher_dashboard')

    assigned_classes = teacher.classes.all()

    if request.method == 'POST':
        class_id = request.POST.get('classroom')

        if not assigned_classes.filter(id=class_id).exists():
            messages.error(request, "You can only register students into your assigned classes.")
            return redirect('teacher_register_student')

        email  = request.POST.get('email', '').strip().lower()
        reg_no = request.POST.get('registration_number', '').strip().upper()

        if Student.objects.filter(email__iexact=email).exists():
            messages.error(request, f"A student with email '{email}' already exists.")
            return redirect('teacher_register_student')

        if Student.objects.filter(registration_number__iexact=reg_no).exists():
            messages.error(request, f"Registration number '{reg_no}' is already in use.")
            return redirect('teacher_register_student')

        try:
            classroom = ClassRoom.objects.get(id=class_id)
            student = Student.objects.create(
                full_name=request.POST.get('full_name', '').strip(),
                email=email,
                registration_number=reg_no,
                classroom=classroom,
                admission_year=request.POST.get('admission_year', today_year()),
            )
            messages.success(request, f"Student '{student.full_name}' registered in {classroom.name}!")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect('teacher_register_student')

    context = {
        'teacher': teacher,
        'assigned_classes': assigned_classes,
        'current_year': today_year(),
    }
    return render(request, 'teachers/register_student.html', context)


def today_year():
    return datetime.date.today().year


# ──────────────────────────────────────────────────────────────────
# TEACHER — enter results
# ──────────────────────────────────────────────────────────────────

@login_required
def teacher_enter_results(request):
    if request.user.role != 'TEACHER':
        return redirect('dashboard')

    teacher = _get_teacher(request)
    if not teacher:
        messages.error(request, "Teacher profile not found.")
        return redirect('teacher_dashboard')

    assigned_classes  = teacher.classes.all()
    assigned_subjects = teacher.subjects.all()

    selected_class   = request.GET.get('class_id', '')
    selected_subject = request.GET.get('subject_id', '')
    selected_exam    = request.GET.get('exam_id', '')

    students = Student.objects.none()
    exams    = Exam.objects.none()
    exam_obj = subject_obj = None

    if selected_class and assigned_classes.filter(id=selected_class).exists():
        students = Student.objects.filter(classroom__id=selected_class).order_by('full_name')
        exams    = Exam.objects.filter(classroom__id=selected_class).order_by('-date')

    if selected_exam:
        try:
            exam_obj = Exam.objects.get(id=selected_exam, classroom__in=assigned_classes)
        except Exam.DoesNotExist:
            pass

    if selected_subject:
        try:
            subject_obj = Subject.objects.get(id=selected_subject)
        except Subject.DoesNotExist:
            pass

    if request.method == 'POST':
        p_class   = request.POST.get('class_id', '')
        p_exam_id = request.POST.get('exam_id', '')
        p_subj_id = request.POST.get('subject_id', '')

        if not assigned_classes.filter(id=p_class).exists():
            messages.error(request, "Invalid class.")
            return redirect('teacher_enter_results')

        try:
            p_exam = Exam.objects.get(id=p_exam_id, classroom__id=p_class)
        except Exam.DoesNotExist:
            messages.error(request, "Exam not found.")
            return redirect('teacher_enter_results')

        try:
            p_subject = Subject.objects.get(id=p_subj_id)
        except Subject.DoesNotExist:
            messages.error(request, "Subject not found.")
            return redirect('teacher_enter_results')

        saved = 0
        for student in Student.objects.filter(classroom__id=p_class):
            marks_str = request.POST.get(f'marks_{student.id}', '').strip()
            if marks_str:
                try:
                    marks = int(marks_str)
                    if 0 <= marks <= 100:
                        Result.objects.update_or_create(
                            student=student,
                            exam=p_exam,
                            subject=p_subject,
                            defaults={'marks': marks}
                        )
                        saved += 1
                except ValueError:
                    pass

        messages.success(request, f"Saved {saved} result(s) ✓")
        return redirect(
            f"{request.path}?class_id={p_class}&exam_id={p_exam_id}&subject_id={p_subj_id}"
        )

    # Build existing marks as JSON for JS pre-fill
    existing_marks_json = '{}'
    if exam_obj and subject_obj:
        em = {
            str(r.student_id): r.marks
            for r in Result.objects.filter(exam=exam_obj, subject=subject_obj)
        }
        existing_marks_json = json.dumps(em)

    context = {
        'teacher': teacher,
        'assigned_classes': assigned_classes,
        'assigned_subjects': assigned_subjects,
        'students': students,
        'exams': exams,
        'exam_obj': exam_obj,
        'subject_obj': subject_obj,
        'selected_class': selected_class,
        'selected_subject': selected_subject,
        'selected_exam': selected_exam,
        'existing_marks_json': existing_marks_json,
    }
    return render(request, 'teachers/enter_results.html', context)
