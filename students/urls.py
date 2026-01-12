from django.urls import path
from .views import *
from . import views


app_name = 'students'   # 👈 ONGEZA HII

urlpatterns = [
    path('', student_list, name='student_list'),
    path('add/', add_student, name='add_student'),
    path('edit/<int:id>/', edit_student, name='edit_student'),
    path('delete/<int:id>/', delete_student, name='delete_student'),
    path('portal/', views.student_portal, name='student_portal'),
    path('change-password/', views.change_password, name='change_password'),
    path('<int:student_id>/', views.student_detail, name='student_detail'),
    # Add this line - PDF download will be handled by the same view with ?download=pdf paramete

    path('download-pdf/', views.download_students_pdf, name='download_pdf'),
    path('detail/<int:student_id>/', views.student_detail, name='student_detail'),
    path('portal/download-results/', views.download_results_pdf, name='download_results_pdf'),
]
