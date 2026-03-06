from django.contrib import admin
from .models import TimetableEntry


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display  = ('classroom', 'day', 'start_time', 'end_time', 'subject', 'teacher', 'room')
    list_filter   = ('classroom', 'day', 'subject')
    search_fields = ('subject__name', 'teacher__full_name', 'classroom__name', 'room')
    ordering      = ('classroom', 'day', 'start_time')