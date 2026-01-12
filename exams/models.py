#exams/model
from django.db import models
from classes.models import ClassRoom, Subject
from students.models import Student

class Exam(models.Model):
    EXAM_TYPE_CHOICES = (
        ('MIDTERM', 'Midterm'),
        ('FINAL', 'Final'),
        ('MONTHLY', 'Monthly Test'),
    )

    name = models.CharField(max_length=100)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='MONTHLY')

    def __str__(self):
        return f"{self.name} - {self.classroom}"


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
