import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import ChatSession, ChatMessage


# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────

def _message_to_dict(msg):
    return {
        'id':        msg.id,
        'sender':    msg.sender,
        'message':   msg.message,
        'timestamp': msg.timestamp.strftime('%H:%M'),
        'is_read':   msg.is_read,
    }


# ─────────────────────────────────────────
#  STUDENT / GUEST ENDPOINTS
# ─────────────────────────────────────────

@csrf_exempt
def start_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data = json.loads(request.body or '{}')

    if request.user.is_authenticated:
        session, _ = ChatSession.objects.get_or_create(
            user=request.user,
            status='open',
            defaults={'guest_name': request.user.get_full_name()}
        )
    else:
        guest_name  = data.get('name', 'Guest')
        guest_email = data.get('email', '')
        sid = request.session.get('chat_session_id')
        session = None
        if sid:
            session = ChatSession.objects.filter(session_id=sid, status='open').first()
        if not session:
            session = ChatSession.objects.create(
                guest_name=guest_name,
                guest_email=guest_email,
            )
            request.session['chat_session_id'] = str(session.session_id)

    # Auto welcome message (only once)
    if not session.messages.exists():
        ChatMessage.objects.create(
            session=session,
            sender='admin',
            message='Hello 👋 Welcome to Charles Academy. How can we assist you today?',
        )

    return JsonResponse({
        'session_id': str(session.session_id),
        'status':     session.status,
    })


@csrf_exempt
def send_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data       = json.loads(request.body or '{}')
    session_id = data.get('session_id')
    text       = data.get('message', '').strip()

    if not session_id or not text:
        return JsonResponse({'error': 'session_id and message required'}, status=400)

    session = get_object_or_404(ChatSession, session_id=session_id)
    msg = ChatMessage.objects.create(session=session, sender='student', message=text)

    session.is_read_by_admin = False
    session.save(update_fields=['updated_at', 'is_read_by_admin'])

    return JsonResponse({'ok': True, 'message': _message_to_dict(msg)})


def poll_messages(request, session_id):
    session  = get_object_or_404(ChatSession, session_id=session_id)
    try:
        after_id = int(request.GET.get('after', 0))
    except (ValueError, TypeError):
        after_id = 0

    msgs = session.messages.filter(id__gt=after_id)
    msgs.filter(sender='admin').update(is_read=True)

    return JsonResponse({
        'messages':       [_message_to_dict(m) for m in msgs],
        'session_status': session.status,
    })


@csrf_exempt
def delete_session(request):
    """Student deletes their own chat — clears messages and removes session."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data       = json.loads(request.body or '{}')
    session_id = data.get('session_id')
    if not session_id:
        return JsonResponse({'ok': True})  # nothing to delete

    session = ChatSession.objects.filter(session_id=session_id).first()
    if session:
        # Verify ownership
        if request.user.is_authenticated:
            if session.user != request.user:
                return JsonResponse({'error': 'Forbidden'}, status=403)
        else:
            sid = request.session.get('chat_session_id')
            if str(session.session_id) != sid:
                return JsonResponse({'error': 'Forbidden'}, status=403)

        session.messages.all().delete()
        session.delete()
        # Clear from browser session too
        if 'chat_session_id' in request.session:
            del request.session['chat_session_id']

    return JsonResponse({'ok': True})


# ─────────────────────────────────────────
#  ADMIN ENDPOINTS
# ─────────────────────────────────────────

@staff_member_required
def admin_chat_panel(request):
    sessions = ChatSession.objects.all().order_by('-updated_at')
    return render(request, 'chat/admin_panel.html', {'sessions': sessions})


@staff_member_required
def admin_get_sessions(request):
    sessions = ChatSession.objects.all().order_by('-updated_at')
    data = []
    for s in sessions:
        last_msg = s.messages.last()
        data.append({
            'id':           str(s.session_id),
            'name':         s.display_name,
            'last_message': last_msg.message[:60] if last_msg else '',
            'last_time':    last_msg.timestamp.strftime('%H:%M') if last_msg else '',
            'unread':       s.unread_for_admin,
            'status':       s.status,
        })
    return JsonResponse({'sessions': data})


@staff_member_required
def admin_get_messages(request, session_id):
    session  = get_object_or_404(ChatSession, session_id=session_id)
    try:
        after_id = int(request.GET.get('after', 0))
    except (ValueError, TypeError):
        after_id = 0

    msgs = session.messages.filter(id__gt=after_id)
    msgs.filter(sender='student').update(is_read=True)
    session.is_read_by_admin = True
    session.save(update_fields=['is_read_by_admin'])

    return JsonResponse({
        'messages': [_message_to_dict(m) for m in msgs],
        'name':     session.display_name,
        'status':   session.status,
    })


@csrf_exempt
@staff_member_required
def admin_send_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data       = json.loads(request.body or '{}')
    session_id = data.get('session_id')
    text       = data.get('message', '').strip()

    if not session_id or not text:
        return JsonResponse({'error': 'session_id and message required'}, status=400)

    session = get_object_or_404(ChatSession, session_id=session_id)
    msg = ChatMessage.objects.create(session=session, sender='admin', message=text)
    session.save(update_fields=['updated_at'])

    return JsonResponse({'ok': True, 'message': _message_to_dict(msg)})


@csrf_exempt
@staff_member_required
def admin_close_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data    = json.loads(request.body or '{}')
    session = get_object_or_404(ChatSession, session_id=data.get('session_id'))
    session.status = 'closed'
    session.save(update_fields=['status'])
    return JsonResponse({'ok': True})


@csrf_exempt
@staff_member_required
def admin_delete_session(request):
    """Admin deletes a chat session entirely."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data    = json.loads(request.body or '{}')
    session = ChatSession.objects.filter(session_id=data.get('session_id')).first()
    if session:
        session.messages.all().delete()
        session.delete()
    return JsonResponse({'ok': True})