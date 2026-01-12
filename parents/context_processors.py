from .models import Parent
from dashboard.models import SchoolSettings
from django.utils import timezone


def parent_context(request):
    """Add parent-specific context to all templates"""
    context = {}
    
    # Add school settings
    school_settings = SchoolSettings.objects.first()
    if school_settings:
        context['school_settings'] = school_settings
    
    # Add parent information if logged in
    if request.user.is_authenticated:
        try:
            parent = Parent.objects.get(user=request.user)
            context['parent'] = parent
            context['children_count'] = parent.children_count
        except Parent.DoesNotExist:
            pass
    
    # Add current year
    context['current_year'] = timezone.now().year
    
    # Add today's date
    context['today'] = timezone.now().date()
    
    return context