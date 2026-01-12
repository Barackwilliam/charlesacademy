from django.db import models
from django.core.validators import FileExtensionValidator

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
    
    def __str__(self):
        return self.title
    
    def get_short_message(self):
        """Return truncated message for display in lists"""
        if len(self.message) > 100:
            return self.message[:100] + '...'
        return self.message

        
#dashboard/model.py
class SchoolSettings(models.Model):
    """School-wide settings"""
    name = models.CharField(max_length=200, default="Charles Academy")
    logo = models.ImageField(
        upload_to='logo/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])]
    )
    contact_email = models.EmailField(default="admin@charlesacademy.edu")
    phone = models.CharField(max_length=20, default="+255 123 456 789")
    academic_year = models.CharField(max_length=20, default="2025")
    theme_color = models.CharField(max_length=20, default="#4361ee", help_text="Primary theme color in hex format")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "School Settings"
        verbose_name_plural = "School Settings"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings object exists
        if not self.pk and SchoolSettings.objects.exists():
            # Update existing instance instead of creating new one
            existing = SchoolSettings.objects.first()
            existing.name = self.name
            existing.logo = self.logo
            existing.contact_email = self.contact_email
            existing.phone = self.phone
            existing.academic_year = self.academic_year
            existing.theme_color = self.theme_color
            existing.save()
            return existing
        return super().save(*args, **kwargs)