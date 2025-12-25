from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from students.models import Student
from teachers.models import Teacher
from classes.models import ClassRoom, Subject
from fees.models import FeeStructure
from django.db import models  # hii inahitajika kwa Sum
from django.db.models import Sum
# from fees.models import Payment
from django.db.models import Sum


# fees_collected = Payment.objects.aggregate(
#     total=Sum('amount_paid')
# )['total'] or 0


# Decorator: only admin can access
def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.role=='ADMIN')(view_func)

# @login_required
# @admin_required
# def dashboard(request):
#     total_students = Student.objects.count()
#     total_teachers = Teacher.objects.count()
#     total_classes = ClassRoom.objects.count()
#     total_subjects = Subject.objects.count()

#     # fees_pending = FeeStructure.objects.filter(status='PENDING').aggregate(total=models.Sum('amount'))['total'] or 0


#     context = {
#         'total_students': total_students,
#         'total_teachers': total_teachers,
#         'total_classes': total_classes,
#         'total_subjects': total_subjects,
#         'fees_collected': fees_collected,
#         # 'fees_pending': fees_pending,
#     }
#     return render(request, 'dashboard/index.html', context)
# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from fees.models import FeePayment, FeeStructure


def index(request):
    return render(request, 'dashboard/home.html')


@login_required
def dashboard(request):
    total_students = Student.objects.count()
    total_teachers = Teacher.objects.count()
    total_classes = ClassRoom.objects.count()

    fees_collected = FeePayment.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0

    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_classes': total_classes,
        'fees_collected': fees_collected,
    }

    return render(request, 'dashboard/index.html', context)
