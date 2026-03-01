# exams/views.py

import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import Http404, StreamingHttpResponse
from django.conf import settings as django_settings

from .models import Exam, Result, Assignment, Submission
from students.models import Student
from classes.models import ClassRoom, Subject
from dashboard.models import SchoolSettings
from .utils import report_card_pdf


# ─────────────────────────────────────────────────────────────────
#  HELPER — Uploadcare proxy download
# ─────────────────────────────────────────────────────────────────

def _proxy_uploadcare_file(uc_file_obj):
    """
    Pakia file kutoka Uploadcare kwa kutumia keys za settings.py.
    Inajaribu njia mbili — CDN na REST API.
    """
    uploadcare_config = getattr(django_settings, 'UPLOADCARE', {})
    pub_key    = uploadcare_config.get('pub_key', '')
    secret_key = uploadcare_config.get('secret', '')

    try:
        uuid = str(uc_file_obj.uuid).strip().strip('/')
    except Exception:
        raise Http404("Invalid file reference.")

    urls_to_try = [f"https://ucarecdn.com/{uuid}/"]

    try:
        fname = uc_file_obj.filename
        if fname:
            urls_to_try.insert(0, f"https://ucarecdn.com/{uuid}/{fname}")
    except Exception:
        pass

    # Jaribu CDN URLs
    for url in urls_to_try:
        try:
            resp = requests.get(
                url,
                auth=(pub_key, secret_key),
                timeout=30,
                stream=True
            )
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', 'application/octet-stream')
                return resp, content_type
        except requests.RequestException:
            continue

    # Last resort — REST API
    try:
        api_resp = requests.get(
            f"https://api.uploadcare.com/files/{uuid}/",
            headers={
                'Authorization': f'Uploadcare.Simple {pub_key}:{secret_key}',
                'Accept': 'application/vnd.uploadcare-v0.7+json',
            },
            timeout=15
        )
        if api_resp.status_code == 200:
            file_info  = api_resp.json()
            direct_url = file_info.get('original_file_url') or file_info.get('url')
            if direct_url:
                direct_resp = requests.get(direct_url, timeout=30, stream=True)
                if direct_resp.status_code == 200:
                    content_type = direct_resp.headers.get('Content-Type', 'application/octet-stream')
                    return direct_resp, content_type
    except requests.RequestException:
        pass

    raise Http404("File not found on Uploadcare.")


def _make_streaming_response(uc_file_obj, filename):
    """Tengeneza StreamingHttpResponse kutoka Uploadcare file object."""
    resp, content_type = _proxy_uploadcare_file(uc_file_obj)
    django_resp = StreamingHttpResponse(
        resp.iter_content(chunk_size=8192),
        content_type=content_type
    )
    safe_filename = filename.replace('"', '_')
    django_resp['Content-Disposition'] = f'inline; filename="{safe_filename}"'
    return django_resp


# ─────────────────────────────────────────────────────────────────
#  EXISTING VIEWS
# ─────────────────────────────────────────────────────────────────

