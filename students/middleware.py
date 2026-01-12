from django.contrib import messages
from django.shortcuts import redirect
from .models import Student
from django.contrib.auth.models import User
import re


class AutoLinkStudentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is logged in and is a student
        if request.user.is_authenticated and request.user.role == 'STUDENT':
            # Check if user has a student profile
            if not hasattr(request.user, 'student_profile'):
                try:
                    # Try to find student by name
                    user_full_name = f"{request.user.first_name} {request.user.last_name}".strip()
                    
                    # Try exact match
                    student = Student.objects.filter(
                        full_name__iexact=user_full_name
                    ).first()
                    
                    if not student:
                        # Try partial match
                        if request.user.first_name and request.user.last_name:
                            students = Student.objects.filter(
                                full_name__icontains=request.user.first_name
                            ) | Student.objects.filter(
                                full_name__icontains=request.user.last_name
                            )
                            student = students.first()
                    
                    if student:
                        # Link student to user
                        student.user = request.user
                        student.save()
                        
                        # Add success message
                        messages.success(
                            request, 
                            f"Your account has been linked to student: {student.full_name}"
                        )
                    else:
                        # Try to find by username (might be admission/registration number)
                        username_upper = request.user.username.upper()
                        
                        # Check if username matches registration number
                        student = Student.objects.filter(
                            registration_number__iexact=username_upper
                        ).first()
                        
                        if not student:
                            # Try admission number format
                            # Check if username looks like ADM001, REG2024001, etc.
                            student = Student.objects.filter(
                                registration_number__icontains=username_upper
                            ).first()
                        
                        if student:
                            student.user = request.user
                            student.save()
                            messages.success(
                                request, 
                                f"Your account has been linked to student: {student.full_name}"
                            )
                
                except Exception as e:
                    # Log error but don't crash
                    print(f"Auto-linking error: {e}")
        
        response = self.get_response(request)
        return response