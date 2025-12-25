# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student'),
        ('PARENT', 'Parent'),
        ('ACCOUNTANT', 'Accountant'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.role})"


class DummyModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)



# from accounts.models import User

# admin = User.objects.create_user(
#     username='admin',
#     password='admin123',
#     role='ADMIN',
#     is_staff=True,
#     is_superuser=True
# )

# admin.save()
