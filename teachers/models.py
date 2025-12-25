# teachers/models.py
from django.db import models
from classes.models import ClassRoom
from classes.models import Subject   # hakikisha Subject iko students au classes

class Teacher(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    subjects = models.ManyToManyField(Subject, blank=True)
    classes = models.ManyToManyField(ClassRoom, blank=True)

    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
