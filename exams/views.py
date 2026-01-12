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


# Create new exam
def create_exam(request):
    settings_obj = SchoolSettings.objects.first()

    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('exams:exam_list')
    else:
        form = ExamForm()
    return render(request, 'exams/create_exam.html', {'form': form,'school_settings': settings_obj
})





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
