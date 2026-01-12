from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from students.models import Student
from teachers.models import Teacher
from classes.models import ClassRoom, Subject
from fees.models import FeeStructure
from django.db import models  # hii inahitajika kwa Sum
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
    settings_obj = SchoolSettings.objects.first()


    fees_collected = FeePayment.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0

    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_classes': total_classes,
        'fees_collected': fees_collected,
        'school_settings': settings_obj,

    }

    return render(request, 'dashboard/index.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Announcement, SchoolSettings
from .forms import AnnouncementForm, SchoolSettingsForm

# Announcements Views
@login_required
def announcement_list(request):
    """List all announcements"""
    announcements = Announcement.objects.all().order_by('-created_at')
    settings_obj = SchoolSettings.objects.first()

    
    context = {
        'announcements': announcements,
        'page_title': 'Announcements',
        'school_settings': settings_obj,

    }
    return render(request, 'dashboard/announcements/list.html', context)

@login_required
def announcement_create(request):
    settings_obj = SchoolSettings.objects.first()

    """Create new announcement"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, 'Announcement created successfully')
            return redirect('announcement_list')
    else:
        form = AnnouncementForm()
    
    context = {
        'form': form,
        'page_title': 'Create Announcement',
    }
    return render(request, 'dashboard/announcements/form.html', context)

@login_required
def announcement_edit(request, pk):

    """Edit existing announcement"""
    settings_obj = SchoolSettings.objects.first()

    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement updated successfully')
            return redirect('announcement_list')
    else:
        form = AnnouncementForm(instance=announcement)
    
    context = {
        'form': form,
        'announcement': announcement,
        'page_title': 'Edit Announcement',
        'school_settings': settings_obj,

    }
    return render(request, 'dashboard/announcements/form.html', context)

@login_required
def announcement_delete(request, pk):
    settings_obj = SchoolSettings.objects.first()

    """Delete announcement"""
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully')
        return redirect('announcement_list')
    
    context = {
        'announcement': announcement,
        'page_title': 'Delete Announcement',
        'school_settings': settings_obj,

    }
    return render(request, 'dashboard/announcements/delete.html', context)

@login_required
def announcement_detail(request, pk):
    settings_obj = SchoolSettings.objects.first()

    """View announcement details"""
    announcement = get_object_or_404(Announcement, pk=pk)
    
    context = {
        'announcement': announcement,
        'page_title': announcement.title,
        'school_settings': settings_obj,

    }
    return render(request, 'dashboard/announcements/detail.html', context)

# School Settings View (uliokua nayo)
@login_required
def settings_view(request):
    """School settings"""
    settings_obj = SchoolSettings.objects.first()
    
    if not settings_obj:
        settings_obj = SchoolSettings.objects.create()
    
    if request.method == 'POST':
        form = SchoolSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully')
            return redirect('settings')
    else:
        form = SchoolSettingsForm(instance=settings_obj)
    
    context = {
        'form': form,
        'school_settings': settings_obj,
        'page_title': 'School Settings',
    }
    
    return render(request, 'dashboard/school.html', context)
















from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from .models import Announcement, SchoolSettings
from .forms import AnnouncementForm, SchoolSettingsForm
from django.core.paginator import Paginator

# Dashboard View
@login_required
def dashboards(request):
    """Main dashboard view"""
    # Get latest 5 announcements
    latest_announcements = Announcement.objects.all().order_by('-created_at')[:5]
    announcements_count = Announcement.objects.count()
    school_settings = SchoolSettings.objects.first()
    
    context = {
        'latest_announcements': latest_announcements,
        'announcements_count': announcements_count,
        'school_settings': school_settings,
        'current_date': timezone.now(),
        'page_title': 'Dashboard',
    }
    return render(request, 'dashboard/dashboard.html', context)

# Announcement Views
@login_required
def announcement_list(request):
    """List all announcements with pagination"""
    announcements_list = Announcement.objects.all().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(announcements_list, 10)  # Show 10 announcements per page
    page_number = request.GET.get('page')
    announcements = paginator.get_page(page_number)
    
    # Get latest announcement date
    latest_announcement = announcements_list.first()
    
    context = {
        'announcements': announcements,
        'latest_announcement_date': latest_announcement.created_at if latest_announcement else None,
        'page_title': 'Announcements',
    }
    return render(request, 'dashboard/announcements/list.html', context)

@login_required
def announcement_create(request):
    """Create new announcement"""
    if not request.user.is_superuser and getattr(request.user, 'role', None) != 'ADMIN':
        messages.error(request, 'You do not have permission to create announcements.')
        return redirect('announcement_list')
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, 'Announcement created successfully!')
            return redirect('announcement_detail', pk=announcement.pk)
    else:
        form = AnnouncementForm()
    
    context = {
        'form': form,
        'page_title': 'Create Announcement',
    }
    return render(request, 'dashboard/announcements/form.html', context)

@login_required
def announcement_detail(request, pk):
    """View announcement details"""
    announcement = get_object_or_404(Announcement, pk=pk)
    
    # Get next and previous announcements
    try:
        next_announcement = Announcement.objects.filter(
            created_at__lt=announcement.created_at
        ).order_by('-created_at').first()
    except:
        next_announcement = None
        
    try:
        previous_announcement = Announcement.objects.filter(
            created_at__gt=announcement.created_at
        ).order_by('created_at').first()
    except:
        previous_announcement = None
    
    context = {
        'announcement': announcement,
        'next_announcement': next_announcement,
        'previous_announcement': previous_announcement,
        'page_title': announcement.title,
    }
    return render(request, 'dashboard/announcements/detail.html', context)

@login_required
def announcement_edit(request, pk):
    """Edit existing announcement"""
    if not request.user.is_superuser and getattr(request.user, 'role', None) != 'ADMIN':
        messages.error(request, 'You do not have permission to edit announcements.')
        return redirect('announcement_detail', pk=pk)
    
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement updated successfully!')
            return redirect('announcement_detail', pk=announcement.pk)
    else:
        form = AnnouncementForm(instance=announcement)
    
    context = {
        'form': form,
        'announcement': announcement,
        'page_title': 'Edit Announcement',
    }
    return render(request, 'dashboard/announcements/form.html', context)

@login_required
def announcement_delete(request, pk):
    """Delete announcement"""
    if not request.user.is_superuser and getattr(request.user, 'role', None) != 'ADMIN':
        messages.error(request, 'You do not have permission to delete announcements.')
        return redirect('announcement_detail', pk=pk)
    
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully!')
        return redirect('announcement_list')
    
    context = {
        'announcement': announcement,
        'page_title': 'Delete Announcement',
    }
    return render(request, 'dashboard/announcements/delete.html', context)

# School Settings View
@login_required
def settings_view(request):
    """School settings"""
    if not request.user.is_superuser and getattr(request.user, 'role', None) != 'ADMIN':
        messages.error(request, 'You do not have permission to access settings.')
        return redirect('dashboard')
    
    settings_obj = SchoolSettings.objects.first()
    
    if not settings_obj:
        settings_obj = SchoolSettings.objects.create()
    
    if request.method == 'POST':
        form = SchoolSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'School settings updated successfully!')
            return redirect('settings')
    else:
        form = SchoolSettingsForm(instance=settings_obj)
    
    context = {
        'form': form,
        'school_settings': settings_obj,
        'page_title': 'School Settings',
    }
    
    return render(request, 'dashboard/school.html', context)

