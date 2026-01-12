# students/models.py

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
            # Validate email format
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError({'email': 'Please enter a valid email address'})
            
            # Check if email is unique
            if Student.objects.filter(email=self.email).exclude(id=self.id).exists():
                raise ValidationError({'email': 'This email is already registered'})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)