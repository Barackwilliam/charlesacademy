

# # students/utils.py - Kurekebishwa tu
# from accounts.models import User  # Tumia User yako halisi
# from django.core.mail import send_mail
# from django.conf import settings
# from django.template.loader import render_to_string
# from django.utils.html import strip_tags
# from django.urls import reverse
# from .models import Student
# import uuid
# import logging

# logger = logging.getLogger(__name__)

# def generate_registration_number(class_code, year):
#     """
#     Generate unique registration number
#     """
#     try:
#         last_student = Student.objects.filter(
#             classroom__code=class_code,
#             admission_year=year
#         ).count() + 1

#         return f"CA/{class_code}/{year}/{str(last_student).zfill(4)}"
#     except Exception as e:
#         logger.error(f"Error generating reg number: {e}")
#         return f"CA/{class_code}/{year}/0001"

# def create_student_user(student):
#     """
#     Create a unique user account for student - FIXED VERSION
#     """
#     try:
#         # Get first name for password
#         first_name_parts = student.full_name.split()
#         if first_name_parts:
#             first_name = first_name_parts[0].lower()
#         else:
#             first_name = "student"
        
#         # Create password: firstname + @123
#         password = f"{first_name}@123"
        
#         # Generate unique username
#         # Use registration_number + unique suffix if needed
#         base_username = student.registration_number.replace('/', '_')
#         username = base_username
#         suffix = 1
        
#         # Check if username exists and generate unique one
#         while User.objects.filter(username=username).exists():
#             # Add suffix to make it unique
#             username = f"{base_username}_{suffix}"
#             suffix += 1
        
#         # Get email - ensure uniqueness
#         base_email = student.email or f"{username}@charlesacademy.com"
#         email = base_email
        
#         # Check if email exists
#         email_suffix = 1
#         while User.objects.filter(email=email).exists() and email:
#             email = f"{username}_{email_suffix}@charlesacademy.com"
#             email_suffix += 1
        
#         # Split name for first_name and last_name
#         name_parts = student.full_name.split()
#         if len(name_parts) >= 2:
#             first_name_part = name_parts[0]
#             last_name_part = ' '.join(name_parts[1:])
#         else:
#             first_name_part = student.full_name if student.full_name else ''
#             last_name_part = ''
        
#         # Create user with UNIQUE username - USE YOUR User MODEL
#         user = User.objects.create_user(
#             username=username,  # This is now guaranteed unique
#             password=password,
#             role='STUDENT',  # This matches your User model
#             email=email,
#             first_name=first_name_part,
#             last_name=last_name_part
#         )
        
#         # Link user to student
#         student.user = user
#         student.save()
        
#         logger.info(f"Created user: {username} for student: {student.registration_number}")
#         return user
        
#     except Exception as e:
#         logger.error(f"Error creating user for student {student.registration_number}: {e}")
        
#         # Try simpler approach
#         try:
#             # Generate completely unique username
#             unique_username = f"{student.registration_number}_{uuid.uuid4().hex[:6]}"
            
#             name_parts = student.full_name.split()
#             first_name_part = name_parts[0] if name_parts else ''
#             last_name_part = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            
#             user = User.objects.create_user(
#                 username=unique_username,
#                 password=f"{first_name_part.lower() if first_name_part else 'student'}@123",
#                 role='STUDENT',
#                 email=student.email or f"{unique_username}@charlesacademy.com",
#                 first_name=first_name_part,
#                 last_name=last_name_part
#             )
            
#             student.user = user
#             student.save()
#             logger.info(f"Created user with UUID: {unique_username}")
#             return user
            
#         except Exception as e2:
#             logger.error(f"Failed even with UUID: {e2}")
#             return None

# def send_student_credentials(student, user, request=None):
#     """
#     Send login credentials to student's email - FIXED VERSION
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
#             login_url = "http://127.0.0.1:8000/accounts/login/"
        
#         # Prepare email content
#         subject = f"Your Student Portal Login Credentials - {student.registration_number}"
        
#         # Create context for email template
#         context = {
#             'student': student,
#             'username': user.username,  # Use the ACTUAL username
#             'password': password,
#             'first_name': first_name.capitalize(),
#             'school_name': "Charles Academy",
#             'portal_url': login_url,
#         }
        
#         # Try to render HTML email template
#         try:
#             html_message = render_to_string('students/emails/credentials_email.html', context)
#         except:
#             # Fallback template
#             html_message = f"""
#             <html>
#             <body>
#                 <h2>Welcome to Charles Academy!</h2>
#                 <p>Hello {first_name.capitalize()},</p>
#                 <p>Your student account has been created successfully.</p>
#                 <p><strong>Username:</strong> {user.username}</p>
#                 <p><strong>Password:</strong> {password}</p>
#                 <p><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></p>
#                 <p>Please change your password after first login.</p>
#             </body>
#             </html>
#             """
        
#         plain_message = strip_tags(html_message)
        
#         # Send email
#         send_mail(
#             subject=subject,
#             message=plain_message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[student.email],
#             html_message=html_message,
#             fail_silently=True,  # Set to True to avoid crashes
#         )
        
#         logger.info(f"Credentials email sent. Username: {user.username}")
#         return True
#     except Exception as e:
#         logger.error(f"Failed to send credentials email: {e}")
#         return False





# students/utils.py - FIXED VERSION
from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from .models import Student
import uuid
import logging
from django.db import connection

