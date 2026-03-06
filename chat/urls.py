from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Student / guest
    path('start/',                            views.start_chat,          name='start_chat'),
    path('send/',                             views.send_message,        name='send_message'),
    path('poll/<uuid:session_id>/',           views.poll_messages,       name='poll_messages'),
    path('delete/',                           views.delete_session,      name='delete_session'),

    # Admin
    path('admin/panel/',                      views.admin_chat_panel,    name='admin_panel'),
    path('admin/sessions/',                   views.admin_get_sessions,  name='admin_sessions'),
    path('admin/messages/<uuid:session_id>/', views.admin_get_messages,  name='admin_messages'),
    path('admin/send/',                       views.admin_send_message,  name='admin_send'),
    path('admin/close/',                      views.admin_close_session, name='admin_close'),
    path('admin/delete/',                     views.admin_delete_session,name='admin_delete'),
]