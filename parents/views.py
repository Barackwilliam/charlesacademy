from django.shortcuts import render

# Create your views here.
def parent_portal(request):
    children = Student.objects.filter(parent=request.user)
    return render(request, 'parents/portal.html', {
        'children': children
    })
