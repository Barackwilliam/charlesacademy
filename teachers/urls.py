# teachers/urls.py
from django.urls import path
from .views import teacher_list, add_teacher, edit_teacher,teacher_dashboard

urlpatterns = [
    path('', teacher_list, name='teacher_list'),
    path('add/', add_teacher, name='add_teacher'),
    path('edit/<int:id>/', edit_teacher, name='edit_teacher'),
    path('dashboard/', teacher_dashboard, name='teacher_dashboard'),

]
