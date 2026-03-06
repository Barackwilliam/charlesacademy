from django.urls import path
from . import views

app_name = 'timetable'

urlpatterns = [
    path('my-timetable/',         views.student_timetable,  name='student_timetable'),
    path('manage/',               views.admin_timetable,    name='admin_timetable'),
    path('manage/save/',          views.admin_save_entry,   name='save_entry'),
    path('manage/delete/',        views.admin_delete_entry, name='delete_entry'),
    path('entry/<int:entry_id>/', views.get_entry,          name='get_entry'),
]