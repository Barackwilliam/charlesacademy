# teachers/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Teacher
from classes.models import Subject
from classes.models import ClassRoom
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib import messages



@login_required
@role_required(['ADMIN'])
def teacher_list(request):
    teachers = Teacher.objects.all()
    return render(request, 'teachers/teacher_list.html', {'teachers': teachers})



@login_required
@role_required(['ADMIN'])
def add_teacher(request):
    if request.method == 'POST':
        email = request.POST['email']

        # 🔴 CHECK KAMA TEACHER EMAIL IPO
        if Teacher.objects.filter(email=email).exists():
            messages.error(request, "Teacher with this email already exists.")
            return redirect('add_teacher')

        teacher = Teacher.objects.create(
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            email=email,
            phone=request.POST['phone']
        )
#William@123
        # 🔐 CREATE LOGIN ACCOUNT
        password = f"{teacher.first_name}@123"
        User.objects.create_user(
            username=teacher.email,
            email=teacher.email,
            password=password,
            role='TEACHER'
        )

        messages.success(
            request,
            f"Teacher added successfully. Login password: {password}"
        )

        return redirect('teacher_list')

    return render(request, 'teachers/add_teacher.html')



@login_required
@role_required(['ADMIN'])
def edit_teacher(request, id):
    teacher = get_object_or_404(Teacher, id=id)

    if request.method == 'POST':
        teacher.first_name = request.POST['first_name']
        teacher.last_name = request.POST['last_name']
        teacher.email = request.POST['email']
        teacher.phone = request.POST['phone']
        teacher.is_available = request.POST.get('is_available') == 'on'
        teacher.save()

        teacher.subjects.set(request.POST.getlist('subjects'))
        teacher.classes.set(request.POST.getlist('classes'))

        return redirect('teacher_list')

    context = {
        'teacher': teacher,
        'subjects': Subject.objects.all(),
        'classes': ClassRoom.objects.all()
    }
    return render(request, 'teachers/edit_teacher.html', context)


@login_required
def teacher_dashboard(request):
    teacher = Teacher.objects.get(email=request.user.email)

    context = {
        'teacher': teacher,
        'subjects': teacher.subjects.all(),
        'classes': teacher.classes.all(),
    }
    return render(request, 'teachers/dashboard.html', context)
