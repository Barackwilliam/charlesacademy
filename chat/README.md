# Live Chat System — Setup Guide

## 1. Copy the `chat` folder into your Django project root
   (same level as `manage.py`)

## 2. Add to INSTALLED_APPS in settings.py
```python
INSTALLED_APPS = [
    ...
    'chat',
]
```

## 3. Add to main urls.py
```python
from django.urls import path, include

urlpatterns = [
    ...
    path('chat/', include('chat.urls', namespace='chat')),
]
```

## 4. Run migrations
```bash
python manage.py migrate
```

## 5. Include widget in base.html
Add this ONE line just before the closing </body> tag in your base.html:
```html
{% include 'chat/widget.html' %}
```
This makes the chat button appear on ALL pages automatically —
both inside and outside the login system.

## 6. Admin panel URL
Admin staff can access the support panel at:
  http://yoursite.com/chat/admin/panel/

You can add it to your sidebar with:
```html
<a href="{% url 'chat:admin_panel' %}">
  <i class="bi bi-headset"></i> Live Chat
</a>
```

## File structure
```
chat/
  __init__.py
  apps.py
  models.py
  views.py
  urls.py
  migrations/
    __init__.py
    0001_initial.py
  templates/
    chat/
      widget.html       ← floating button (included in base.html)
      admin_panel.html  ← admin support panel
```

## Features included
- Floating button (bottom-right) on all pages
- Works for logged-in students AND guests (no account needed)
- Guest form asks for name before starting chat
- Real-time polling every 3 seconds
- Sound notification for new messages
- Unread badge on floating button
- Admin panel with session list, search, and reply
- Read receipts (✓✓)
- Session close by admin
- Toast notifications for admin

## No extra packages needed
Just standard Django — no Redis, no Channels, no WebSockets setup required.
