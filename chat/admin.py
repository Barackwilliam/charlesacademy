from django.contrib import admin
from .models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('sender', 'message', 'timestamp', 'is_read')
    ordering = ('timestamp',)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        'display_name',
        'guest_email',
        'status',
        'created_at',
        'updated_at',
        'is_read_by_admin'
    )

    list_filter = ('status', 'created_at', 'is_read_by_admin')

    search_fields = (
        'guest_name',
        'guest_email',
        'user__username',
        'user__first_name',
        'user__last_name'
    )

    readonly_fields = (
        'session_id',
        'created_at',
        'updated_at'
    )

    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        'session',
        'sender',
        'short_message',
        'timestamp',
        'is_read'
    )

    list_filter = ('sender', 'timestamp', 'is_read')
    search_fields = ('message',)

    def short_message(self, obj):
        return obj.message[:50]
    short_message.short_description = "Message"