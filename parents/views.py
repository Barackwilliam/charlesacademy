from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate


from django.contrib.auth import get_user_model
User = get_user_model()


from django.db.models import Sum, Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta

# PDF Generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import os

# App imports
from dashboard.models import SchoolSettings, Announcement
from students.models import Student
from attendance .models import StudentAttendance

from exams.models import Result, Exam, Subject
from fees.models import FeeStructure, Payment
from .models import Parent
from .forms import ParentLoginForm, ParentProfileForm, UserUpdateForm


# ==================== AUTHENTICATION VIEWS ====================

def parent_login(request):
    """Parent login view"""
    if request.user.is_authenticated:
        # Check if user is a parent
        try:
            parent = Parent.objects.get(user=request.user)
            return redirect('parents:dashboard')
        except Parent.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = ParentLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Check if user has parent profile
                try:
                    parent = Parent.objects.get(user=user)
                    if parent.is_active:
                        login(request, user)
                        
                        # Set session expiry based on remember me
                        if not form.cleaned_data.get('remember_me'):
                            request.session.set_expiry(0)  # Session expires when browser closes
                        
                        messages.success(request, f"Welcome back, {parent.full_name}!")
                        
                        # Redirect to next page or dashboard
                        next_page = request.GET.get('next', 'parents:dashboard')
                        return redirect(next_page)
                    else:
                        messages.error(request, "Your parent account is inactive. Please contact school administration.")
                except Parent.DoesNotExist:
                    messages.error(request, "No parent profile found for this account.")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ParentLoginForm()
    
    # Get school settings for branding
    school_settings = SchoolSettings.objects.first()
    
    context = {
        'form': form,
        'school_settings': school_settings,
        'title': 'Parent Login'
    }
    
    return render(request, 'parents/login.html', context)


@login_required
def parent_logout(request):
    """Parent logout view"""
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('parents:login')


# ==================== DASHBOARD VIEWS ====================

