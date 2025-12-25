from django.db import models
from students.models import Student
from teachers.models import Teacher

ATTENDANCE_STATUS = (
    ('PRESENT', 'Present'),
    ('ABSENT', 'Absent'),
    ('LATE', 'Late'),
)

class StudentAttendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS)

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"


class TeacherAttendance(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS)

    class Meta:
        unique_together = ('teacher', 'date')

    def __str__(self):
        return f"{self.teacher} - {self.date} - {self.status}"
