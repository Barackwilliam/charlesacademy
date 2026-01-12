from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'parents'

urlpatterns = [
    # Authentication URLs
    path('login/', views.parent_login, name='login'),
    path('logout/', views.parent_logout, name='logout'),
    
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='parents/password_reset.html',
             email_template_name='parents/password_reset_email.html',
             subject_template_name='parents/password_reset_subject.txt'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='parents/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='parents/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='parents/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Dashboard URL
    path('', views.parent_dashboard, name='dashboard'),
    
    # Attendance URLs
    path('attendance/', views.child_attendance, name='child_attendance'),
    path('attendance/<int:student_id>/', views.child_attendance, name='child_attendance_single'),
    path('api/attendance-summary/', views.attendance_summary_api, name='attendance_summary_api'),
    
    # Results URLs
    path('results/', views.child_results, name='child_results'),
    path('results/<int:student_id>/', views.child_results, name='child_results_single'),
    path('download-results/<int:student_id>/', views.download_results_pdf, name='download_results_pdf'),
    
    # Fees URLs
    path('fees/', views.child_fees, name='child_fees'),
    path('fees/<int:student_id>/', views.child_fees, name='child_fees_single'),
    path('download-fee/<int:student_id>/', views.download_fee_statement, name='download_fee_statement'),
    
    # Announcements URLs
    path('announcements/', views.announcements, name='announcements'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    
    # Profile URLs
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),


   # Registration URLs
    path('register/', views.parent_register, name='register'),
    path('registration-success/', views.registration_success, name='registration_success'),
    path('registration-closed/', views.registration_closed, name='registration_closed'),
    
    
    # API URLs
    path('api/dashboard-stats/', views.get_dashboard_stats, name='dashboard_stats'),
    path('api/children/', views.get_child_list, name='child_list'),
    
    # Error handlers
    path('404/', views.parent_404, name='404'),
    path('500/', views.parent_500, name='500'),
]