from django.contrib import messages
from django.shortcuts import redirect
from .models import Student
import re

# class AutoLinkStudentMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         if request.user.is_authenticated and request.user.role == 'STUDENT':
#             if not hasattr(request.user, 'student_profile'):
#                 try:
#                     user_full_name = f"{request.user.first_name} {request.user.last_name}".strip()
                    
#                     student = Student.objects.filter(
#                         full_name__iexact=user_full_name
#                     ).first()
                    
#                     if not student:
#                         if request.user.first_name and request.user.last_name:
#                             students = Student.objects.filter(
#                                 full_name__icontains=request.user.first_name
#                             ) | Student.objects.filter(
#                                 full_name__icontains=request.user.last_name
#                             )
#                             student = students.first()
                    
#                     if student:
#                         student.user = request.user
#                         student.save()
                        
#                         messages.success(
#                             request, 
#                             f"Your account has been linked to student: {student.full_name}"
#                         )
#                     else:
#                         username_upper = request.user.username.upper()
                        
#                         student = Student.objects.filter(
#                             registration_number__iexact=username_upper
#                         ).first()
                        
#                         if not student:
#                             student = Student.objects.filter(
#                                 registration_number__icontains=username_upper
#                             ).first()
                        
#                         if student:
#                             student.user = request.user
#                             student.save()
#                             messages.success(
#                                 request, 
#                                 f"Your account has been linked to student: {student.full_name}"
#                             )
                
#                 except Exception as e:
#                     print(f"Auto-linking error: {e}")
        
#         response = self.get_response(request)
#         return response




class AutoLinkStudentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.role == 'STUDENT':
            try:
                # Kama user tayari ana student, USIFANYE CHOCHOTE
                if hasattr(request.user, 'student'):
                    return self.get_response(request)

                # Link kwa kutumia registration number PEKEE
                student = Student.objects.filter(
                    registration_number=request.user.username
                ).first()

                if student and student.user is None:
                    student.user = request.user
                    student.save()

            except Exception as e:
                print("AutoLink error:", e)

        return self.get_response(request)
