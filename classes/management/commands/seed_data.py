from django.core.management.base import BaseCommand
from classes.models import ClassRoom, Subject

class Command(BaseCommand):
    def handle(self, *args, **kwargs):

        classes = {
            'English Class': ('ENG', [
                'Grammar','Writing skills','Reading skills','Speaking & listening'
            ]),
            'Kiswahili Class': ('KISW', [
                'Sarufi','Uandishi','Kusoma','Kuongea'
            ]),
            'French Class': ('FRA', [
                'Grammaire','Écriture','Lecture','Conversation'
            ]),
            'Website Design': ('WED', [
                'HTML','CSS','JavaScript','WordPress','Website hosting'
            ]),
            'Graphics Design': ('GD', [
                'Canva','PixelLab','Design principles','Branding basics'
            ]),
            'Entrepreneurship': ('ENT', [
                'Business idea creation','Marketing basics',
                'Financial literacy','Business planning'
            ])
        }

        for name, (code, subjects) in classes.items():
            c, _ = ClassRoom.objects.get_or_create(
                name=name, code=code, fee=30000
            )
            for s in subjects:
                Subject.objects.get_or_create(name=s, classroom=c)

        self.stdout.write(self.style.SUCCESS('Classes & Subjects seeded'))



#python manage.py seed_data
