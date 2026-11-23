import logging

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Prefetch
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    FilterCategory,
    FilterOption,
    Project,
    ProjectApplication,
    ProjectEnrollment,
    ProjectListItem,
)


logger = logging.getLogger(__name__)

admin.site.site_header = "Управление проектами"
admin.site.site_title = "Управление проектами"
admin.site.index_title = "Панель управления проектами"


def get_student_profile(student):
    return getattr(student, "student_profile", None)


def get_student_group(student):
    profile = get_student_profile(student)

    if profile is None:
        return "Профиль не заполнен"

    if profile.group is None:
        return "Группа не указана"

    return profile.group.name


def get_student_course(student):
    profile = get_student_profile(student)

    if profile is None:
        return "—"

    return f"{profile.course} курс"


def student_admin_link(student):
    url = reverse("admin:users_user_change", args=[student.pk])
    return format_html('<a href="{}">{}</a>', url, student.get_full_name())


def create_project_from_application(application):
    project = Project.objects.create(
        title=application.title,
        short_description=(application.relevance or "")[:150],
        relevance=application.relevance,
        problem=application.problem,
        goal=application.goal,
        tasks=application.tasks,
        expected_result=application.expected_result,
        spots_remaining=0,
        is_active=True,
    )

    project.specialties.set(application.specialties.all())

    if application.tasks and application.tasks.strip():
        ProjectListItem.objects.create(
            project=project,
            type="tasks",
            text=application.tasks,
        )

    return project


class ProjectListItemInline(TabularInline):
    model = ProjectListItem
    extra = 0
    fields = ("type", "text")
    ordering = ("type", "id")
    verbose_name = "Элемент проекта"
    verbose_name_plural = "Задачи и технологии"


class ProjectEnrollmentInline(TabularInline):
    model = ProjectEnrollment
    extra = 0
    can_delete = False
    show_change_link = False
    fields = (
        "student_link",
        "student_email",
        "student_group",
        "student_course",
        "created_at",
    )
    readonly_fields = fields
    ordering = ("-created_at",)
    verbose_name = "Записавшийся студент"
    verbose_name_plural = "Записанные студенты"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "student",
            "student__student_profile__group",
        )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    @admin.display(description="Студент")
    def student_link(self, obj):
        return student_admin_link(obj.student)

    @admin.display(description="Email")
    def student_email(self, obj):
        return obj.student.email

    @admin.display(description="Группа")
    def student_group(self, obj):
        return get_student_group(obj.student)

    @admin.display(description="Курс")
    def student_course(self, obj):
        return get_student_course(obj.student)


class FilterOptionInline(TabularInline):
    model = FilterOption
    extra = 0
    fields = ("name", "is_active")
    show_change_link = True
    verbose_name = "Опция"
    verbose_name_plural = "Опции категории"




@admin.register(FilterCategory)
class FilterCategoryAdmin(ModelAdmin):
    actions = None
    list_display = ("name", "options_count", "is_active")
    list_editable = ("is_active",)
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = (FilterOptionInline,)
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _options_count=Count("options", distinct=True)
        )

    @admin.display(description="Количество опций", ordering="_options_count")
    def options_count(self, obj):
        return obj._options_count




@admin.register(FilterOption)
class FilterOptionAdmin(ModelAdmin):
    actions = None
    list_display = ("name", "category", "is_active")
    list_editable = ("is_active",)
    list_filter = ("category", "is_active")
    search_fields = ("name", "category__name")
    autocomplete_fields = ("category",)
    list_select_related = ("category",)
    ordering = ("category__name", "name")
    list_per_page = 50



