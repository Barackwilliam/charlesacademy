from django.db import models
from students.models import Student
from teachers.models import Teacher
from classes.models import Subject

ATTENDANCE_STATUS = (
    ('PRESENT', 'Present'),
    ('ABSENT', 'Absent'),
    ('LATE', 'Late'),
)

class StudentAttendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Subject / Somo'
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS)

    class Meta:
        unique_together = ('student', 'date', 'subject')

    def __str__(self):
        subject_name = self.subject.name if self.subject else "General"
        return f"{self.student} - {subject_name} - {self.date} - {self.status}"


class TeacherAttendance(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS)

    class Meta:
        unique_together = ('teacher', 'date')

    def __str__(self):
        return f"{self.teacher} - {self.date} - {self.status}"
