
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




#
from pyuploadcare.dj.models import FileField as UploadcareFileField

class Certificate(models.Model):
    CERTIFICATE_TYPES = (
        ('COMPLETION',    'Certificate of Completion'),
        ('ACHIEVEMENT',   'Certificate of Achievement'),
        ('EXCELLENCE',    'Certificate of Excellence'),
        ('ATTENDANCE',    'Certificate of Attendance'),
        ('PARTICIPATION', 'Certificate of Participation'),
        ('OTHER',         'Other'),
    )

    student     = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    title       = models.CharField(max_length=200)
    cert_type   = models.CharField(
        max_length=20,
        choices=CERTIFICATE_TYPES,
        default='COMPLETION',
        verbose_name='Certificate Type'
    )
    # ── Uploadcare field (stores UUID / CDN URL, not local file) ──
    file        = UploadcareFileField(
        blank=False,
        null=False,
        verbose_name='Certificate File'
    )
    description = models.TextField(blank=True, null=True)
    issued_date = models.DateField(default=timezone.now)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_certificates'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Certificate"
        verbose_name_plural = "Certificates"
        ordering            = ['-issued_date']

    def __str__(self):
        return f"{self.title} — {self.student.full_name}"

    def get_file_url(self):
        """Rudisha CDN URL ya Uploadcare"""
        if self.file:
            return str(self.file.cdn_url)
        return None