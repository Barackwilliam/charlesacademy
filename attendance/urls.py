from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('students/',       views.student_attendance_list,  name='student_attendance_list'),
    path('students/mark/',  views.mark_student_attendance,  name='mark_student_attendance'),
    path('teachers/',       views.teacher_attendance_list,  name='teacher_attendance_list'),
    path('teachers/mark/',  views.mark_teacher_attendance,  name='mark_teacher_attendance'),
    path('teacher/mark/',   views.teacher_mark_attendance,  name='teacher_mark_attendance'),
    path('my/',             views.my_attendance,            name='my_attendance'),
    path('students/monthly/', views.monthly_student_report, name='monthly_student_report'),
]
