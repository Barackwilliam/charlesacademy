# exams/urls.py

from django.urls import path
from .views import exam_list, enter_marks, student_report_card
from . import views

app_name = 'exams'

urlpatterns = [
    # ── Existing ────────────────────────────────────────────────
    path('',                               exam_list,                        name='exam_list'),
    path('create/',                        views.create_exam,                name='create_exam'),
    path('report/<int:student_id>/',       student_report_card,              name='student_report_card'),
    path('enter-marks/<int:exam_id>/',     views.enter_marks,                name='enter_marks'),
    path('results/<int:exam_id>/',         views.exam_results,               name='exam_results'),

    # ── Assignments (Admin/Teacher) ──────────────────────────────
    path('assignments/',                   views.assignment_list,            name='assignment_list'),
    path('assignments/create/',            views.create_assignment,          name='create_assignment'),
    path('assignments/<int:assignment_id>/submissions/',
                                           views.assignment_submissions,     name='assignment_submissions'),

    # ── Assignments (Student) ────────────────────────────────────
    path('my-assignments/',                views.my_assignments,             name='my_assignments'),
    path('my-assignments/<int:assignment_id>/submit/',
                                           views.submit_assignment,          name='submit_assignment'),

    # ── Downloads (proxy — hakuna CDN redirect) ──────────────────
    path('assignments/<int:assignment_id>/download/',
                                           views.download_assignment_file,   name='download_assignment_file'),
    path('submissions/<int:submission_id>/download/',
                                           views.download_submission_file,   name='download_submission_file'),
]