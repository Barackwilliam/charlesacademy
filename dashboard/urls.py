from django.urls import path
from .views import dashboard,index

urlpatterns = [
    path('', index, name='index'),
    path('dashboard', dashboard, name='dashboard'),

]
