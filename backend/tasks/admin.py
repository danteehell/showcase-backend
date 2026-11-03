from django.contrib import admin, messages
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline

from .models import Task, TaskAssignment, TaskCategory, TaskSkill


@admin.register(TaskCategory)
class TaskCategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "tasks_count")
    search_fields = ("name", "slug")
    list_display_links = ("name",)
    list_editable = ("slug",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request)

    @admin.display(description="Задач")
    def tasks_count(self, obj):
        return obj.tasks.count()


class SkillInline(TabularInline):
    model = TaskSkill
    extra = 1
    fields = ("skill", "level_required")


class AssignmentInline(TabularInline):
    model = TaskAssignment
    extra = 0
    can_delete = False
    fields = ("student", "status", "revision_count", "taken_at", "completed_at")
    readonly_fields = fields
    ordering = ("-taken_at",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = (
        "id",
        "title",
        "project",
        "curator",
        "category",
        "difficulty",
        "points",
        "status",
        "filled_display",
        "deadline",
    )
    list_filter = ("status", "difficulty", "category", "project", "curator")
    list_display_links = ("title",)
    search_fields = ("title", "short_description", "description")
    list_select_related = ("project", "curator", "category")
    list_per_page = 20
    date_hierarchy = "created_at"
    save_on_top = True
    raw_id_fields = ("project", "curator")
    autocomplete_fields = ("category",)
    inlines = (SkillInline, AssignmentInline)

    readonly_fields = (
        "created_at",
        "updated_at",
        "published_at",
        "taken_at",
        "completed_at",
        "withdrawn_at",
        "expired_at",
        "removed_at",
        "filled_people",
    )

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": ("title", "short_description", "description"),
            },
        ),
        (
            "Проект и куратор",
            {
                "fields": ("project", "curator", "category"),
            },
        ),
        (
            "Характеристики",
            {
                "fields": ("difficulty", "points"),
            },
        ),
        (
            "Сроки",
            {
                "fields": ("start_date", "deadline"),
            },
        ),
        (
            "Требования к исполнителю",
            {
                "fields": (
                    "required_people",
                    "filled_people",
                    "required_course_min",
                    "required_course_max",
                    "required_specialty",
                ),
            },
        ),
        (
            "Состояние",
            {
                "fields": ("status",),
            },
        ),
        (
            "Снятие с биржи",
            {
                "classes": ("collapse",),
                "fields": ("removal_reason", "removal_comment", "removed_at"),
            },
        ),
        (
            "Системные метки",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                    "published_at",
                    "taken_at",
                    "completed_at",
                    "withdrawn_at",
                    "expired_at",
                ),
            },
        ),
    )

    actions = ("action_publish", "action_withdraw", "action_expire")

    @admin.display(description="Набрано")
    def filled_display(self, obj):
        return f"{obj.filled_people} / {obj.required_people}"

    @admin.action(description="Опубликовать")
    def action_publish(self, request, queryset):
        updated = queryset.filter(status=Task.Status.DRAFT).update(
            status=Task.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.message_user(request, f"Опубликовано: {updated}", messages.SUCCESS)

    @admin.action(description="Снять с биржи")
    def action_withdraw(self, request, queryset):
        now = timezone.now()
        updated = queryset.exclude(
            status__in=[Task.Status.COMPLETED, Task.Status.WITHDRAWN]
        ).update(
            status=Task.Status.WITHDRAWN,
            withdrawn_at=now,
            removed_at=now,
            removal_reason=Task.RemovalReason.OTHER,
            removal_comment="Снято из админки",
        )
        self.message_user(request, f"Снято: {updated}", messages.SUCCESS)

    @admin.action(description="Пометить как истёкшие")
    def action_expire(self, request, queryset):
        updated = queryset.filter(status=Task.Status.PUBLISHED).update(
            status=Task.Status.EXPIRED,
            expired_at=timezone.now(),
        )
        self.message_user(request, f"Помечено: {updated}", messages.SUCCESS)


@admin.register(TaskSkill)
class TaskSkillAdmin(ModelAdmin):
    list_display = ("id", "task", "skill", "level_required")
    list_filter = ("level_required",)
    search_fields = ("skill", "task__title")
    list_select_related = ("task",)
    autocomplete_fields = ("task",)


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(ModelAdmin):
    list_display = (
        "id",
        "task",
        "student",
        "status",
        "revision_count",
        "revisions_left_display",
        "taken_at",
    )
    list_filter = ("status", "task__project", "task__curator")
    search_fields = ("task__title", "student__username", "student__email")
    list_select_related = ("task", "student")
    date_hierarchy = "taken_at"
    raw_id_fields = ("student", "removed_by")
    autocomplete_fields = ("task",)

    readonly_fields = (
        "taken_at",
        "started_at",
        "submitted_at",
        "completed_at",
        "removed_at",
        "removed_by",
        "removal_reason",
        "revision_count",
    )

    fieldsets = (
        (
            "Запись",
            {
                "fields": ("task", "student", "status"),
            },
        ),
        (
            "Ход работы",
            {
                "fields": (
                    "taken_at",
                    "started_at",
                    "submitted_at",
                    "completed_at",
                    "revision_count",
                ),
            },
        ),
        (
            "Снятие",
            {
                "fields": ("removed_at", "removal_reason", "removed_by"),
            },
        ),
    )

    actions = ("action_accept", "action_return")

    @admin.display(description="Осталось возвратов")
    def revisions_left_display(self, obj):
        return max(3 - obj.revision_count, 0)

    @admin.action(description="Принять работу")
    def action_accept(self, request, queryset):
        updated = queryset.filter(status=TaskAssignment.Status.SUBMITTED).update(
            status=TaskAssignment.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        skipped = queryset.count() - updated
        msg = f"Принято: {updated}"
        if skipped:
            msg += f", пропущено (не на проверке): {skipped}"
        self.message_user(request, msg, messages.SUCCESS)

    @admin.action(description="Вернуть на доработку")
    def action_return(self, request, queryset):
        qs = queryset.filter(
            status=TaskAssignment.Status.SUBMITTED,
            revision_count__lt=3,
        )
        count = 0
        for a in qs:
            a.status = TaskAssignment.Status.RETURNED
            a.revision_count = a.revision_count + 1
            a.save(update_fields=["status", "revision_count"])
            count += 1
        skipped = queryset.count() - count
        msg = f"Возвращено: {count}"
        if skipped:
            msg += f", пропущено (не submitted или лимит 3): {skipped}"
        self.message_user(request, msg, messages.SUCCESS)
