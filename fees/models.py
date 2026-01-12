from django.db import models
from classes.models import ClassRoom
from students.models import Student
from dashboard.models import SchoolSettings


class FeeStructure(models.Model):
    classroom = models.OneToOneField(ClassRoom, on_delete=models.CASCADE)
    total_fee = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.classroom.name} - {self.total_fee}"

    @staticmethod
    def get_class_fee(classroom):
        """Get fee for a specific class"""
        try:
            return FeeStructure.objects.get(classroom=classroom).total_fee
        except FeeStructure.DoesNotExist:
            return 0


class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount_paid = models.PositiveIntegerField()
    date = models.DateField(auto_now_add=True)
    receipt_no = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.amount_paid}"

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            import uuid
            self.receipt_no = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    @property
    def student_balance(self):
        """Calculate remaining balance for this student"""
        total_paid = Payment.objects.filter(
            student=self.student
        ).aggregate(total=models.Sum('amount_paid'))['total'] or 0
        
        try:
            fee_structure = FeeStructure.objects.get(classroom=self.student.classroom)
            return fee_structure.total_fee - total_paid
        except FeeStructure.DoesNotExist:
            return 0

    @staticmethod
    def get_student_payment_summary(student):
        """Get complete payment summary for a student"""
        payments = Payment.objects.filter(student=student).order_by('-date')
        
        total_paid = payments.aggregate(
            models.Sum('amount_paid')
        )['amount_paid__sum'] or 0

        try:
            fee_structure = FeeStructure.objects.get(classroom=student.classroom)
            total_fee = fee_structure.total_fee
            balance = total_fee - total_paid
        except FeeStructure.DoesNotExist:
            total_fee = 0
            balance = 0
            fee_structure = None

        return {
            'student': student,
            'total_fee': total_fee,
            'total_paid': total_paid,
            'balance': balance,
            'payments': payments,
            'fee_structure': fee_structure
        }

    @staticmethod
    def get_student_balance(student):
        """Get student's fee balance"""
        total_paid = Payment.objects.filter(student=student).aggregate(
            models.Sum('amount_paid')
        )['amount_paid__sum'] or 0

        try:
            fee = FeeStructure.objects.get(classroom=student.classroom).total_fee
            return fee - total_paid
        except FeeStructure.DoesNotExist:
            return 0


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