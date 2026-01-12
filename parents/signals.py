from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Parent


@receiver(post_save, sender=User)
def create_or_update_parent_profile(sender, instance, created, **kwargs):
    """
    Automatically create parent profile when a user is created
    with parent permissions or flag
    """
    if created:
        # Check if user should have parent profile
        # This logic depends on how you create parent users
        # For example, if email contains 'parent' or specific group
        if instance.email and 'parent' in instance.email.lower():
            Parent.objects.create(
                user=instance,
                full_name=f"{instance.first_name} {instance.last_name}".strip() or instance.username,
                email=instance.email,
                phone='+255000000000',  # Default phone
                address='Not provided',
                relationship='GUARDIAN'
            )
    else:
        # Update parent profile if user info changes
        try:
            parent = instance.parent_profile
            if parent:
                # Update parent email if user email changed
                if instance.email != parent.email:
                    parent.email = instance.email
                    parent.save()
        except Parent.DoesNotExist:
            pass


@receiver(post_save, sender=Parent)
def send_parent_welcome_email(sender, instance, created, **kwargs):
    """
    Send welcome email to parent when account is created
    """
    if created and instance.email:
        subject = f"Welcome to {settings.SCHOOL_NAME} Parent Portal"
        
        context = {
            'parent': instance,
            'school_name': settings.SCHOOL_NAME,
            'login_url': f"{settings.SITE_URL}/parents/login/",
            'support_email': settings.SUPPORT_EMAIL,
        }
        
        html_message = render_to_string('parents/emails/welcome_email.html', context)
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as e:
            # Log error but don't crash
            print(f"Failed to send welcome email: {e}")


@receiver(post_save, sender=Parent)
def notify_parent_account_activation(sender, instance, created, **kwargs):
    """
    Notify parent when account is activated/deactivated
    """
    if not created and instance.email:
        # Check if active status changed
        try:
            old_instance = Parent.objects.get(id=instance.id)
            if old_instance.is_active != instance.is_active:
                subject = f"Account Status Update - {settings.SCHOOL_NAME}"
                
                if instance.is_active:
                    status = "ACTIVATED"
                    message = "Your parent account has been activated. You can now access the parent portal."
                else:
                    status = "DEACTIVATED"
                    message = "Your parent account has been deactivated. Please contact school administration."
                
                context = {
                    'parent': instance,
                    'school_name': settings.SCHOOL_NAME,
                    'status': status,
                    'message': message,
                    'support_email': settings.SUPPORT_EMAIL,
                }
                
                html_message = render_to_string('parents/emails/account_status.html', context)
                plain_message = strip_tags(html_message)
                
                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[instance.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Failed to send status email: {e}")
        except Parent.DoesNotExist:
            pass


@receiver(pre_save, sender=Parent)
def validate_parent_phone(sender, instance, **kwargs):
    """
    Validate and clean phone number before saving
    """
    if instance.phone:
        # Remove any spaces or special characters
        phone = instance.phone.strip()
        
        # Ensure it starts with +
        if not phone.startswith('+'):
            if phone.startswith('0'):
                # Convert 0xxxx to +255xxxx
                phone = '+255' + phone[1:]
            else:
                # Add + if not present
                phone = '+' + phone
        
        instance.phone = phone


@receiver(post_delete, sender=Parent)
def delete_associated_user(sender, instance, **kwargs):
    """
    Delete associated user when parent is deleted
    (Optional - depends on your requirements)
    """
    # Only delete user if it has no other profiles
    # try:
    #     if not hasattr(instance.user, 'teacher_profile') and \
    #        not hasattr(instance.user, 'staff_profile') and \
    #        not instance.user.is_staff:
    #         instance.user.delete()
    # except Exception:
    #     pass
    pass