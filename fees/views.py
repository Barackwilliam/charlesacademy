from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import FeeStructure, Payment, FeePayment
from students.models import Student
from django.db import models
import uuid
from dashboard.models import SchoolSettings
from django.db.models import Sum
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from io import BytesIO
from django.utils import timezone
import os


# =============================================
# DEBUG VIEW - Check Database Records
# =============================================

@login_required
def debug_fees(request):
    """Debug view to see what's in the database"""
    context = {}
    
    try:
        student = Student.objects.get(user=request.user)
        context['student'] = student
        
        # Check if student has a class
        if student.classroom:
            context['classroom'] = student.classroom
            
            # Check fee structure for this class
            try:
                fee_structure = FeeStructure.objects.get(classroom=student.classroom)
                context['fee_structure'] = fee_structure
                context['total_fee'] = fee_structure.total_fee
            except FeeStructure.DoesNotExist:
                context['fee_structure_error'] = "No fee structure found for this class"
                
            # Check payments for this student
            payments = Payment.objects.filter(student=student)
            context['payments_count'] = payments.count()
            context['payments'] = payments
            
            # Calculate totals
            total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
            context['total_paid'] = total_paid
            
        else:
            context['classroom_error'] = "Student has no classroom assigned"
            
    except Student.DoesNotExist:
        context['student_error'] = "Student profile not found"
    
    # Also show all fee structures and payments in system
    context['all_structures'] = FeeStructure.objects.all()
    context['all_payments'] = Payment.objects.all()[:10]  # First 10
    
    return render(request, 'fees/debug.html', context)


# =============================================
# MAIN FEE VIEWS
# =============================================
@login_required
def my_fees(request):
    settings_obj = SchoolSettings.objects.first()

    """
    View for students to see their own fees - BETTER VERSION
    """
    # Step 1: Try to get student profile directly
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        # Step 2: Auto-link if possible
        student = None
        
        # Search by name
        user_full_name = f"{request.user.first_name} {request.user.last_name}".strip()
        if user_full_name and user_full_name != ' ':
            student = Student.objects.filter(
                full_name__iexact=user_full_name
            ).first()
        
        # If not found by name, try by username (might be registration number)
        if not student:
            username_upper = request.user.username.upper()
            student = Student.objects.filter(
                registration_number__iexact=username_upper
            ).first()
        
        # If still not found, show all students for manual selection
        if not student:
            messages.error(
                request,
                "No student profile found for your account. "
                "Please contact administrator to link your account."
            )
            
            # Show available students for debugging
            all_students = Student.objects.filter(user__isnull=True)[:10]
            
            return render(request, 'fees/link_account.html',"school_settings': settings_obj", {
                'user_info': {
                    'username': request.user.username,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'email': request.user.email,
                },
                'available_students': all_students,
            })
        else:
            # Link the found student to user
            student.user = request.user
            student.save()
            messages.success(
                request, 
                f"Successfully linked to student: {student.full_name}"
            )
    
    # Step 3: Now show fees for the student
    return student_fee_detail(request, student.id)


@login_required
def link_student_account(request, student_id):
    settings_obj = SchoolSettings.objects.first()

    """Allow user to manually link to a student account"""
    if request.method == 'POST':
        try:
            student = Student.objects.get(id=student_id)
            
            # Check if student is already linked to another user
            if student.user and student.user != request.user:
                messages.error(
                    request,
                    f"This student is already linked to another account: {student.user.username}"
                )
            else:
                # Link student to current user
                student.user = request.user
                student.save()
                messages.success(
                    request,
                    f"Successfully linked to student: {student.full_name}"
                )
                return redirect('fees:my_fees',"school_settings': settings_obj")
                
        except Student.DoesNotExist:
            messages.error(request, "Student not found")
    
    return redirect('fees:my_fees')

