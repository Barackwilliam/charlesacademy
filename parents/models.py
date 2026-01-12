from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from students.models import Student
from django.utils import timezone

# Get the custom user model
User = get_user_model()


class Parent(models.Model):
    RELATIONSHIP_CHOICES = (
        ('FATHER', 'Father'),
        ('MOTHER', 'Mother'),
        ('GUARDIAN', 'Guardian'),
        ('OTHER', 'Other'),
    )
    
    user = models.OneToOneField(
        User,  # Hii sasa itatumia Custom User Model yako
        on_delete=models.CASCADE, 
        related_name='parent_profile',
        verbose_name="User Account"
    )
    
    full_name = models.CharField(
        max_length=200,
        verbose_name="Full Name"
    )
    
    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+255123456789'. Up to 15 digits allowed."
            )
        ],
        verbose_name="Phone Number"
    )
    
    email = models.EmailField(
        verbose_name="Email Address"
    )
    
    relationship = models.CharField(
        max_length=20, 
        choices=RELATIONSHIP_CHOICES, 
        default='GUARDIAN',
        verbose_name="Relationship"
    )
    
    address = models.TextField(
        verbose_name="Address"
    )
    
    occupation = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Occupation"
    )
    
    students = models.ManyToManyField(
        Student, 
        related_name='parents',
        blank=True,
        verbose_name="Children"
    )
    
    profile_picture = models.ImageField(
        upload_to='parents/profile_pictures/',
        blank=True,
        null=True,
        verbose_name="Profile Picture"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active Status"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )
    
    class Meta:
        verbose_name = "Parent"
        verbose_name_plural = "Parents"
        ordering = ['full_name']
        permissions = [
            ("view_parent_dashboard", "Can view parent dashboard"),
            ("view_child_attendance", "Can view child attendance"),
            ("view_child_results", "Can view child results"),
            ("view_child_fees", "Can view child fees"),
            ("view_school_announcements", "Can view school announcements"),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.relationship})"
    
    @property
    def children_count(self):
        """Count of children/students"""
        return self.students.count()
    
    @property
    def primary_student(self):
        """Get the primary/oldest student if multiple"""
        return self.students.first() if self.students.exists() else None
    
    @property
    def get_initials(self):
        """Get initials for avatar"""
        names = self.full_name.split()
        if len(names) >= 2:
            return f"{names[0][0]}{names[-1][0]}".upper()
        return self.full_name[:2].upper() if len(self.full_name) >= 2 else self.full_name[0].upper()
    
    def get_attendance_summary(self):
        """Get attendance summary for all children"""
        from attendance.models import Attendance  # Import here to avoid circular import
        
        summary = []
        for student in self.students.all():
            attendance_data = Attendance.objects.filter(student=student)
            if attendance_data.exists():
                present_count = attendance_data.filter(status='PRESENT').count()
                total_count = attendance_data.count()
                attendance_percentage = (present_count / total_count) * 100 if total_count > 0 else 0
                
                summary.append({
                    'student': student,
                    'present_count': present_count,
                    'total_count': total_count,
                    'percentage': round(attendance_percentage, 1)
                })
        return summary
    
    def get_fee_summary(self):
        """Get fee summary for all children"""
        from fees.models import FeeStructure, Payment  # Import here to avoid circular import
        
        summary = []
        for student in self.students.all():
            if student.classroom:
                try:
                    fee_structure = FeeStructure.objects.get(classroom=student.classroom)
                    total_fee = fee_structure.total_fee
                except FeeStructure.DoesNotExist:
                    total_fee = 0
            
                total_paid = Payment.objects.filter(student=student).aggregate(
                    total=models.Sum('amount_paid')
                )['total'] or 0
                
                balance = total_fee - total_paid
                
                summary.append({
                    'student': student,
                    'total_fee': total_fee,
                    'total_paid': total_paid,
                    'balance': balance
                })
        return summary
    
    def get_full_family_balance(self):
        """Get total fee balance for all children"""
        summary = self.get_fee_summary()
        return sum(item['balance'] for item in summary)