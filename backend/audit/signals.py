from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver

from .context import get_current_user, is_audit_suspended
from .models import AuditEntry
from .snapshots import create_snapshot


TRACKED_APPS = {"showcase", "users", "tasks"}


def should_track(sender, raw=False):
    return (
        not raw
        and not is_audit_suspended()
        and sender._meta.app_label in TRACKED_APPS
        and sender is not AuditEntry
    )


def get_actor():
    user = get_current_user()

    if user is not None and getattr(user, "is_authenticated", False):
        return user

    return None


def create_entry(instance, action, before, after):
    AuditEntry.objects.create(
        actor=get_actor(),
        content_type=ContentType.objects.get_for_model(instance.__class__),
        object_id=str(instance.pk),
        object_repr=str(instance)[:500],
        action=action,
        before_data=before,
        after_data=after,
    )


@receiver(pre_save)
def capture_before_save(sender, instance, raw=False, **kwargs):
    if not should_track(sender, raw):
        return

    if instance.pk is None:
        instance._audit_before = None
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_before = None
    else:
        instance._audit_before = create_snapshot(old_instance)


@receiver(post_save)
def record_save(sender, instance, created, raw=False, **kwargs):
    if not should_track(sender, raw):
        return

    before = getattr(instance, "_audit_before", None)
    after = create_snapshot(instance)

    if not created and before == after:
        return

    action = (
        AuditEntry.Action.CREATE
        if created
        else AuditEntry.Action.UPDATE
    )

    create_entry(instance, action, before, after)


@receiver(pre_delete)
def capture_before_delete(sender, instance, **kwargs):
    if not should_track(sender):
        return

    instance._audit_before_delete = create_snapshot(instance)


@receiver(post_delete)
def record_delete(sender, instance, **kwargs):
    if not should_track(sender):
        return

    create_entry(
        instance,
        AuditEntry.Action.DELETE,
        getattr(instance, "_audit_before_delete", None),
        None,
    )


@receiver(m2m_changed)
def record_many_to_many(sender, instance, action, reverse, **kwargs):
    if reverse or not should_track(instance.__class__):
        return

    field = next(
        (
            item
            for item in instance._meta.many_to_many
            if item.remote_field.through is sender
        ),
        None,
    )

    if field is None or not field.remote_field.through._meta.auto_created:
        return

    if action in {"pre_add", "pre_remove", "pre_clear"}:
        instance._audit_m2m_before = create_snapshot(instance)
        return

    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    before = getattr(instance, "_audit_m2m_before", None)
    after = create_snapshot(instance)

    if before == after:
        return

    create_entry(
        instance,
        AuditEntry.Action.UPDATE,
        before,
        after,
    )

    instance._audit_m2m_before = None
