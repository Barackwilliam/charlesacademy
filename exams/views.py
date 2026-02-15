from django.shortcuts import render, get_object_or_404, redirect
from .models import Exam, Result
from students.models import Student
from classes.models import Subject
from django.contrib import messages
from .utils import report_card_pdf
from dashboard .models import SchoolSettings

# List all exams
def exam_list(request):
    settings_obj = SchoolSettings.objects.first()

    exams = Exam.objects.all().order_by('-date')
    return render(request, 'exams/exam_list.html', {'exams': exams,'school_settings': settings_obj,
})



from .forms import ExamForm, ResultForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Exam, Result
from classes.models import ClassRoom, Subject

@login_required
def create_exam(request):
    """Create a new exam"""
    settings_obj = SchoolSettings.objects.first()
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            subject_name = request.POST.get('subject')
            exam_date = request.POST.get('exam_date')
            exam_type = request.POST.get('exam_type', 'MONTHLY')
            
            # Get selected classes
            selected_classes = request.POST.getlist('classes')
            
            # Validate required fields
            if not name:
                messages.error(request, "Exam name is required")
                return redirect('exams:create_exam')
                
            if not subject_name or subject_name == "-- Select Subject --":
                messages.error(request, "Please select a subject")
                return redirect('exams:create_exam')
                
            if not selected_classes:
                messages.error(request, "Please select at least one class")
                return redirect('exams:create_exam')
            
            if not exam_date:
                messages.error(request, "Exam date is required")
                return redirect('exams:create_exam')
            
            # Get or create subject
            subject, created = Subject.objects.get_or_create(
                name=subject_name,
                defaults={'code': subject_name[:3].upper()}
            )
            
            # Create exams
            exams_created = 0
            for class_id in selected_classes:
                try:
                    if class_id == "all":
                        # Get all classes
                        classrooms = ClassRoom.objects.all()
                        for classroom in classrooms:
                            # Check if exam already exists
                            if not Exam.objects.filter(
                                name=name,
                                classroom=classroom,
                                subject=subject,
                                date=exam_date
                            ).exists():
                                exam = Exam.objects.create(
                                    name=name,
                                    classroom=classroom,
                                    subject=subject,
                                    date=exam_date,
                                    exam_type=exam_type
                                )
                                exams_created += 1
                    else:
                        # Get specific class
                        classroom = ClassRoom.objects.get(id=class_id)
                        
                        # Check if exam already exists
                        if not Exam.objects.filter(
                            name=name,
                            classroom=classroom,
                            subject=subject,
                            date=exam_date
                        ).exists():
                            exam = Exam.objects.create(
                                name=name,
                                classroom=classroom,
                                subject=subject,
                                date=exam_date,
                                exam_type=exam_type
                            )
                            exams_created += 1
                        
                except ClassRoom.DoesNotExist:
                    messages.warning(request, f"Class with ID {class_id} not found")
                except Exception as e:
                    messages.warning(request, f"Error creating exam: {str(e)}")
            
            if exams_created > 0:
                messages.success(request, f"Successfully created {exams_created} exam(s)!")
                return redirect('exams:exam_list')
            else:
                messages.error(request, "No exams were created. They might already exist.")
                
        except Exception as e:
            messages.error(request, f"Error creating exam: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Exam creation error: {e}", exc_info=True)
    
    # GET request
    context = {
        'school_settings': settings_obj,
        'classes': ClassRoom.objects.all().order_by('name'),
        'subjects': Subject.objects.all().order_by('name'),
        'exam_types': Exam.EXAM_TYPE_CHOICES,
        'today': timezone.now().date().isoformat(),
    }
    return render(request, 'exams/create_exam.html', context)


def enter_marks(request, exam_id):
    settings_obj = SchoolSettings.objects.first()

    exam = get_object_or_404(Exam, id=exam_id)
    students = Student.objects.filter(classroom=exam.classroom)
    subjects = Subject.objects.filter(classroom=exam.classroom)

    # =====================
    # SAVE MARKS (POST)
    # =====================
    if request.method == 'POST':
        for student in students:
            for subject in subjects:
                key = f"marks_{student.id}_{subject.id}"
                marks = request.POST.get(key)

                if marks not in [None, '']:
                    Result.objects.update_or_create(
                        student=student,
                        exam=exam,
                        subject=subject,
                        defaults={'marks': int(marks)}
                    )

        messages.success(request, "Marks saved successfully")
        return redirect('exams:exam_list')

    # =====================
    # LOAD MARKS (GET)
    # =====================
    results = Result.objects.filter(exam=exam)

    marks_dict = {
        f"{r.student_id}_{r.subject_id}": r.marks
        for r in results
    }

    return render(request, 'exams/enter_marks.html', {
        'exam': exam,
        'students': students,
        'subjects': subjects,
        'marks_dict': marks_dict,
        'school_settings': settings_obj,

    })

# Generate report card PDF
def student_report_card(request, student_id):
    settings_obj = SchoolSettings.objects.first()

    student = get_object_or_404(Student, id=student_id)
    return report_card_pdf(student)
# exams/views.py
from django.shortcuts import render, get_object_or_404
from .models import Exam, Student, Result, Subject

def exam_results(request, exam_id):
    settings_obj = SchoolSettings.objects.first()

    exam = get_object_or_404(Exam, id=exam_id)
    students = Student.objects.filter(classroom=exam.classroom)
    subjects = exam.classroom.subject_set.all()  # assuming subjects related to classroom

    results_dict = {}
    for student in students:
        student_results = {}
        total = 0
        count = 0
        for subject in subjects:
            result = Result.objects.filter(student=student, exam=exam, subject=subject).first()
            marks = result.marks if result else None
            student_results[subject.name] = marks
            if marks is not None:
                total += marks
                count += 1
        average = round(total / count, 2) if count else 0
        # pick grade from first Result object if exists
        grade = result.grade()[0] if count else '-'
        student_results['total'] = total
        student_results['average'] = average
        student_results['grade'] = grade
        results_dict[student.id] = student_results

    return render(request, 'exams/exam_results.html', {
        'exam': exam,
        'students': students,
        'subjects': subjects,
        'results_dict': results_dict,
        'school_settings': settings_obj,

    })
