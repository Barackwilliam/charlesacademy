
from django.contrib import admin

# Register your models here.
from .models import ClassRoom, Subject


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'fee')
    search_fields = ('name', 'code')
    list_filter = ('fee',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'classroom')
    search_fields = ('name',)
    list_filter = ('classroom',)
