
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages

from students.models import Student
from teachers.models import Teacher
from .models import StudentAttendance, TeacherAttendance



def attendance_list(request):
    attendances = StudentAttendance.objects.all()
    return render(request, 'attendance/attendance_list.html', {'attendances': attendances})

def mark_student_attendance(request):
    students = Student.objects.all()
    today = timezone.now().date()

    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'student_{student.id}')
            if status:
                StudentAttendance.objects.update_or_create(
                    student=student,
                    date=today,
                    defaults={'status': status}
                )
        messages.success(request, "Student attendance saved successfully")
        return redirect('attendance:student_attendance_list')

    return render(request, 'attendance/mark_student_attendance.html', {
        'students': students,
        'today': today
    })



def mark_teacher_attendance(request):
    teachers = Teacher.objects.all()
    today = timezone.now().date()

    if request.method == 'POST':
        for teacher in teachers:
            status = request.POST.get(f'teacher_{teacher.id}')
            if status:
                TeacherAttendance.objects.update_or_create(
                    teacher=teacher,
                    date=today,
                    defaults={'status': status}
                )
        messages.success(request, "Teacher attendance saved successfully")
        return redirect('attendance:teacher_attendance_list')

    return render(request, 'attendance/mark_teacher_attendance.html', {
        'teachers': teachers,
        'today': today
    })




def student_attendance_list(request):
    records = StudentAttendance.objects.select_related('student').order_by('-date')
    return render(request, 'attendance/student_attendance_list.html', {'records': records})


def teacher_attendance_list(request):
    records = TeacherAttendance.objects.select_related('teacher').order_by('-date')
    return render(request, 'attendance/teacher_attendance_list.html', {'records': records})



def monthly_student_report(request):
    month = request.GET.get('month')
    records = StudentAttendance.objects.all()

    if month:
        records = records.filter(date__month=month)

    return render(request, 'attendance/monthly_report.html', {
        'records': records,
        'month': month
    })


from django.contrib.auth.decorators import login_required
from .models import StudentAttendance
from students.models import Student

@login_required
def my_attendance(request):
    try:
        student = request.user.student
        records = StudentAttendance.objects.filter(student=student).order_by('-date')
    except Student.DoesNotExist:
        records = []

    return render(request, 'attendance/my_attendance.html', {'records': records})