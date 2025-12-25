from django.contrib import admin
from .models import FeeStructure, Payment, FeePayment

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'total_fee')
    search_fields = ('classroom__name',)
    ordering = ('classroom',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount_paid', 'date', 'receipt_no')
    search_fields = ('student__first_name', 'student__last_name', 'receipt_no')
    list_filter = ('date',)
    ordering = ('-date',)


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount_paid', 'date_paid', 'reference', 'classroom_fee')
    search_fields = ('student__first_name', 'student__last_name', 'reference')
    list_filter = ('date_paid',)
    ordering = ('-date_paid',)