@admin.register(ProjectApplication)
class ProjectApplicationAdmin(ModelAdmin):
    actions = None
    list_display = (
        "id",
        "title",
        "applicant_name",
        "applicant_email",
        "applicant_group",
        "specialties_display",
        "status_badge",
        "created_at",
    )
    list_display_links = ("title",)
    list_filter = ("status", "created_at", "rejection_reason_choice")
    search_fields = (
        "title",
        "relevance",
        "problem",
        "applicant__email",
        "applicant__first_name",
        "applicant__last_name",
        "applicant__middle_name",
        "applicant__student_profile__group__name",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_per_page = 25
    save_on_top = True

    readonly_fields = (
        "applicant",
        "status",
        "rejection_reason_choice",
        "rejection_reason_text",
        "title",
        "relevance",
        "problem",
        "goal",
        "tasks",
        "expected_result",
        "specialties",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Заявитель и статус",
            {
                "fields": (
                    "applicant",
                    "status",
                    ("created_at", "updated_at"),
                )
            },
        ),
        (
            "Описание проекта",
            {
                "fields": (
                    "title",
                    "relevance",
                    "problem",
                    "goal",
                    "tasks",
                    "expected_result",
                )
            },
        ),
        ("Требуемые направления подготовки", {"fields": ("specialties",)}),
        (
            "Решение по заявке",
            {
                "fields": (
                    "rejection_reason_choice",
                    "rejection_reason_text",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("applicant", "applicant__student_profile__group")
            .prefetch_related("specialties")
        )

    @admin.display(description="Заявитель", ordering="applicant__last_name")
    def applicant_name(self, obj):
        return student_admin_link(obj.applicant)

    @admin.display(description="Группа")
    def applicant_group(self, obj):
        return get_student_group(obj.applicant)

    @admin.display(description="Email", ordering="applicant__email")
    def applicant_email(self, obj):
        return obj.applicant.email

    @admin.display(description="Направления")
    def specialties_display(self, obj):
        return ", ".join(
            f"{specialty.code} — {specialty.name}"
            for specialty in obj.specialties.all()
        ) or "Не указаны"

    @admin.display(description="Статус", ordering="status")
    def status_badge(self, obj):
        colors = {
            ProjectApplication.Status.PENDING: ("#D97706", "#FFFBEB"),
            ProjectApplication.Status.APPROVED: ("#059669", "#ECFDF5"),
            ProjectApplication.Status.REJECTED: ("#DC2626", "#FEF2F2"),
        }
        color, background = colors.get(obj.status, ("#6B7280", "#F3F4F6"))

        return format_html(
            '<span style="display:inline-block;padding:3px 9px;border-radius:999px;'
            'color:{};background:{};font-weight:600;white-space:nowrap">{}</span>',
            color,
            background,
            obj.get_status_display(),
        )




    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == ProjectApplication.Status.APPROVED:
            return False
        return super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        if queryset.filter(status=ProjectApplication.Status.APPROVED).exists():
            self.message_user(
                request,
                "Нельзя удалять одобренные заявки: созданный проект не связан с заявкой в базе данных.",
                level=messages.ERROR,
            )
            return

        super().delete_queryset(request, queryset)


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    actions = None
    list_display = (
        "id",
        "title",
        "partner",
        "curator",
        "display_specialties",
        "enrollment_count",
        "spots_remaining",
        "internship",
        "is_active",
        "updated_at",
    )
    list_display_links = ("title",)
    list_editable = ("internship", "is_active")
    list_filter = (
        "is_active",
        "internship",
        "theme",
        "campus",
        "difficulty",
        "partner",
        "curator",
        "specialties",
    )
    search_fields = (
        "title",
        "short_description",
        "relevance",
        "problem",
        "goal",
        "tasks",
        "expected_result",
        "partner__name",
        "curator__email",
        "curator__first_name",
        "curator__last_name",
    )
    autocomplete_fields = (
        "theme",
        "specialties",
        "campus",
        "courses",
        "difficulty",
        "partner",
        "curator",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_per_page = 25
    list_select_related = (
        "theme",
        "campus",
        "difficulty",
        "partner",
        "curator",
    )
    inlines = (ProjectListItemInline, ProjectEnrollmentInline)
    readonly_fields = (
        "created_at",
        "updated_at",
        "enrollment_summary",
    )
    save_on_top = True

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "title",
                    "short_description",
                    ("is_active", "internship"),
                )
            },
        ),
        (
            "Описание проекта",
            {
                "fields": (
                    "relevance",
                    "problem",
                    "goal",
                    "tasks",
                    "expected_result",
                )
            },
        ),
        (
            "Направления и параметры",
            {
                "fields": (
                    "theme",
                    "specialties",
                    "difficulty",
                    "courses",
                )
            },
        ),
        (
            "Место проведения",
            {"fields": ("campus", "location_address")},
        ),
        (
            "Партнёрство и сопровождение",
            {"fields": ("partner", "curator")},
        ),
        (
            "Запись студентов",
            {"fields": ("spots_remaining", "enrollment_summary")},
        ),
        (
            "Системная информация",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        enrollment_queryset = ProjectEnrollment.objects.select_related(
            "student",
            "student__student_profile__group",
        )

        return (
            super()
            .get_queryset(request)
            .select_related(
                "theme",
                "campus",
                "difficulty",
                "partner",
                "curator",
            )
            .prefetch_related(
                "specialties",
                "courses",
                "list_items",
                Prefetch("enrollments", queryset=enrollment_queryset),
            )
            .annotate(enrollment_total=Count("enrollments", distinct=True))
        )

    @admin.display(description="Направления")
    def display_specialties(self, obj):
        return ", ".join(
            specialty.code for specialty in obj.specialties.all()
        ) or "—"

    @admin.display(description="Записано студентов", ordering="enrollment_total")
    def enrollment_count(self, obj):
        return obj.enrollment_total

    @admin.display(description="Участники")
    def enrollment_summary(self, obj):
        count = obj.enrollment_total
        if count == 0:
            return "Пока никто не записался"
        return f"Записано студентов: {count}"




@admin.register(ProjectEnrollment)
class ProjectEnrollmentAdmin(ModelAdmin):
    actions = None
    list_display = (
        "student_link",
        "student_email",
        "student_group",
        "student_course",
        "project",
        "created_at",
    )
    list_filter = ("project", "created_at")
    search_fields = (
        "student__email",
        "student__first_name",
        "student__last_name",
        "student__middle_name",
        "student__student_profile__group__name",
        "project__title",
    )
    list_select_related = ("student", "project")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_per_page = 50
    fields = (
        "project",
        "student_link",
        "student_email",
        "student_group",
        "student_course",
        "created_at",
    )
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "project",
            "student",
            "student__student_profile__group",
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Студент", ordering="student__last_name")
    def student_link(self, obj):
        return student_admin_link(obj.student)

    @admin.display(description="Email", ordering="student__email")
    def student_email(self, obj):
        return obj.student.email

    @admin.display(description="Группа", ordering="student__student_profile__group__name")
    def student_group(self, obj):
        return get_student_group(obj.student)

    @admin.display(description="Курс", ordering="student__student_profile__course")
    def student_course(self, obj):
        return get_student_course(obj.student)
