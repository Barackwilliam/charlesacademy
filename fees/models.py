
from django.db import models
from classes.models import ClassRoom
from students.models import Student

class FeeStructure(models.Model):
    classroom = models.OneToOneField(ClassRoom, on_delete=models.CASCADE)
    total_fee = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.classroom.name} - {self.total_fee}"



class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount_paid = models.PositiveIntegerField()
    date = models.DateField(auto_now_add=True)
    receipt_no = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.amount_paid}"

    def get_student_balance(student):
        total_paid = Payment.objects.filter(student=student).aggregate(
            models.Sum('amount_paid')
        )['amount_paid__sum'] or 0

        fee = FeeStructure.objects.get(classroom=student.classroom).total_fee
        return fee - total_paid

class FeePayment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount_paid = models.PositiveIntegerField()
    date_paid = models.DateField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.student} - {self.amount_paid}"

    @property
    def classroom_fee(self):
        structure = FeeStructure.objects.filter(
            classroom=self.student.classroom
        ).first()
        return structure.total_fee if structure else 0