@login_required
@permission_required('parents.view_parent_dashboard', raise_exception=True)
def parent_dashboard(request):
    """Parent Dashboard - Main view"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found. Please contact administrator.")
        logout(request)
        return redirect('parents:login')
    
    if not parent.is_active:
        messages.error(request, "Your parent account is inactive. Please contact school administration.")
        logout(request)
        return redirect('parents:login')
    
    # Get school settings
    school_settings = SchoolSettings.objects.first()
    
    # Get parent's students
    students = parent.students.all().select_related('classroom')
    
    # Get recent announcements (last 5)
    recent_announcements = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        is_published=True
    ).order_by('-created_at')[:5]
    
    # Get attendance summary for all children
    attendance_summary = parent.get_attendance_summary()
    
    # Get recent results (last 5)
    recent_results = []
    for student in students:
        results = Result.objects.filter(
            student=student
        ).select_related('exam', 'subject').order_by('-exam__date')[:3]
        recent_results.extend(results)
    recent_results = recent_results[:5]  # Limit to 5
    
    # Get fee summary
    fee_summary = parent.get_fee_summary()
    
    # Calculate overall statistics
    total_children = students.count()
    
    # Calculate average attendance percentage
    if attendance_summary:
        avg_attendance = sum(item['percentage'] for item in attendance_summary) / len(attendance_summary)
    else:
        avg_attendance = 0
    
    # Calculate total fee balance
    total_balance = parent.get_full_family_balance()
    
    # Get today's attendance status
    today_attendance = []
    for student in students:
        attendance = Attendance.objects.filter(
            student=student,
            date=timezone.now().date()
        ).first()
        today_attendance.append({
            'student': student,
            'attendance': attendance
        })
    
    # Get upcoming events/announcements
    upcoming_events = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        announcement_type='EVENT',
        is_published=True,
        event_date__gte=timezone.now().date()
    ).order_by('event_date')[:3]
    
    context = {
        'parent': parent,
        'school_settings': school_settings,
        'students': students,
        'recent_announcements': recent_announcements,
        'attendance_summary': attendance_summary,
        'recent_results': recent_results,
        'fee_summary': fee_summary,
        'today_attendance': today_attendance,
        'upcoming_events': upcoming_events,
        'stats': {
            'total_children': total_children,
            'avg_attendance': round(avg_attendance, 1),
            'total_balance': total_balance,
            'announcements_count': recent_announcements.count(),
            'results_count': len(recent_results),
        },
        'today': timezone.now().date(),
    }
    
    return render(request, 'parents/dashboard.html', context)


# ==================== ATTENDANCE VIEWS ====================

@login_required
@permission_required('parents.view_child_attendance', raise_exception=True)
def child_attendance(request, student_id=None):
    """View child attendance records"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    # Get filter parameters
    filter_month = request.GET.get('month')
    filter_year = request.GET.get('year', timezone.now().year)
    filter_status = request.GET.get('status')
    
    # Get specific student or all students
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        # Verify parent has access to this student
        if student not in parent.students.all():
            messages.error(request, "Access denied to this student's records.")
            return redirect('parents:dashboard')
        students = [student]
        selected_student = student
    else:
        students = parent.students.all()
        selected_student = None
    
    # Process attendance data for each student
    attendance_data = []
    
    for student in students:
        # Get attendance queryset
        attendance_qs = StudentAttendance.objects.filter(student=student)
        
        # Apply filters
        if filter_year:
            attendance_qs = attendance_qs.filter(date__year=filter_year)
        
        if filter_month:
            attendance_qs = attendance_qs.filter(date__month=filter_month)
        
        if filter_status and filter_status != 'ALL':
            attendance_qs = attendance_qs.filter(status=filter_status)
        
        # Order by date descending
        attendance_qs = attendance_qs.order_by('-date')
        
        # Paginate results
        paginator = Paginator(attendance_qs, 30)  # 30 records per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Calculate statistics
        all_attendance = StudentAttendance.objects.filter(student=student)
        present_count = all_attendance.filter(status='PRESENT').count()
        absent_count = all_attendance.filter(status='ABSENT').count()
        late_count = all_attendance.filter(status='LATE').count()
        excused_count = all_attendance.filter(status='EXCUSED').count()
        total_count = all_attendance.count()
        
        attendance_percentage = (present_count / total_count * 100) if total_count > 0 else 0
        
        # Get monthly attendance for chart
        monthly_data = []
        for i in range(6):  # Last 6 months
            month_date = timezone.now() - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i > 0:
                next_month = timezone.now() - timedelta(days=30*(i-1))
                month_end = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                month_end = timezone.now()
            
            month_attendance = StudentAttendance.objects.filter(
                student=student,
                date__range=[month_start, month_end]
            )
            month_present = month_attendance.filter(status='PRESENT').count()
            month_total = month_attendance.count()
            month_percentage = (month_present / month_total * 100) if month_total > 0 else 0
            
            monthly_data.append({
                'month': month_start.strftime('%b'),
                'percentage': round(month_percentage, 1),
                'present': month_present,
                'total': month_total
            })
        
        attendance_data.append({
            'student': student,
            'attendance': page_obj,
            'paginator': paginator,
            'page_obj': page_obj,
            'statistics': {
                'present_count': present_count,
                'absent_count': absent_count,
                'late_count': late_count,
                'excused_count': excused_count,
                'total_count': total_count,
                'percentage': round(attendance_percentage, 1)
            },
            'monthly_data': monthly_data[::-1],  # Reverse to show oldest first
            'filter': {
                'month': filter_month,
                'year': filter_year,
                'status': filter_status
            }
        })
    
    # Get available years for filter
    attendance_years = StudentAttendance.objects.dates('date', 'year')
    available_years = sorted(set(year.year for year in attendance_years), reverse=True)
    
    context = {
        'parent': parent,
        'attendance_data': attendance_data,
        'selected_student': selected_student,
        'available_years': available_years,
        'attendance_statuses': ['PRESENT', 'ABSENT', 'LATE', 'EXCUSED'],
        'title': 'Child Attendance'
    }
    
    return render(request, 'parents/child_attendance.html', context)


