from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('students/', include(('students.urls', 'students'), namespace='students')),
    path('teachers/', include('teachers.urls')),
    path('exams/', include('exams.urls')),
    path('attendance/', include('attendance.urls')),
    path('fees/', include('fees.urls')),
    path('accounts/', include('accounts.urls')),
    path('parents/', include('parents.urls', namespace='parents')),

    ]




# from django.urls import path, include

# urlpatterns = [
#     path('accounts/', include('accounts.urls')),
#     path('', include('dashboard.urls')),  # dashboard app
#     path('teachers/', include('teachers.urls')),
#     path('students/', include('students.urls')),
#     path('attendance/', include('attendance.urls')),
#     path('exams/', include('exams.urls')),
#     path('fees/', include('fees.urls')),
# ]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
