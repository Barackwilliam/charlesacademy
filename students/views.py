from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from io import BytesIO
import os

from .models import Student
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

def add_student(request):
    settings_obj = SchoolSettings.objects.first()

    if request.method == 'POST':
        classroom = ClassRoom.objects.get(id=request.POST.get('classroom'))
        year = int(request.POST.get('admission_year', timezone.now().year))
        
        # Generate registration number
        reg = generate_registration_number(classroom.code, year)
        
        # Create student
        student = Student.objects.create(
            full_name=request.POST.get('full_name'),
            email=request.POST.get('email'),
            classroom=classroom,
            admission_year=year,
            registration_number=reg,
            status=request.POST.get('status')
        )
        
        # Handle file uploads
        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
        if 'documents' in request.FILES:
            student.documents = request.FILES['documents']
        student.save()

        # Create linked user
        user = create_student_user(student)
        
        # Send credentials to student's email if provided
        if student.email:
            send_student_credentials(student, user, request)  # <-- Pass request object
        
        messages.success(request, f"Student {student.full_name} added successfully!")
        if student.email:
            messages.info(request, f"Credentials sent to {student.email}")
        
        return redirect('students:student_list')

    return render(request, 'students/add.html', {
        'school_settings': settings_obj,
        'classes': ClassRoom.objects.all(),
        'current_year': timezone.now().year,
    })






def delete_student(request, id):
    settings_obj = SchoolSettings.objects.first()

    Student.objects.filter(id=id).delete()
    return redirect('students:student_list')



from django.shortcuts import render, get_object_or_404, redirect
from .models import Student
# students/views.py - FIXED
def edit_student(request, id):  # CHANGED: student_id → id
    """Edit student information"""
    student = get_object_or_404(Student, id=id)  # CHANGED: student_id → id
    settings_obj = SchoolSettings.objects.first()
    
    if request.method == 'POST':
        # Check if email is being added for the first time
        old_email = student.email
        new_email = request.POST.get('email')
        
        # Update student info
        student.full_name = request.POST.get('full_name')
        student.email = new_email
        
        # Handle classroom
        classroom_id = request.POST.get('classroom')
        if classroom_id:
            try:
                student.classroom = ClassRoom.objects.get(id=classroom_id)
            except ClassRoom.DoesNotExist:
                messages.error(request, "Selected class does not exist.")
                return render(request, 'students/edit.html', {
                    'student': student,
                    'school_settings': settings_obj,
                    'classes': ClassRoom.objects.all()
                })
        
        student.status = request.POST.get('status')
        
        # Handle file uploads
        if 'photo' in request.FILES:
            student.photo = request.FILES['photo']
        if 'documents' in request.FILES:
            student.documents = request.FILES['documents']
        
        student.save()
        
        # Send credentials if email changed
        if new_email and (not old_email or old_email != new_email) and student.user:
            try:
                # Import function here
                from .utils import send_student_credentials
                send_student_credentials(student, student.user, request)
                messages.info(request, f"New credentials sent to {new_email}")
            except Exception as e:
                messages.warning(request, f"Student updated but failed to send email: {str(e)}")
        
        messages.success(request, "Student updated successfully!")
        return redirect('students:student_list')
    
    return render(request, 'students/edit.html', {
        'student': student,
        'school_settings': settings_obj,
        'classes': ClassRoom.objects.all()
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
        'attendance': attendance,
        'average_marks': round(average_marks, 2) if average_marks else 0,
        'has_results': results.exists(),
    })


@login_required
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

@login_required
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
@login_required
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