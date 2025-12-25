from django.shortcuts import render, redirect
from .models import Student
from classes.models import ClassRoom
from .utils import generate_registration_number
from django.utils import timezone
from django.contrib.auth.decorators import login_required


def student_list(request):
    return render(request, 'students/list.html', {
        'students': Student.objects.all()
    })


  # students/views.py
from .utils import create_student_user

def add_student(request):
    if request.method == 'POST':
        classroom = ClassRoom.objects.get(id=request.POST.get('classroom'))
        year = timezone.now().year
        reg = generate_registration_number(classroom.code, year)

        student = Student.objects.create(
            full_name=request.POST.get('full_name'),
            classroom=classroom,
            admission_year=year,
            registration_number=reg,
            status=request.POST.get('status')
        )

        # Create linked user
        create_student_user(student)

        return redirect('students:student_list')

    return render(request, 'students/add.html', {
        'classes': ClassRoom.objects.all()
    })


def delete_student(request, id):
    Student.objects.filter(id=id).delete()
    return redirect('students:student_list')



from django.shortcuts import render, get_object_or_404, redirect
from .models import Student


def edit_student(request, id):
    student = get_object_or_404(Student, id=id)

    if request.method == 'POST':
        student.full_name = request.POST.get('full_name')
        student.classroom = ClassRoom.objects.get(id=request.POST.get('classroom'))
        student.status = request.POST.get('status')
        student.save()
        return redirect('students:student_list')


    return render(request, 'students/edit.html', {
        'student': student,
        'classes': ClassRoom.objects.all()   # 👈 HII NDIO FIX
    })



@login_required
def student_portal(request):
    user = request.user
    student = Student.objects.get(registration_number=user.username)

    return render(request, 'students/portal.html', {
        'student': student,
        'results': student.result_set.all() if hasattr(student, 'result_set') else [],
        'attendance': student.attendance_set.all() if hasattr(student, 'attendance_set') else []
    })


# students/views.py
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep user logged in
            return redirect('students:student_portal')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'students/change_password.html', {'form': form})