logger = logging.getLogger(__name__)

def fix_user_sequence():
    """
    Fix PostgreSQL sequence for User model
    """
    try:
        with connection.cursor() as cursor:
            # Reset sequence for accounts_user table
            cursor.execute("""
                SELECT setval(pg_get_serial_sequence('accounts_user', 'id'), 
                COALESCE((SELECT MAX(id) FROM accounts_user), 1), false);
            """)
            logger.info("✓ Fixed User ID sequence")
    except Exception as e:
        logger.error(f"✗ Error fixing sequence: {e}")

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
    Create a unique user account for student - COMPLETELY FIXED
    """
    try:
        # Fix sequence first
        fix_user_sequence()
        
        # Get first name for password
        first_name_parts = student.full_name.split()
        if first_name_parts:
            first_name = first_name_parts[0].lower()
        else:
            first_name = "student"
        
        # Create password: firstname + @123
        password = f"{first_name}@123"
        
        # Generate unique username - SIMPLE VERSION
        base_username = f"student_{student.registration_number.replace('/', '_')}"
        username = base_username
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            # Add timestamp for uniqueness
            import time
            username = f"{base_username}_{int(time.time()) % 10000}"
        
        # Get email
        email = student.email.strip().lower() if student.email else f"{username}@charlesacademy.com"
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            # Add suffix to email
            base_email = email.split('@')[0]
            domain = email.split('@')[1] if '@' in email else "charlesacademy.com"
            import time
            email = f"{base_email}_{int(time.time()) % 10000}@{domain}"
        
        # Split name
        name_parts = student.full_name.split()
        if len(name_parts) >= 2:
            first_name_part = name_parts[0]
            last_name_part = ' '.join(name_parts[1:])
        else:
            first_name_part = student.full_name if student.full_name else ''
            last_name_part = ''
        
        # CREATE USER WITH EXPLICIT ID
        try:
            # Get next available ID
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('accounts_user_id_seq')")
                next_id = cursor.fetchone()[0]
            
            # Create user with explicit ID to avoid sequence issues
            user = User(
                id=next_id,
                username=username,
                email=email,
                first_name=first_name_part,
                last_name=last_name_part,
                role='STUDENT'
            )
            user.set_password(password)
            user.save()
            
        except Exception as id_error:
            logger.error(f"ID creation failed: {id_error}")
            # Fallback - let Django handle ID
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name_part,
                last_name=last_name_part,
                role='STUDENT'
            )
        
        # Link user to student
        student.user = user
        student.save()
        
        logger.info(f"✓ Created user: {username} for student: {student.registration_number}")
        return user
        
    except Exception as e:
        logger.error(f"✗ Error creating user for student {student.registration_number}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # ULTIMATE FALLBACK - Create user without linking
        try:
            # Generate completely unique username
            unique_username = f"student_{student.registration_number}_{uuid.uuid4().hex[:6]}"
            
            user = User.objects.create_user(
                username=unique_username,
                password="student@123",  # Default password
                email=f"{unique_username}@charlesacademy.com",
                first_name=student.full_name.split()[0] if student.full_name.split() else '',
                last_name=' '.join(student.full_name.split()[1:]) if len(student.full_name.split()) > 1 else '',
                role='STUDENT'
            )
            
            student.user = user
            student.save()
            logger.info(f"✓ Created fallback user: {unique_username}")
            return user
            
        except Exception as e2:
            logger.error(f"✗ Ultimate fallback failed: {e2}")
            return None

def send_student_credentials(student, user, request=None):
    """
    Send login credentials to student's email - SIMPLIFIED
    """
    try:
        # Skip email if in production without proper config
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.info("Email not configured, skipping")
            return False
        
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
            login_url = "https://www.charlesacademy.co.tz/accounts/login/"
        
        # Prepare email content
        subject = f"Your Student Portal Login - {student.registration_number}"
        
        # Simple HTML email
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: #4361ee; color: white; padding: 20px; text-align: center;">
                    <h2>Welcome to Charles Academy!</h2>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border: 1px solid #ddd;">
                    <p>Dear <strong>{first_name.capitalize()}</strong>,</p>
                    
                    <p>Your student portal account has been created.</p>
                    
                    <div style="background: white; border: 2px solid #4361ee; padding: 15px; margin: 15px 0;">
                        <h3>Login Details:</h3>
                        <p><strong>Name:</strong> {student.full_name}</p>
                        <p><strong>Reg No:</strong> {student.registration_number}</p>
                        <p><strong>Username:</strong> <code>{user.username}</code></p>
                        <p><strong>Password:</strong> <code>{password}</code></p>
                        <p><strong>Login:</strong> <a href="{login_url}">{login_url}</a></p>
                    </div>
                    
                    <p><strong>Note:</strong> Change password after first login.</p>
                    
                    <p>Best regards,<br>
                    <strong>Charles Academy</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = f"""
        Welcome to Charles Academy!
        
        Dear {first_name.capitalize()},
        
        Your student portal account has been created.
        
        Login Details:
        - Name: {student.full_name}
        - Reg No: {student.registration_number}
        - Username: {user.username}
        - Password: {password}
        - Login URL: {login_url}
        
        Note: Please change your password after first login.
        
        Best regards,
        Charles Academy
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=True,  # Don't crash if email fails
        )
        
        logger.info(f"✓ Email sent to {student.email}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Email failed: {e}")
        return False