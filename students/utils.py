# # students/utils.py - Complete file
# from accounts.models import User
# from django.core.mail import send_mail
# from django.conf import settings
# from django.template.loader import render_to_string
# from django.utils.html import strip_tags
# from django.urls import reverse
# from .models import Student

# def generate_registration_number(class_code, year):
#     last_student = Student.objects.filter(
#         classroom__code=class_code,
#         admission_year=year
#     ).count() + 1

#     return f"CA/{class_code}/{year}/{str(last_student).zfill(4)}"

# def create_student_user(student):
#     # Get first name for password
#     first_name_parts = student.full_name.split()
#     if first_name_parts:
#         first_name = first_name_parts[0].lower()
#     else:
#         first_name = "student"
    
#     # Create password: firstname + @123
#     password = f"{first_name}@123"
    
#     # Create user with student's registration number as username
#     user = User.objects.create_user(
#         username=student.registration_number,
#         password=password,
#         role='STUDENT',
#         email=student.email,
#         first_name=student.full_name.split()[0] if student.full_name.split() else '',
#         last_name=' '.join(student.full_name.split()[1:]) if len(student.full_name.split()) > 1 else ''
#     )
    
#     # Link user to student
#     student.user = user
#     student.save()
    
#     return user

# def send_student_credentials(student, user, request=None):
#     """
#     Send login credentials to student's email
#     """
#     try:
#         # Generate password
#         first_name_parts = student.full_name.split()
#         if first_name_parts:
#             first_name = first_name_parts[0].lower()
#         else:
#             first_name = "student"
#         password = f"{first_name}@123"
        
#         # Get login URL
#         if request:
#             login_url = request.build_absolute_uri(reverse('login'))
#         else:
#             login_url = "http://127.0.0.1:8000/login/"
        
#         # Prepare email content
#         subject = f"Your Student Portal Login Credentials - {student.registration_number}"
        
#         # Create context for email template
#         context = {
#             'student': student,
#             'username': student.registration_number,
#             'password': password,
#             'first_name': first_name.capitalize(),
#             'school_name': "Charles Academy",
#             'portal_url': login_url,
#         }
        
#         # Render HTML email template
#         html_message = render_to_string('students/emails/credentials_email.html', context)
#         plain_message = strip_tags(html_message)
        
#         # Send email
#         send_mail(
#             subject=subject,
#             message=plain_message,
#             from_email='info.charlesacademy@gmail.com',
#             recipient_list=[student.email],
#             html_message=html_message,
#             fail_silently=True,  # Change to False in production
#         )
        
#         print(f"Credentials email sent to {student.email}")
#         return True
#     except Exception as e:
#         print(f"Failed to send credentials email: {e}")
#         return False




# students/utils.py - Complete file with fixes
from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from .models import Student
import uuid

def generate_registration_number(class_code, year):
    last_student = Student.objects.filter(
        classroom__code=class_code,
        admission_year=year
    ).count() + 1

    return f"CA/{class_code}/{year}/{str(last_student).zfill(4)}"

def create_student_user(student):
    """
    Create a unique user account for student
    """
    try:
        # Get first name for password
        first_name_parts = student.full_name.split()
        if first_name_parts:
            first_name = first_name_parts[0].lower()
        else:
            first_name = "student"
        
        # Create password: firstname + @123
        password = f"{first_name}@123"
        
        # Generate unique username
        # Use registration_number + unique suffix if needed
        base_username = student.registration_number
        username = base_username
        suffix = 1
        
        # Check if username exists and generate unique one
        while User.objects.filter(username=username).exists():
            # Add suffix to make it unique
            username = f"{base_username}_{suffix}"
            suffix += 1
        
        # Get email - ensure uniqueness
        base_email = student.email or f"{username}@charlesacademy.com"
        email = base_email
        
        # Check if email exists
        email_suffix = 1
        while User.objects.filter(email=email).exists() and email:
            email = f"{username}_{email_suffix}@charlesacademy.com"
            email_suffix += 1
        
        # Create user with UNIQUE username
        user = User.objects.create_user(
            username=username,  # This is now guaranteed unique
            password=password,
            role='STUDENT',
            email=email,
            first_name=student.full_name.split()[0] if student.full_name.split() else '',
            last_name=' '.join(student.full_name.split()[1:]) if len(student.full_name.split()) > 1 else ''
        )
        
        # Link user to student
        student.user = user
        student.save()
        
        print(f"Created user: {username} for student: {student.registration_number}")
        return user
        
    except Exception as e:
        print(f"Error creating user for student {student.registration_number}: {e}")
        # Try alternative approach with UUID
        try:
            # Generate completely unique username
            unique_username = f"{student.registration_number}_{uuid.uuid4().hex[:8]}"
            
            user = User.objects.create_user(
                username=unique_username,
                password=password,
                role='STUDENT',
                email=f"{unique_username}@charlesacademy.com",
                first_name=student.full_name.split()[0] if student.full_name.split() else '',
                last_name=' '.join(student.full_name.split()[1:]) if len(student.full_name.split()) > 1 else ''
            )
            
            student.user = user
            student.save()
            print(f"Created user with UUID: {unique_username}")
            return user
            
        except Exception as e2:
            print(f"Failed even with UUID: {e2}")
            return None

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
            'username': user.username,  # Use the ACTUAL username
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
            recipient_list=[student.email] if student.email else [user.email],
            html_message=html_message,
            fail_silently=True,
        )
        
        print(f"Credentials email sent. Username: {user.username}")
        return True
    except Exception as e:
        print(f"Failed to send credentials email: {e}")
        return False