@login_required
@permission_required('parents.view_child_attendance', raise_exception=True)
def attendance_summary_api(request):
    """API endpoint for attendance summary chart"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        return JsonResponse({'error': 'Parent not found'}, status=404)
    
    student_id = request.GET.get('student_id')
    months = int(request.GET.get('months', 6))
    
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        if student not in parent.students.all():
            return JsonResponse({'error': 'Access denied'}, status=403)
        students = [student]
    else:
        students = parent.students.all()
    
    data = []
    
    for student in students:
        student_data = {
            'student_name': student.full_name,
            'months': [],
            'total_present': 0,
            'total_days': 0
        }
        
        for i in range(months):
            month_date = timezone.now() - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if i > 0:
                next_month = timezone.now() - timedelta(days=30*(i-1))
                month_end = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                month_end = timezone.now()
            
            month_attendance = StudentAttendance.objects.filter(
                student=student,
                date__range=[month_start, month_end]
            )
            
            month_present = month_attendance.filter(status='PRESENT').count()
            month_total = month_attendance.count()
            
            student_data['months'].append({
                'month': month_start.strftime('%b %Y'),
                'present': month_present,
                'total': month_total,
                'percentage': (month_present / month_total * 100) if month_total > 0 else 0
            })
            
            student_data['total_present'] += month_present
            student_data['total_days'] += month_total
        
        student_data['overall_percentage'] = (
            student_data['total_present'] / student_data['total_days'] * 100
        ) if student_data['total_days'] > 0 else 0
        
        data.append(student_data)
    
    return JsonResponse({'data': data})


# ==================== RESULTS VIEWS ====================

@login_required
@permission_required('parents.view_child_results', raise_exception=True)
def child_results(request, student_id=None):
    """View child academic results"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    # Get filter parameters
    filter_exam = request.GET.get('exam')
    filter_subject = request.GET.get('subject')
    filter_year = request.GET.get('year', timezone.now().year)
    
    # Get specific student or all students
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        # Verify parent has access to this student
        if student not in parent.students.all():
            messages.error(request, "Access denied to this student's records.")
            return redirect('parents:dashboard')
        students = [student]
        selected_student = student
    else:
        students = parent.students.all()
        selected_student = None
    
    # Process results data for each student
    results_data = []
    
    for student in students:
        # Get results queryset
        results_qs = Result.objects.filter(student=student).select_related('exam', 'subject')
        
        # Apply filters
        if filter_year:
            results_qs = results_qs.filter(exam__date__year=filter_year)
        
        if filter_exam and filter_exam != 'ALL':
            results_qs = results_qs.filter(exam_id=filter_exam)
        
        if filter_subject and filter_subject != 'ALL':
            results_qs = results_qs.filter(subject_id=filter_subject)
        
        # Get all results for statistics
        all_results = Result.objects.filter(student=student)
        
        # Calculate overall statistics
        total_subjects = all_results.count()
        total_marks = all_results.aggregate(total=Sum('marks'))['total'] or 0
        average_marks = total_marks / total_subjects if total_subjects > 0 else 0
        
        # Get highest and lowest scores
        highest_result = all_results.order_by('-marks').first()
        lowest_result = all_results.order_by('marks').first()
        
        # Group results by exam
        exams_data = {}
        for result in all_results:
            exam = result.exam
            if exam:
                exam_id = exam.id
                exam_name = exam.name
                exam_date = exam.date
                
                if exam_id not in exams_data:
                    exams_data[exam_id] = {
                        'exam': exam,
                        'results': [],
                        'total_marks': 0,
                        'subject_count': 0,
                        'grades': {}
                    }
                
                exams_data[exam_id]['results'].append(result)
                exams_data[exam_id]['total_marks'] += result.marks
                exams_data[exam_id]['subject_count'] += 1
                
                # Count grades
                grade = result.grade
                if grade:
                    if grade not in exams_data[exam_id]['grades']:
                        exams_data[exam_id]['grades'][grade] = 0
                    exams_data[exam_id]['grades'][grade] += 1
        
        # Calculate exam averages and percentages
        for exam_id, data in exams_data.items():
            if data['subject_count'] > 0:
                data['average'] = data['total_marks'] / data['subject_count']
                
                # Calculate percentage (assuming max marks per subject is 100)
                total_max_marks = data['subject_count'] * 100
                data['percentage'] = (data['total_marks'] / total_max_marks) * 100 if total_max_marks > 0 else 0
                
                # Determine overall grade
                percentage = data['percentage']
                if percentage >= 80:
                    data['overall_grade'] = 'A'
                elif percentage >= 70:
                    data['overall_grade'] = 'B'
                elif percentage >= 60:
                    data['overall_grade'] = 'C'
                elif percentage >= 50:
                    data['overall_grade'] = 'D'
                elif percentage >= 40:
                    data['overall_grade'] = 'E'
                else:
                    data['overall_grade'] = 'F'
        
        # Get available exams and subjects for filter
        available_exams = Exam.objects.filter(
            result__student=student
        ).distinct().order_by('-date')
        
        available_subjects = Subject.objects.filter(
            result__student=student
        ).distinct().order_by('name')
        
        # Get exam years
        exam_years = Exam.objects.filter(
            result__student=student
        ).dates('date', 'year')
        available_years = sorted(set(year.year for year in exam_years), reverse=True)
        
        results_data.append({
            'student': student,
            'results': results_qs.order_by('-exam__date', 'subject__name'),
            'exams_data': exams_data,
            'statistics': {
                'total_subjects': total_subjects,
                'total_marks': total_marks,
                'average_marks': round(average_marks, 2),
                'exams_count': len(exams_data),
                'highest_score': highest_result.marks if highest_result else 0,
                'lowest_score': lowest_result.marks if lowest_result else 0,
                'highest_subject': highest_result.subject.name if highest_result else 'N/A',
                'lowest_subject': lowest_result.subject.name if lowest_result else 'N/A',
            },
            'available_exams': available_exams,
            'available_subjects': available_subjects,
            'available_years': available_years,
            'filter': {
                'exam': filter_exam,
                'subject': filter_subject,
                'year': filter_year
            }
        })
    
    context = {
        'parent': parent,
        'results_data': results_data,
        'selected_student': selected_student,
        'title': 'Academic Results'
    }
    
    return render(request, 'parents/child_results.html', context)


