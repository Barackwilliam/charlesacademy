from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from io import BytesIO
import os
import mimetypes
from .models import Student, Certificate
from classes.models import ClassRoom
from dashboard.models import SchoolSettings
from accounts.decorators import role_required

# For PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# students/views.py - PDF Download Fix
@login_required
@role_required(['ADMIN', 'TEACHER'])
def student_list(request):
    """View and filter students with PDF download option"""
    # Check if this is a PDF download request
    if request.GET.get('download') == 'pdf':
        return download_students_pdf(request)
    
    # Get school settings
    settings_obj = SchoolSettings.objects.first()
    
    # Start with all students
    students_queryset = Student.objects.all().select_related('classroom')
    
    # Get filter parameters
    filter_class = request.GET.get('class', '')
    filter_status = request.GET.get('status', '')
    filter_year = request.GET.get('year', '')
    search_query = request.GET.get('search', '')
    
    # Apply filters if provided
    if filter_class:
        students_queryset = students_queryset.filter(classroom__id=filter_class)
    
    if filter_status and filter_status != 'ALL':
        students_queryset = students_queryset.filter(status=filter_status)
    
    if filter_year:
        students_queryset = students_queryset.filter(admission_year=filter_year)
    
    if search_query:
        students_queryset = students_queryset.filter(
            Q(full_name__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(classroom__name__icontains=search_query)
        )
    
    # Calculate statistics
    total_count = students_queryset.count()
    active_count = students_queryset.filter(status='ACTIVE').count()
    
    # Get unique classes
    class_set = set()
    for student in students_queryset:
        if student.classroom and student.classroom.name:
            class_set.add(student.classroom.name)
    class_count = len(class_set)
    
    # Count students with email
    email_count = students_queryset.exclude(email__isnull=True).exclude(email='').count()
    
    # Get all classes for dropdown
    all_classes = ClassRoom.objects.all()
    
    # Get available years
    admission_years = Student.objects.values_list('admission_year', flat=True).distinct().order_by('-admission_year')
    
    # Get status choices
    status_choices = Student.STATUS_CHOICES
    
    context = {
        'school_settings': settings_obj,
        'students': students_queryset,
        'all_classes': all_classes,
        'admission_years': admission_years,
        'status_choices': status_choices,
        'filter_class': filter_class,
        'filter_status': filter_status,
        'filter_year': filter_year,
        'search_query': search_query,
        'total_count': total_count,
        'active_count': active_count,
        'class_count': class_count,
        'email_count': email_count,
    }
    
    return render(request, 'students/list.html', context)


@login_required
@role_required(['ADMIN', 'TEACHER'])
def download_students_pdf(request):
    """Generate and download PDF of filtered students"""
    # Get filter parameters from request
    filter_class = request.GET.get('class', '')
    filter_status = request.GET.get('status', '')
    filter_year = request.GET.get('year', '')
    search_query = request.GET.get('search', '')
    
    # Apply the same filters as student_list
    students_queryset = Student.objects.all().select_related('classroom')
    
    if filter_class:
        students_queryset = students_queryset.filter(classroom__id=filter_class)
    
    if filter_status and filter_status != 'ALL':
        students_queryset = students_queryset.filter(status=filter_status)
    
    if filter_year:
        students_queryset = students_queryset.filter(admission_year=filter_year)
    
    if search_query:
        students_queryset = students_queryset.filter(
            Q(full_name__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(classroom__name__icontains=search_query)
        )
    
    # Get school settings
    school_settings = SchoolSettings.objects.first()
    
    # Create PDF in memory
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
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        alignment=1
    )
    
    # School information
    school_name = school_settings.name if school_settings else "School System"
    # school_address = school_settings.address if school_settings else ""
    
    # Header
    header_text = f"""
    <b><font size="16">{school_name}</font></b><br/>
    <font size="10">Student List Report</font>
    """
    elements.append(Paragraph(header_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Report title
    title_text = "STUDENTS LIST"
    if filter_class:
        try:
            classroom = ClassRoom.objects.get(id=filter_class)
            title_text = f"STUDENTS LIST - {classroom.name.upper()}"
        except:
            pass
    
    elements.append(Paragraph(title_text, title_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Filter information
    filter_info = []
    filter_info.append(f"Total Students: {students_queryset.count()}")
    if filter_status and filter_status != 'ALL':
        filter_info.append(f"Status: {filter_status}")
    if filter_year:
        filter_info.append(f"Year: {filter_year}")
    if filter_info:
        filter_text = " | ".join(filter_info)
        elements.append(Paragraph(f"<i>{filter_text}</i>", styles['Normal']))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Students table
    if students_queryset.exists():
        # Table header
        table_data = [
            ['No.', 'Name', 'Reg. No', 'Class', 'Status', 'Email']
        ]
        
        # Add student rows
        for idx, student in enumerate(students_queryset, 1):
            status_display = student.get_status_display()
            status_color = colors.black
            
            if student.status == 'ACTIVE':
                status_color = colors.green
            elif student.status == 'GRADUATED':
                status_color = colors.blue
            elif student.status == 'TRANSFERRED':
                status_color = colors.orange
            
            table_data.append([
                str(idx),
                student.full_name[:30],  # Limit name length
                student.registration_number,
                student.classroom.name if student.classroom else "-",
                status_display,
                student.email or "-"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.5*inch, 2*inch, 1.5*inch, 1.2*inch, 1*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        elements.append(table)
    else:
        elements.append(Paragraph("No students found.", styles['Normal']))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_text = f"""
    <font size="8">
    Generated: {timezone.now().strftime('%d/%m/%Y %H:%M')}<br/>
    Report ID: STU-{timezone.now().strftime('%Y%m%d%H%M')}
    </font>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    
    # Create filename
    filename = f"students_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


from .utils import generate_registration_number, create_student_user, send_student_credentials  # <-- Add send_student_credentials

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from classes.models import ClassRoom
from .models import Student
from .utils import (
    create_student_user, 
    send_student_credentials,
    get_next_registration_sequence,
    generate_registration_number
)
import logging
import re

logger = logging.getLogger(__name__)

@login_required
@permission_required('students.add_student', raise_exception=True)
def add_student(request):
    """Add new student with automatic user creation"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                full_name = request.POST.get('full_name', '').strip()
                email = request.POST.get('email', '').strip().lower()
                classroom_id = request.POST.get('classroom')
                admission_year = request.POST.get('admission_year', timezone.now().year)
                status = request.POST.get('status', 'ACTIVE')
                
                # Validate required fields
                if not all([full_name, email, classroom_id]):
                    messages.error(request, "All fields are required")
                    return redirect('students:add_student')
                
                # Get classroom
                try:
                    classroom = ClassRoom.objects.get(id=classroom_id)
                except ClassRoom.DoesNotExist:
                    messages.error(request, "Invalid class selected")
                    return redirect('students:add_student')
                
                # Validate email format
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    messages.error(request, "Invalid email format")
                    return redirect('students:add_student')
                
                # Check if email exists
                if Student.objects.filter(email__iexact=email).exists():
                    messages.error(request, "Email already registered")
                    return redirect('students:add_student')
                
                # Handle registration number
                reg_number = request.POST.get('registration_number', '').strip().upper()
                
                if reg_number:
                    # Validate custom registration number
                    if not re.match(r'^CA/[A-Z]+/\d{4}/\d{4}$', reg_number):
                        messages.error(request, 
                            "Invalid registration number format. Use: CA/CLASS/YEAR/NUMBER (e.g., CA/CS1/2024/0001)")
                        return redirect('students:add_student')
                    
                    # Check if registration number exists
                    if Student.objects.filter(registration_number__iexact=reg_number).exists():
                        messages.error(request, "Registration number already exists")
                        return redirect('students:add_student')
                else:
                    # Generate registration number
                    try:
                        admission_year = int(admission_year)
                        sequence = get_next_registration_sequence(classroom.code, admission_year)
                        reg_number = generate_registration_number(
                            classroom.code, 
                            admission_year, 
                            sequence
                        )
                    except Exception as e:
                        logger.error(f"Error generating reg number: {e}")
                        messages.error(request, "Error generating registration number")
                        return redirect('students:add_student')
                
                # Create student object
                student = Student(
                    full_name=full_name,
                    email=email,
                    classroom=classroom,
                    admission_year=admission_year,
                    registration_number=reg_number,
                    status=status
                )
                
                # Handle file uploads
                if 'photo' in request.FILES:
                    student.photo = request.FILES['photo']
                
                if 'documents' in request.FILES:
                    student.documents = request.FILES['documents']
                
                # Save student
                student.save()
                
                # Create user account
                user = create_student_user(student)
                
                if user:
                    # Send credentials email
                    password = f"{student.get_first_name()}@123"
                    email_sent = send_student_credentials(student, user, password, request)
                    
                    if email_sent:
                        messages.success(request, 
                            f"Student '{student.full_name}' registered successfully! "
                            f"Credentials sent to {student.email}")
                    else:
                        messages.success(request, 
                            f"Student '{student.full_name}' registered successfully! "
                            f"Username: {user.username}, Password: {password}")
                else:
                    messages.warning(request, 
                        f"Student '{student.full_name}' registered but user account creation failed. "
                        "Please contact administrator.")
                
                return redirect('students:student_list')
                
        except IntegrityError as e:
            if 'unique' in str(e).lower():
                messages.error(request, "Registration number or email already exists")
            else:
                messages.error(request, "Database error occurred")
            logger.error(f"Integrity error: {e}")
            
        except ValidationError as e:
            messages.error(request, str(e))
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            logger.error(f"Add student error: {e}", exc_info=True)
    
    # GET request - show form
    context = {
        'classes': ClassRoom.objects.all().order_by('name'),
        'current_year': timezone.now().year,
        'years': range(timezone.now().year - 5, timezone.now().year + 3)
    }
    return render(request, 'students/add.html', context)

@login_required
@permission_required('students.change_student', raise_exception=True)
def reset_student_password(request, student_id):
    """Reset student password"""
    try:
        student = get_object_or_404(Student, id=student_id)
        
        if not student.user:
            messages.error(request, "Student does not have a user account")
            return redirect('students:student_list')
        
        # Generate new password
        new_password = f"{student.get_first_name()}@123"
        
        # Update password
        student.user.set_password(new_password)
        student.user.save()
        
        # Send new credentials
        send_student_credentials(student, student.user, new_password, request)
        
        messages.success(request, 
            f"Password reset for {student.full_name}. "
            f"New password: {new_password}")
            
    except Exception as e:
        messages.error(request, f"Error resetting password: {str(e)}")
        logger.error(f"Password reset error: {e}")
    
    return redirect('students:student_list')

@login_required
@permission_required('students.add_student', raise_exception=True)
def bulk_create_users(request):
    """Create user accounts for students without users"""
    if request.method == 'POST':
        try:
            students_without_users = Student.objects.filter(user__isnull=True)
            
            if not students_without_users.exists():
                messages.info(request, "All students already have user accounts")
                return redirect('students:student_list')
            
            success_count = 0
            failed_count = 0
            
            for student in students_without_users:
                try:
                    create_student_user(student)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to create user for {student.registration_number}: {e}")
                    failed_count += 1
            
            messages.success(request, 
                f"Created {success_count} user accounts. "
                f"{failed_count} failed.")
                
        except Exception as e:
            messages.error(request, f"Bulk operation failed: {str(e)}")
    
    return redirect('students:student_list')


def delete_student(request, id):
    settings_obj = SchoolSettings.objects.first()

    Student.objects.filter(id=id).delete()
    return redirect('students:student_list')

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Student
from classes.models import ClassRoom  # ← Hii imekosekana!
from dashboard.models import SchoolSettings  # ← Na hii pia!

@login_required  # ← Usisahau kuongeza decorator
def edit_student(request, id):
    """Edit student information"""
    student = get_object_or_404(Student, id=id)
    
    # Handle case where SchoolSettings doesn't exist
    try:
        settings_obj = SchoolSettings.objects.first()
    except:
        settings_obj = None
    
    if request.method == 'POST':
        try:
            # Get form data
            full_name = request.POST.get('full_name', '').strip()
            classroom_id = request.POST.get('classroom')
            status = request.POST.get('status', 'ACTIVE')
            email = request.POST.get('email', '').strip()
            
            # Validate required fields
            if not full_name:
                messages.error(request, "Full name is required")
                return redirect('students:edit_student', id=id)
            
            # Update student info
            student.full_name = full_name
            student.email = email
            student.status = status
            
            # Update classroom if provided
            if classroom_id:
                try:
                    classroom = ClassRoom.objects.get(id=classroom_id)
                    student.classroom = classroom
                except ClassRoom.DoesNotExist:
                    messages.warning(request, "Selected class not found, keeping previous class")
            
            # Handle file uploads (if any in form)
            if 'photo' in request.FILES:
                # Delete old photo if exists
                if student.photo:
                    student.photo.delete(save=False)
                student.photo = request.FILES['photo']
                
            if 'documents' in request.FILES:
                if student.documents:
                    student.documents.delete(save=False)
                student.documents = request.FILES['documents']
            
            # Save the student
            student.save()
            
            # Check if email changed and send notification
            old_email = student.email
            if email and email != old_email and student.user:
                try:
                    from .utils import send_student_credentials
                    # Generate new password or use existing
                    new_password = f"{student.get_first_name()}@123"
                    student.user.set_password(new_password)
                    student.user.save()
                    send_student_credentials(student, student.user, new_password, request)
                    messages.info(request, f"New credentials sent to {email}")
                except Exception as e:
                    messages.warning(request, f"Student updated but email notification failed: {str(e)}")
            
            messages.success(request, f"Student '{student.full_name}' updated successfully!")
            return redirect('students:student_list')
            
        except Exception as e:
            messages.error(request, f"Error updating student: {str(e)}")
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Edit student error: {e}", exc_info=True)
    
    # GET request - show form with current data
    context = {
        'student': student,
        'school_settings': settings_obj,
        'classes': ClassRoom.objects.all().order_by('name'),
        'status_choices': Student.STATUS_CHOICES,
    }
    
    return render(request, 'students/edit.html', context)
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import os

from .models import Student
from dashboard.models import SchoolSettings


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b)


def draw_rounded_rect(cv, x, y, w, h, radius, fill=None, stroke=None, lw=0):
    cv.saveState()
    if fill:
        cv.setFillColorRGB(*fill)
    if stroke:
        cv.setStrokeColorRGB(*stroke)
        cv.setLineWidth(lw)
    path = cv.beginPath()
    path.moveTo(x + radius, y)
    path.lineTo(x + w - radius, y)
    path.arcTo(x + w - 2*radius, y,         x + w, y + 2*radius,         -90, 90)
    path.lineTo(x + w, y + h - radius)
    path.arcTo(x + w - 2*radius, y + h - 2*radius, x + w, y + h,           0, 90)
    path.lineTo(x + radius, y + h)
    path.arcTo(x, y + h - 2*radius, x + 2*radius, y + h,                  90, 90)
    path.lineTo(x, y + radius)
    path.arcTo(x, y, x + 2*radius, y + 2*radius,                         180, 90)
    path.close()
    cv.drawPath(path, fill=(1 if fill else 0), stroke=(1 if stroke else 0))
    cv.restoreState()


def draw_circle(cv, cx, cy, r, fill=None, stroke=None, lw=1):
    cv.saveState()
    if fill:
        cv.setFillColorRGB(*fill)
    if stroke:
        cv.setStrokeColorRGB(*stroke)
        cv.setLineWidth(lw)
    cv.circle(cx, cy, r, fill=(1 if fill else 0), stroke=(1 if stroke else 0))
    cv.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
#  Main view
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def download_id_card_pdf(request, student_id):
    """Generate beautiful university-style student ID card (credit-card size 85.6x54mm)."""

    # ── Fetch objects ─────────────────────────────────────────────────────────
    if request.user.role == 'STUDENT':
        student = get_object_or_404(Student, user=request.user, id=student_id)
    else:
        student = get_object_or_404(Student, id=student_id)

    try:
        school_settings = SchoolSettings.objects.first()
    except Exception:
        school_settings = None

    # ── Color palette ─────────────────────────────────────────────────────────
    theme_hex = (
        school_settings.theme_color
        if school_settings and school_settings.theme_color
        else '#1a237e'
    )
    primary  = hex_to_rgb(theme_hex)
    accent   = tuple(min(1.0, v * 0.55 + 0.45) for v in primary)
    dark     = tuple(max(0.0, v * 0.68) for v in primary)
    WHITE    = (1.0, 1.0, 1.0)
    MID_GREY = (0.52, 0.52, 0.58)
    GOLD     = (1.0, 0.80, 0.18)

    # ── School meta ───────────────────────────────────────────────────────────
    school_name   = school_settings.name          if school_settings else "CHARLES ACADEMY"
    academic_year = school_settings.academic_year if school_settings else str(timezone.now().year)

    # ── Student data ──────────────────────────────────────────────────────────
    full_name  = student.full_name.upper()
    reg_number = student.registration_number

    # Subject: query Subject model linked to student classroom
    subject = 'N/A'
    if student.classroom:
        from classes.models import Subject
        subjects = Subject.objects.filter(classroom=student.classroom).values_list('name', flat=True)
        if subjects.exists():
            subject = ', '.join(subjects[:3])  # max 3 subjects
        else:
            subject = student.classroom.name   # fallback to class name
    if len(subject) > 30:
        subject = subject[:30] + '...' 

    adm_year = str(student.admission_year) if student.admission_year else str(timezone.now().year)

    # ── Canvas setup ──────────────────────────────────────────────────────────
    W = 85.6 * mm
    H = 54.0 * mm
    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=(W, H))
    cv.setTitle("Student ID Card")

    # ══════════════════════════════════════════════════════════════════════════
    #  BACKGROUND
    # ══════════════════════════════════════════════════════════════════════════
    cv.setFillColorRGB(*WHITE)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    HEADER_H = H * 0.42

    # Header solid band
    cv.setFillColorRGB(*primary)
    cv.rect(0, H - HEADER_H, W, HEADER_H, fill=1, stroke=0)

    # Decorative parallelograms on header
    cv.saveState()
    lighter = tuple(min(1.0, v + 0.10) for v in primary)
    cv.setFillColorRGB(*lighter)
    for i in range(7):
        xs = -12 * mm + i * 17 * mm
        p = cv.beginPath()
        p.moveTo(xs,           H - HEADER_H)
        p.lineTo(xs + 9 * mm,  H - HEADER_H)
        p.lineTo(xs + 12 * mm, H)
        p.lineTo(xs + 3 * mm,  H)
        p.close()
        cv.drawPath(p, fill=1, stroke=0)
    cv.restoreState()

    # Decorative circles top-right
    cv.saveState()
    cv.setFillColorRGB(*tuple(min(1.0, v + 0.18) for v in primary))
    cv.circle(W - 7 * mm, H - 3 * mm, 11 * mm, fill=1, stroke=0)
    cv.setFillColorRGB(*tuple(min(1.0, v + 0.26) for v in primary))
    cv.circle(W - 1 * mm, H - 9 * mm,  7 * mm, fill=1, stroke=0)
    cv.restoreState()

    # Gold stripe below header
    STRIPE_H = 2.2 * mm
    cv.setFillColorRGB(*GOLD)
    cv.rect(0, H - HEADER_H - STRIPE_H, W, STRIPE_H, fill=1, stroke=0)

    # Footer band
    FOOTER_H = 7 * mm
    cv.setFillColorRGB(*dark)
    cv.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)

    # Accent circle in footer-left
    draw_circle(cv, 5 * mm, FOOTER_H / 2, 3.5 * mm, fill=accent)

    # Info section boundaries
    INFO_TOP    = H - HEADER_H - STRIPE_H
    INFO_BOTTOM = FOOTER_H
    INFO_H      = INFO_TOP - INFO_BOTTOM

    # ══════════════════════════════════════════════════════════════════════════
    #  HEADER: SCHOOL LOGO  +  SCHOOL NAME
    # ══════════════════════════════════════════════════════════════════════════
    LOGO_CX = 10 * mm
    LOGO_CY = H - HEADER_H / 2
    LOGO_R  = 8.5 * mm

    # White halo behind logo
    draw_circle(cv, LOGO_CX, LOGO_CY, LOGO_R + 1.4 * mm, fill=WHITE)

    # Load logo from static/images/logo.jpeg
    logo_drawn = False
    from django.conf import settings as django_settings
    from django.contrib.staticfiles import finders
    logo_path = finders.find('images/logo.jpeg')

    if logo_path and os.path.exists(logo_path):
        try:
            reader = ImageReader(logo_path)
            cv.saveState()
            clip = cv.beginPath()
            clip.circle(LOGO_CX, LOGO_CY, LOGO_R)
            cv.clipPath(clip, stroke=0)
            side = LOGO_R * 2
            cv.drawImage(reader,
                         LOGO_CX - LOGO_R, LOGO_CY - LOGO_R,
                         width=side, height=side,
                         preserveAspectRatio=True, mask='auto')
            cv.restoreState()
            logo_drawn = True
        except Exception:
            pass

    if not logo_drawn:
        # Fallback: accent-colored circle with school initials
        draw_circle(cv, LOGO_CX, LOGO_CY, LOGO_R, fill=accent)
        initials = ''.join(word[0].upper() for word in school_name.split()[:3])
        fs = 10 if len(initials) <= 2 else 7.5
        cv.saveState()
        cv.setFillColorRGB(*WHITE)
        cv.setFont('Helvetica-Bold', fs)
        cv.drawCentredString(LOGO_CX, LOGO_CY - fs * 0.36, initials)
        cv.restoreState()

    # School name + subtitle text (right of logo)
    TEXT_X = LOGO_CX + LOGO_R + 3 * mm
    cv.saveState()
    cv.setFillColorRGB(*WHITE)
    disp_name = school_name[:22] + ('...' if len(school_name) > 22 else '')
    cv.setFont('Helvetica-Bold', 8.5)
    cv.drawString(TEXT_X, H - 9 * mm, disp_name)

    cv.setFillColorRGB(*tuple(min(1.0, v + 0.38) for v in primary))
    cv.setFont('Helvetica', 5.5)
    cv.drawString(TEXT_X, H - 13.5 * mm, "SCHOOL IDENTIFICATION CARD")

    # Gold "STUDENT ID" badge pill
    BX, BY, BW, BH = TEXT_X, H - 19 * mm, 20 * mm, 4.5 * mm
    draw_rounded_rect(cv, BX, BY, BW, BH, radius=1 * mm, fill=GOLD)
    cv.setFillColorRGB(*dark)
    cv.setFont('Helvetica-Bold', 5.5)
    cv.drawCentredString(BX + BW / 2, BY + 1.2 * mm, "STUDENT ID")
    cv.restoreState()

    # ══════════════════════════════════════════════════════════════════════════
    #  INFO ROWS  (full-width layout — no photo column)
    # ══════════════════════════════════════════════════════════════════════════
    LX      = 4 * mm
    LABEL_W = 17 * mm
    VAL_X   = LX + LABEL_W + 1.5 * mm

    def draw_row(label, value, y, bold_val=False, val_color=None, tinted=False):
        cv.saveState()
        if tinted:
            tint = tuple(min(1.0, v * 0.05 + 0.95) for v in primary)
            cv.setFillColorRGB(*tint)
            cv.rect(LX - 1 * mm, y - 1.6 * mm, W - LX - 2 * mm, 5 * mm, fill=1, stroke=0)

        # Gold bullet dot
        cv.setFillColorRGB(*GOLD)
        cv.circle(LX - 0.8 * mm, y + 1.3 * mm, 0.75 * mm, fill=1, stroke=0)

        # Label text
        cv.setFillColorRGB(*MID_GREY)
        cv.setFont('Helvetica', 5.5)
        cv.drawString(LX + 0.8 * mm, y, label.upper())
        cv.drawString(LX + LABEL_W, y, ':')

        # Value text
        vc = val_color if val_color else (0.08, 0.08, 0.08)
        cv.setFillColorRGB(*vc)
        cv.setFont('Helvetica-Bold' if bold_val else 'Helvetica', 6.5)
        cv.drawString(VAL_X, y, str(value))
        cv.restoreState()

    BASE_Y  = INFO_BOTTOM + INFO_H - 3.5 * mm
    ROW_GAP = INFO_H / 5.8

    # Subtle horizontal dividers between rows
    cv.saveState()
    cv.setStrokeColorRGB(0.87, 0.87, 0.92)
    cv.setLineWidth(0.35)
    for i in range(1, 5):
        ly = BASE_Y - i * ROW_GAP + 1.3 * mm
        cv.line(LX, ly, W - 3 * mm, ly)
    cv.restoreState()

    name_disp = full_name[:28] + ('...' if len(full_name) > 28 else '')

    draw_row("Full Name",  name_disp,      BASE_Y,               bold_val=True, val_color=primary, tinted=True)
    draw_row("Reg No",     reg_number,     BASE_Y - ROW_GAP)
    draw_row("Subject",    subject,        BASE_Y - 2 * ROW_GAP, val_color=dark,                   tinted=True)
    draw_row("Adm. Year",  adm_year,       BASE_Y - 3 * ROW_GAP)
    draw_row("Status",     student.status, BASE_Y - 4 * ROW_GAP, val_color=MID_GREY,               tinted=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  FOOTER TEXT
    # ══════════════════════════════════════════════════════════════════════════
    cv.saveState()
    cv.setFillColorRGB(*WHITE)
    cv.setFont('Helvetica-Bold', 5.5)
    cv.drawString(10 * mm, 2.2 * mm, f"VALID: {academic_year}")
    cv.setFont('Helvetica', 5)
    cv.setFillColorRGB(*tuple(min(1.0, v + 0.38) for v in dark))
    cv.drawRightString(W - 3 * mm, 2.2 * mm, f"ID: {reg_number[-8:]}")
    cv.restoreState()

    # Outer card border
    cv.saveState()
    cv.setStrokeColorRGB(*primary)
    cv.setLineWidth(1.0)
    cv.rect(0.5, 0.5, W - 1, H - 1, fill=0, stroke=1)
    cv.restoreState()

    cv.save()

    pdf = buf.getvalue()
    buf.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"ID_CARD_{reg_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ─────────────────────────────────────────────────────────────────────────────

@login_required
def my_id_card(request):
    """View student's own ID card in browser."""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('dashboard')

    school_settings = SchoolSettings.objects.first()
    return render(request, 'students/id_card_view.html', {
        'student': student,
        'school_settings': school_settings,
    })
    
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
from django.utils import timezone
from dashboard.models import SchoolSettings
from students.models import Student
from exams.models import Result, Exam


@login_required
def student_portal(request):
    settings_obj = SchoolSettings.objects.first()

    user = request.user
    
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('home')
    
    # Get student results from exams app
    results = Result.objects.filter(student=student).select_related('exam', 'subject')
    # Calculate average marks if results exist
    average_marks = 0
    if results.exists():
        total_marks = sum([r.marks for r in results if r.marks])
        average_marks = total_marks / results.count()
    
    # Get unique exams for this student
    exams = Exam.objects.filter(result__student=student).distinct()
    
    # Get attendance records
    attendance = student.attendance_set.all() if hasattr(student, 'attendance_set') else []

    return render(request, 'students/portal.html', {
        'student': student,
        'school_settings': settings_obj,
        'results': results,
        'exams': exams,
        'has_id_card': True,
        'attendance': attendance,
        'average_marks': round(average_marks, 2) if average_marks else 0,
        'has_results': results.exists(),
    })


def download_results_pdf(request):
    """Download student results as PDF"""
    user = request.user
    
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('students:student_portal')
    
    # Get student results from exams app
    results = Result.objects.filter(student=student).select_related('exam', 'subject')
    
    if not results.exists():
        messages.warning(request, "No results available to download.")
        return redirect('students:student_portal')
    
    # Get school settings
    try:
        school_settings = SchoolSettings.objects.first()
    except:
        school_settings = None
    
    # Group results by exam
    results_by_exam = {}
    for result in results:
        exam_name = result.exam.name if result.exam else "Unknown Exam"
        if exam_name not in results_by_exam:
            results_by_exam[exam_name] = []
        results_by_exam[exam_name].append(result)
    
    # Calculate statistics
    total_subjects = results.count()
    total_marks = sum([r.marks for r in results if r.marks])
    average_marks = total_marks / total_subjects if total_subjects > 0 else 0
    
    # Count grades using the grade() method from model
    grades_count = {}
    for result in results:
        grade_info = result.grade()
        grade = grade_info[0] if grade_info else 'N/A'
        grades_count[grade] = grades_count.get(grade, 0) + 1
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    elements = []
    
    # Custom Styles
    styles = getSampleStyleSheet()
    
    # Theme color from school settings
    theme_color = school_settings.theme_color if school_settings else '#4361ee'
    
    # Title Style
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor(theme_color),
        spaceAfter=15,
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    # Subtitle Style
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=10,
        alignment=1,
        fontName='Helvetica'
    )
    
    # Section Title Style
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor(theme_color),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    # Normal Style
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    # Bold Style
    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Footer Style
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
        fontName='Helvetica-Oblique'
    )
    
    # ========== HEADER SECTION ==========
    # School information
    school_name = school_settings.name if school_settings else "Charles Academy"
    phone = school_settings.phone if school_settings else "+255 123 456 789"
    email = school_settings.contact_email if school_settings else "admin@charlesacademy.edu"
    academic_year = school_settings.academic_year if school_settings else str(timezone.now().year)
    
    # School Header
    school_header = f"""
    <b><font size="18" color="{theme_color}">{school_name}</font></b><br/>
    <font size="11" color="#475569">ACADEMIC TRANSCRIPT</font><br/>
    <font size="9" color="#64748b">Phone: {phone} | Email: {email} | Academic Year: {academic_year}</font>
    """
    
    elements.append(Paragraph(school_header, normal_style))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("OFFICIAL EXAMINATION RESULTS", title_style))
    elements.append(Paragraph("Individual Academic Performance Report", subtitle_style))
    
    # Document Info
    doc_info = f"""
    <b>Document No:</b> AT-{student.registration_number}-{timezone.now().strftime("%Y%m%d")} | 
    <b>Generated:</b> {timezone.now().strftime("%d/%m/%Y %I:%M %p")} |
    <b>Student ID:</b> {student.registration_number}
    """
    elements.append(Paragraph(doc_info, normal_style))
    elements.append(Spacer(1, 20))
    
    # ========== STUDENT INFORMATION ==========
    elements.append(Paragraph("STUDENT INFORMATION", section_style))
    
    student_data = [
        ['FULL NAME:', student.full_name, 'ADMISSION NO:', student.registration_number],
        ['CLASS:', str(student.classroom) if student.classroom else 'Not Assigned', 
         'ADMISSION YEAR:', str(student.admission_year)],
        ['STATUS:', student.status, 'REPORT DATE:', timezone.now().strftime("%d/%m/%Y")],
    ]
    
    student_table = Table(student_data, colWidths=[80, 150, 80, 130])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    ]))
    
    elements.append(student_table)
    elements.append(Spacer(1, 25))
    
    # ========== ACADEMIC SUMMARY ==========
    elements.append(Paragraph("ACADEMIC SUMMARY", section_style))
    
    # Get overall grade from average marks
    overall_grade_info = get_grade_info(average_marks)
    overall_grade = overall_grade_info[0] if overall_grade_info else 'N/A'
    overall_remark = overall_grade_info[1] if overall_grade_info else 'N/A'
    
    summary_data = [
        ['TOTAL SUBJECTS', 'AVERAGE MARKS', 'OVERALL GRADE', 'PERFORMANCE'],
        [str(total_subjects), f"{average_marks:.1f}/100", 
         overall_grade, 
         overall_remark]
    ]
    
    summary_table = Table(summary_data, colWidths=[120, 120, 120, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(theme_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8fafc')),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 15))
    
    # Grade Distribution
    if grades_count:
        grade_dist_text = "<b>Grade Distribution:</b> "
        for grade, count in grades_count.items():
            grade_dist_text += f"{grade}: {count} | "
        elements.append(Paragraph(grade_dist_text[:-3], normal_style))
    
    elements.append(Spacer(1, 20))
    
    # ========== DETAILED RESULTS BY EXAM ==========
    for exam_name, exam_results in results_by_exam.items():
        elements.append(Paragraph(f"EXAM: {exam_name.upper()}", section_style))
        
        # Prepare results data for this exam
        exam_results_data = [['SUBJECT', 'MARKS', 'GRADE', 'REMARKS']]
        total_exam_marks = 0
        
        for result in exam_results:
            grade_info = result.grade()
            grade = grade_info[0] if grade_info else 'N/A'
            remark = grade_info[1] if grade_info else 'N/A'
            exam_results_data.append([
                result.subject.name if result.subject else "Unknown Subject",
                f"{result.marks}/100",
                grade,
                remark
            ])
            total_exam_marks += result.marks
        
        # Calculate average for this exam
        exam_average = total_exam_marks / len(exam_results) if exam_results else 0
        exam_grade_info = get_grade_info(exam_average)
        
        results_table = Table(exam_results_data, colWidths=[150, 80, 80, 140])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(theme_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (2, 1), (2, -1), get_grade_color),
        ]))
        
        elements.append(results_table)
        
        # Exam summary
        exam_summary = f"""
        <b>Exam Average:</b> {exam_average:.1f}/100 | 
        <b>Overall Grade:</b> {exam_grade_info[0] if exam_grade_info else 'N/A'} | 
        <b>Subjects:</b> {len(exam_results)}
        """
        elements.append(Paragraph(exam_summary, normal_style))
        elements.append(Spacer(1, 20))
    
    # ========== PERFORMANCE ANALYSIS ==========
    elements.append(Paragraph("PERFORMANCE ANALYSIS", section_style))
    
    if results.exists():
        # Find top and lowest subjects across all exams
        all_results = list(results)
        top_result = max(all_results, key=lambda x: x.marks)
        lowest_result = min(all_results, key=lambda x: x.marks)
        
        analysis_data = [
            ['METRIC', 'SUBJECT', 'MARKS', 'ANALYSIS'],
            ['Strongest Subject', top_result.subject.name if top_result.subject else "Unknown", 
             f"{top_result.marks}/100", f"Excellent performance in {top_result.subject.name if top_result.subject else 'this subject'}"],
            ['Needs Improvement', lowest_result.subject.name if lowest_result.subject else "Unknown", 
             f"{lowest_result.marks}/100", f"Focus required in {lowest_result.subject.name if lowest_result.subject else 'this subject'}"]
        ]
        
        analysis_table = Table(analysis_data, colWidths=[100, 100, 80, 140])
        analysis_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, 1), (0, 2), colors.HexColor('#f8fafc')),
        ]))
        
        elements.append(analysis_table)
    else:
        elements.append(Paragraph("Insufficient data for detailed analysis.", normal_style))
    
    elements.append(Spacer(1, 25))
    
    # ========== GRADING SYSTEM ==========
    elements.append(Paragraph("GRADING SYSTEM USED", section_style))
    
    grading_data = [
        ['MARKS RANGE', 'GRADE', 'REMARKS'],
        ['80 - 100', 'A', 'Excellent'],
        ['70 - 79', 'B', 'Very Good'],
        ['60 - 69', 'C', 'Good'],
        ['50 - 59', 'D', 'Fair'],
        ['40 - 49', 'E', 'Pass'],
        ['0 - 39', 'F', 'Fail']
    ]
    
    grading_table = Table(grading_data, colWidths=[100, 60, 160])
    grading_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    elements.append(grading_table)
    elements.append(Spacer(1, 25))
    
    # ========== FOOTER SECTION ==========
    elements.append(Paragraph("_" * 100, normal_style))
    elements.append(Spacer(1, 15))
    
    # Important Notes
    notes_data = [
        ['IMPORTANT NOTES:'],
        ['• This is an official academic transcript from Charles Academy.'],
        ['• Please keep this document for your records.'],
        ['• For any discrepancies, contact academic office within 14 days.'],
        ['• Results are subject to verification by the examination board.'],
        ['• This transcript is confidential and intended for personal use only.'],
    ]
    
    notes_table = Table(notes_data, colWidths=[480])
    notes_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#64748b')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    elements.append(notes_table)
    elements.append(Spacer(1, 20))
    
    # Signature Section
    signature_data = [
        ['', ''],
        ['___________________________', '___________________________'],
        ['Student/Parent Signature', 'Class Teacher Signature'],
        ['', ''],
        ['Date: ___________________', f'Stamp & Seal: {school_name}'],
    ]
    
    signature_table = Table(signature_data, colWidths=[240, 240])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica'),
        ('FONTSIZE', (0, 2), (-1, 2), 8),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 4), (-1, 4), 8),
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#475569')),
    ]))
    
    elements.append(signature_table)
    elements.append(Spacer(1, 20))
    
    # Final Footer
    footer_text = f"""
    {school_name} • Dar es Salaam, Tanzania • Tel: {phone} • Email: {email}<br/>
    This document is valid only with official school stamp and signature.<br/>
    Generated on: {timezone.now().strftime("%d %B, %Y at %I:%M %p")} • Transcript ID: AT-{student.registration_number}-{timezone.now().strftime("%Y%m%d%H%M")}
    """
    
    elements.append(Paragraph(footer_text, footer_style))
    
    # ========== BUILD PDF ==========
    try:
        doc.build(elements)
    except Exception as e:
        # Fallback to simple PDF
        print(f"PDF generation error: {e}")
        return generate_simple_results_pdf(student, results, school_settings)
    
    # Get PDF value from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create HTTP response with PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"Academic_Transcript_{student.registration_number}_{student.full_name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response


