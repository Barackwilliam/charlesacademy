from django.urls import path
from .views import exam_list, enter_marks, student_report_card
from . import views
app_name = 'exams'

urlpatterns = [
    path('', exam_list, name='exam_list'),
    path('create/', views.create_exam, name='create_exam'),
    # path('enter-marks/<int:exam_id>/', views.enter_marks, name='enter_marks'),
    path('report/<int:student_id>/', student_report_card, name='student_report_card'),
    path('enter-marks/<int:exam_id>/', views.enter_marks, name='enter_marks'),
    path('results/<int:exam_id>/', views.exam_results, name='exam_results'),

]

