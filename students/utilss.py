from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from .models import Student
import logging
import re
from django.db import connection, transaction

logger = logging.getLogger(__name__)

def generate_registration_number(class_code, year, sequence_number):
    """Generate registration number: CA/CLASS/YEAR/SEQUENCE"""
    try:
        # Format: CA/CS1/2024/0001
        return f"CA/{class_code}/{year}/{str(sequence_number).zfill(4)}"
    except Exception as e:
        logger.error(f"Error generating reg number: {e}")
        return f"CA/{class_code}/{year}/0001"

def get_next_registration_sequence(class_code, year):
    """Pata nambari inayofuata ya registration kwa darasa na mwaka"""
    try:
        # Tafuta registration number ya mwisho kwa darasa hilo na mwaka
        last_student = Student.objects.filter(
            classroom__code=class_code,
            admission_year=year
        ).order_by('-registration_number').first()
        
        if last_student and last_student.registration_number:
            # Extract sequence number from registration number
            match = re.search(r'/(\d{4})$', last_student.registration_number)
            if match:
                return int(match.group(1)) + 1
        
        return 1
    except Exception as e:
        logger.error(f"Error getting sequence: {e}")
        return 1
def create_username_from_reg_number(registration_number):
    """Create username kutoka kwa registration number (keep original format)"""
    # Return registration number as-is (lowercase)
    username = registration_number.strip().lower()
    
    # Clean - remove extra spaces, keep slashes
    username = username.replace(' ', '')
    
    return username

def create_student_user(student, password=None):
    """
    Create user account for student
    Username = registration number (lowercase, with slashes)
    Password = firstname@123
    """
    try:
        with transaction.atomic():
            # 1. CREATE USERNAME (kutoka kwa registration number, keep slashes)
            username = student.registration_number.strip().lower()
            
            # Hakikisha username ni unique
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
                if counter > 100:
                    # Fallback: badilisha / kuwa _
                    username = original_username.replace('/', '_')
                    if User.objects.filter(username=username).exists():
                        username = f"{username}_{counter}"
            
            # 2. CREATE PASSWORD
            if not password:
                password = f"{student.get_first_name()}@123"
            
            # 3. CREATE EMAIL (kama hakuna)
            email = student.email
            if not email or email == "":
                email = f"{username.replace('/', '_')}@charlesacademy.com"
            
            # 4. SPLIT NAME
            name_parts = student.full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            else:
                first_name = student.full_name
                last_name = ""
            
            # 5. CREATE USER
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='STUDENT'
            )
            
            # 6. LINK STUDENT TO USER
            student.user = user
            student.save(update_fields=['user'])
            
            logger.info(f"✓ Created user '{username}' for student '{student.registration_number}'")
            return user
            
    except Exception as e:
        logger.error(f"✗ Error creating user: {e}", exc_info=True)
        raise

def send_student_credentials(student, user, password, request=None):
    """Send login credentials to student email"""
    try:
        # Check email configuration
        if not all([settings.EMAIL_HOST, settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD]):
            logger.warning("Email not configured, skipping email send")
            return False
        
        # Prepare login URL
        if request:
            login_url = request.build_absolute_uri(reverse('login'))
        else:
            login_url = f"{settings.SITE_URL}/accounts/login/" if hasattr(settings, 'SITE_URL') else "https://charlesacademy.co.tz/accounts/login/"
        
        # Prepare subject
        subject = f"Student Portal Login Credentials - {student.registration_number}"
        
        # Prepare context for template
        context = {
            'student': student,
            'user': user,
            'password': password,
            'login_url': login_url,
            'school_name': "Charles Academy"
        }
        
        # HTML message
        html_message = render_to_string('students/email/credentials_email.html', context)
        
        # Plain text message
        plain_message = f"""
Dear {student.full_name},

Your student portal account has been created successfully.

LOGIN DETAILS:
- Username: {user.username}
- Registration Number: {student.registration_number}
- Password: {password}
- Login URL: {login_url}

IMPORTANT:
1. Use your username or registration number to login
2. Change your password after first login
3. Keep your credentials secure

For assistance, contact the administration.

Best regards,
Charles Academy
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✓ Credentials email sent to {student.email}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to send email: {e}", exc_info=True)
        return False

def batch_create_student_users(students):
    """Create user accounts for multiple students"""
    results = {
        'success': [],
        'failed': []
    }
    
    for student in students:
        try:
            if student.user:
                results['success'].append({
                    'student': student,
                    'message': 'Already has user account'
                })
                continue
                
            user = create_student_user(student)
            results['success'].append({
                'student': student,
                'user': user
            })
            
        except Exception as e:
            results['failed'].append({
                'student': student,
                'error': str(e)
            })
    
    return results