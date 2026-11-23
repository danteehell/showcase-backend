import json

from django.core.serializers.json import DjangoJSONEncoder


SENSITIVE_FIELDS = {
    "password",
    "token",
    "secret",
    "api_key",
    "access_token",
    "refresh_token",
}


def create_snapshot(obj):
    if obj is None:
        return None

    fields = {}

    for field in obj._meta.concrete_fields:
        if field.name.lower() in SENSITIVE_FIELDS:
            continue

        fields[field.attname] = getattr(obj, field.attname)

    many_to_many = {}

    for field in obj._meta.many_to_many:
        if field.remote_field.through._meta.auto_created:
            many_to_many[field.name] = list(
                getattr(obj, field.name).values_list("pk", flat=True)
            )

    snapshot = {
        "model": obj._meta.label_lower,
        "pk": obj.pk,
        "fields": fields,
        "many_to_many": many_to_many,
    }

    return json.loads(json.dumps(snapshot, cls=DjangoJSONEncoder))


def apply_snapshot(obj, snapshot):
    if not snapshot:
        return obj

    fields = {
        field.attname: field
        for field in obj._meta.concrete_fields
    }

    for name, value in snapshot["fields"].items():
        field = fields.get(name)

        if field is None:
            continue

        setattr(obj, name, field.to_python(value))

    obj.save(force_insert=obj._state.adding)

    for name, ids in snapshot.get("many_to_many", {}).items():
        field = obj._meta.get_field(name)

        if field.remote_field.through._meta.auto_created:
            getattr(obj, name).set(ids)

    return obj
