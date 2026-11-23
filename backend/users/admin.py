from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin, StackedInline

from .models import (
    AdminProxy,
    CuratorProfile,
    CuratorProxy,
    DeanProxy,
    Department,
    DirectionHeadProxy,
    Faculty,
    Group,
    Partner,
    PartnerProxy,
    PartnerRepresentative,
    Specialty,
    StudentProfile,
    StudentProxy,
    User,
)


class NoActionsAdminMixin:
    actions = None


class StudentProfileInline(StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = "Учебная информация"
    extra = 1
    max_num = 1
    fk_name = "user"
    fields = ("group", "course", "specialty")


class CuratorProfileInline(StackedInline):
    model = CuratorProfile
    can_delete = False
    verbose_name_plural = "Рабочая информация"
    extra = 1
    max_num = 1
    fk_name = "user"
    fields = ("department",)


class PartnerRepresentativeInline(StackedInline):
    model = PartnerRepresentative
    verbose_name_plural = "Представляемые партнёры"
    extra = 1
    fk_name = "user"
    autocomplete_fields = ("partner",)
    fields = ("partner",)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "role")


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(Specialty)
class SpecialtyAdmin(NoActionsAdminMixin, ModelAdmin):
    list_display = ("code", "name", "faculty", "head")
    list_filter = ("faculty", "head")
    search_fields = (
        "code",
        "name",
        "faculty__name",
        "head__email",
        "head__last_name",
    )
    list_select_related = ("faculty", "head")
    ordering = ("code",)


@admin.register(Faculty)
class FacultyAdmin(NoActionsAdminMixin, ModelAdmin):
    list_display = ("name", "dean")
    search_fields = (
        "name",
        "dean__email",
        "dean__first_name",
        "dean__last_name",
    )
    list_select_related = ("dean",)
    ordering = ("name",)


@admin.register(Department)
class DepartmentAdmin(NoActionsAdminMixin, ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Group)
class GroupAdmin(NoActionsAdminMixin, ModelAdmin):
    list_display = ("name", "specialty", "year")
    list_filter = ("year", "specialty__faculty")
    search_fields = (
        "name",
        "specialty__code",
        "specialty__name",
    )
    list_select_related = ("specialty", "specialty__faculty")
    ordering = ("name",)


@admin.register(Partner)
class PartnerModelAdmin(NoActionsAdminMixin, ModelAdmin):
    list_display = (
        "name",
        "short_name",
        "email",
        "phone",
        "internship",
        "is_curator_contact",
    )
    list_display_links = ("name",)
    list_editable = ("internship", "is_curator_contact")
    list_filter = ("internship", "is_curator_contact")
    search_fields = (
        "name",
        "short_name",
        "email",
        "contact_person",
    )
    ordering = ("name",)


@admin.register(PartnerRepresentative)
class PartnerRepresentativeAdmin(NoActionsAdminMixin, ModelAdmin):
    list_display = ("user", "partner")
    list_filter = ("partner",)
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "partner__name",
    )
    list_select_related = ("user", "partner")


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = (
        "email",
        "display_full_name",
        "role",
        "enrolled_project",
        "is_active",
    )
    list_display_links = ("email",)
    list_editable = ("is_active",)
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = (
        "email",
        "first_name",
        "last_name",
        "middle_name",
    )
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональная информация",
            {"fields": ("last_name", "first_name", "middle_name")},
        ),
        (
            "Роль и статус",
            {"fields": ("role", "is_active")},
        ),
        (
            "Права Django",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Даты",
            {"fields": ("last_login", "date_joined")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "role", "password1", "password2"),
            },
        ),
    )

    readonly_fields = ("last_login", "date_joined")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "project_enrollments__project",
        )

    def get_inlines(self, request, obj):
        if obj is None:
            return []

        if obj.role == User.Roles.STUDENT:
            return [StudentProfileInline]

        if obj.role == User.Roles.CURATOR:
            return [CuratorProfileInline]

        if obj.role == User.Roles.PARTNER:
            return [PartnerRepresentativeInline]

        return []

    @admin.display(description="ФИО")
    def display_full_name(self, obj):
        return obj.get_full_name()

    @admin.display(description="Проект")
    def enrolled_project(self, obj):
        if obj.role != User.Roles.STUDENT:
            return "-"

        enrollment = next(iter(obj.project_enrollments.all()), None)

        if enrollment:
            return enrollment.project.title

        return "Не записан"


