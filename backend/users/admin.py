from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin, StackedInline

from .models import *


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "role")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("email", "role")


class StudentProfileInline(StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = "Учебная информация (Студент)"
    extra = 0
    fk_name = "user"


class CuratorProfileInline(StackedInline):
    model = CuratorProfile
    can_delete = False
    verbose_name_plural = "Рабочая информация (Куратор)"
    extra = 0
    fk_name = "user"


@admin.register(Specialty)
class SpecialtyAdmin(ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ("email", "display_full_name", "role", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name", "middle_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональная информация",
            {"fields": ("last_name", "first_name", "middle_name")},
        ),
        (
            "Права в системе",
            {"fields": ("role", "is_active", "is_staff", "is_superuser")},
        ),
    )

    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password", "role")}),
    )

    @admin.display(description="ФИО")
    def display_full_name(self, obj):
        return obj.get_full_name()

    def get_inlines(self, request, obj):
        return [StudentProfileInline, CuratorProfileInline]


@admin.register(StudentProxy)
class StudentAdmin(CustomUserAdmin):
    list_display = (
        "email",
        "display_full_name",
        "display_course",
        "display_specialty",
        "is_active",
    )
    list_filter = ("student_profile__course", "student_profile__specialty", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="student")

    def get_inlines(self, request, obj):
        return [StudentProfileInline]

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {"fields": ("email", "password")}),
            (
                "Персональная информация",
                {"fields": ("last_name", "first_name", "middle_name")},
            ),
            ("Права в системе", {"fields": ("role", "is_active")}),
        )

    @admin.display(description="Курс")
    def display_course(self, obj):
        if hasattr(obj, "student_profile"):
            return f"{obj.student_profile.course} курс"
        return "-"

    @admin.display(description="Специальность")
    def display_specialty(self, obj):
        if hasattr(obj, "student_profile") and obj.student_profile.specialty:
            return obj.student_profile.specialty.name
        return "-"


@admin.register(CuratorProxy)
class CuratorAdmin(CustomUserAdmin):
    list_display = ("email", "display_full_name", "display_department", "is_active")
    list_filter = ("curator_profile__department", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="curator")

    def get_inlines(self, request, obj):
        return [CuratorProfileInline]

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {"fields": ("email", "password")}),
            (
                "Персональная информация",
                {"fields": ("last_name", "first_name", "middle_name")},
            ),
            ("Права в системе", {"fields": ("role", "is_active")}),
        )

    @admin.display(description="Кафедра")
    def display_department(self, obj):
        if hasattr(obj, "curator_profile") and obj.curator_profile.department:
            return obj.curator_profile.department.name
        return "-"


@admin.register(AdminProxy)
class AdminRoleAdmin(CustomUserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role="admin")