# Helper functions
def get_grade_info(marks):
    """Convert marks to grade and remark"""
    if marks >= 80:
        return ('A', 'Excellent')
    elif marks >= 70:
        return ('B', 'Very Good')
    elif marks >= 60:
        return ('C', 'Good')
    elif marks >= 50:
        return ('D', 'Fair')
    elif marks >= 40:
        return ('E', 'Pass')
    else:
        return ('F', 'Fail')


def get_grade_color(col, row, sty):
    """Return color based on grade"""
    if row == 0:
        return colors.white
    grade = sty.text
    if grade == 'A':
        return colors.HexColor('#10b981')  # Green
    elif grade == 'B':
        return colors.HexColor('#3b82f6')  # Blue
    elif grade == 'C':
        return colors.HexColor('#f59e0b')  # Orange
    elif grade == 'D':
        return colors.HexColor('#8b5cf6')  # Purple
    elif grade == 'E':
        return colors.HexColor('#ef4444')  # Red
    elif grade == 'F':
        return colors.HexColor('#dc2626')  # Dark Red
    return colors.black


def generate_simple_results_pdf(student, results, school_settings):
    """Simple fallback PDF generator for results"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # School info
    school_name = school_settings.name if school_settings else "Charles Academy"
    
    # Simple header
    elements.append(Paragraph(f"<b>{school_name}</b>", styles['Heading1']))
    elements.append(Paragraph("Academic Results", styles['Heading2']))
    elements.append(Paragraph(f"Student: {student.full_name}", styles['Normal']))
    elements.append(Paragraph(f"Admission No: {student.registration_number}", styles['Normal']))
    elements.append(Paragraph(f"Class: {student.classroom}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Results table
    if results:
        results_data = [['Subject', 'Marks', 'Grade', 'Remarks']]
        for result in results:
            grade_info = result.grade()
            results_data.append([
                result.subject.name if result.subject else "Unknown",
                str(result.marks),
                grade_info[0] if grade_info else 'N/A',
                grade_info[1] if grade_info else 'N/A'
            ])
        
        results_table = Table(results_data)
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(results_table)
    
    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Italic']))
    elements.append(Paragraph(f"Transcript ID: AT-{student.registration_number}", styles['Italic']))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"Results_{student.registration_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response

# students/views.py
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

def change_password(request):
    settings_obj = SchoolSettings.objects.first()

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep user logged in
            return redirect('students:student_portal')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'students/change_password.html', {'form': form, 'school_settings': settings_obj,
})





# students/views.py
@role_required(['ADMIN', 'TEACHER', 'STUDENT'])
def student_detail(request, student_id):
    """View student details"""
    student = get_object_or_404(Student, id=student_id)
    school_settings = SchoolSettings.objects.first()
    
    # For students: ensure they can only view their own profile
    if request.user.role == 'STUDENT' and request.user != student.user:
        messages.error(request, "You can only view your own profile.")
        return redirect('dashboard')
    
    # For teachers: ensure they teach this student's class
    if request.user.role == 'TEACHER':
        if not student.classroom or student.classroom not in request.user.teacher_profile.classes.all():
            messages.error(request, "You can only view students in your classes.")
            return redirect('dashboard')
    
    # Get attendance records
    from attendance.models import StudentAttendance
    attendance_records = StudentAttendance.objects.filter(student=student).order_by('-date')[:10]
    
    # Get exam results
    from exams.models import Result
    exam_results = Result.objects.filter(student=student).select_related('exam', 'subject').order_by('-exam__date')[:5]
    
    # Get fee payments
    from fees.models import Payment
    fee_payments = Payment.objects.filter(student=student).order_by('-date')[:5]
    
    context = {
        'student': student,
        'school_settings': school_settings,
        'attendance_records': attendance_records,
        'exam_results': exam_results,
        'fee_payments': fee_payments,
        'today': timezone.now().date(),
    }
    
    return render(request, 'students/detail.html', context)




# ── Ongeza hizi views ndani ya students/views.py ──────────────────────────
# (Import hii pia juu: from .models import Student, Certificate)

import mimetypes
from django.http import FileResponse, Http404


@login_required
def my_certificates(request):
    """Student anaona certificates zake zote."""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('dashboard')

    certificates = student.certificates.all().order_by('-issued_date')
    school_settings = SchoolSettings.objects.first()

    return render(request, 'students/certificates.html', {
        'student':        student,
        'certificates':   certificates,
        'school_settings': school_settings,
    })


import requests
from django.http import HttpResponse, Http404, StreamingHttpResponse
from django.conf import settings


def _proxy_uploadcare_file(uuid, filename=None):
    """
    Pakia file kutoka Uploadcare REST API kwa kutumia secret key.
    Rudisha (content, content_type, filename) au raise Http404.
    """
    uploadcare_config = getattr(settings, 'UPLOADCARE', {})
    pub_key    = uploadcare_config.get('pub_key', '')
    secret_key = uploadcare_config.get('secret', '')

    if not uuid:
        raise Http404("No file UUID.")

    # Clean UUID — ondoa slashes/spaces
    uuid = str(uuid).strip().strip('/')

    # Uploadcare CDN URL — direct na UUID tu
    cdn_url = f"https://ucarecdn.com/{uuid}/"
    if filename:
        cdn_url = f"https://ucarecdn.com/{uuid}/{filename}"

    try:
        response = requests.get(
            cdn_url,
            auth=(pub_key, secret_key),   # Basic auth na Uploadcare keys
            timeout=30,
            stream=True
        )

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            return response, content_type
        
        # Kama CDN imefail, jaribu REST API
        api_url = f"https://api.uploadcare.com/files/{uuid}/"
        api_response = requests.get(
            api_url,
            headers={
                'Authorization': f'Uploadcare.Simple {pub_key}:{secret_key}',
                'Accept': 'application/vnd.uploadcare-v0.7+json',
            },
            timeout=15
        )

        if api_response.status_code == 200:
            file_info   = api_response.json()
            direct_url  = file_info.get('original_file_url') or file_info.get('url')
            if direct_url:
                direct_resp = requests.get(direct_url, timeout=30, stream=True)
                if direct_resp.status_code == 200:
                    content_type = direct_resp.headers.get('Content-Type', 'application/octet-stream')
                    return direct_resp, content_type

    except requests.RequestException as e:
        raise Http404(f"File fetch failed: {e}")

    raise Http404("File not found on Uploadcare.")


# ─────────────────────────────────────────────────────────────────
#  1. students/views.py — badilisha download_certificate
# ─────────────────────────────────────────────────────────────────

@login_required
def download_certificate(request, cert_id):
    """Download certificate — proxy kupitia Uploadcare API."""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        raise Http404

    from .models import Certificate
    certificate = get_object_or_404(Certificate, id=cert_id, student=student)

    if not certificate.file:
        messages.error(request, "Certificate file not available.")
        return redirect('students:my_certificates')

    try:
        uuid     = str(certificate.file.uuid)
        filename = f"Certificate_{certificate.title.replace(' ', '_')}.pdf"

        response, content_type = _proxy_uploadcare_file(uuid, filename)

        django_response = StreamingHttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=content_type
        )
        # django_response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['Content-Disposition'] = 'attachment; filename="..."'  # ← hii inadownload        

    except Http404:
        messages.error(request, "Certificate file could not be retrieved.")
        return redirect('students:my_certificates')
    

# ── Admin: upload certificate kwa student fulani (optional extra view) ──────
@login_required
@role_required(['ADMIN'])
def admin_upload_certificate(request, student_id):
    """Admin anaweza upload certificate kwa student fulani bila kwenda admin panel."""
    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        cert_type   = request.POST.get('cert_type', 'COMPLETION')
        issued_date = request.POST.get('issued_date')
        description = request.POST.get('description', '')
        cert_file   = request.FILES.get('file')

        if not title or not cert_file:
            messages.error(request, "Title and file are required.")
        else:
            from .models import Certificate
            Certificate.objects.create(
                student     = student,
                title       = title,
                cert_type   = cert_type,
                issued_date = issued_date or timezone.now().date(),
                description = description,
                file        = cert_file,
                uploaded_by = request.user,
            )
            messages.success(
                request,
                f"Certificate '{title}' uploaded for {student.full_name}."
            )
            return redirect('students:student_detail', student_id=student.id)

    from .models import Certificate
    context = {
        'student':           student,
        'cert_type_choices': Certificate.CERTIFICATE_TYPES,
        'school_settings':   SchoolSettings.objects.first(),
    }
    return render(request, 'students/upload_certificate.html', context)