def exam_list(request):
    settings_obj = SchoolSettings.objects.first()
    today        = timezone.now().date()
    next_week    = today + timezone.timedelta(days=7)

    exams = Exam.objects.all().order_by('-date')

    assignments_qs     = Assignment.objects.select_related('classroom', 'subject').all()
    total_assignments  = assignments_qs.count()
    open_assignments   = assignments_qs.filter(status='PUBLISHED', due_date__gte=timezone.now()).count()
    recent_submissions = Submission.objects.filter(
        submitted_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    assignments_recent = assignments_qs.order_by('-created_at')[:5]

    return render(request, 'exams/exam_list.html', {
        'exams':               exams,
        'school_settings':     settings_obj,
        'today':               today,
        'next_week':           next_week,
        'total_assignments':   total_assignments,
        'open_assignments':    open_assignments,
        'recent_submissions':  recent_submissions,
        'assignments_recent':  assignments_recent,
    })


@login_required
def create_exam(request):
    settings_obj = SchoolSettings.objects.first()

    if request.method == 'POST':
        try:
            name             = request.POST.get('name')
            subject_name     = request.POST.get('subject')
            exam_date        = request.POST.get('exam_date')
            exam_type        = request.POST.get('exam_type', 'MONTHLY')
            selected_classes = request.POST.getlist('classes')

            if not name:
                messages.error(request, "Exam name is required")
                return redirect('exams:create_exam')
            if not subject_name or subject_name == "-- Select Subject --":
                messages.error(request, "Please select a subject")
                return redirect('exams:create_exam')
            if not selected_classes:
                messages.error(request, "Please select at least one class")
                return redirect('exams:create_exam')
            if not exam_date:
                messages.error(request, "Exam date is required")
                return redirect('exams:create_exam')

            try:
                subject = Subject.objects.get(name=subject_name)
            except Subject.MultipleObjectsReturned:
                subjects = Subject.objects.filter(name=subject_name)
                subject  = subjects.first()
                subjects.exclude(id=subject.id).delete()
                messages.warning(request, f"Found duplicate subjects. Cleaned up '{subject_name}'.")
            except Subject.DoesNotExist:
                subject = Subject.objects.create(
                    name=subject_name,
                    code=subject_name[:3].upper()
                )

            exams_created = 0
            for class_id in selected_classes:
                try:
                    if class_id == "all":
                        for classroom in ClassRoom.objects.all():
                            _, created = Exam.objects.get_or_create(
                                name=name, classroom=classroom,
                                subject=subject, date=exam_date,
                                defaults={'exam_type': exam_type}
                            )
                            if created:
                                exams_created += 1
                    else:
                        classroom = ClassRoom.objects.get(id=class_id)
                        _, created = Exam.objects.get_or_create(
                            name=name, classroom=classroom,
                            subject=subject, date=exam_date,
                            defaults={'exam_type': exam_type}
                        )
                        if created:
                            exams_created += 1
                except ClassRoom.DoesNotExist:
                    messages.warning(request, f"Class with ID {class_id} not found")
                except Exception as e:
                    messages.warning(request, f"Error creating exam: {str(e)}")

            if exams_created > 0:
                messages.success(request, f"Successfully created {exams_created} exam(s)!")
                return redirect('exams:exam_list')
            else:
                messages.info(request, "No new exams were created. They might already exist.")

        except Exception as e:
            messages.error(request, f"Error creating exam: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Exam creation error: {e}", exc_info=True)

    context = {
        'school_settings': settings_obj,
        'classes':    ClassRoom.objects.all().order_by('name'),
        'subjects':   Subject.objects.all().order_by('name'),
        'exam_types': Exam.EXAM_TYPE_CHOICES,
        'today':      timezone.now().date().isoformat(),
    }
    return render(request, 'exams/create_exam.html', context)


def enter_marks(request, exam_id):
    settings_obj = SchoolSettings.objects.first()
    exam     = get_object_or_404(Exam, id=exam_id)
    students = Student.objects.filter(classroom=exam.classroom)
    subjects = Subject.objects.filter(classroom=exam.classroom)

    if request.method == 'POST':
        for student in students:
            for subject in subjects:
                key   = f"marks_{student.id}_{subject.id}"
                marks = request.POST.get(key)
                if marks not in [None, '']:
                    Result.objects.update_or_create(
                        student=student, exam=exam, subject=subject,
                        defaults={'marks': int(marks)}
                    )
        messages.success(request, "Marks saved successfully")
        return redirect('exams:exam_list')

    results    = Result.objects.filter(exam=exam)
    marks_dict = {f"{r.student_id}_{r.subject_id}": r.marks for r in results}

    return render(request, 'exams/enter_marks.html', {
        'exam': exam, 'students': students,
        'subjects': subjects, 'marks_dict': marks_dict,
        'school_settings': settings_obj,
    })


def student_report_card(request, student_id):
    settings_obj = SchoolSettings.objects.first()
    student = get_object_or_404(Student, id=student_id)
    return report_card_pdf(student)


def exam_results(request, exam_id):
    settings_obj = SchoolSettings.objects.first()
    exam     = get_object_or_404(Exam, id=exam_id)
    students = Student.objects.filter(classroom=exam.classroom)
    subjects = exam.classroom.subject_set.all()

    results_dict = {}
    for student in students:
        student_results = {}
        total = count = 0
        result = None
        for subject in subjects:
            result = Result.objects.filter(
                student=student, exam=exam, subject=subject
            ).first()
            marks = result.marks if result else None
            student_results[subject.name] = marks
            if marks is not None:
                total += marks
                count += 1
        average = round(total / count, 2) if count else 0
        grade   = result.grade()[0] if count else '-'
        student_results.update({'total': total, 'average': average, 'grade': grade})
        results_dict[student.id] = student_results

    return render(request, 'exams/exam_results.html', {
        'exam': exam, 'students': students,
        'subjects': subjects, 'results_dict': results_dict,
        'school_settings': settings_obj,
    })


# ─────────────────────────────────────────────────────────────────
#  ASSIGNMENT VIEWS — ADMIN/TEACHER
# ─────────────────────────────────────────────────────────────────

@login_required
def assignment_list(request):
    settings_obj = SchoolSettings.objects.first()
    assignments  = Assignment.objects.select_related('classroom', 'subject').all()

    class_filter = request.GET.get('classroom', '')
    if class_filter:
        assignments = assignments.filter(classroom__id=class_filter)

    return render(request, 'exams/assignment_list.html', {
        'assignments':     assignments,
        'classes':         ClassRoom.objects.all(),
        'class_filter':    class_filter,
        'school_settings': settings_obj,
    })


@login_required
def create_assignment(request):
    settings_obj = SchoolSettings.objects.first()

    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        classroom_id = request.POST.get('classroom')
        subject_id   = request.POST.get('subject')
        due_date     = request.POST.get('due_date')
        status       = request.POST.get('status', 'PUBLISHED')
        uc_file      = request.POST.get('file')

        if not all([title, classroom_id, due_date]):
            messages.error(request, "Title, Class, and Due Date are required.")
        else:
            try:
                classroom  = ClassRoom.objects.get(id=classroom_id)
                subject    = Subject.objects.get(id=subject_id) if subject_id else None
                assignment = Assignment(
                    title=title, description=description,
                    classroom=classroom, subject=subject,
                    due_date=due_date, status=status,
                    created_by=request.user
                )
                if uc_file:
                    assignment.file = uc_file
                assignment.save()
                messages.success(request, f"Assignment '{title}' created successfully!")
                return redirect('exams:assignment_list')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    return render(request, 'exams/create_assignment.html', {
        'classes':         ClassRoom.objects.all().order_by('name'),
        'subjects':        Subject.objects.all().order_by('name'),
        'school_settings': settings_obj,
        'min_datetime':    timezone.now().strftime('%Y-%m-%dT%H:%M'),
    })


@login_required
def assignment_submissions(request, assignment_id):
    settings_obj = SchoolSettings.objects.first()
    assignment   = get_object_or_404(Assignment, id=assignment_id)
    submissions  = assignment.submissions.select_related('student').order_by('submitted_at')

    if request.method == 'POST':
        sub_id   = request.POST.get('submission_id')
        marks    = request.POST.get('marks')
        feedback = request.POST.get('feedback', '')
        status   = request.POST.get('status', 'GRADED')
        try:
            sub           = Submission.objects.get(id=sub_id, assignment=assignment)
            sub.marks     = int(marks) if marks else None
            sub.feedback  = feedback
            sub.status    = status
            sub.graded_by = request.user
            sub.graded_at = timezone.now()
            sub.save()
            messages.success(request, f"Graded {sub.student.full_name} successfully.")
        except Submission.DoesNotExist:
            messages.error(request, "Submission not found.")
        return redirect('exams:assignment_submissions', assignment_id=assignment_id)

    return render(request, 'exams/assignment_submissions.html', {
        'assignment':      assignment,
        'submissions':     submissions,
        'school_settings': settings_obj,
    })


# ─────────────────────────────────────────────────────────────────
#  ASSIGNMENT VIEWS — STUDENT
# ─────────────────────────────────────────────────────────────────

@login_required
def my_assignments(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('dashboard')

    if not student.classroom:
        messages.warning(request, "You are not assigned to any class.")
        return redirect('students:student_portal')

    now         = timezone.now()
    assignments = Assignment.objects.filter(
        classroom=student.classroom,
        status='PUBLISHED'
    ).order_by('due_date')

    submitted_ids = list(
        Submission.objects.filter(student=student)
        .values_list('assignment_id', flat=True)
    )

    return render(request, 'exams/my_assignments.html', {
        'student':            student,
        'open_assignments':   assignments.filter(due_date__gte=now),
        'closed_assignments': assignments.filter(due_date__lt=now),
        'submitted_ids':      submitted_ids,
        'school_settings':    SchoolSettings.objects.first(),
    })


@login_required
def submit_assignment(request, assignment_id):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        raise Http404

    assignment = get_object_or_404(
        Assignment,
        id=assignment_id,
        classroom=student.classroom,
        status='PUBLISHED'
    )

    existing = Submission.objects.filter(
        assignment=assignment, student=student
    ).first()

    if request.method == 'POST':
        if existing:
            messages.warning(request, "You have already submitted this assignment.")
            return redirect('exams:my_assignments')

        uc_file = request.POST.get('file')
        comment = request.POST.get('comment', '').strip()

        if not uc_file:
            messages.error(request, "Please upload your file before submitting.")
        else:
            is_late = timezone.now() > assignment.due_date
            sub     = Submission(
                assignment=assignment, student=student,
                comment=comment,
                status='LATE' if is_late else 'SUBMITTED',
            )
            sub.file = uc_file
            sub.save()
            if is_late:
                messages.warning(request, "Submitted successfully, but it was LATE.")
            else:
                messages.success(request, "Assignment submitted successfully! 🎉")
            return redirect('exams:my_assignments')

    return render(request, 'exams/submit_assignment.html', {
        'assignment':      assignment,
        'submission':      existing,
        'school_settings': SchoolSettings.objects.first(),
        'student':         student,
    })


# ─────────────────────────────────────────────────────────────────
#  DOWNLOAD VIEWS — proxy, hakuna CDN redirect
# ─────────────────────────────────────────────────────────────────

@login_required
def download_assignment_file(request, assignment_id):
    """Student download assignment file kupitia proxy."""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        raise Http404

    assignment = get_object_or_404(
        Assignment,
        id=assignment_id,
        classroom=student.classroom,
        status='PUBLISHED'
    )

    if not assignment.file:
        messages.error(request, "No file attached to this assignment.")
        return redirect('exams:my_assignments')

    try:
        filename = f"Assignment_{assignment.title.replace(' ', '_')}.pdf"
        return _make_streaming_response(assignment.file, filename)
    except Http404:
        messages.error(request, "File could not be retrieved. Please contact your teacher.")
        return redirect('exams:my_assignments')


@login_required
def download_submission_file(request, submission_id):
    """Teacher/Admin download submission ya mwanafunzi kupitia proxy."""
    submission = get_object_or_404(Submission, id=submission_id)

    if not submission.file:
        raise Http404("No file for this submission.")

    try:
        name     = submission.student.full_name.replace(' ', '_')
        filename = f"Submission_{name}.pdf"
        return _make_streaming_response(submission.file, filename)
    except Http404:
        messages.error(request, "Submission file could not be retrieved.")
        return redirect('exams:assignment_submissions', assignment_id=submission.assignment.id)