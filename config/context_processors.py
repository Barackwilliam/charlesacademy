
from django.conf import settings as django_settings

def uploadcare_key(request):
    """Weka Uploadcare public key ipatikane kwenye templates zote."""
    uploadcare_config = getattr(django_settings, 'UPLOADCARE', {})
    return {
        'UPLOADCARE_PUBLIC_KEY': uploadcare_config.get('pub_key', '')
    }

