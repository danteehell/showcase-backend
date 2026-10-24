from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import *

admin.site.site_header = "Управление проектами"

class ProjectListItemInline(TabularInline):
    model = ProjectListItem
    extra = 1
    autocomplete_fields = ("project",)
    fields = ("type", "position", "text")
    ordering = ("position",)

class FilterOptionInline(TabularInline):
    model = FilterOption
    extra = 1
    fields = ("name",)
    show_change_link = True


class PartnerAdmin(ModelAdmin):
    list_display = ("name", "website", "email", "phone", "internship", "projects_count")
    search_fields = ("name", "email", "phone")
    list_filter = ("internship",)
    ordering = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "website")}),
        ("Контакты", {"fields": ("email", "phone"), "classes": ("collapse",)}),
        ("Дополнительно", {"fields": ("internship",), "classes": ("collapse",)}),
    )
    def projects_count(self, obj):
        return Project.objects.filter(partner=obj).count()
    projects_count.short_description = "Проектов"

class CuratorAdmin(ModelAdmin):
    list_display = ("first_name", "last_name", "email", "projects_count")
    search_fields = ("first_name", "last_name", "email")
    ordering = ("last_name", "first_name")
    def projects_count(self, obj):
        return Project.objects.filter(curator=obj).count()
    projects_count.short_description = "Проектов"

class FilterCategoryAdmin(ModelAdmin):
    list_display = ("name", "category_type", "options_count")
    search_fields = ("name",)
    list_filter = ("category_type",)
    ordering = ("name",)
    inlines = [FilterOptionInline]
    def options_count(self, obj):
        return obj.options.count()
    options_count.short_description = "Опций"

class FilterOptionAdmin(ModelAdmin):
    list_display = ("name", "category", "projects_count")
    search_fields = ("name", "category__name")
    list_filter = ("category",)
    autocomplete_fields = ("category",)
    ordering = ("category__name", "name")
    raw_id_fields = ("category",)
    def projects_count(self, obj):
        return (
            obj.projects_as_theme.count() +
            obj.projects_as_specialty.count() +
            obj.projects_as_course.count() +
            obj.projects_as_difficulty.count()
        )
    projects_count.short_description = "Проектов"

class ScheduleItemAdmin(ModelAdmin):
    list_display = ("day_of_week", "start_time", "end_time", "note")
    list_filter = ("day_of_week",)
    search_fields = ("note",)
    ordering = ("day_of_week", "start_time")
    raw_id_fields = ()

class CourseYearAdmin(ModelAdmin):
    list_display = ("year",)
    search_fields = ("year",)
    ordering = ("year",)

class ProjectAdmin(ModelAdmin):
    list_display = (
        "id",
        "title",
        "partner",
        "curator",
        "difficulty",
        "spots_remaining",
        "internship",
        "is_active",
    )
    list_filter = (
        "is_active",
        "internship",
        "difficulty",
        "campus",
        "partner",
        "curator",
    )
    search_fields = (
        "title",
        "short_description",
        "long_description",
    )
    raw_id_fields = ("theme", "campus", "difficulty", "partner", "curator")
    autocomplete_fields = ("specialties", "courses")
    list_editable = (
        "spots_remaining",
        "internship",
        "is_active",
    )
    ordering = ("-created_at",)
    inlines = [ProjectListItemInline]
    fieldsets = (
        ("Основная информация", {
            "fields": (
                "title",
                "short_description",
                "long_description",
            )
        }),
        ("Фильтры", {
            "fields": (
                "theme",
                "specialties",
                "campus",
                "courses",
                "difficulty",
            )
        }),
        ("Партнёры и кураторы", {
            "fields": (
                "partner",
                "curator",
                "internship",
            )
        }),
        ("Доступность", {
            "fields": (
                "spots_remaining",
                "is_active",
            )
        }),
    )

admin.site.register(Partner, PartnerAdmin)
admin.site.register(Curator, CuratorAdmin)
admin.site.register(FilterCategory, FilterCategoryAdmin)
admin.site.register(FilterOption, FilterOptionAdmin)
admin.site.register(ScheduleItem, ScheduleItemAdmin)
admin.site.register(CourseYear, CourseYearAdmin)
admin.site.register(Project, ProjectAdmin)