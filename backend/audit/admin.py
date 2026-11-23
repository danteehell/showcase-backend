import json

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import AuditEntry
from .services import redo_entry, undo_entry


@admin.register(AuditEntry)
class AuditEntryAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "actor",
        "action",
        "object_repr",
        "status",
        "object_id",
        "history_controls",
    )

    list_filter = ("action", "status", "created_at")

    search_fields = (
        "object_repr",
        "object_id",
        "actor__username",
        "actor__first_name",
        "actor__last_name",
    )

    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_per_page = 50
    actions = None

    readonly_fields = (
        "actor",
        "content_type",
        "object_id",
        "object_repr",
        "action",
        "status",
        "before_data_pretty",
        "after_data_pretty",
        "created_at",
        "undone_at",
        "restored_at",
    )

    fields = (
        "created_at",
        "actor",
        "action",
        "object_repr",
        "content_type",
        "object_id",
        "status",
        "before_data_pretty",
        "after_data_pretty",
        "undone_at",
        "restored_at",
    )

    def get_urls(self):
        custom_urls = [
            path(
                "<int:entry_id>/undo/",
                self.admin_site.admin_view(self.undo_view),
                name="audit_auditentry_undo",
            ),
            path(
                "<int:entry_id>/redo/",
                self.admin_site.admin_view(self.redo_view),
                name="audit_auditentry_redo",
            ),
        ]

        return custom_urls + super().get_urls()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def history_controls(self, obj):
        request = self._request

        if obj.status == AuditEntry.Status.ACTIVE:
            permission = "audit.undo_auditentry"
            url = reverse("admin:audit_auditentry_undo", args=(obj.pk,))
            label = "Отменить"
        else:
            permission = "audit.redo_auditentry"
            url = reverse("admin:audit_auditentry_redo", args=(obj.pk,))
            label = "Повторить"

        if not request.user.has_perm(permission):
            return "—"

        return format_html(
            '<a href="{}" class="inline-flex items-center rounded-default '
            'bg-primary-600 px-3 py-1.5 text-sm font-medium text-white '
            'hover:bg-primary-700">{}</a>',
            url,
            label,
        )

    history_controls.short_description = "Управление"

    def get_queryset(self, request):
        self._request = request
        return super().get_queryset(request)

    def undo_view(self, request, entry_id):
        return self.process_action(request, entry_id, undo_entry)

    def redo_view(self, request, entry_id):
        return self.process_action(request, entry_id, redo_entry)

    def process_action(self, request, entry_id, service):
        if not self.has_view_permission(request):
            raise PermissionDenied

        permission = (
            "audit.undo_auditentry"
            if service is undo_entry
            else "audit.redo_auditentry"
        )

        if not request.user.has_perm(permission):
            raise PermissionDenied

        entry = get_object_or_404(AuditEntry, pk=entry_id)

        if request.method == "GET":
            operation = "отменить" if service is undo_entry else "повторить"

            context = {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "entry": entry,
                "operation": operation,
            }

            return TemplateResponse(
                request,
                "admin/audit/auditentry/action_confirm.html",
                context,
            )

        if request.method != "POST":
            raise PermissionDenied

        try:
            service(entry.pk)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Операция успешно выполнена.")

        return redirect("admin:audit_auditentry_changelist")
    def before_data_pretty(self, obj):
        return self.format_json(obj.before_data)

    before_data_pretty.short_description = "Состояние до действия"

    def after_data_pretty(self, obj):
        return self.format_json(obj.after_data)

    after_data_pretty.short_description = "Состояние после действия"

    @staticmethod
    def format_json(data):
        if data is None:
            return "Нет данных"

        return format_html(
            '<pre class="max-w-4xl whitespace-pre-wrap">{}</pre>',
            json.dumps(data, ensure_ascii=False, indent=2),
        )
