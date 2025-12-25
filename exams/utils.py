#exam/utils.py
from reportlab.pdfgen import canvas
from django.http import HttpResponse
def report_card_pdf(student):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.full_name}_report.pdf"'
    p = canvas.Canvas(response)
    p.drawString(100, 800, "Charles Academy Report Card")
    p.drawString(100, 770, f"Student: {student.full_name}")
    p.drawString(100, 750, f"Reg No: {student.registration_number}")

    y = 720
    results = student.result_set.select_related('subject', 'exam').all()
    total_marks = 0
    subjects_count = results.count()
    for r in results:
        grade, remark = r.grade()
        p.drawString(100, y, f"{r.exam.name} - {r.subject.name}: {r.marks} - {grade} ({remark})")
        total_marks += r.marks
        y -= 20

    if subjects_count > 0:
        average = total_marks / subjects_count
        p.drawString(100, y-20, f"Average Marks: {average:.2f}")

    p.showPage()
    p.save()
    return response
