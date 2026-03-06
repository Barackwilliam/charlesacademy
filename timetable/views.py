from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json

from .models import TimetableEntry, DAYS
from classes.models import ClassRoom as Classroom


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_grid(entries):
    """
    Returns (time_slots, grid) where:
      time_slots = sorted list of 'HH:MM – HH:MM' strings
      grid       = { time_label: { 'MON': entry|None, 'TUE': ... } }
    """
    day_keys = [d[0] for d in DAYS]
    slots    = {}

    for e in entries:
        label = e.time_label
        if label not in slots:
            slots[label] = {d: None for d in day_keys}
            slots[label]['_sort'] = e.start_time
        slots[label][e.day] = e

    time_slots = sorted(slots.keys(), key=lambda l: slots[l]['_sort'])
    return time_slots, slots


# ── Student view ──────────────────────────────────────────────────────────────

@login_required
def student_timetable(request):
    try:
        from students.models import Student
        student   = Student.objects.get(user=request.user)
        classroom = student.classroom
    except Exception:
        messages.warning(request, "No class assigned to your account yet.")
        return redirect('students:student_portal')

    entries          = TimetableEntry.objects.filter(classroom=classroom)\
                                              .select_related('subject', 'teacher')
    time_slots, grid = _build_grid(entries)

    return render(request, 'timetable/student_timetable.html', {
        'classroom':  classroom,
        'time_slots': time_slots,
        'grid':       grid,
        'days':       DAYS,
    })


# ── Admin views ───────────────────────────────────────────────────────────────

@login_required
def admin_timetable(request):
    if not request.user.is_staff:
        return redirect('/')

    classrooms  = Classroom.objects.all().order_by('name')
    selected_id = request.GET.get('classroom')
    selected    = None
    time_slots  = []
    grid        = {}

    if selected_id:
        selected = get_object_or_404(Classroom, pk=selected_id)
    elif classrooms.exists():
        selected = classrooms.first()

    if selected:
        entries          = TimetableEntry.objects.filter(classroom=selected)\
                                                  .select_related('subject', 'teacher')
        time_slots, grid = _build_grid(entries)

    from classes.models import Subject
    from teachers.models import Teacher

    subjects = Subject.objects.all().order_by('name')
    teachers = Teacher.objects.all().order_by('first_name', 'last_name')

    return render(request, 'timetable/admin_timetable.html', {
        'classrooms': classrooms,
        'selected':   selected,
        'time_slots': time_slots,
        'grid':       grid,
        'days':       DAYS,
        'subjects':   subjects,
        'teachers':   teachers,
    })


@login_required
@csrf_exempt
def admin_save_entry(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data         = json.loads(request.body)
    entry_id     = data.get('id')
    classroom_id = data.get('classroom_id')
    subject_id   = data.get('subject_id')
    teacher_id   = data.get('teacher_id') or None
    day          = data.get('day')
    start_time   = data.get('start_time')
    end_time     = data.get('end_time')
    room         = data.get('room', '')

    try:
        classroom = Classroom.objects.get(pk=classroom_id)
        from classes.models import Subject
        subject   = Subject.objects.get(pk=subject_id)
        teacher   = None
        if teacher_id:
            from teachers.models import Teacher
            teacher = Teacher.objects.get(pk=teacher_id)

        if entry_id:
            entry = TimetableEntry.objects.get(pk=entry_id)
            entry.subject    = subject
            entry.teacher    = teacher
            entry.day        = day
            entry.start_time = start_time
            entry.end_time   = end_time
            entry.room       = room
            entry.save()
            action = 'updated'
        else:
            # Check for duplicate before creating
            existing = TimetableEntry.objects.filter(
                classroom=classroom, day=day, start_time=start_time
            ).first()
            if existing:
                return JsonResponse({
                    'error': f'Slot {start_time} on {day} already has "{existing.subject}" assigned. Edit it instead.'
                }, status=400)

            entry = TimetableEntry.objects.create(
                classroom=classroom, subject=subject, teacher=teacher,
                day=day, start_time=start_time, end_time=end_time, room=room
            )
            action = 'created'

        return JsonResponse({
            'ok': True, 'action': action, 'id': entry.id,
            'subject': str(subject),
            'teacher': str(teacher) if teacher else '',
            'time':    entry.time_label,
            'room':    entry.room,
            'colour':  entry.colour,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def admin_delete_entry(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    TimetableEntry.objects.filter(pk=data.get('id')).delete()
    return JsonResponse({'ok': True})


@login_required
def get_entry(request, entry_id):
    """Return entry data as JSON for the edit modal."""
    entry = get_object_or_404(TimetableEntry, pk=entry_id)

    # Handle both time object and string
    start = entry.start_time
    end   = entry.end_time

    return JsonResponse({
        'id':         entry.id,
        'subject_id': entry.subject_id,
        'teacher_id': entry.teacher_id or '',
        'day':        entry.day,
        'start_time': start.strftime('%H:%M') if hasattr(start, 'strftime') else str(start)[:5],
        'end_time':   end.strftime('%H:%M') if hasattr(end, 'strftime') else str(end)[:5],
        'room':       entry.room,
    })