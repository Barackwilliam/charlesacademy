from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import re

User = get_user_model()

class SlashFriendlyModelBackend(ModelBackend):
    """Backend that handles usernames with slashes"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        # Try exact match first
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        
        # Try case-insensitive match
        try:
            user = User.objects.get(username__iexact=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        
        # Try with underscores replaced (for legacy)
        try:
            username_with_underscores = username.replace('/', '_')
            user = User.objects.get(username__iexact=username_with_underscores)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        
        # Try with underscores replaced the other way
        try:
            username_with_slashes = username.replace('_', '/')
            user = User.objects.get(username__iexact=username_with_slashes)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        
        return None