class RoleProxyAdmin(CustomUserAdmin):
    role_value = None
    role_inlines = ()

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональная информация",
            {"fields": ("last_name", "first_name", "middle_name")},
        ),
        ("Статус", {"fields": ("is_active",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            role=self.role_value,
        )

    def get_inlines(self, request, obj):
        return self.role_inlines

    def save_model(self, request, obj, form, change):
        obj.role = self.role_value
        super().save_model(request, obj, form, change)


@admin.register(StudentProxy)
class StudentAdmin(RoleProxyAdmin):
    role_value = User.Roles.STUDENT
    role_inlines = (StudentProfileInline,)

    list_display = (
        "email",
        "display_full_name",
        "enrolled_project",
        "display_course",
        "display_specialty",
        "is_active",
    )
    list_display_links = ("email",)
    list_editable = ("is_active",)
    list_filter = (
        "student_profile__course",
        "student_profile__specialty",
        "is_active",
    )
    readonly_fields = ("enrolled_project",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональная информация",
            {"fields": ("last_name", "first_name", "middle_name")},
        ),
        ("Проект", {"fields": ("enrolled_project",)}),
        ("Статус", {"fields": ("is_active",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "student_profile__group",
            "student_profile__specialty",
        )

    @admin.display(description="Курс")
    def display_course(self, obj):
        profile = getattr(obj, "student_profile", None)

        if profile:
            return f"{profile.course} курс"

        return "-"

    @admin.display(description="Специальность")
    def display_specialty(self, obj):
        profile = getattr(obj, "student_profile", None)

        if profile and profile.specialty:
            return profile.specialty.name

        return "-"


@admin.register(CuratorProxy)
class CuratorAdmin(RoleProxyAdmin):
    role_value = User.Roles.CURATOR
    role_inlines = (CuratorProfileInline,)

    list_display = (
        "email",
        "display_full_name",
        "display_department",
        "is_active",
    )
    list_display_links = ("email",)
    list_editable = ("is_active",)
    list_filter = ("curator_profile__department", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "curator_profile__department",
        )

    @admin.display(description="Кафедра")
    def display_department(self, obj):
        profile = getattr(obj, "curator_profile", None)

        if profile and profile.department:
            return profile.department.name

        return "-"


@admin.register(AdminProxy)
class AdminRoleAdmin(RoleProxyAdmin):
    role_value = User.Roles.ADMIN

    list_display = (
        "email",
        "display_full_name",
        "is_active",
    )
    list_display_links = ("email",)
    list_editable = ("is_active",)
    list_filter = ("is_active",)


@admin.register(DirectionHeadProxy)
class DirectionHeadAdmin(RoleProxyAdmin):
    role_value = User.Roles.DIRECTION_HEAD

    list_display = (
        "email",
        "display_full_name",
        "display_specialties",
        "is_active",
    )
    list_display_links = ("email",)
    list_editable = ("is_active",)
    list_filter = ("is_active",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "headed_specialties",
        )

    @admin.display(description="Направления")
    def display_specialties(self, obj):
        specialties = obj.headed_specialties.all()

        return ", ".join(
            specialty.code for specialty in specialties
        ) or "-"


@admin.register(DeanProxy)
class DeanAdmin(RoleProxyAdmin):
    role_value = User.Roles.DEAN

    list_display = (
        "email",
        "display_full_name",
        "display_faculties",
        "is_active",
    )
    list_display_links = ("email",)
    list_editable = ("is_active",)
    list_filter = ("is_active",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "dean_of_faculties",
        )

    @admin.display(description="Факультеты")
    def display_faculties(self, obj):
        faculties = obj.dean_of_faculties.all()

        return ", ".join(
            faculty.name for faculty in faculties
        ) or "-"


@admin.register(PartnerProxy)
class PartnerUserAdmin(RoleProxyAdmin):
    role_value = User.Roles.PARTNER
    role_inlines = (PartnerRepresentativeInline,)

    list_display = (
        "email",
        "display_full_name",
        "display_partners",
        "is_active",
    )
    list_display_links = ("email",)
    list_editable = ("is_active",)
    list_filter = ("is_active",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "partner_roles__partner",
        )

    @admin.display(description="Партнёры")
    def display_partners(self, obj):
        representatives = obj.partner_roles.all()

        return ", ".join(
            representative.partner.name
            for representative in representatives
        ) or "-"
