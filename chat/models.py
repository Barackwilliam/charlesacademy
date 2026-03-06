from django.db import models
from django.conf import settings
import uuid


class ChatSession(models.Model):
    """Represents a chat session — works for logged-in and guest users"""
    STATUS_CHOICES = [('open', 'Open'), ('closed', 'Closed')]

    session_id   = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    guest_name   = models.CharField(max_length=100, blank=True, default='Guest')
    guest_email  = models.EmailField(blank=True)
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    is_read_by_admin = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        name = self.user.get_full_name() if self.user else self.guest_name
        return f"Chat – {name} ({self.session_id})"

    @property
    def display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.guest_name or 'Guest'

    @property
    def unread_for_admin(self):
        return self.messages.filter(sender='student', is_read=False).count()


class ChatMessage(models.Model):
    SENDER_CHOICES = [('student', 'Student'), ('admin', 'Admin')]

    session   = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender    = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message   = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read   = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.sender}] {self.message[:50]}"
