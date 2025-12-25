# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user.role == 'ADMIN':
                return redirect('dashboard')
            elif user.role == 'TEACHER':
                return redirect('teacher_dashboard')
            elif user.role == 'STUDENT':
                return redirect('students:student_portal')
            elif user.role == 'PARENT':
                return redirect('parent_portal')
            elif user.role == 'ACCOUNTANT':
                return redirect('fees_list')
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid username or password'})

    return render(request, 'dashboard/home.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')
