# students/utils.py - Complete file
from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from .models import Student

def generate_registration_number(class_code, year):
    last_student = Student.objects.filter(
        classroom__code=class_code,
        admission_year=year
    ).count() + 1

    return f"CA/{class_code}/{year}/{str(last_student).zfill(4)}"

def create_student_user(student):
    # Get first name for password
    first_name_parts = student.full_name.split()
    if first_name_parts:
        first_name = first_name_parts[0].lower()
    else:
        first_name = "student"
    
    # Create password: firstname + @123
    password = f"{first_name}@123"
    
    # Create user with student's registration number as username
    user = User.objects.create_user(
        username=student.registration_number,
        password=password,
        role='STUDENT',
        email=student.email,
        first_name=student.full_name.split()[0] if student.full_name.split() else '',
        last_name=' '.join(student.full_name.split()[1:]) if len(student.full_name.split()) > 1 else ''
    )
    
    # Link user to student
    student.user = user
    student.save()
    
    return user

def send_student_credentials(student, user, request=None):
    """
    Send login credentials to student's email
    """
    try:
        # Generate password
        first_name_parts = student.full_name.split()
        if first_name_parts:
            first_name = first_name_parts[0].lower()
        else:
            first_name = "student"
        password = f"{first_name}@123"
        
        # Get login URL
        if request:
            login_url = request.build_absolute_uri(reverse('login'))
        else:
            login_url = "http://127.0.0.1:8000/login/"
        
        # Prepare email content
        subject = f"Your Student Portal Login Credentials - {student.registration_number}"
        
        # Create context for email template
        context = {
            'student': student,
            'username': student.registration_number,
            'password': password,
            'first_name': first_name.capitalize(),
            'school_name': "Charles Academy",
            'portal_url': login_url,
        }
        
        # Render HTML email template
        html_message = render_to_string('students/emails/credentials_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email='info.charlesacademy@gmail.com',
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=True,  # Change to False in production
        )
        
        print(f"Credentials email sent to {student.email}")
        return True
    except Exception as e:
        print(f"Failed to send credentials email: {e}")
        return False