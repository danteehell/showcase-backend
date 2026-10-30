from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import *

admin.site.site_header = "Управление проектами"

class ProjectListItemInline(TabularInline):
    model = ProjectListItem
    extra = 1
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
    
    @admin.display(description="Проектов")
    def projects_count(self, obj):
        return Project.objects.filter(partner=obj).count()




class FilterCategoryAdmin(ModelAdmin):
    list_display = ("name", "options_count")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [FilterOptionInline]
    
    @admin.display(description="Опций")
    def options_count(self, obj):
        return obj.options.count()


class FilterOptionAdmin(ModelAdmin):
    list_display = ("name", "category", "projects_count")
    search_fields = ("name", "category__name")
    list_filter = ("category",)
    autocomplete_fields = ("category",)
    ordering = ("category__name", "name")
    
    @admin.display(description="Проектов")
    def projects_count(self, obj):
        return (
            obj.projects_as_theme.count() +
            obj.projects_as_specialty.count() +
            obj.projects_as_campus.count() +
            obj.projects_as_course.count() +
            obj.projects_as_difficulty.count()
        )


class ScheduleItemAdmin(ModelAdmin):
    list_display = ("day_of_week", "start_time", "end_time", "note")
    list_filter = ("day_of_week",)
    search_fields = ("note",)
    ordering = ("day_of_week", "start_time")


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
    autocomplete_fields = ("theme", "campus", "difficulty", "partner", "specialties", "courses", "curator")
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
admin.site.register(FilterCategory, FilterCategoryAdmin)
admin.site.register(FilterOption, FilterOptionAdmin)
admin.site.register(ScheduleItem, ScheduleItemAdmin)
admin.site.register(Project, ProjectAdmin)