from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditEntry(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Создание"
        UPDATE = "update", "Изменение"
        DELETE = "delete", "Удаление"

    class Status(models.TextChoices):
        ACTIVE = "active", "Выполнено"
        UNDONE = "undone", "Отменено"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name="Пользователь",
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_entries",
        verbose_name="Тип объекта",
    )

    object_id = models.CharField(
        max_length=255,
        verbose_name="ID объекта",
    )

    content_object = GenericForeignKey("content_type", "object_id")

    object_repr = models.CharField(
        max_length=500,
        verbose_name="Объект",
    )

    action = models.CharField(
        max_length=10,
        choices=Action.choices,
        verbose_name="Действие",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Статус",
    )

    before_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Состояние до действия",
    )

    after_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Состояние после действия",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата действия",
    )

    undone_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата отмены",
    )

    restored_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата повтора",
    )

    class Meta:
        verbose_name = "Запись истории"
        verbose_name_plural = "История действий"
        ordering = ("-created_at", "-pk")

        permissions = [
            ("undo_auditentry", "Может отменять действия"),
            ("redo_auditentry", "Может повторять действия"),
        ]

        indexes = [
            models.Index(fields=("content_type", "object_id")),
            models.Index(fields=("actor", "created_at")),
            models.Index(fields=("status", "created_at")),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.object_repr}"