@login_required
def student_fee_detail(request, student_id=None):
    settings_obj = SchoolSettings.objects.first()

    """
    View for individual student to check their fee details
    If student_id is None, show current student's fee
    """
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        # Check if user has permission to view other students
        if not request.user.is_staff and student.user != request.user:
            messages.error(request, "You don't have permission to view this student's fee details.")
            return redirect('fees:my_fees')
    else:
        # Try to get student associated with logged in user
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            messages.error(request, "No student profile found for your account.")
            return redirect('fees:payment_list')
    
    # Direct calculation instead of using Payment.get_student_payment_summary
    if not student.classroom:
        messages.error(request, "Student is not assigned to any class.")
        return render(request, 'fees/student_fee_detail.html', {
            'student': student,
            'total_fee': 0,
            'total_paid': 0,
            'balance': 0,
            'payments': [],
            'error': 'no_classroom'
        })
    
    # Get fee structure
    try:
        fee_structure = FeeStructure.objects.get(classroom=student.classroom)
        total_fee = fee_structure.total_fee
    except FeeStructure.DoesNotExist:
        messages.warning(request, f"No fee structure defined for {student.classroom.name}")
        total_fee = 0
        fee_structure = None
    
    # Get payments
    payments = Payment.objects.filter(student=student).order_by('-date')
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
    balance = total_fee - total_paid
    
    context = {
        'student': student,
        'total_fee': total_fee,
        'total_paid': total_paid,
        'balance': balance,
        'payments': payments,
        'fee_structure': fee_structure,
        'school_settings': settings_obj,
    }
    
    return render(request, 'fees/student_fee_detail.html', context)


# =============================================
# ADMIN FEE VIEWS
# =============================================

def fee_structure_list(request):
    settings_obj = SchoolSettings.objects.first()

    structures = FeeStructure.objects.all()
    return render(request, 'fees/fee_structure_list.html', {'structures': structures,'school_settings': settings_obj})


def add_fee_structure(request):
    settings_obj = SchoolSettings.objects.first()

    if request.method == 'POST':
        classroom_id = request.POST['classroom']
        total_fee = request.POST['total_fee']
        
        # Check if structure already exists for this class
        if FeeStructure.objects.filter(classroom_id=classroom_id).exists():
            messages.error(request, "Fee structure already exists for this class!")
        else:
            FeeStructure.objects.create(
                classroom_id=classroom_id,
                total_fee=total_fee
            )
            messages.success(request, "Fee structure added successfully!")
        return redirect('fees:fee_structure_list')

    from classes.models import ClassRoom
    classrooms = ClassRoom.objects.all()
    return render(request, 'fees/add_fee_structure.html', {'classrooms': classrooms,'school_settings': settings_obj})


def record_payment(request):
    settings_obj = SchoolSettings.objects.first()

    if request.method == 'POST':
        student_id = request.POST['student']
        amount = request.POST['amount']
        
        try:
            student = Student.objects.get(id=student_id)
            
            # Create payment
            payment = Payment.objects.create(
                student=student,
                amount_paid=amount
                # receipt_no will be auto-generated in save() method
            )
            
            messages.success(request, f"Payment of {amount} recorded for {student.full_name}. Receipt: {payment.receipt_no}")
            return redirect('fees:payment_list')
            
        except Student.DoesNotExist:
            messages.error(request, "Student not found!")
    
    students = Student.objects.all()
    return render(request, 'fees/record_payment.html', {'students': students,'school_settings': settings_obj})


def payment_list(request):
    settings_obj = SchoolSettings.objects.first()

    payments = Payment.objects.select_related('student').order_by('-date')
    return render(request, 'fees/payment_list.html', {'payments': payments,'school_settings': settings_obj})


def student_fee_report(request, student_id):
    settings_obj = SchoolSettings.objects.first()

    student = get_object_or_404(Student, id=student_id)
    
    if not student.classroom:
        messages.error(request, "Student has no classroom assigned.")
        return render(request, 'fees/student_fee_report.html', {
            'student': student,
            'payments': [],
            'total_fee': 0,
            'total_paid': 0,
            'balance': 0
        })
    
    payments = Payment.objects.filter(student=student)
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
    
    try:
        total_fee = FeeStructure.objects.get(classroom=student.classroom).total_fee
    except FeeStructure.DoesNotExist:
        total_fee = 0
        messages.warning(request, "No fee structure for this student's class.")
    
    balance = total_fee - total_paid

    return render(request, 'fees/student_fee_report.html', {
        'student': student,
        'payments': payments,
        'total_fee': total_fee,
        'total_paid': total_paid,
        'balance': balance,
        'school_settings': settings_obj
    })


