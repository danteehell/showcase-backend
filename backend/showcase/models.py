from django.db import models
from django.core.exceptions import ValidationError
from backend import settings
from users.models import Specialty


class Partner(models.Model):
    name = models.CharField(max_length=200, verbose_name="Партнёр")
    short_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Сокращенное название")
    website = models.URLField(blank=True, null=True, verbose_name="Сайт")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Телефон")
    contact_person = models.CharField(max_length=255, blank=True, null=True, verbose_name="Контактное лицо")
    is_curator_contact = models.BooleanField(default=False, verbose_name="Куратор проекта является контактным лицом")
    additional_contact = models.CharField(max_length=255, blank=True, null=True, verbose_name="Доп. способ связи")
    internship = models.BooleanField(default=False, verbose_name="Стажировка")

    class Meta:
        verbose_name = "Партнёр"
        verbose_name_plural = "Партнёры"

    def __str__(self):
        return self.name


class FilterCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")

    class Meta:
        verbose_name = "Категория фильтра"
        verbose_name_plural = "Категории фильтров"

    def __str__(self):
        return self.name


class FilterOption(models.Model):
    category = models.ForeignKey(
        FilterCategory,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name="Категория",
    )
    name = models.CharField(max_length=200, verbose_name="Опция фильтра")

    class Meta:
        verbose_name = "Опция фильтра"
        verbose_name_plural = "Опции фильтров"

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class ProjectApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На рассмотрении"
        APPROVED = "approved", "Одобрена"
        REJECTED = "rejected", "Отклонена"

    class RejectionReason(models.TextChoices):
        INCOMPLETE = "incomplete", "Неполные или некорректные данные"
        DUPLICATE = "duplicate", "Дублирующая заявка"
        NO_BUDGET = "no_budget", "Нет свободных мест / бюджета"
        OUT_OF_SCOPE = "out_of_scope", "Не соответствует выбранной тематике"
        OTHER = "other", "Другая причина"

    applicant = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="project_applications",
        verbose_name="Заявитель"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус заявки"
    )
    rejection_reason_choice = models.CharField(
        max_length=50,
        choices=RejectionReason.choices,
        blank=True,
        null=True,
        verbose_name="Категория отклонения"
    )
    rejection_reason_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="Комментарий к отклонению",
        help_text="Обязательно к заполнению, если выбрана 'Другая причина'"
    )

    title = models.CharField(max_length=300, verbose_name="Название проекта")
    theme = models.ForeignKey(
        FilterOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="applications_as_theme", limit_choices_to={"category__name": "Тематика"},
        verbose_name="Тематика"
    )
    specialties = models.ManyToManyField(
        Specialty, blank=True, related_name="project_applications", verbose_name="Направления подготовки"
    )
    campus = models.ForeignKey(
        FilterOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="applications_as_campus", limit_choices_to={"category__name": "Корпус"},
        verbose_name="Корпус"
    )
    location_address = models.CharField(
        max_length=300, blank=True, null=True, 
        verbose_name="Адрес (если на базе партнёра)"
    )
    courses = models.ManyToManyField(
        FilterOption, blank=True, related_name="applications_as_course",
        limit_choices_to={"category__name": "Курс"}, verbose_name="Курсы студентов"
    )
    difficulty = models.ForeignKey(
        FilterOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="applications_as_difficulty", limit_choices_to={"category__name": "Сложность"},
        verbose_name="Сложность"
    )
    partner = models.ForeignKey(
        "Partner", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Партнёр"
    )
    curator = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="curated_applications", limit_choices_to={"role": "curator"},
        verbose_name="Куратор"
    )
    internship = models.BooleanField(default=False, verbose_name="Стажировка")
    total_spots = models.PositiveIntegerField(default=10, verbose_name="Всего мест")
    
    short_description = models.TextField(blank=True, verbose_name="Короткое описание")
    long_description = models.TextField(blank=True, verbose_name="Расширенное описание")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата подачи")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Заявка на проект"
        verbose_name_plural = "Заявки на проекты"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заявка: {self.title} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        if self.status == self.Status.REJECTED:
            if not self.rejection_reason_choice:
                raise ValidationError({"rejection_reason_choice": "Необходимо выбрать категорию отклонения."})
            if self.rejection_reason_choice == self.RejectionReason.OTHER and not self.rejection_reason_text:
                raise ValidationError({"rejection_reason_text": "Так как выбрана 'Другая причина', необходимо написать комментарий."})


class Project(models.Model):
    title = models.CharField(max_length=300, verbose_name="Название проекта")
    theme = models.ForeignKey(
        FilterOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="projects_as_theme", limit_choices_to={"category__name": "Тематика"},
        verbose_name="Тематика",
    )
    specialties = models.ManyToManyField(
        Specialty, blank=True, related_name="projects", verbose_name="Направления подготовки",
    )
    campus = models.ForeignKey(
        FilterOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="projects_as_campus", limit_choices_to={"category__name": "Корпус"},
        verbose_name="Корпус",
    )
    location_address = models.CharField(
        max_length=300, blank=True, null=True, verbose_name="Адрес (если на базе партнёра)"
    )
    courses = models.ManyToManyField(
        FilterOption, blank=True, related_name="projects_as_course",
        limit_choices_to={"category__name": "Курс"}, verbose_name="Курсы студентов",
    )
    difficulty = models.ForeignKey(
        FilterOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="projects_as_difficulty", limit_choices_to={"category__name": "Сложность"},
        verbose_name="Сложность",
    )
    partner = models.ForeignKey(
        "Partner", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Партнёр",
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={"role": "curator"}, related_name="curated_projects",
        verbose_name="Куратор",
    )
    internship = models.BooleanField(default=False, verbose_name="Стажировка")
    spots_remaining = models.PositiveIntegerField(default=0, verbose_name="Оставшиеся места")
    short_description = models.TextField(blank=True, verbose_name="Короткое описание", null=True)
    long_description = models.TextField(blank=True, verbose_name="Расширенное описание", null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(default=True, verbose_name="Доступен")

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"

    def __str__(self):
        return self.title

    @classmethod
    def get_total_count(cls):
        return cls.objects.count()

    @classmethod
    def get_active_count(cls):
        return cls.objects.filter(is_active=True).count()

    @classmethod
    def get_available_count(cls):
        return cls.objects.filter(is_active=True, spots_remaining__gt=0).count()

class BaseListItem(models.Model):
    TYPES = [
        ("tasks", "Основные задачи"),
        ("technologies", "Технологии"),
    ]
    type = models.CharField(max_length=50, choices=TYPES, verbose_name="Тип элемента")
    text = models.TextField(verbose_name="Текст")
    class Meta:
        abstract = True  

class ProjectListItem(BaseListItem):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="list_items", verbose_name="Проект"
    )

    def __str__(self):
        return f"{self.project.title} - {self.get_type_display()}"


class ProjectApplicationListItem(BaseListItem):
    application = models.ForeignKey(
        ProjectApplication, on_delete=models.CASCADE, related_name="list_items", verbose_name="Заявка"
    )


class ProjectEnrollment(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="enrollments", verbose_name="Проект"
    )
    student = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="project_enrollments", verbose_name="Студент"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата записи")

    class Meta:
        verbose_name = "Запись на проект"
        verbose_name_plural = "Записи на проекты"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "project"], name="unique_student_project_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.student} -> {self.project}"