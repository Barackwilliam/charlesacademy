from django.urls import path
from . import views

app_name = 'fees'

urlpatterns = [
    path('', views.payment_list, name='payment_list'),

    path('structures/', views.fee_structure_list, name='fee_structure_list'),
    path('structures/add/', views.add_fee_structure, name='add_fee_structure'),

    path('payments/add/', views.record_payment, name='record_payment'),

    path('student/<int:student_id>/', views.student_fee_report, name='student_fee_report'),

    path('due/', views.due_fee_list, name='due_fee_list'),
]
