from django.urls import path
from . import views

app_name = 'fees'

urlpatterns = [
    path('', views.payment_list, name='payment_list'),
    path('debug/', views.debug_fees, name='debug_fees'),


    path('structures/', views.fee_structure_list, name='fee_structure_list'),
    path('structures/add/', views.add_fee_structure, name='add_fee_structure'),

    path('payments/add/', views.record_payment, name='record_payment'),

    path('student/<int:student_id>/', views.student_fee_report, name='student_fee_report'),

    path('due/', views.due_fee_list, name='due_fee_list'),

    
    # My fees (for students)
    path('my-fees/', views.my_fees, name='my_fees'),
    path('link-student/<int:student_id>/', views.link_student_account, name='link_student_account'),

    path('student-detail/<int:student_id>/', views.student_fee_detail, name='student_fee_detail'),
    path('download-pdf/<int:student_id>/', views.generate_fee_pdf, name='download_pdf'),
    ]
