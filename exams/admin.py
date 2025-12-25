from django.contrib import admin
from .models import Exam, Result


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'classroom', 'exam_type', 'date')
    list_filter = ('exam_type', 'classroom')
    search_fields = ('name',)
    ordering = ('-date',)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'subject', 'marks', 'get_grade')
    list_filter = ('exam', 'subject')
    search_fields = ('student__first_name', 'student__last_name')
    
    def get_grade(self, obj):
        return obj.grade()[0]
    get_grade.short_description = 'Grade'
