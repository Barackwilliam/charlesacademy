# students/templatetags/student_filters.py
from django import template

register = template.Library()

@register.filter
def filter_by_status(queryset, status):
    """Filter students by status"""
    return queryset.filter(status=status)

@register.filter
def count_by_status(queryset, status):
    """Count students by status"""
    return queryset.filter(status=status).count()