def due_fee_list(request):
    settings_obj = SchoolSettings.objects.first()

    students = Student.objects.all()
    due_list = []

    for student in students:
        if not student.classroom:
            continue
            
        try:
            structure = FeeStructure.objects.get(classroom=student.classroom)
            total_fee = structure.total_fee
        except FeeStructure.DoesNotExist:
            continue

        paid = Payment.objects.filter(
            student=student
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        balance = total_fee - paid

        if balance > 0:
            due_list.append({
                'student': student,
                'total_fee': total_fee,
                'paid': paid,
                'balance': balance
            })

    return render(request, 'fees/due_fee_list.html', {
        'due_list': due_list,
        'school_settings': settings_obj
    })


# =============================================
# PDF GENERATION
# =============================================

# def generate_fee_pdf(request, student_id):
#     """Generate PDF receipt for student fee summary"""
#     student = get_object_or_404(Student, id=student_id)
    
#     # Check permission
#     if not request.user.is_staff and student.user != request.user:
#         messages.error(request, "You don't have permission to download this receipt.")
#         return redirect('fees:my_fees')
    
#     # Get payment data directly
#     if not student.classroom:
#         messages.error(request, "Student has no classroom assigned.")
#         return redirect('fees:my_fees')
    
#     try:
#         fee_structure = FeeStructure.objects.get(classroom=student.classroom)
#         total_fee = fee_structure.total_fee
#     except FeeStructure.DoesNotExist:
#         total_fee = 0
#         messages.warning(request, "No fee structure found for student's class.")
    
#     payments = Payment.objects.filter(student=student).order_by('-date')
#     total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
#     balance = total_fee - total_paid
    
#     # Create PDF
#     buffer = BytesIO()
#     doc = SimpleDocTemplate(buffer, pagesize=letter)
#     elements = []
    
#     # Styles
#     styles = getSampleStyleSheet()
    
#     # Title
#     title_style = ParagraphStyle(
#         'CustomTitle',
#         parent=styles['Heading1'],
#         fontSize=16,
#         spaceAfter=30,
#         alignment=1
#     )
    
#     elements.append(Paragraph("FEE PAYMENT SUMMARY", title_style))
#     elements.append(Spacer(1, 20))
    
#     # Student Information
#     info_data = [
#         ['STUDENT INFORMATION', ''],
#         ['Full Name:', student.full_name],
#         ['Admission/Reg No:', student.registration_number],
#         ['Class:', str(student.classroom) if student.classroom else 'Not Assigned'],
#         ['Date Generated:', timezone.now().strftime("%Y-%m-%d %H:%M")],
#     ]
    
#     info_table = Table(info_data, colWidths=[150, 300])
#     info_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, 0), 12),
#         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
#         ('GRID', (0, 0), (-1, -1), 1, colors.black),
#     ]))
    
#     elements.append(info_table)
#     elements.append(Spacer(1, 30))
    
#     # Fee Summary
#     summary_data = [
#         ['FEE SUMMARY', 'Amount (KES)'],
#         ['Total Fee Due:', f"{total_fee:,.2f}"],
#         ['Total Amount Paid:', f"{total_paid:,.2f}"],
#         ['Remain:', f"{balance:,.2f}"],
#     ]
    
#     summary_table = Table(summary_data, colWidths=[300, 150])
#     summary_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, 0), 12),
#         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#         ('GRID', (0, 0), (-1, -1), 1, colors.black),
#         ('BACKGROUND', (0, 3), (-1, 3), colors.yellow if balance > 0 else colors.lightgreen),
#         ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
#     ]))
    
#     elements.append(summary_table)
#     elements.append(Spacer(1, 30))
    
#     # Payment History
#     if payments.exists():
#         elements.append(Paragraph("PAYMENT HISTORY", styles['Heading2']))
#         elements.append(Spacer(1, 10))
        
#         payment_data = [['Date', 'Receipt No', 'Amount (Tsh)']]
#         for payment in payments:
#             payment_data.append([
#                 payment.date.strftime("%Y-%m-%d"),
#                 payment.receipt_no,
#                 f"{payment.amount_paid:,.2f}"
#             ])
        
#         payment_table = Table(payment_data, colWidths=[100, 150, 100])
#         payment_table.setStyle(TableStyle([
#             ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#             ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#             ('FONTSIZE', (0, 0), (-1, 0), 10),
#             ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#             ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
#             ('GRID', (0, 0), (-1, -1), 1, colors.black),
#         ]))
        
#         elements.append(payment_table)
#     else:
#         elements.append(Paragraph("No payment records found.", styles['Normal']))
    
#     # Footer
#     elements.append(Spacer(1, 40))
#     elements.append(Paragraph("This is a computer-generated receipt.", styles['Italic']))
#     elements.append(Paragraph("Signature: ________________________", styles['Normal']))
    
#     # Build PDF
#     doc.build(elements)
    
#     # Get PDF value from buffer
#     pdf = buffer.getvalue()
#     buffer.close()
    
#     # Create HTTP response with PDF
#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="Fee_Summary_{student.registration_number}_{timezone.now().strftime("%Y%m%d")}.pdf"'
#     response.write(pdf)
    
#     return response
def generate_fee_pdf(request, student_id):
    settings_obj = SchoolSettings.objects.first()

    """Generate beautiful PDF receipt for student fee summary"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not request.user.is_staff and student.user != request.user:
        messages.error(request, "You don't have permission to download this receipt.")
        return redirect('fees:my_fees')
    
    # Get payment data
    if not student.classroom:
        messages.error(request, "Student has no classroom assigned.")
        return redirect('fees:my_fees')
    
    try:
        fee_structure = FeeStructure.objects.get(classroom=student.classroom)
        total_fee = fee_structure.total_fee
    except FeeStructure.DoesNotExist:
        total_fee = 0
    
    payments = Payment.objects.filter(student=student).order_by('-date')
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
    balance = total_fee - total_paid
    
    # Calculate payment percentage
    if total_fee > 0:
        payment_percentage = (total_paid / total_fee) * 100
    else:
        payment_percentage = 0
    
    # Get school settings
    try:
        school_settings = SchoolSettings.objects.first()
    except:
        school_settings = None
    
    # Create PDF with custom page size
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
    
    # Use theme color from school settings
    theme_color = school_settings.theme_color if school_settings else '#4361ee'
    
    # Add custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor(theme_color),
        spaceAfter=20,
        alignment=1,  # Center
        fontName='Helvetica-Bold'
    )
    
    sub_title_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15,
        alignment=1,
        fontName='Helvetica'
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor(theme_color),
        spaceAfter=10,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
        fontName='Helvetica-Oblique'
    )
    
    amount_style = ParagraphStyle(
        'AmountStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.black,
        alignment='RIGHT',
        fontName='Helvetica-Bold'
    )
    
    # ========== HEADER SECTION ==========
    # School Logo and Name
    header_table_data = []
    
    # Create header with logo (if available) and school name
    if school_settings and school_settings.logo:
        try:
            # Try to add school logo
            logo_path = school_settings.logo.path
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=80, height=80)
                header_table_data.append([logo, ''])
            else:
                # Logo placeholder with school initial
                school_initials = school_settings.name[:2].upper() if school_settings else "CA"
                logo_placeholder = f"""
                <font size="20" color="{theme_color}">
                <b>{school_initials}</b>
                </font>
                """
                header_table_data.append([Paragraph(logo_placeholder, normal_style), ''])
        except Exception as e:
            # Fallback to text logo
            school_initials = school_settings.name[:2].upper() if school_settings else "CA"
            logo_placeholder = f"""
            <font size="20" color="{theme_color}">
            <b>{school_initials}</b>
            </font>
            """
            header_table_data.append([Paragraph(logo_placeholder, normal_style), ''])
    else:
        # No logo, use school initials
        school_initials = school_settings.name[:2].upper() if school_settings else "CA"
        logo_placeholder = f"""
        <font size="20" color="{theme_color}">
        <b>{school_initials}</b>
        </font>
        """
        header_table_data.append([Paragraph(logo_placeholder, normal_style), ''])
    
    # School information from settings
    school_name = school_settings.name if school_settings else "Charles Academy"
    phone = school_settings.phone if school_settings else "+255 123 456 789"
    email = school_settings.contact_email if school_settings else "admin@charlesacademy.edu"
    academic_year = school_settings.academic_year if school_settings else str(timezone.now().year)
    
    # School info cell - FIXED: removed 'address' variable
    school_info = f"""
    <b><font size="16" color="{theme_color}">{school_name}</font></b><br/>
    <font size="10" color="#475569">Dar es Salaam, Tanzania</font><br/>
    <font size="9" color="#64748b">Phone: {phone} | Email: {email}</font>
    """
    
    header_table_data[0][1] = Paragraph(school_info, normal_style)
    
    header_table = Table(header_table_data, colWidths=[100, 400])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    
    # Main Title
    elements.append(Paragraph("OFFICIAL FEE STATEMENT", title_style))
    elements.append(Paragraph("Student Fee Payment Summary", sub_title_style))
    
    # Document Info
    doc_info = f"""
    <b>Document No:</b> FS-{student.registration_number}-{timezone.now().strftime("%Y%m%d")} | 
    <b>Generated:</b> {timezone.now().strftime("%d/%m/%Y %I:%M %p")} |
    <b>Academic Year:</b> {academic_year}
    """
    elements.append(Paragraph(doc_info, normal_style))
    elements.append(Spacer(1, 20))
    
    # ========== STUDENT INFORMATION ==========
    # elements.append(Paragraph("STUDENT INFORMATION", section_title_style))
    
    # Student info in a nice table
    # student_data = [
    #     ['FULL NAME:', student.full_name, 'ADMISSION NO:', student.registration_number],
    #     ['CLASS:', str(student.classroom) if student.classroom else 'Not Assigned', 
    #      'ADMISSION YEAR:', str(student.admission_year)],
    #     ['STATUS:', student.status, 'GENERATED DATE:', timezone.now().strftime("%d/%m/%Y")],
    # ]
    
    # student_table = Table(student_data, colWidths=[80, 150, 80, 130])
    # student_table.setStyle(TableStyle([
    #     ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
    #     ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
    #     ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    #     ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    #     ('FONTSIZE', (0, 0), (-1, -1), 9),
    #     ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    #     ('TOPPADDING', (0, 0), (-1, -1), 8),
    #     ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    # ]))
    
    # elements.append(student_table)
    # elements.append(Spacer(1, 25))
    
    # ========== FEE SUMMARY ==========
    elements.append(Paragraph("FEE SUMMARY", section_title_style))
    
    # Fee summary with better formatting
    summary_data = [
        ['DESCRIPTION', 'AMOUNT (TZS)'],
        ['Total Annual Fee', f"{total_fee:,.2f}"],
        ['Total Amount Paid', f"{total_paid:,.2f}"],
        ['Balance', f"{balance:,.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[350, 130])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(theme_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 3), (-1, 3), 
         colors.HexColor('#fef3c7') if balance > 0 else colors.HexColor('#d1fae5')),
        ('TEXTCOLOR', (0, 3), (-1, 3), 
         colors.HexColor('#92400e') if balance > 0 else colors.HexColor('#065f46')),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 10))
    
    # Payment Progress Bar (visual representation)
    # progress_width = 400
    # if total_fee > 0:
    #     paid_width = (total_paid / total_fee) * progress_width
    #     progress_data = [
    #         ['Payment Progress:'],
    #         [f"Paid: {payment_percentage:.1f}% ({total_paid:,.2f} / {total_fee:,.2f})"]
    #     ]
        
    #     progress_table = Table(progress_data, colWidths=[progress_width])
    #     progress_table.setStyle(TableStyle([
    #         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    #         ('FONTSIZE', (0, 0), (-1, 0), 9),
    #         ('FONTSIZE', (0, 1), (-1, 1), 8),
    #         ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#475569')),
    #         ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    #     ]))
        
    #     elements.append(progress_table)
        
    #     # Visual progress bar using theme color for paid portion
    #     paid_blocks = int(paid_width // 10)
    #     remaining_blocks = int((progress_width - paid_width) // 10)
    #     bar_data = [[
    #         Paragraph(f'<font color="{theme_color}">{"█" * paid_blocks}</font>'
    #                  f'<font color="#e2e8f0">{"█" * remaining_blocks}</font>', 
    #                  normal_style)
    #     ]]
    #     bar_table = Table(bar_data, colWidths=[progress_width])
    #     bar_table.setStyle(TableStyle([
    #         ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    #     ]))
        
    #     elements.append(bar_table)
    
    # elements.append(Spacer(1, 25))
    
    # ========== PAYMENT HISTORY ==========
    if payments.exists():
        elements.append(Paragraph("PAYMENT HISTORY", section_title_style))
        
        payment_data = [['DATE', 'RECEIPT NO.', 'DESCRIPTION', 'AMOUNT (TZS)', 'STATUS']]
        
        for payment in payments:
            payment_data.append([
                payment.date.strftime("%d/%m/%Y"),
                payment.receipt_no,
                "School Fee Payment",
                f"{payment.amount_paid:,.2f}",
                "PAID"
            ])
        
        payment_table = Table(payment_data, colWidths=[70, 100, 180, 90, 60])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(theme_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (4, 1), (4, -1), colors.HexColor('#10b981')),
            ('FONTNAME', (4, 1), (4, -1), 'Helvetica-Bold'),
        ]))
        
        elements.append(payment_table)
        elements.append(Spacer(1, 15))
        
        # Payment Summary
        summary_note = f"<b>Total Payments:</b> {payments.count()} transaction(s) | <b>Last Payment:</b> {payments.first().date.strftime('%d/%m/%Y')}"
        elements.append(Paragraph(summary_note, normal_style))
    else:
        no_payments = Paragraph(
            "<b>No payment records found.</b><br/>"
            "Payment history will be displayed here once payments are recorded.",
            normal_style
        )
        elements.append(no_payments)
    
    elements.append(Spacer(1, 30))
    
    # ========== FOOTER SECTION ==========
    elements.append(Paragraph("_" * 100, normal_style))
    elements.append(Spacer(1, 15))
    
    # Important Notes
    notes_data = [
        ['IMPORTANT NOTES:'],
        ['• This is an official computer-generated fee statement.'],
        ['• Please keep this document for your records.'],
        ['• For any discrepancies, contact accounts office within 7 days.'],
        ['• All payments should be made to authorized bank accounts only.'],
        ['• Bring this statement when making payments for verification.'],
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
        ['Student/Parent Signature', 'Accounts Officer Signature'],
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
    
    # Final Footer - FIXED: removed 'address' variable
    footer_text = f"""
    {school_name} • Dar es Salaam, Tanzania • Tel: {phone} • Email: {email}<br/>
    This document is valid only with official school stamp and signature.<br/>
    Generated on: {timezone.now().strftime("%d %B, %Y at %I:%M %p")} • Document ID: FS-{student.registration_number}-{timezone.now().strftime("%Y%m%d%H%M")}
    """
    
    elements.append(Paragraph(footer_text, footer_style))
    
    # ========== BUILD PDF ==========
    try:
        doc.build(elements)
    except Exception as e:
        # Fallback to simple PDF if complex one fails
        print(f"PDF generation error: {e}")
        return generate_simple_pdf(student, total_fee, total_paid, balance, payments, school_settings)
    
    # Get PDF value from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create HTTP response with PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"Fee_Statement_{student.registration_number}_{student.full_name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response


def generate_simple_pdf(student, total_fee, total_paid, balance, payments, school_settings):
    settings_obj = SchoolSettings.objects.first()

    """Simple fallback PDF generator"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # School info
    school_name = school_settings.name if school_settings else "Charles Academy"
    phone = school_settings.phone if school_settings else "+255 123 456 789"
    email = school_settings.contact_email if school_settings else "admin@charlesacademy.edu"
    academic_year = school_settings.academic_year if school_settings else str(timezone.now().year)
    
    # Simple header
    elements.append(Paragraph(f"<b>{school_name}</b>", styles['Heading1']))
    elements.append(Paragraph("Fee Payment Statement", styles['Heading2']))
    elements.append(Paragraph(f"Phone: {phone} | Email: {email} | Academic Year: {academic_year}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Student info
    elements.append(Paragraph(f"<b>STUDENT INFORMATION</b>", styles['Heading3']))
    elements.append(Paragraph(f"Name: {student.full_name}", styles['Normal']))
    elements.append(Paragraph(f"Admission No: {student.registration_number}", styles['Normal']))
    elements.append(Paragraph(f"Class: {student.classroom}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Fee summary
    elements.append(Paragraph(f"<b>FEE SUMMARY</b>", styles['Heading3']))
    elements.append(Paragraph(f"Total Fee: TZS {total_fee:,.2f}", styles['Normal']))
    elements.append(Paragraph(f"Total Paid: TZS {total_paid:,.2f}", styles['Normal']))
    elements.append(Paragraph(f"Balance: TZS {balance:,.2f}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Payment history if exists
    if payments.exists():
        elements.append(Paragraph(f"<b>PAYMENT HISTORY ({payments.count()} payments)</b>", styles['Heading3']))
        for payment in payments:
            elements.append(Paragraph(f"{payment.date.strftime('%d/%m/%Y')} - {payment.receipt_no} - TZS {payment.amount_paid:,.2f}", styles['Normal']))
    
    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Italic']))
    elements.append(Paragraph(f"Document ID: FS-{student.registration_number}-{timezone.now().strftime('%Y%m%d%H%M')}", styles['Italic']))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"Fee_Statement_{student.registration_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response