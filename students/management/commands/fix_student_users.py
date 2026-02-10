from django.core.management.base import BaseCommand
from students.models import Student
from accounts.models import User
from students.utils import create_student_user
import logging
import re

logger = logging.getLogger(__name__)

def create_username_with_slashes(registration_number):
    """
    Create username with slashes (not underscores)
    Returns registration number in lowercase
    """
    # Return registration number in lowercase, keep slashes
    username = registration_number.strip().lower()
    # Remove any extra whitespace
    username = username.replace(' ', '')
    return username

class Command(BaseCommand):
    help = 'Fix student user accounts and ensure proper linking'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='Reset all student passwords to default format'
        )
        parser.add_argument(
            '--fix-usernames',
            action='store_true',
            help='Fix usernames to match registration numbers (with slashes)'
        )
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Create missing user accounts for students'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force fix even if accounts exist'
        )
        parser.add_argument(
            '--reg-number',
            type=str,
            help='Fix specific student by registration number'
        )
        parser.add_argument(
            '--keep-case',
            action='store_true',
            help='Keep original case of registration number for username'
        )
    
    def handle(self, *args, **options):
        # Filter students if specific reg number provided
        if options['reg_number']:
            students = Student.objects.filter(
                registration_number__icontains=options['reg_number']
            )
        else:
            students = Student.objects.all()
        
        fixed_count = 0
        error_count = 0
        created_count = 0
        skipped_count = 0
        
        self.stdout.write(f"\n🔍 Processing {students.count()} students...\n")
        
        for student in students:
            try:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"Student: {student.full_name}")
                self.stdout.write(f"Reg No: {student.registration_number}")
                self.stdout.write(f"Email: {student.email}")
                self.stdout.write(f"User Account: {'✓' if student.user else '✗'}")
                
                # 1. CREATE MISSING USER ACCOUNTS
                if not student.user:
                    self.stdout.write(self.style.WARNING("  ⚠ No user account found!"))
                    
                    if options['create_missing'] or options['force']:
                        try:
                            # Get correct username with slashes
                            if options['keep_case']:
                                correct_username = student.registration_number.strip()
                            else:
                                correct_username = student.registration_number.strip().lower()
                            
                            # Check if username already exists
                            if User.objects.filter(username=correct_username).exists():
                                # Add suffix
                                counter = 1
                                while User.objects.filter(username=f"{correct_username}_{counter}").exists():
                                    counter += 1
                                correct_username = f"{correct_username}_{counter}"
                            
                            # Create password
                            name_parts = student.full_name.split()
                            if name_parts:
                                first_name = re.sub(r'[^a-zA-Z]', '', name_parts[0]).lower()
                            else:
                                first_name = "student"
                            password = f"{first_name}@123"
                            
                            # Split name
                            if len(name_parts) >= 2:
                                first_name_part = name_parts[0]
                                last_name_part = ' '.join(name_parts[1:])
                            else:
                                first_name_part = student.full_name
                                last_name_part = ""
                            
                            # Create user
                            user = User.objects.create_user(
                                username=correct_username,
                                email=student.email.strip().lower() if student.email else f"{correct_username.replace('/', '_')}@charlesacademy.com",
                                password=password,
                                first_name=first_name_part,
                                last_name=last_name_part,
                                role='STUDENT'
                            )
                            
                            # Link to student
                            student.user = user
                            student.save(update_fields=['user'])
                            
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"  ✅ Created user: {correct_username}")
                            )
                            self.stdout.write(
                                self.style.SUCCESS(f"     Password: {password}")
                            )
                            
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(f"  ❌ Creation error: {e}")
                            )
                    else:
                        skipped_count += 1
                    continue
                
                # 2. CHECK AND FIX USERNAME (only if needed)
                if options['keep_case']:
                    correct_username = student.registration_number.strip()
                else:
                    correct_username = student.registration_number.strip().lower()
                
                current_username = student.user.username
                
                # Check if username already has slashes and is correct
                has_slashes = '/' in current_username
                is_correct = current_username.lower() == correct_username.lower()
                
                if not is_correct:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Username needs fixing!")
                    )
                    self.stdout.write(f"    Current: {current_username}")
                    self.stdout.write(f"    Correct: {correct_username}")
                    self.stdout.write(f"    Has slashes: {'✓' if has_slashes else '✗'}")
                    
                    if options['fix_usernames'] or options['force']:
                        # Check if correct username exists
                        if User.objects.filter(username=correct_username).exclude(id=student.user.id).exists():
                            self.stdout.write(
                                self.style.ERROR(f"  ❌ Username {correct_username} already taken")
                            )
                            
                            # Try alternatives
                            alternatives = [
                                f"{correct_username}_{student.id}",
                                f"{correct_username.replace('/', '-')}",
                                f"stu_{student.registration_number.lower().replace('/', '')}"
                            ]
                            
                            fixed = False
                            for alt in alternatives:
                                if not User.objects.filter(username=alt).exists():
                                    student.user.username = alt
                                    student.user.save()
                                    fixed_count += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(f"  ✅ Changed to alternative: {alt}")
                                    )
                                    fixed = True
                                    break
                            
                            if not fixed:
                                error_count += 1
                                self.stdout.write(
                                    self.style.ERROR(f"  ❌ Could not find alternative username")
                                )
                        else:
                            try:
                                student.user.username = correct_username
                                student.user.save()
                                fixed_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"  ✅ Fixed username to: {correct_username}")
                                )
                            except Exception as e:
                                error_count += 1
                                self.stdout.write(
                                    self.style.ERROR(f"  ❌ Error fixing username: {e}")
                                )
                else:
                    # Username is already correct
                    if has_slashes:
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✓ Username already has slashes: {current_username}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ Username correct but no slashes: {current_username}")
                        )
                        if options['fix_usernames'] or options['force']:
                            # Try to add slashes
                            username_with_slashes = current_username.replace('_', '/')
                            if username_with_slashes != current_username and not User.objects.filter(username=username_with_slashes).exists():
                                student.user.username = username_with_slashes
                                student.user.save()
                                fixed_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"  ✅ Added slashes: {username_with_slashes}")
                                )
                
                # 3. CHECK AND FIX EMAIL
                student_email = student.email.strip().lower() if student.email else ""
                user_email = student.user.email.strip().lower() if student.user.email else ""
                
                if student_email and user_email != student_email:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Email mismatch!")
                    )
                    self.stdout.write(f"    Student: {student_email}")
                    self.stdout.write(f"    User: {user_email}")
                    
                    if options['force']:
                        # Check if email exists
                        if User.objects.filter(email=student_email).exclude(id=student.user.id).exists():
                            self.stdout.write(
                                self.style.ERROR(f"  ❌ Email {student_email} already taken")
                            )
                        else:
                            try:
                                student.user.email = student_email
                                student.user.save()
                                fixed_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"  ✅ Fixed email to: {student_email}")
                                )
                            except Exception as e:
                                error_count += 1
                                self.stdout.write(
                                    self.style.ERROR(f"  ❌ Error fixing email: {e}")
                                )
                
                # 4. RESET PASSWORDS
                if options['reset_passwords'] or options['force']:
                    try:
                        # Get first name for password
                        name_parts = student.full_name.split()
                        if name_parts:
                            first_name = re.sub(r'[^a-zA-Z]', '', name_parts[0]).lower()
                        else:
                            first_name = "student"
                        
                        new_password = f"{first_name}@123"
                        student.user.set_password(new_password)
                        student.user.save()
                        
                        fixed_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✅ Reset password to: {new_password}")
                        )
                        
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"  ❌ Error resetting password: {e}")
                        )
                
                # 5. CHECK LOGIN CAPABILITY
                if student.user:
                    try:
                        from django.contrib.auth import authenticate
                        
                        # Get password to test
                        name_parts = student.full_name.split()
                        if name_parts:
                            first_name = re.sub(r'[^a-zA-Z]', '', name_parts[0]).lower()
                        else:
                            first_name = "student"
                        
                        test_password = f"{first_name}@123"
                        
                        # Try multiple username formats for login
                        usernames_to_try = [
                            student.user.username,  # Current username
                            student.registration_number.lower(),  # Reg number lowercase
                            student.registration_number.upper(),  # Reg number uppercase
                        ]
                        
                        logged_in = False
                        for test_username in usernames_to_try:
                            user = authenticate(
                                username=test_username,
                                password=test_password
                            )
                            
                            if user:
                                logged_in = True
                                self.stdout.write(
                                    self.style.SUCCESS(f"  ✅ Login passed with: {test_username}")
                                )
                                break
                        
                        if not logged_in:
                            self.stdout.write(
                                self.style.WARNING(f"  ⚠ Login failed with all formats")
                            )
                            # Show what was tried
                            self.stdout.write(f"     Tried usernames: {', '.join(usernames_to_try[:2])}")
                            self.stdout.write(f"     Password used: {test_password}")
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ Could not test login: {e}")
                        )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Error processing {student.registration_number}: {e}")
                )
        
        # SUMMARY
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(
            f"\n📊 SUMMARY:\n"
            f"✅ Created: {created_count} new user accounts\n"
            f"✅ Fixed: {fixed_count} issues\n"
            f"❌ Errors: {error_count}\n"
            f"⏭️  Skipped: {skipped_count} (no action taken)\n"
            f"📋 Total students processed: {students.count()}"
        ))
        
        # RECOMMENDATIONS
        self.stdout.write(f"\n💡 RECOMMENDED COMMANDS:")
        
        students_without_users = students.filter(user__isnull=True).count()
        if students_without_users > 0:
            self.stdout.write(f"  python manage.py fix_student_users --create-missing")
            self.stdout.write(f"    → Will create {students_without_users} missing accounts")
        
        self.stdout.write(f"  python manage.py fix_student_users --fix-usernames --reset-passwords")
        self.stdout.write(f"    → Fix usernames and reset passwords")
        
        self.stdout.write(f"  python manage.py fix_student_users --force")
        self.stdout.write(f"    → Fix EVERYTHING (create, fix, reset)")
        
        self.stdout.write(f"  python manage.py fix_student_users --keep-case")
        self.stdout.write(f"    → Keep original case of registration numbers")
        
        # Show quick test command
        self.stdout.write(f"\n🔐 QUICK LOGIN TEST:")
        self.stdout.write(f"  python manage.py shell")
        self.stdout.write(f"  >>> from django.contrib.auth import authenticate")
        self.stdout.write(f"  >>> user = authenticate(username='ca/eng/2025/0047', password='akimana@123')")
        self.stdout.write(f"  >>> print('Success!' if user else 'Failed')")