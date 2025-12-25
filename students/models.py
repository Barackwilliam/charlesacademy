# students/models.py
from django.db import models
from classes.models import ClassRoom
from django.utils import timezone
from django.conf import settings


class Student(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('GRADUATED', 'Graduated'),
        ('TRANSFERRED', 'Transferred'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='students/', blank=True)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True)
    admission_year = models.PositiveIntegerField(default=timezone.now().year)
    registration_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    documents = models.FileField(upload_to='documents/', blank=True)

    def __str__(self):
        return self.full_name
