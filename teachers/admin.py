from django.contrib import admin
from .models import Teacher

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'is_available', 'created_at')
    list_filter = ('is_available', 'created_at', 'classes')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    ordering = ('-created_at',)
    filter_horizontal = ('subjects', 'classes')  # kwa ManyToMany fields
