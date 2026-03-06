# students/context_processors.py  ← tengeneza file hii

from students.models import Student

def student_context(request):
    """Weka student kwenye context kila page kwa student users."""
    if request.user.is_authenticated and hasattr(request.user, 'role'):
        if request.user.role == 'STUDENT':
            try:
                student = Student.objects.get(user=request.user)
                return {'student': student}
            except Student.DoesNotExist:
                pass
    return {}