@login_required
@permission_required('parents.view_child_results', raise_exception=True)
def download_results_pdf(request, student_id):
    """Download results PDF for a specific child"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Verify parent has access to this student
    if student not in parent.students.all():
        messages.error(request, "Access denied to this student's records.")
        return redirect('parents:dashboard')
    
    # Get school settings
    school_settings = SchoolSettings.objects.first()
    
    # Get student results
    results = Result.objects.filter(student=student).select_related('exam', 'subject')
    
    if not results.exists():
        messages.warning(request, "No results available to download.")
        return redirect('parents:child_results')
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        alignment=1
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=6
    )
    
    # School header
    if school_settings and school_settings.logo:
        try:
            logo_path = school_settings.logo.path
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
                elements.append(logo)
        except:
            pass
    
    school_name = school_settings.name if school_settings else "SCHOOL MANAGEMENT SYSTEM"
    school_address = school_settings.address if school_settings else ""
    school_phone = school_settings.phone if school_settings else ""
    
    header_text = f"""
    <b><font size="14">{school_name}</font></b><br/>
    <font size="10">{school_address}</font><br/>
    <font size="9">Phone: {school_phone}</font>
    """
    elements.append(Paragraph(header_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Title
    elements.append(Paragraph("ACADEMIC RESULTS REPORT", title_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Student and Parent Information
    info_text = f"""
    <b>Student:</b> {student.full_name}<br/>
    <b>Class:</b> {student.classroom}<br/>
    <b>Admission No:</b> {student.registration_number}<br/>
    <b>Parent:</b> {parent.full_name} ({parent.relationship})<br/>
    <b>Report Date:</b> {timezone.now().strftime('%d/%m/%Y %I:%M %p')}
    """
    elements.append(Paragraph(info_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Group results by exam
    exams = {}
    for result in results:
        exam = result.exam
        if exam:
            if exam.id not in exams:
                exams[exam.id] = {
                    'exam': exam,
                    'results': [],
                    'total_marks': 0,
                    'subject_count': 0
                }
            exams[exam.id]['results'].append(result)
            exams[exam.id]['total_marks'] += result.marks
            exams[exam.id]['subject_count'] += 1
    
    # Add results for each exam
    for exam_id, exam_data in exams.items():
        exam = exam_data['exam']
        
        elements.append(Paragraph(f"<b>Exam:</b> {exam.name}", header_style))
        if exam.date:
            elements.append(Paragraph(f"<b>Date:</b> {exam.date.strftime('%d/%m/%Y')}", styles['Normal']))
        
        # Create results table
        table_data = [
            ['Subject', 'Marks', 'Out of', 'Percentage', 'Grade', 'Remarks']
        ]
        
        for result in exam_data['results']:
            percentage = (result.marks / result.max_marks * 100) if result.max_marks > 0 else 0
            table_data.append([
                result.subject.name,
                f"{result.marks:.1f}",
                f"{result.max_marks:.1f}",
                f"{percentage:.1f}%",
                result.grade,
                result.remarks or "-"
            ])
        
        # Add total row
        avg_marks = exam_data['total_marks'] / exam_data['subject_count'] if exam_data['subject_count'] > 0 else 0
        total_percentage = (avg_marks / 100) * 100  # Assuming max marks per subject is 100
        overall_grade = "A" if total_percentage >= 80 else \
                       "B" if total_percentage >= 70 else \
                       "C" if total_percentage >= 60 else \
                       "D" if total_percentage >= 50 else \
                       "E" if total_percentage >= 40 else "F"
        
        table_data.append([
            '<b>TOTAL/AVERAGE</b>',
            f"<b>{exam_data['total_marks']:.1f}</b>",
            f"<b>{exam_data['subject_count'] * 100}</b>",
            f"<b>{total_percentage:.1f}%</b>",
            f"<b>{overall_grade}</b>",
            ""
        ])
        
        # Create table
        table = Table(table_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 1, colors.HexColor('#ddd')),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#2c3e50')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Performance Summary
    elements.append(Paragraph("PERFORMANCE SUMMARY", header_style))
    
    # Calculate overall statistics
    total_results = results.count()
    total_marks = results.aggregate(total=Sum('marks'))['total'] or 0
    avg_marks = total_marks / total_results if total_results > 0 else 0
    avg_percentage = (avg_marks / 100) * 100  # Assuming max marks per subject is 100
    
    summary_data = [
        ['Total Exams Taken', str(len(exams))],
        ['Total Subjects', str(total_results)],
        ['Total Marks', f"{total_marks:.1f}"],
        ['Average Marks', f"{avg_marks:.1f}"],
        ['Average Percentage', f"{avg_percentage:.1f}%"],
        ['Overall Grade', overall_grade]
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_text = f"""
    <font size="8">
    <i>
    This is an official academic report for {student.full_name}.<br/>
    Generated for parent: {parent.full_name} on {timezone.now().strftime('%d %B, %Y')}.<br/>
    Report ID: AR-{student.registration_number}-{timezone.now().strftime('%Y%m%d%H%M')}
    </i>
    </font>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create HTTP response with PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"Results_Report_{student.registration_number}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response


