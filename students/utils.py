# from django.contrib.auth.models import User
# from django.core.mail import EmailMessage
# from django.conf import settings
# from django.template.loader import render_to_string
# from django.utils.html import strip_tags
# from django.urls import reverse
# from .models import Student
# import logging

# # Setup logger
# logger = logging.getLogger(__name__)

# def generate_registration_number(class_code, year):
#     """
#     Generate unique registration number
#     """
#     try:
#         # Count existing students in same class and year
#         count = Student.objects.filter(
#             classroom__code=class_code,
#             admission_year=year
#         ).count()
        
#         # Increment for new student
#         sequence = count + 1
        
#         return f"CA/{class_code}/{year}/{str(sequence).zfill(4)}"
#     except Exception as e:
#         logger.error(f"Error generating registration number: {e}")
#         # Fallback to timestamp
#         import time
#         timestamp = int(time.time())
#         return f"CA/{class_code}/{year}/{timestamp}"

# def create_student_user(student):
#     """
#     Create user account for student with unique username
#     """
#     try:
#         # Extract first name for password
#         first_name = student.full_name.split()[0].lower() if student.full_name.split() else "student"
#         password = f"{first_name}@123"
        
#         # Generate username from registration number (remove special chars)
#         base_username = student.registration_number.replace('/', '_').replace('\\', '_')
#         username = base_username
        
#         # Ensure username is unique
#         counter = 1
#         while User.objects.filter(username=username).exists():
#             username = f"{base_username}_{counter}"
#             counter += 1
#             if counter > 100:
#                 import uuid
#                 username = f"student_{uuid.uuid4().hex[:8]}"
#                 break
        
#         # Ensure email is unique
#         email = student.email
#         if User.objects.filter(email=email).exists():
#             # Try to find available email
#             base_email = email.split('@')[0]
#             domain = email.split('@')[1] if '@' in email else "charlesacademy.com"
#             counter = 1
#             while User.objects.filter(email=email).exists():
#                 email = f"{base_email}{counter}@{domain}"
#                 counter += 1
#                 if counter > 10:
#                     email = f"{username}@{domain}"
#                     break
        
#         # Create user
#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password,
#             first_name=student.full_name.split()[0] if student.full_name.split() else '',
#             last_name=' '.join(student.full_name.split()[1:]) if len(student.full_name.split()) > 1 else ''
#         )
        
#         # Link student to user
#         student.user = user
#         student.save(update_fields=['user'])
        
#         logger.info(f"Created user {username} for student {student.registration_number}")
#         return user
        
#     except Exception as e:
#         logger.error(f"Error creating user for student {student.registration_number}: {e}")
#         return None

# def send_student_credentials(student, user, request=None):
#     """
#     Send email with login credentials
#     """
#     try:
#         # Prepare email content
#         first_name = student.full_name.split()[0] if student.full_name.split() else "Student"
#         password = f"{first_name.lower()}@123"
        
#         # Build login URL
#         if request:
#             login_url = request.build_absolute_uri(reverse('login'))
#         else:
#             login_url = f"{settings.BASE_URL}/login/" if hasattr(settings, 'BASE_URL') else "http://127.0.0.1:8000/login/"
        
#         # Email context
#         context = {
#             'student': student,
#             'username': user.username,
#             'password': password,
#             'first_name': first_name,
#             'school_name': "Charles Academy",
#             'login_url': login_url,
#             'portal_name': "Student Portal",
#         }
        
#         # Render email template
#         subject = f"Welcome to Charles Academy - Your Login Credentials"
#         html_message = render_to_string('students/emails/credentials_email.html', context)
#         plain_message = strip_tags(html_message)
        
#         # Create email
#         email = EmailMessage(
#             subject=subject,
#             body=plain_message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             to=[student.email],
#             reply_to=[settings.DEFAULT_FROM_EMAIL],
#         )
#         email.content_subtype = "html"
#         email.body = html_message
        
#         # Send email
#         email_sent = email.send(fail_silently=False)
        
#         if email_sent:
#             logger.info(f"Email sent successfully to {student.email}")
#             return True
#         else:
#             logger.error(f"Failed to send email to {student.email}")
#             return False
            
#     except Exception as e:
#         logger.error(f"Error sending email to {student.email}: {e}")
#         return False
















# students/utils.py - Kurekebishwa tu
from accounts.models import User  # Tumia User yako halisi
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from .models import Student
import uuid
import logging

logger = logging.getLogger(__name__)

def generate_registration_number(class_code, year):
    """
    Generate unique registration number
    """
    try:
        last_student = Student.objects.filter(
            classroom__code=class_code,
            admission_year=year
        ).count() + 1

        return f"CA/{class_code}/{year}/{str(last_student).zfill(4)}"
    except Exception as e:
        logger.error(f"Error generating reg number: {e}")
        return f"CA/{class_code}/{year}/0001"

def create_student_user(student):
    """
    Create a unique user account for student - FIXED VERSION
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
        base_username = student.registration_number.replace('/', '_')
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
        
        # Split name for first_name and last_name
        name_parts = student.full_name.split()
        if len(name_parts) >= 2:
            first_name_part = name_parts[0]
            last_name_part = ' '.join(name_parts[1:])
        else:
            first_name_part = student.full_name if student.full_name else ''
            last_name_part = ''
        
        # Create user with UNIQUE username - USE YOUR User MODEL
        user = User.objects.create_user(
            username=username,  # This is now guaranteed unique
            password=password,
            role='STUDENT',  # This matches your User model
            email=email,
            first_name=first_name_part,
            last_name=last_name_part
        )
        
        # Link user to student
        student.user = user
        student.save()
        
        logger.info(f"Created user: {username} for student: {student.registration_number}")
        return user
        
    except Exception as e:
        logger.error(f"Error creating user for student {student.registration_number}: {e}")
        
        # Try simpler approach
        try:
            # Generate completely unique username
            unique_username = f"{student.registration_number}_{uuid.uuid4().hex[:6]}"
            
            name_parts = student.full_name.split()
            first_name_part = name_parts[0] if name_parts else ''
            last_name_part = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            
            user = User.objects.create_user(
                username=unique_username,
                password=f"{first_name_part.lower() if first_name_part else 'student'}@123",
                role='STUDENT',
                email=student.email or f"{unique_username}@charlesacademy.com",
                first_name=first_name_part,
                last_name=last_name_part
            )
            
            student.user = user
            student.save()
            logger.info(f"Created user with UUID: {unique_username}")
            return user
            
        except Exception as e2:
            logger.error(f"Failed even with UUID: {e2}")
            return None

def send_student_credentials(student, user, request=None):
    """
    Send login credentials to student's email - FIXED VERSION
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
            login_url = "http://127.0.0.1:8000/accounts/login/"
        
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
        
        # Try to render HTML email template
        try:
            html_message = render_to_string('students/emails/credentials_email.html', context)
        except:
            # Fallback template
            html_message = f"""
            <html>
            <body>
                <h2>Welcome to Charles Academy!</h2>
                <p>Hello {first_name.capitalize()},</p>
                <p>Your student account has been created successfully.</p>
                <p><strong>Username:</strong> {user.username}</p>
                <p><strong>Password:</strong> {password}</p>
                <p><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></p>
                <p>Please change your password after first login.</p>
            </body>
            </html>
            """
        
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=True,  # Set to True to avoid crashes
        )
        
        logger.info(f"Credentials email sent. Username: {user.username}")
        return True
    except Exception as e:
        logger.error(f"Failed to send credentials email: {e}")
        return False