from django.shortcuts import render, redirect, get_object_or_404
from .models import FeeStructure,Payment
from students.models import Student
from django.db import models
import uuid
from django.db.models import Sum



def fee_structure_list(request):
    structures = FeeStructure.objects.all()
    return render(request, 'fees/fee_structure_list.html', {'structures': structures})


def add_fee_structure(request):
    if request.method == 'POST':
        classroom_id = request.POST['classroom']
        total_fee = request.POST['total_fee']

        FeeStructure.objects.create(
            classroom_id=classroom_id,
            total_fee=total_fee
        )
        return redirect('fees:fee_structure_list')

    from classes.models import ClassRoom
    classrooms = ClassRoom.objects.all()
    return render(request, 'fees/add_fee_structure.html', {'classrooms': classrooms})



def record_payment(request):
    if request.method == 'POST':
        student_id = request.POST['student']
        amount = request.POST['amount']

        Payment.objects.create(
            student_id=student_id,
            amount_paid=amount,
            receipt_no=str(uuid.uuid4())[:8]
        )
        return redirect('fees:payment_list')

    students = Student.objects.all()
    return render(request, 'fees/record_payment.html', {'students': students})


def payment_list(request):
    payments = Payment.objects.select_related('student')
    return render(request, 'fees/payment_list.html', {'payments': payments})


def student_fee_report(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    payments = Payment.objects.filter(student=student)

    total_paid = payments.aggregate(
        models.Sum('amount_paid')
    )['amount_paid__sum'] or 0

    total_fee = FeeStructure.objects.get(classroom=student.classroom).total_fee
    balance = total_fee - total_paid

    return render(request, 'fees/student_fee_report.html', {
        'student': student,
        'payments': payments,
        'total_fee': total_fee,
        'total_paid': total_paid,
        'balance': balance
    })



def due_fee_list(request):
    students = Student.objects.all()
    due_list = []

    for s in students:
        structure = FeeStructure.objects.filter(
            classroom=s.classroom
        ).first()

        # kama class haina fee structure → ruka mwanafunzi
        if not structure:
            continue

        total_fee = structure.total_fee

        paid = Payment.objects.filter(
            student=s
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        balance = total_fee - paid

        if balance > 0:
            due_list.append({
                'student': s,
                'total_fee': total_fee,
                'paid': paid,
                'balance': balance
            })

    return render(request, 'fees/due_fee_list.html', {
        'due_list': due_list
    })