# ==================== FEES VIEWS ====================

@login_required
@permission_required('parents.view_child_fees', raise_exception=True)
def child_fees(request, student_id=None):
    """View child fee balances and payments"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    # Get filter parameters
    filter_year = request.GET.get('year')
    filter_status = request.GET.get('status')
    
    # Get specific student or all students
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        # Verify parent has access to this student
        if student not in parent.students.all():
            messages.error(request, "Access denied to this student's records.")
            return redirect('parents:dashboard')
        students = [student]
        selected_student = student
    else:
        students = parent.students.all()
        selected_student = None
    
    # Process fee data for each student
    fees_data = []
    
    for student in students:
        # Get fee structure
        if student.classroom:
            try:
                fee_structure = FeeStructure.objects.get(classroom=student.classroom)
                total_fee = fee_structure.total_fee
                fee_breakdown = {
                    'tuition_fee': fee_structure.tuition_fee,
                    'exam_fee': fee_structure.exam_fee,
                    'library_fee': fee_structure.library_fee,
                    'sports_fee': fee_structure.sports_fee,
                    'lab_fee': fee_structure.lab_fee,
                    'activity_fee': fee_structure.activity_fee,
                    'other_charges': fee_structure.other_charges,
                }
            except FeeStructure.DoesNotExist:
                total_fee = 0
                fee_structure = None
                fee_breakdown = {}
        else:
            total_fee = 0
            fee_structure = None
            fee_breakdown = {}
        
        # Get payments queryset
        payments_qs = Payment.objects.filter(student=student)
        
        # Apply filters
        if filter_year and filter_year != 'ALL':
            payments_qs = payments_qs.filter(academic_year=filter_year)
        
        if filter_status and filter_status != 'ALL':
            if filter_status == 'VERIFIED':
                payments_qs = payments_qs.filter(is_verified=True)
            elif filter_status == 'PENDING':
                payments_qs = payments_qs.filter(is_verified=False)
        
        # Order by date descending
        payments_qs = payments_qs.order_by('-date')
        
        # Paginate payments
        paginator = Paginator(payments_qs, 20)  # 20 payments per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Calculate statistics
        total_paid = Payment.objects.filter(student=student).aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        balance = total_fee - total_paid
        
        # Calculate payment percentage
        payment_percentage = (total_paid / total_fee * 100) if total_fee > 0 else 0
        
        # Get payment history by month for chart
        monthly_payments = []
        for i in range(6):  # Last 6 months
            month_date = timezone.now() - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i > 0:
                next_month = timezone.now() - timedelta(days=30*(i-1))
                month_end = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                month_end = timezone.now()
            
            month_payments = Payment.objects.filter(
                student=student,
                date__range=[month_start, month_end]
            )
            month_total = month_payments.aggregate(total=Sum('amount_paid'))['total'] or 0
            
            monthly_payments.append({
                'month': month_start.strftime('%b'),
                'amount': month_total,
                'count': month_payments.count()
            })
        
        # Get payment modes summary
        payment_modes = Payment.objects.filter(student=student).values(
            'payment_mode'
        ).annotate(
            total_amount=Sum('amount_paid'),
            count=Count('id')
        ).order_by('-total_amount')
        
        fees_data.append({
            'student': student,
            'fee_structure': fee_structure,
            'fee_breakdown': fee_breakdown,
            'payments': page_obj,
            'paginator': paginator,
            'page_obj': page_obj,
            'statistics': {
                'total_fee': total_fee,
                'total_paid': total_paid,
                'balance': balance,
                'payment_percentage': round(payment_percentage, 1),
                'payments_count': Payment.objects.filter(student=student).count(),
                'verified_payments': Payment.objects.filter(student=student, is_verified=True).count(),
            },
            'monthly_payments': monthly_payments[::-1],  # Reverse to show oldest first
            'payment_modes': payment_modes,
            'filter': {
                'year': filter_year,
                'status': filter_status
            }
        })
    
    # Calculate total family balance
    total_family_balance = sum(data['statistics']['balance'] for data in fees_data)
    total_family_paid = sum(data['statistics']['total_paid'] for data in fees_data)
    total_family_fee = sum(data['statistics']['total_fee'] for data in fees_data)
    
    # Get available academic years for filter
    payment_years = Payment.objects.values_list('academic_year', flat=True).distinct()
    available_years = sorted(set(payment_years), reverse=True)
    
    context = {
        'parent': parent,
        'fees_data': fees_data,
        'selected_student': selected_student,
        'family_summary': {
            'total_balance': total_family_balance,
            'total_paid': total_family_paid,
            'total_fee': total_family_fee,
            'total_children': len(students),
            'overall_percentage': (total_family_paid / total_family_fee * 100) if total_family_fee > 0 else 0
        },
        'available_years': available_years,
        'payment_statuses': ['VERIFIED', 'PENDING'],
        'title': 'Fee Management'
    }
    
    return render(request, 'parents/child_fees.html', context)


@login_required
@permission_required('parents.view_child_fees', raise_exception=True)
def download_fee_statement(request, student_id):
    """Download fee statement PDF for a specific child"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Verify parent has access to this student
    if student not in parent.students.all():
        messages.error(request, "Access denied to this student's records.")
        return redirect('parents:dashboard')
    
    # Get school settings
    school_settings = SchoolSettings.objects.first()
    
    # Get fee data
    if student.classroom:
        try:
            fee_structure = FeeStructure.objects.get(classroom=student.classroom)
            total_fee = fee_structure.total_fee
        except FeeStructure.DoesNotExist:
            total_fee = 0
            fee_structure = None
    else:
        total_fee = 0
        fee_structure = None
    
    payments = Payment.objects.filter(student=student).order_by('-date')
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
    balance = total_fee - total_paid
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        alignment=1
    )
    
    # School header
    if school_settings and school_settings.logo:
        try:
            logo_path = school_settings.logo.path
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
                elements.append(logo)
        except:
            pass
    
    school_name = school_settings.name if school_settings else "SCHOOL MANAGEMENT SYSTEM"
    school_address = school_settings.address if school_settings else ""
    school_phone = school_settings.phone if school_settings else ""
    
    header_text = f"""
    <b><font size="16">{school_name}</font></b><br/>
    <font size="11">{school_address}</font><br/>
    <font size="10">Phone: {school_phone}</font>
    """
    elements.append(Paragraph(header_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Title
    elements.append(Paragraph("OFFICIAL FEE STATEMENT", title_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Student and Parent Information
    info_text = f"""
    <b>Statement For:</b> {parent.full_name} ({parent.relationship})<br/>
    <b>Phone:</b> {parent.phone} | <b>Email:</b> {parent.email}<br/>
    <b>Student:</b> {student.full_name} | <b>Class:</b> {student.classroom}<br/>
    <b>Admission No:</b> {student.registration_number}<br/>
    <b>Statement Date:</b> {timezone.now().strftime('%d/%m/%Y %I:%M %p')}
    """
    elements.append(Paragraph(info_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Fee Summary
    elements.append(Paragraph("<b>FEE SUMMARY</b>", styles['Heading2']))
    
    summary_data = [
        ['DESCRIPTION', 'AMOUNT (TZS)'],
        ['Total Annual Fee', f"{total_fee:,.2f}"],
        ['Total Amount Paid', f"{total_paid:,.2f}"],
        ['Balance Outstanding', f"{balance:,.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd')),
        ('BACKGROUND', (0, 3), (-1, 3), 
         colors.HexColor('#ffebee') if balance > 0 else colors.HexColor('#e8f5e9')),
        ('TEXTCOLOR', (0, 3), (-1, 3), 
         colors.red if balance > 0 else colors.darkgreen),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Fee Breakdown if available
    if fee_structure:
        elements.append(Paragraph("<b>FEE BREAKDOWN</b>", styles['Heading2']))
        
        breakdown_data = [
            ['FEE ITEM', 'AMOUNT (TZS)']
        ]
        
        if fee_structure.tuition_fee > 0:
            breakdown_data.append(['Tuition Fee', f"{fee_structure.tuition_fee:,.2f}"])
        if fee_structure.exam_fee > 0:
            breakdown_data.append(['Examination Fee', f"{fee_structure.exam_fee:,.2f}"])
        if fee_structure.library_fee > 0:
            breakdown_data.append(['Library Fee', f"{fee_structure.library_fee:,.2f}"])
        if fee_structure.sports_fee > 0:
            breakdown_data.append(['Sports Fee', f"{fee_structure.sports_fee:,.2f}"])
        if fee_structure.lab_fee > 0:
            breakdown_data.append(['Laboratory Fee', f"{fee_structure.lab_fee:,.2f}"])
        if fee_structure.activity_fee > 0:
            breakdown_data.append(['Activity Fee', f"{fee_structure.activity_fee:,.2f}"])
        if fee_structure.other_charges > 0:
            breakdown_data.append(['Other Charges', f"{fee_structure.other_charges:,.2f}"])
        
        breakdown_data.append(['<b>TOTAL FEE</b>', f"<b>{total_fee:,.2f}</b>"])
        
        breakdown_table = Table(breakdown_data, colWidths=[4*inch, 2*inch])
        breakdown_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 1, colors.HexColor('#ddd')),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#2c3e50')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        elements.append(breakdown_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Payment History
    if payments.exists():
        elements.append(Paragraph("<b>PAYMENT HISTORY</b>", styles['Heading2']))
        
        payment_data = [['DATE', 'RECEIPT NO', 'MODE', 'AMOUNT (TZS)', 'STATUS']]
        
        for payment in payments[:15]:  # Last 15 payments
            status = "Verified" if payment.is_verified else "Pending"
            status_color = colors.green if payment.is_verified else colors.orange
            
            payment_data.append([
                payment.date.strftime("%d/%m/%Y"),
                payment.receipt_no,
                payment.payment_mode,
                f"{payment.amount_paid:,.2f}",
                status
            ])
        
        payment_table = Table(payment_data, colWidths=[1*inch, 1.5*inch, 1*inch, 1.2*inch, 1*inch])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd')),
        ]))
        
        elements.append(payment_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Payment Summary
        elements.append(Paragraph("<b>PAYMENT SUMMARY</b>", styles['Heading2']))
        
        verified_total = payments.filter(is_verified=True).aggregate(total=Sum('amount_paid'))['total'] or 0
        pending_total = payments.filter(is_verified=False).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        payment_summary_data = [
            ['Verified Payments', f"{verified_total:,.2f}"],
            ['Pending Payments', f"{pending_total:,.2f}"],
            ['Total Payments', f"{total_paid:,.2f}"]
        ]
        
        payment_summary_table = Table(payment_summary_data, colWidths=[3*inch, 3*inch])
        payment_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e67e22')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.white),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(payment_summary_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Footer Notes
    elements.append(Paragraph("_" * 100, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    notes_text = f"""
    <font size="9">
    <b>IMPORTANT NOTES:</b><br/>
    1. This is an official fee statement for parent records.<br/>
    2. All amounts are in Tanzanian Shillings (TZS).<br/>
    3. Please keep this document for your reference.<br/>
    4. For any discrepancies, contact accounts office within 7 days.<br/>
    5. All payments should be made to authorized bank accounts only.<br/>
    6. Late payments may attract penalty charges.<br/>
    <br/>
    <i>Generated for: {parent.full_name}</i><br/>
    <i>Date: {timezone.now().strftime('%d %B, %Y')}</i><br/>
    <i>Document ID: FS-{student.registration_number}-{timezone.now().strftime('%Y%m%d%H%M')}</i>
    </font>
    """
    
    elements.append(Paragraph(notes_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create HTTP response with PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"Fee_Statement_{student.registration_number}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response


# ==================== ANNOUNCEMENTS VIEWS ====================

@login_required
@permission_required('parents.view_school_announcements', raise_exception=True)
def announcements(request):
    """View school announcements"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    # Get filter parameters
    filter_type = request.GET.get('type')
    filter_audience = request.GET.get('audience')
    search_query = request.GET.get('search', '')
    
    # Get announcements queryset
    announcements_qs = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        is_published=True
    )
    
    # Apply filters
    if filter_type and filter_type != 'ALL':
        announcements_qs = announcements_qs.filter(announcement_type=filter_type)
    
    if filter_audience and filter_audience != 'ALL':
        announcements_qs = announcements_qs.filter(audience=filter_audience)
    
    if search_query:
        announcements_qs = announcements_qs.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(posted_by__username__icontains=search_query)
        )
    
    # Order by created date descending
    announcements_qs = announcements_qs.order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(announcements_qs, 10)  # 10 announcements per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get announcement types for filter
    announcement_types = Announcement.ANNOUNCEMENT_TYPE_CHOICES
    audience_types = Announcement.AUDIENCE_CHOICES
    
    # Get important announcements (pinned)
    important_announcements = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        is_published=True,
        is_pinned=True
    ).order_by('-created_at')[:5]
    
    # Get upcoming events
    upcoming_events = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        announcement_type='EVENT',
        is_published=True,
        event_date__gte=timezone.now().date()
    ).order_by('event_date')[:5]
    
    context = {
        'parent': parent,
        'announcements': page_obj,
        'paginator': paginator,
        'page_obj': page_obj,
        'important_announcements': important_announcements,
        'upcoming_events': upcoming_events,
        'announcement_types': announcement_types,
        'audience_types': audience_types,
        'filter': {
            'type': filter_type,
            'audience': filter_audience,
            'search': search_query
        },
        'title': 'School Announcements'
    }
    
    return render(request, 'parents/announcements.html', context)


@login_required
@permission_required('parents.view_school_announcements', raise_exception=True)
def announcement_detail(request, announcement_id):
    """View announcement detail"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    announcement = get_object_or_404(
        Announcement,
        id=announcement_id,
        is_published=True,
        audience__in=['PARENTS', 'ALL']
    )
    
    # Get related announcements
    related_announcements = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        is_published=True,
        announcement_type=announcement.announcement_type
    ).exclude(id=announcement.id).order_by('-created_at')[:5]
    
    context = {
        'parent': parent,
        'announcement': announcement,
        'related_announcements': related_announcements,
        'title': announcement.title
    }
    
    return render(request, 'parents/announcement_detail.html', context)


# ==================== PROFILE VIEWS ====================

@login_required
def profile(request):
    """Parent profile view and update"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('home')
    
    if request.method == 'POST':
        parent_form = ParentProfileForm(request.POST, request.FILES, instance=parent)
        user_form = UserUpdateForm(request.POST, instance=request.user)
        
        if parent_form.is_valid() and user_form.is_valid():
            parent_form.save()
            user_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('parents:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        parent_form = ParentProfileForm(instance=parent)
        user_form = UserUpdateForm(instance=request.user)
    
    # Get profile statistics
    children_count = parent.children_count
    total_balance = parent.get_full_family_balance()
    
    # Get last login IP (if available)
    last_login_ip = request.META.get('REMOTE_ADDR', 'Unknown')
    
    # Get account activity
    account_age = (timezone.now() - parent.created_at).days
    
    context = {
        'parent': parent,
        'parent_form': parent_form,
        'user_form': user_form,
        'children_count': children_count,
        'total_balance': total_balance,
        'last_login_ip': last_login_ip,
        'account_age': account_age,
        'title': 'My Profile'
    }
    
    return render(request, 'parents/profile.html', context)


@login_required
def change_password(request):
    """Change password view"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('parents:dashboard')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('parents:profile')
        
        # Validate new password
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('parents:profile')
        
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('parents:profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Your password has been changed successfully!")
        return redirect('parents:profile')
    
    return redirect('parents:profile')


# ==================== API VIEWS ====================

@login_required
def get_dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        return JsonResponse({'error': 'Parent not found'}, status=404)
    
    # Get statistics
    children_count = parent.children_count
    attendance_summary = parent.get_attendance_summary()
    fee_summary = parent.get_fee_summary()
    
    # Calculate averages
    if attendance_summary:
        avg_attendance = sum(item['percentage'] for item in attendance_summary) / len(attendance_summary)
    else:
        avg_attendance = 0
    
    total_balance = sum(item['balance'] for item in fee_summary)
    
    # Get recent announcements count
    recent_announcements_count = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        is_published=True,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Get upcoming events count
    upcoming_events_count = Announcement.objects.filter(
        Q(audience='PARENTS') | Q(audience='ALL'),
        announcement_type='EVENT',
        is_published=True,
        event_date__gte=timezone.now().date()
    ).count()
    
    stats = {
        'children_count': children_count,
        'avg_attendance': round(avg_attendance, 1),
        'total_balance': total_balance,
        'recent_announcements': recent_announcements_count,
        'upcoming_events': upcoming_events_count,
        'today': timezone.now().strftime('%Y-%m-%d')
    }
    
    return JsonResponse({'stats': stats})


@login_required
def get_child_list(request):
    """API endpoint for child list"""
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        return JsonResponse({'error': 'Parent not found'}, status=404)
    
    children = []
    for student in parent.students.all():
        children.append({
            'id': student.id,
            'name': student.full_name,
            'class': str(student.classroom) if student.classroom else 'N/A',
            'registration_number': student.registration_number,
            'avatar_initials': student.full_name[:2].upper() if len(student.full_name) >= 2 else student.full_name[0].upper()
        })
    
    return JsonResponse({'children': children})


# ==================== ERROR HANDLERS ====================

def parent_404(request, exception):
    """Custom 404 page for parent app"""
    return render(request, 'parents/404.html', status=404)


def parent_500(request):
    """Custom 500 page for parent app"""
    return render(request, 'parents/500.html', status=500)


# Add these imports at the top
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import ParentRegistrationForm, ParentApprovalForm

# ==================== REGISTRATION VIEWS ====================

def parent_register(request):
    """Parent registration view"""
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        try:
            parent = Parent.objects.get(user=request.user)
            return redirect('parents:dashboard')
        except Parent.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = ParentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                parent = form.save()
                
                # Send notification email to admin
                send_registration_notification_to_admin(parent)
                
                # Send confirmation email to parent
                send_registration_confirmation_email(parent)
                
                messages.success(request, """
                    Registration successful! 
                    Your account has been created and is pending approval.
                    You will receive an email notification once your account is approved.
                    Please contact the school administration for any questions.
                """)
                
                return redirect('parents:registration_success')
                
            except Exception as e:
                messages.error(request, f"Registration failed: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ParentRegistrationForm()
    
    # Get school settings
    school_settings = SchoolSettings.objects.first()
    
    context = {
        'form': form,
        'school_settings': school_settings,
        'title': 'Parent Registration',
        'registration_open': True,  # You can add a setting for this
    }
    
    return render(request, 'parents/register.html', context)


def registration_success(request):
    """Registration success page"""
    school_settings = SchoolSettings.objects.first()
    
    context = {
        'school_settings': school_settings,
        'title': 'Registration Successful',
    }
    
    return render(request, 'parents/registration_success.html', context)


def registration_closed(request):
    """Registration closed page"""
    school_settings = SchoolSettings.objects.first()
    
    context = {
        'school_settings': school_settings,
        'title': 'Registration Closed',
    }
    
    return render(request, 'parents/registration_closed.html', context)