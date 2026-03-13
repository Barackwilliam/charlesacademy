from django.urls import path
from . import views

urlpatterns = [
    path('',                       views.teacher_list,             name='teacher_list'),
    path('add/',                   views.add_teacher,              name='add_teacher'),
    path('edit/<int:id>/',         views.edit_teacher,             name='edit_teacher'),
    path('dashboard/',             views.teacher_dashboard,        name='teacher_dashboard'),
    path('register-student/',      views.teacher_register_student, name='teacher_register_student'),
    path('enter-results/',         views.teacher_enter_results,    name='teacher_enter_results'),
]
