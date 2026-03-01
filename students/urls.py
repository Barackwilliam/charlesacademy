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
    path('download-id/<int:student_id>/', views.download_id_card_pdf, name='download_id_card'),
    path('my-id-card/', views.my_id_card, name='my_id_card'),  # Kwa ajili ya mwanafunzi kuona ID yake
    path('certificates/',
     views.my_certificates,
     name='my_certificates'),
     path('certificates/<int:cert_id>/download/',
     views.download_certificate,
     name='download_certificate'),
    path('<int:student_id>/upload-certificate/',
     views.admin_upload_certificate,
     name='upload_certificate'),

    path('download-pdf/', views.download_students_pdf, name='download_pdf'),
    path('detail/<int:student_id>/', views.student_detail, name='student_detail'),
    path('portal/download-results/', views.download_results_pdf, name='download_results_pdf'),
]
