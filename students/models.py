# from django.db import models
# from django.conf import settings
# from classes.models import ClassRoom
# from django.utils import timezone
# from django.core.validators import validate_email
# from django.core.exceptions import ValidationError
# import re

# class Student(models.Model):
#     STATUS_CHOICES = (
#         ('ACTIVE', 'Active'),
#         ('GRADUATED', 'Graduated'),
#         ('TRANSFERRED', 'Transferred'),
#     )
    
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
#     full_name = models.CharField(max_length=200)
#     email = models.EmailField(unique=True, blank=True, null=True)
#     photo = models.ImageField(upload_to='students/photos/', blank=True, null=True)
#     classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True)
#     admission_year = models.PositiveIntegerField(default=timezone.now().year)
#     registration_number = models.CharField(max_length=50, unique=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
#     documents = models.FileField(upload_to='students/documents/', blank=True, null=True)
#     date_created = models.DateTimeField(auto_now_add=True)
#     date_updated = models.DateTimeField(auto_now=True)

#     class Meta:
#         verbose_name = "Student"
#         verbose_name_plural = "Students"
#         ordering = ['-date_created', 'full_name']
#         indexes = [
#             models.Index(fields=['email']),
#             models.Index(fields=['registration_number']),
#             models.Index(fields=['classroom', 'admission_year']),
#         ]

#     def __str__(self):
#         return f"{self.full_name} ({self.registration_number})"
    
#     def clean(self):
#         """Validate student data"""
#         errors = {}
        
#         # Validate email
#         if self.email:
#             self.email = self.email.strip().lower()
            
#             # Check email format
#             try:
#                 validate_email(self.email)
#             except ValidationError:
#                 errors['email'] = 'Please enter a valid email address'
            
#             # Check if email exists (excluding current instance)
#             qs = Student.objects.filter(email=self.email)
#             if self.pk:
#                 qs = qs.exclude(pk=self.pk)
            
#             if qs.exists():
#                 errors['email'] = 'This email is already registered'
        
#         # Validate full name
#         if not self.full_name or len(self.full_name.strip()) < 3:
#             errors['full_name'] = 'Full name must be at least 3 characters long'
        
#         if errors:
#             raise ValidationError(errors)
    
#     def save(self, *args, **kwargs):
#         # Clean data before saving
#         self.full_name = self.full_name.strip() if self.full_name else ""
#         if self.email:
#             self.email = self.email.strip().lower()
        
#         # Validate before saving
#         self.clean()
        
#         # Save the instance
#         super().save(*args, **kwargs)
















# students/models.py - Sawa kabisa hii
from django.db import models
from django.conf import settings
from classes.models import ClassRoom
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class Student(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('GRADUATED', 'Graduated'),
        ('TRANSFERRED', 'Transferred'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True, blank=True, null=True)  # ✅ New email field
    photo = models.ImageField(upload_to='students/', blank=True)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True)
    admission_year = models.PositiveIntegerField(default=timezone.now().year)
    registration_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    documents = models.FileField(upload_to='documents/', blank=True)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.registration_number})"
    
    def clean(self):
        """Validate email format and uniqueness"""
        if self.email:
            # Clean email
            self.email = self.email.strip().lower()
            
            # Validate email format
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError({'email': 'Please enter a valid email address'})
    
    def save(self, *args, **kwargs):
        # Clean email before saving
        if self.email:
            self.email = self.email.strip().lower()
        
        # Call clean method for validation
        self.clean()
        super().save(*args, **kwargs)