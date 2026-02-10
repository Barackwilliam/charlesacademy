import logging
from django.utils.deprecation import MiddlewareMixin
from .models import Student

logger = logging.getLogger(__name__)

class AutoLinkStudentMiddleware(MiddlewareMixin):
    """Automatically link logged in student users to their student profiles"""
    
    def process_request(self, request):
        if request.user.is_authenticated and request.user.role == 'STUDENT':
            try:
                # Skip if already linked
                if hasattr(request.user, 'student_profile'):
                    return
                
                # Try to find student by multiple methods
                student = None
                
                # Method 1: By username (registration number format)
                username = request.user.username.lower()
                
                # Try to extract registration number from username
                reg_patterns = [
                    username.upper().replace('_', '/'),  # username = ca_cs1_2024_0001
                    username.upper(),  # username = CA/CS1/2024/0001
                ]
                
                for pattern in reg_patterns:
                    student = Student.objects.filter(
                        registration_number__iexact=pattern
                    ).first()
                    if student:
                        break
                
                # Method 2: By email
                if not student and request.user.email:
                    student = Student.objects.filter(
                        email__iexact=request.user.email
                    ).first()
                
                # Method 3: By name (fallback)
                if not student:
                    full_name = f"{request.user.first_name} {request.user.last_name}".strip()
                    if full_name:
                        student = Student.objects.filter(
                            full_name__icontains=request.user.first_name
                        ).first()
                
                # Link if found and not already linked
                if student and not student.user:
                    student.user = request.user
                    student.save(update_fields=['user'])
                    logger.info(f"Auto-linked student {student.registration_number} to user {request.user.username}")
                    
            except Exception as e:
                logger.error(f"Auto-link middleware error: {e}", exc_info=True)