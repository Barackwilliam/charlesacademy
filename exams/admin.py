# exams/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Exam, Result, Assignment, Submission


# ─── EXISTING ────────────────────────────────────────────────────

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display  = ('name', 'classroom', 'exam_type', 'date')
    list_filter   = ('exam_type', 'classroom')
    search_fields = ('name',)
    ordering      = ('-date',)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display  = ('student', 'exam', 'subject', 'marks', 'get_grade')
    list_filter   = ('exam', 'subject')
    search_fields = ('student__full_name',)

    def get_grade(self, obj):
        return obj.grade()[0]
    get_grade.short_description = 'Grade'


# ─── NEW ─────────────────────────────────────────────────────────

class SubmissionInline(admin.TabularInline):
    model           = Submission
    extra           = 0
    can_delete      = False
    readonly_fields = ('student', 'submitted_at', 'timing', 'view_file')
    fields          = ('student', 'status', 'marks', 'feedback', 'timing', 'view_file', 'submitted_at')

    def timing(self, obj):
        if obj.is_late():
            return format_html('<span style="color:red;font-weight:bold;">⚠ Late</span>')
        return format_html('<span style="color:green;">✓ On time</span>')
    timing.short_description = 'Timing'

    def view_file(self, obj):
        url = obj.get_file_url()
        if url:
            return format_html(
                '<a href="{}" target="_blank" style="background:#4361ee;color:#fff;'
                'padding:3px 8px;border-radius:4px;font-size:11px;text-decoration:none;">⬇ View</a>',
                url
            )
        return '—'
    view_file.short_description = 'File'


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display    = (
        'title', 'classroom', 'subject', 'status',
        'due_date', 'subs_count', 'overdue_badge', 'created_by'
    )
    list_filter     = ('status', 'classroom', 'subject')
    search_fields   = ('title', 'classroom__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    inlines         = [SubmissionInline]
    date_hierarchy  = 'due_date'

    fieldsets = (
        ('Assignment Info', {
            'fields': ('title', 'description', 'classroom', 'subject', 'status')
        }),
        ('File & Deadline', {
            'fields': ('file', 'due_date')
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def subs_count(self, obj):
        n     = obj.submission_count()
        color = '#4361ee' if n else '#aaa'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:12px;font-size:11px;">{}</span>',
            color, n
        )
    subs_count.short_description = 'Submissions'

    def overdue_badge(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color:red;">⏰ Overdue</span>')
        return format_html('<span style="color:green;">✓ Open</span>')
    overdue_badge.short_description = 'Due Status'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display    = (
        'student', 'assignment', 'status', 'marks',
        'submitted_at', 'timing', 'view_file'
    )
    list_filter     = ('status', 'assignment__classroom', 'assignment')
    search_fields   = ('student__full_name', 'assignment__title')
    readonly_fields = ('submitted_at',)

    fieldsets = (
        ('Submission', {
            'fields': ('assignment', 'student', 'file', 'comment', 'status', 'submitted_at')
        }),
        ('Grading', {
            'fields': ('marks', 'feedback', 'graded_by', 'graded_at')
        }),
    )

    def timing(self, obj):
        if obj.is_late():
            return format_html('<span style="color:red;font-weight:bold;">⚠ Late</span>')
        return format_html('<span style="color:green;">✓ On time</span>')
    timing.short_description = 'Timing'

    def view_file(self, obj):
        url = obj.get_file_url()
        if url:
            return format_html(
                '<a href="{}" target="_blank" style="background:#4361ee;color:#fff;'
                'padding:3px 8px;border-radius:4px;font-size:11px;text-decoration:none;">⬇ View</a>',
                url
            )
        return '—'
    view_file.short_description = 'File'