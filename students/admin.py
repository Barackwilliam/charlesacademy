from django.contrib import admin
from .models import Student

# students/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Student, Certificate


# ── Inline: Certificates inside Student admin ──────────────────────────────
class CertificateInline(admin.TabularInline):
    model        = Certificate
    extra        = 1
    fields       = ('title', 'cert_type', 'file', 'issued_date', 'description')
    readonly_fields = ('created_at',)
    show_change_link = True

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


# ── Standalone Certificate Admin ────────────────────────────────────────────
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display  = (
        'title', 'student_name', 'cert_type',
        'issued_date', 'download_link', 'created_at'
    )
    list_filter   = ('cert_type', 'issued_date', 'student__classroom')
    search_fields = (
        'title',
        'student__full_name',
        'student__registration_number',
    )
    autocomplete_fields = ['student']
    readonly_fields     = ('uploaded_by', 'created_at', 'download_link')
    date_hierarchy      = 'issued_date'

    fieldsets = (
        ('Certificate Info', {
            'fields': ('student', 'title', 'cert_type', 'issued_date', 'description')
        }),
        ('File', {
            'fields': ('file', 'download_link')
        }),
        ('Meta', {
            'fields': ('uploaded_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def student_name(self, obj):
        return obj.student.full_name
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'student__full_name'

    
    def download_link(self, obj):
        if obj.file:
            cdn_url = str(obj.file.cdn_url)
            return format_html(
                '<a href="{}" target="_blank" '
                'style="background:#4361ee;color:white;padding:4px 10px;'
                'border-radius:4px;text-decoration:none;font-size:12px;">'
                '⬇ Download</a>',
                cdn_url
            )
        return '—'
    download_link.short_description = 'File'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


# ── Student Admin (with Certificate inline) ─────────────────────────────────
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display   = (
        'full_name', 'registration_number',
        'classroom', 'status', 'admission_year',
        'certificate_count'
    )
    list_filter    = ('status', 'classroom', 'admission_year')
    search_fields  = ('full_name', 'registration_number', 'email')
    inlines        = [CertificateInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Personal Info', {
            'fields': ('full_name', 'email', 'photo')
        }),
        ('Academic Info', {
            'fields': ('classroom', 'registration_number', 'admission_year', 'status')
        }),
        ('Account', {
            'fields': ('user',)
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def certificate_count(self, obj):
        count = obj.certificates.count()
        if count:
            return format_html(
                '<span style="background:#10b981;color:white;padding:2px 8px;'
                'border-radius:12px;font-size:12px;">{} cert(s)</span>',
                count
            )
        # ✅ tumia mark_safe badala ya format_html bila arguments akimana@123
        from django.utils.safestring import mark_safe
        return mark_safe('<span style="color:#aaa;font-size:12px;">None</span>')
    certificate_count.short_description = 'Certificates'