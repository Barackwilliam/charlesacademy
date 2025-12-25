from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'registration_number', 'classroom', 'admission_year', 'status')
    list_filter = ('classroom', 'status', 'admission_year')
    search_fields = ('full_name', 'registration_number')
    ordering = ('-admission_year',)
