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
from dashboard .models import SchoolSettings




@login_required
@role_required(['ADMIN'])
def teacher_list(request):
    settings_obj = SchoolSettings.objects.first()

    teachers = Teacher.objects.all()
    return render(request, 'teachers/teacher_list.html', {'teachers': teachers, 'school_settings': settings_obj,
})



# @login_required
# @role_required(['ADMIN'])
# def add_teacher(request):

#     if request.method == 'POST':
#         email = request.POST['email']

#         # 🔴 CHECK KAMA TEACHER EMAIL IPO
#         if Teacher.objects.filter(email=email).exists():
#             messages.error(request, "Teacher with this email already exists.")
#             return redirect('add_teacher')

#         teacher = Teacher.objects.create(
#             first_name=request.POST['first_name'],
#             last_name=request.POST['last_name'],
#             email=email,
#             phone=request.POST['phone']
#         )
# #William@123
#         # 🔐 CREATE LOGIN ACCOUNT
#         password = f"{teacher.first_name}@123"
#         User.objects.create_user(
#             username=teacher.email,
#             email=teacher.email,
#             password=password,
#             role='TEACHER'
#         )

#         messages.success(
#             request,
#             f"Teacher added successfully. Login password: {password}"
#         )

#         return redirect('teacher_list')

#         context = {
#         'school_settings': settings_obj,
#     }

#     return render(request, 'teachers/add_teacher.html')


# teachers/views.py
from django.contrib import messages
from django.contrib.auth import get_user_model
from .utils import send_teacher_credentials  # Import the function
from accounts.decorators import role_required

User = get_user_model()

@login_required
@role_required(['ADMIN'])
def add_teacher(request):
    settings_obj = SchoolSettings.objects.first()
    
    if request.method == 'POST':
        email = request.POST['email']
        
        # 🔴 CHECK KAMA TEACHER EMAIL IPO
        if Teacher.objects.filter(email=email).exists():
            messages.error(request, "Teacher with this email already exists.")
            return redirect('add_teacher')
        
        # 🔴 CHECK KAMA USER EMAIL IPO
        if User.objects.filter(email=email).exists():
            messages.error(request, "User with this email already exists. Please use different email.")
            return redirect('add_teacher')
        
        # Create teacher
        teacher = Teacher.objects.create(
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            email=email,
            phone=request.POST['phone']
        )
        
        # Add subjects and classes if provided
        if 'subjects' in request.POST:
            teacher.subjects.set(request.POST.getlist('subjects'))
        if 'classes' in request.POST:
            teacher.classes.set(request.POST.getlist('classes'))
        
        # 🔐 CREATE LOGIN ACCOUNT with correct password format
        password = f"{teacher.first_name}@123"  # Format: firstname@123
        user = User.objects.create_user(
            username=teacher.email,
            email=teacher.email,
            password=password,
            role='TEACHER',
            first_name=teacher.first_name,
            last_name=teacher.last_name
        )
        
        # 📧 SEND CREDENTIALS VIA EMAIL
        email_sent = send_teacher_credentials(teacher, password, request)
        
        if email_sent:
            messages.success(
                request,
                f"✅ Teacher {teacher.first_name} {teacher.last_name} added successfully! "
                f"✅ Login credentials sent to {teacher.email}"
            )
        else:
            messages.warning(
                request,
                f"⚠️ Teacher added but failed to send email. "
                f"Username: {teacher.email} | Password: {password}"
            )
        
        return redirect('teacher_list')
    
    context = {
        'school_settings': settings_obj,
        'subjects': Subject.objects.all(),
        'classes': ClassRoom.objects.all()
    }
    
    return render(request, 'teachers/add_teacher.html', context)

# teachers/views.py
@login_required
@role_required(['ADMIN'])
def edit_teacher(request, id):
    settings_obj = SchoolSettings.objects.first()
    teacher = get_object_or_404(Teacher, id=id)
    
    if request.method == 'POST':
        old_email = teacher.email
        new_email = request.POST['email']
        send_new_credentials = False
        
        # Update teacher info
        teacher.first_name = request.POST['first_name']
        teacher.last_name = request.POST['last_name']
        teacher.email = new_email
        teacher.phone = request.POST['phone']
        teacher.is_available = request.POST.get('is_available') == 'on'
        teacher.save()
        
        # Update subjects and classes
        teacher.subjects.set(request.POST.getlist('subjects', []))
        teacher.classes.set(request.POST.getlist('classes', []))
        
        # Check if email changed
        if old_email != new_email:
            try:
                # Find user and update
                user = User.objects.get(email=old_email)
                user.username = new_email
                user.email = new_email
                
                # Generate new password with correct format
                new_password = f"{teacher.first_name}@123"
                user.set_password(new_password)
                user.save()
                
                # Send new credentials
                send_teacher_credentials(teacher, new_password, request)
                send_new_credentials = True
                
            except User.DoesNotExist:
                # Create new user if doesn't exist
                new_password = f"{teacher.first_name}@123"
                user = User.objects.create_user(
                    username=new_email,
                    email=new_email,
                    password=new_password,
                    role='TEACHER',
                    first_name=teacher.first_name,
                    last_name=teacher.last_name
                )
                send_teacher_credentials(teacher, new_password, request)
                send_new_credentials = True
        
        messages.success(request, f"Teacher {teacher.first_name} {teacher.last_name} updated successfully!")
        
        if send_new_credentials:
            messages.info(request, f"New credentials sent to {new_email}")
        
        return redirect('teacher_list')
    
    context = {
        'teacher': teacher,
        'school_settings': settings_obj,
        'subjects': Subject.objects.all(),
        'classes': ClassRoom.objects.all()
    }
    return render(request, 'teachers/edit_teacher.html', context)




    
@login_required
def teacher_dashboard(request):
    settings_obj = SchoolSettings.objects.first()

    teacher = Teacher.objects.get(email=request.user.email)

    context = {
        'school_settings': settings_obj,

        'teacher': teacher,
        'subjects': teacher.subjects.all(),
        'classes': teacher.classes.all(),
    }
    return render(request, 'teachers/dashboard.html', context)
