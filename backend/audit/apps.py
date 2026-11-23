from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
    verbose_name = "История действий"

    def ready(self):
        from . import signals
        from django.db.models.signals import post_migrate

        post_migrate.connect(
            self.grant_admin_permissions,
            sender=self,
        )

    @staticmethod
    def grant_admin_permissions(sender, **kwargs):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from .models import AuditEntry

        user_model = get_user_model()

        content_type = ContentType.objects.get_for_model(AuditEntry)

        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=[
                "view_auditentry",
                "undo_auditentry",
                "redo_auditentry",
            ],
        )

        for user in user_model.objects.filter(
            is_active=True,
            is_staff=True,
        ):
            user.user_permissions.add(*permissions)