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















from django.db import models
from django.conf import settings
from classes.models import ClassRoom
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re

class Student(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('GRADUATED', 'Graduated'),
        ('TRANSFERRED', 'Transferred'),
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='student_profile'
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='students/', blank=True, null=True)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True)
    admission_year = models.PositiveIntegerField(default=timezone.now().year)
    registration_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    documents = models.FileField(upload_to='documents/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['registration_number']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.registration_number})"
    
    def get_first_name(self):
        """Pata jina la kwanza kwa ajili ya password"""
        name_parts = self.full_name.strip().split()
        if name_parts:
            # Ondoa special characters kutoka kwa jina la kwanza
            first_name = re.sub(r'[^a-zA-Z]', '', name_parts[0])
            return first_name.lower()
        return "student"
    
    def clean(self):
        """Validate all fields"""
        super().clean()
        
        # Validate email
        if self.email:
            self.email = self.email.strip().lower()
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError({'email': 'Please enter a valid email address'})
        
        # Validate registration number
        if self.registration_number:
            self.registration_number = self.registration_number.strip().upper()
            
        # Validate full name
        if not self.full_name or len(self.full_name.strip()) < 3:
            raise ValidationError({'full_name': 'Full name must be at least 3 characters'})
    
    def save(self, *args, **kwargs):
        # Clean data before saving
        self.full_name = self.full_name.strip().title()
        
        if self.email:
            self.email = self.email.strip().lower()
        
        if self.registration_number:
            self.registration_number = self.registration_number.strip().upper()
        
        # Validate
        self.clean()
        
        # Call the real save() method
        super().save(*args, **kwargs)