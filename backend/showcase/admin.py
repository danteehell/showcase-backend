from django.contrib import admin, messages
from django.db import transaction
from django.urls import reverse, path
from django.shortcuts import redirect
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin, TabularInline

from .models import *

admin.site.site_header = "Управление проектами"


class ProjectListItemInline(TabularInline):
    model = ProjectListItem
    extra = 1
    fields = ("type", "text")


class ProjectApplicationListItemInline(TabularInline):
    model = ProjectApplicationListItem
    extra = 1
    fields = ("type", "text")


class FilterOptionInline(TabularInline):
    model = FilterOption
    extra = 1
    fields = ("name",)
    show_change_link = True


@admin.register(Partner)
class PartnerAdmin(ModelAdmin):
    list_display = ("name", "short_name", "contact_person", "phone", "is_curator_contact", "internship")
    search_fields = ("name", "short_name", "email", "phone", "contact_person")
    list_filter = ("internship", "is_curator_contact")
    ordering = ("name",)
    fieldsets = (
        ("Основная информация", {"fields": ("name", "short_name", "website")}),
        ("Контакты", {
            "fields": ("email", "phone", "contact_person", "is_curator_contact", "additional_contact"),
            "classes": ("collapse",),
        }),
        ("Дополнительно", {"fields": ("internship",), "classes": ("collapse",)}),
    )


@admin.register(FilterCategory)
class FilterCategoryAdmin(ModelAdmin):
    list_display = ("name", "options_count")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [FilterOptionInline]

    @admin.display(description="Опций")
    def options_count(self, obj):
        return obj.options.count()


@admin.register(FilterOption)
class FilterOptionAdmin(ModelAdmin):
    list_display = ("name", "category")
    search_fields = ("name", "category__name")
    list_filter = ("category",)
    autocomplete_fields = ("category",)
    ordering = ("category__name", "name")


