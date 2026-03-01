#exams/model
from django.db import models
from classes.models import ClassRoom, Subject
from django.conf import settings
from django.utils import timezone  # IMPORT HII! - ndiyo inayokosekana

from students.models import Student
from pyuploadcare.dj.models import FileField as UploadcareFileField



class Exam(models.Model):
    EXAM_TYPE_CHOICES = (
        ('MIDTERM', 'Midterm'),
        ('FINAL', 'Final'),
        ('MONTHLY', 'Monthly Test'),
    )

    name = models.CharField(max_length=100)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)
    date = models.DateField()  # Make sure this is DateField, not DateTimeField
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='MONTHLY')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)  # Add this

    def __str__(self):
        return f"{self.name} - {self.classroom} - {self.date}"


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks = models.PositiveIntegerField()

    def grade(self):
        m = self.marks
        if m >= 80: return ('A', 'Excellent')
        if m >= 70: return ('B', 'Very Good')
        if m >= 60: return ('C', 'Good')
        if m >= 50: return ('D', 'Fair')
        if m >= 40: return ('E', 'Pass')
        return ('F', 'Fail')

    def __str__(self):
        return f"{self.student.full_name} - {self.subject.name} ({self.marks})"



# ─── NEW: ASSIGNMENT & SUBMISSION ────────────────────────────────

class Assignment(models.Model):
    STATUS_CHOICES = (
        ('PUBLISHED', 'Published'),
        ('DRAFT',     'Draft'),
        ('CLOSED',    'Closed'),
    )

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    classroom   = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE,
        related_name='assignments'
    )
    subject     = models.ForeignKey(
        Subject, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assignments'
    )
    # File ya assignment kwenye Uploadcare (optional)
    file = UploadcareFileField(
        blank=True, null=True,
        verbose_name='Assignment File (PDF/Doc)'
    )
    due_date    = models.DateTimeField()
    status      = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='PUBLISHED'
    )
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_assignments'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} — {self.classroom.name}"

    def is_overdue(self):
        return timezone.now() > self.due_date

    def submission_count(self):
        return self.submissions.count()

    def get_file_url(self):
        if self.file:
            url = str(self.file.cdn_url)
            # Ongeza filename mwishoni ili browser ijue ni file gani
            try:
                filename = self.file.filename
                if filename:
                    url = url.rstrip('/') + '/' + filename
            except:
                pass
            return url
        return None
#https://ucarecdn.com/b11eddbe-d832-4a75-a40e-b12e0d7dc089/ID_CARD_CA_ENG_2026_0313.pdf
#https://1q4ei5xyak.ucarecd.net/b11eddbe-d832-4a75-a40e-b12e0d7dc089/ID_CARD_CA_ENG_2026_0313.pdf

class Submission(models.Model):
    STATUS_CHOICES = (
        ('SUBMITTED', 'Submitted'),
        ('LATE',      'Late Submission'),
        ('GRADED',    'Graded'),
        ('RETURNED',  'Returned for Revision'),
    )

    assignment   = models.ForeignKey(
        Assignment, on_delete=models.CASCADE,
        related_name='submissions'
    )
    student      = models.ForeignKey(
        Student, on_delete=models.CASCADE,
        related_name='submissions'
    )
    file         = UploadcareFileField(verbose_name='Submission File')
    comment      = models.TextField(blank=True, verbose_name='Student Comment')
    status       = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='SUBMITTED'
    )
    marks        = models.PositiveIntegerField(null=True, blank=True)
    feedback     = models.TextField(blank=True, verbose_name='Teacher Feedback')
    graded_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='graded_submissions'
    )
    graded_at    = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering        = ['-submitted_at']
        unique_together = ('assignment', 'student')  # mara moja tu

    def __str__(self):
        return f"{self.student.full_name} → {self.assignment.title}"

    def is_late(self):
        return self.submitted_at > self.assignment.due_date

    def get_file_url(self):
        if self.file:
            url = str(self.file.cdn_url)
            # Ongeza filename mwishoni ili browser ijue ni file gani
            try:
                filename = self.file.filename
                if filename:
                    url = url.rstrip('/') + '/' + filename
            except:
                pass
            return url
        return None
