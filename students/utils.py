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
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT setval(pg_get_serial_sequence('accounts_user', 'id'), 
                COALESCE((SELECT MAX(id) FROM accounts_user), 1), false);
            """)
            logger.info("✓ Fixed User ID sequence")
    except Exception as e:
        logger.error(f"✗ Error fixing sequence: {e}")

def generate_registration_number(class_code, year):
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
    Create a unique user account for student - username iwe registration number
    """
    try:
        fix_user_sequence()
        
        # Get first name for password
        first_name_parts = student.full_name.split()
        if first_name_parts:
            first_name = first_name_parts[0].lower()
        else:
            first_name = "student"
        
        # Password: firstname@123
        password = f"{first_name}@123"
        
        # HAPA NIMEBADILISHA: username iwe registration number
        username = student.registration_number  # Tumia registration number moja kwa moja
        
        # Check if username exists - kama ipo, ongeza suffix
        if User.objects.filter(username=username).exists():
            import time
            username = f"{student.registration_number}_{int(time.time()) % 10000}"
        
        # Get email
        email = student.email.strip().lower() if student.email else f"{username}@charlesacademy.com"
        
        if User.objects.filter(email=email).exists():
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
        
        # CREATE USER
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('accounts_user_id_seq')")
                next_id = cursor.fetchone()[0]
            
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
        
        try:
            unique_username = f"{student.registration_number}_{uuid.uuid4().hex[:6]}"
            
            user = User.objects.create_user(
                username=unique_username,
                password="student@123",
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
    try:
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.info("Email not configured, skipping")
            return False
        
        first_name_parts = student.full_name.split()
        if first_name_parts:
            first_name = first_name_parts[0].lower()
        else:
            first_name = "student"
        password = f"{first_name}@123"
        
        if request:
            login_url = request.build_absolute_uri(reverse('login'))
        else:
            login_url = "https://www.charlesacademy.co.tz/accounts/login/"
        
        subject = f"Your Student Portal Login - {student.registration_number}"
        
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
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=True,
        )
        
        logger.info(f"✓ Email sent to {student.email}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Email failed: {e}")
        return False