@admin.register(ProjectApplication)
class ProjectApplicationAdmin(ModelAdmin):
    list_display = ("id", "title", "applicant", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "short_description", "applicant__email")
    
    readonly_fields = ("created_at", "updated_at", "approve_button", "reject_button", "revert_button")
    inlines = [ProjectApplicationListItemInline]
    
    autocomplete_fields = (
        "applicant", "theme", "campus", "difficulty", 
        "partner", "curator", "specialties", "courses"
    )
    
    fieldsets = (
        ("Статус", {"fields": ("status", "applicant", "approve_button", "reject_button", "revert_button")}),
        ("Причина отклонения", {
            "fields": ("rejection_reason_choice", "rejection_reason_text"),
            "classes": ("collapse",), 
        }),
        ("Основная информация", {"fields": ("title", "short_description", "long_description")}),
        ("Локация и фильтры", {"fields": ("theme", "specialties", "campus", "location_address", "courses", "difficulty")}),
        ("Партнёр и куратор", {"fields": ("partner", "curator")}),
        ("Детали", {"fields": ("internship", "total_spots")}),
        ("Системное", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["approve_applications", "reject_applications"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/approve/',
                self.admin_site.admin_view(self.process_approve),
                name='showcase_projectapplication_approve',
            ),
            path(
                '<path:object_id>/reject/',
                self.admin_site.admin_view(self.process_reject),
                name='showcase_projectapplication_reject',
            ),
            path(
                '<path:object_id>/revert/',
                self.admin_site.admin_view(self.process_revert),
                name='showcase_projectapplication_revert',
            ),
        ]
        return custom_urls + urls

    @admin.display(description="Действие")
    def approve_button(self, obj):
        if obj.status == ProjectApplication.Status.PENDING:
            url = reverse('admin:showcase_projectapplication_approve', args=[obj.pk])
            return format_html(
                '<a style="background-color: #10B981; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; text-decoration: none;" href="{}">Одобрить и создать проект</a>',
                url
            )
        return ""

    @admin.display(description="")
    def reject_button(self, obj):
        if obj.status == ProjectApplication.Status.PENDING:
            url = reverse('admin:showcase_projectapplication_reject', args=[obj.pk])
            return format_html(
                '<a style="background-color: #EF4444; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; text-decoration: none;" href="{}">Отклонить заявку</a>',
                url
            )
        return ""

    @admin.display(description="")
    def revert_button(self, obj):
        if obj.status in [ProjectApplication.Status.APPROVED, ProjectApplication.Status.REJECTED]:
            url = reverse('admin:showcase_projectapplication_revert', args=[obj.pk])
            return format_html(
                '<a style="background-color: #F59E0B; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; text-decoration: none;" href="{}">Отменить решение (Вернуть на рассмотрение)</a>',
                url
            )
        return ""

    def process_approve(self, request, object_id):
        application = self.get_object(request, object_id)
        if not application:
            return redirect('admin:showcase_projectapplication_changelist')

        if application.status != ProjectApplication.Status.PENDING:
            self.message_user(request, "Можно одобрять только заявки на рассмотрении.", level=messages.ERROR)
            return redirect(reverse('admin:showcase_projectapplication_change', args=[object_id]))

        try:
            with transaction.atomic():
                project = Project.objects.create(
                    title=application.title,
                    theme=application.theme,
                    campus=application.campus,
                    location_address=application.location_address,
                    difficulty=application.difficulty,
                    partner=application.partner,
                    curator=application.curator,
                    internship=application.internship,
                    spots_remaining=application.total_spots,
                    short_description=application.short_description,
                    long_description=application.long_description,
                    is_active=True
                )
                
                project.specialties.set(application.specialties.all())
                project.courses.set(application.courses.all())

                for item in application.list_items.all():
                    ProjectListItem.objects.create(
                        project=project,
                        type=item.type,
                        text=item.text
                    )

                application.status = ProjectApplication.Status.APPROVED
                application.save()
                
            self.message_user(request, "Заявка одобрена, проект успешно создан!", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Ошибка при создании проекта: {e}", level=messages.ERROR)

        return redirect(reverse('admin:showcase_projectapplication_change', args=[object_id]))

    def process_reject(self, request, object_id):
        application = self.get_object(request, object_id)
        if not application:
            return redirect('admin:showcase_projectapplication_changelist')

        if application.status != ProjectApplication.Status.PENDING:
            self.message_user(request, "Можно отклонять только заявки на рассмотрении.", level=messages.ERROR)
            return redirect(reverse('admin:showcase_projectapplication_change', args=[object_id]))

        application.status = ProjectApplication.Status.REJECTED
        application.rejection_reason_choice = ProjectApplication.RejectionReason.OTHER
        application.rejection_reason_text = "Отклонено через кнопку быстрого действия."
        
        try:
            application.full_clean()
            application.save()
            self.message_user(request, "Заявка отклонена.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Ошибка: {e}", level=messages.ERROR)

        return redirect(reverse('admin:showcase_projectapplication_change', args=[object_id]))

    def process_revert(self, request, object_id):
        application = self.get_object(request, object_id)
        if not application:
            return redirect('admin:showcase_projectapplication_changelist')

        if application.status == ProjectApplication.Status.PENDING:
            self.message_user(request, "Заявка уже находится на рассмотрении.", level=messages.INFO)
            return redirect(reverse('admin:showcase_projectapplication_change', args=[object_id]))

        try:
            with transaction.atomic():
                if application.status == ProjectApplication.Status.APPROVED:
                    project = Project.objects.filter(
                        title=application.title, 
                        curator=application.curator
                    ).order_by('-created_at').first()
                    
                    if project:
                        project.delete()
                
                application.status = ProjectApplication.Status.PENDING
                application.rejection_reason_choice = None
                application.rejection_reason_text = None
                application.save()
                
            self.message_user(request, "Решение отменено. Заявка возвращена в статус 'На рассмотрении'.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Ошибка при отмене: {e}", level=messages.ERROR)

        return redirect(reverse('admin:showcase_projectapplication_change', args=[object_id]))

@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = (
        "id", "title", "partner", "curator", "display_specialties", "difficulty", "spots_remaining", "internship", "is_active",
    )
    list_filter = (
        "is_active", "internship", "difficulty", "campus", "partner", "curator", "specialties", 
    )
    search_fields = (
        "title", "short_description", "long_description",
    )
    autocomplete_fields = (
        "theme", "campus", "difficulty", "partner", "specialties", "courses", "curator",
    )
    list_editable = (
        "spots_remaining", "internship", "is_active",
    )
    ordering = ("-created_at",)
    inlines = [ProjectListItemInline]
    readonly_fields = ("enrolled_students_list",)

    fieldsets = (
        ("Основная информация", {
            "fields": ("title", "short_description", "long_description")
        }),
        ("Локация и фильтры", {
            "fields": ("theme", "specialties", "campus", "location_address", "courses", "difficulty")
        }),
        ("Партнёры и кураторы", {
            "fields": ("partner", "curator", "internship")
        }),
        ("Доступность", {
            "fields": ("spots_remaining", "is_active")
        }),
        ("Участники проекта", {
            "fields": ("enrolled_students_list",), "classes": ("collapse",)
        }),
    )

    @admin.display(description="Специальности")
    def display_specialties(self, obj):
        return ", ".join([s.code for s in obj.specialties.all()])

    @admin.display(description="Список записавшихся")
    def enrolled_students_list(self, obj):
        enrollments = obj.enrollments.select_related("student").all()
        if not enrollments:
            return "Пока никто не записался"

        items = []
        for enrollment in enrollments:
            student = enrollment.student
            url = reverse("admin:users_user_change", args=[student.id])
            name = student.get_full_name() or student.email
            items.append(
                format_html(
                    '<li style="margin-bottom: 5px;"><a href="{}" style="color: #677BFD; font-weight: bold;">{}</a> ({})</li>',
                    url, name, student.email
                )
            )
        return format_html('<ul style="margin: 0; padding-left: 20px;">{}</ul>', format_html_join('', '{}', ((item,) for item in items)))