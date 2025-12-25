from django.urls import path
from . import views
from . views import my_attendance
app_name = 'attendance'

urlpatterns = [
    # path('teachers/mark/', views.mark_teacher_attendance, name='mark_teacher'),
    path('teachers/mark/', views.mark_teacher_attendance, name='mark_teacher_attendance'),  # hii lazima ipo

    path('students/', views.student_attendance_list, name='student_attendance_list'),
    path('students/mark/', views.mark_student_attendance, name='mark_student_attendance'),

    path('teachers/', views.teacher_attendance_list, name='teacher_attendance_list'),
    path('my/', my_attendance, name='my_attendance'),


    path('students/monthly/', views.monthly_student_report, name='monthly_student_report'),
]
