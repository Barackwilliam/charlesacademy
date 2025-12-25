from .models import Student   # 👈 LAZIMA UWEKE HII

def generate_registration_number(class_code, year):
    last_student = Student.objects.filter(
        classroom__code=class_code,
        admission_year=year
    ).count() + 1

    return f"CA/{class_code}/{year}/{str(last_student).zfill(4)}"


# students/utils.py
from accounts.models import User

def create_student_user(student):
    first_name = student.full_name.split()[0]  # first word
    last_name = ' '.join(student.full_name.split()[1:]) if len(student.full_name.split()) > 1 else ''
    default_password = f"{first_name}@123"

    user = User.objects.create_user(
        username=student.registration_number,
        password=default_password,
        role='STUDENT',
        first_name=first_name,
        last_name=last_name
    )
    return user
