from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import Collector
from django.utils import timezone

from .context import resume_audit, suspend_audit
from .models import AuditEntry
from .snapshots import apply_snapshot, create_snapshot


@contextmanager
def audit_suppressed():
    token = suspend_audit()

    try:
        yield
    finally:
        resume_audit(token)


def get_model(entry):
    if entry.content_type is None:
        raise ValidationError("Не удалось определить модель объекта.")

    model = entry.content_type.model_class()

    if model is None:
        raise ValidationError("Модель объекта больше не существует.")

    return model


def get_object(entry, model):
    try:
        return model.objects.select_for_update().get(pk=entry.object_id)
    except model.DoesNotExist:
        return None


def ensure_safe_delete(obj):
    collector = Collector(using=obj._state.db)
    collector.collect([obj])

    related_models = {
        model
        for model, objects in collector.data.items()
        if model is not obj.__class__
        and not model._meta.auto_created
        and objects
    }

    fast_delete_models = {
        queryset.model
        for queryset in collector.fast_deletes
        if not queryset.model._meta.auto_created
    }

    if related_models or fast_delete_models or collector.field_updates:
        raise ValidationError(
            "У объекта есть связанные записи. "
            "Сначала восстановите или обработайте связанные объекты отдельно."
        )


def undo_entry(entry_id):
    with transaction.atomic(), audit_suppressed():
        entry = AuditEntry.objects.select_for_update().get(pk=entry_id)

        if entry.status != AuditEntry.Status.ACTIVE:
            raise ValidationError("Это действие уже отменено.")

        model = get_model(entry)
        obj = get_object(entry, model)

        if entry.action == AuditEntry.Action.CREATE:
            if obj is None:
                raise ValidationError("Созданный объект уже отсутствует.")

            if create_snapshot(obj) != entry.after_data:
                raise ValidationError(
                    "Объект изменился после создания. Отмена невозможна."
                )

            ensure_safe_delete(obj)
            obj.delete()

        elif entry.action == AuditEntry.Action.UPDATE:
            if obj is None:
                raise ValidationError("Объект больше не существует.")

            if create_snapshot(obj) != entry.after_data:
                raise ValidationError(
                    "Объект изменился после действия. Отмена невозможна."
                )

            apply_snapshot(obj, entry.before_data)

        elif entry.action == AuditEntry.Action.DELETE:
            if obj is not None:
                raise ValidationError("Объект с таким ID уже существует.")

            obj = model()
            apply_snapshot(obj, entry.before_data)

        else:
            raise ValidationError("Неизвестный тип действия.")

        entry.status = AuditEntry.Status.UNDONE
        entry.undone_at = timezone.now()
        entry.restored_at = None
        entry.save(
            update_fields=("status", "undone_at", "restored_at")
        )

    return entry


def redo_entry(entry_id):
    with transaction.atomic(), audit_suppressed():
        entry = AuditEntry.objects.select_for_update().get(pk=entry_id)

        if entry.status != AuditEntry.Status.UNDONE:
            raise ValidationError("Это действие нельзя повторить.")

        model = get_model(entry)
        obj = get_object(entry, model)

        if entry.action == AuditEntry.Action.CREATE:
            if obj is not None:
                raise ValidationError("Объект с таким ID уже существует.")

            obj = model()
            apply_snapshot(obj, entry.after_data)

        elif entry.action == AuditEntry.Action.UPDATE:
            if obj is None:
                raise ValidationError("Объект больше не существует.")

            if create_snapshot(obj) != entry.before_data:
                raise ValidationError(
                    "Объект изменился после отмены. Повтор невозможен."
                )

            apply_snapshot(obj, entry.after_data)

        elif entry.action == AuditEntry.Action.DELETE:
            if obj is None:
                raise ValidationError("Объект уже отсутствует.")

            if create_snapshot(obj) != entry.before_data:
                raise ValidationError(
                    "Объект изменился после отмены. Повтор невозможен."
                )

            ensure_safe_delete(obj)
            obj.delete()

        else:
            raise ValidationError("Неизвестный тип действия.")

        entry.status = AuditEntry.Status.ACTIVE
        entry.restored_at = timezone.now()
        entry.undone_at = None
        entry.save(
            update_fields=("status", "restored_at", "undone_at")
        )

    return entry
