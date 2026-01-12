# teachers/utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse

def send_teacher_credentials(teacher, password, request=None):
    """
    Send login credentials to teacher's email
    """
    try:
        # Get login URL
        if request:
            login_url = request.build_absolute_uri(reverse('login'))
        else:
            login_url = "http://127.0.0.1:8000/login/"
        
        # Prepare email content
        subject = f"Teacher Portal Login Credentials - {teacher.first_name} {teacher.last_name}"
        
        # Create context for email template
        context = {
            'teacher': teacher,
            'username': teacher.email,  # Username ni email
            'password': password,
            'first_name': teacher.first_name,
            'school_name': "Charles Academy",
            'portal_url': login_url,
        }
        
        # Render HTML email template
        html_message = render_to_string('teachers/emails/credentials_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email='info.charlesacademy@gmail.com',
            recipient_list=[teacher.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Credentials email sent to {teacher.email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send credentials email: {e}")
        return False