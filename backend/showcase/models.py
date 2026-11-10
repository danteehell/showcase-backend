from django.db import models

from backend import settings
from users.models import Specialty


class Partner(models.Model):
    name = models.CharField(max_length=200, verbose_name="Партнёр")
    website = models.URLField(blank=True, null=True, verbose_name="Сайт")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Телефон"
    )
    internship = models.BooleanField(null=True, blank=True, verbose_name="Стажировка")

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


class ScheduleItem(models.Model):
    DAYS = [
        (0, "Понедельник"),
        (1, "Вторник"),
        (2, "Среда"),
        (3, "Четверг"),
        (4, "Пятница"),
        (5, "Суббота"),
        (6, "Воскресенье"),
    ]
    day_of_week = models.IntegerField(choices=DAYS, verbose_name="День недели")
    start_time = models.TimeField(verbose_name="Время начала")
    end_time = models.TimeField(blank=True, null=True, verbose_name="Время окончания")
    note = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Примечание"
    )

    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписания"

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M') if self.end_time else ''}"


class Project(models.Model):
    title = models.CharField(max_length=300, verbose_name="Название проекта")

    theme = models.ForeignKey(
        FilterOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_as_theme",
        limit_choices_to={"category__name": "Тематика"},
        verbose_name="Тематика",
    )
    specialties = models.ManyToManyField(
        Specialty,
        blank=True,
        related_name="projects",
        verbose_name="Направления подготовки",
    )
    campus = models.ForeignKey(
        FilterOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_as_campus",
        limit_choices_to={"category__name": "Корпус"},
        verbose_name="Корпус",
    )
    courses = models.ManyToManyField(
        FilterOption,
        blank=True,
        related_name="projects_as_course",
        limit_choices_to={"category__name": "Курс"},
        verbose_name="Курсы студентов",
    )
    difficulty = models.ForeignKey(
        FilterOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_as_difficulty",
        limit_choices_to={"category__name": "Сложность"},
        verbose_name="Сложность",
    )

    shedule = models.ForeignKey(
        ScheduleItem,
        on_delete=models.SET_NULL,
        verbose_name="Занятия",
        null=True,
        blank=True,
    )
    partner = models.ForeignKey(
        "Partner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Партнёр",
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "curator"},
        related_name="curated_projects",
        verbose_name="Куратор",
    )
    internship = models.BooleanField(
        default=False, verbose_name="Стажировка", null=True, blank=True
    )
    spots_remaining = models.IntegerField(
        default=0, verbose_name="Оставшиеся места", null=True, blank=True
    )
    short_description = models.TextField(
        blank=True, verbose_name="Короткое описание", null=True
    )
    long_description = models.TextField(
        blank=True, verbose_name="Расширенное описание", null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(
        default=True, verbose_name="Доступен", null=True, blank=True
    )

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


class ProjectListItem(models.Model):
    TYPES = [
        ("tasks", "Основные задачи"),
        ("technologies", "Технологии"), 
    ]
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="list_items",
        verbose_name="Проект",
    )
    type = models.CharField(max_length=50, choices=TYPES, verbose_name="Тип элемента")
    text = models.TextField(verbose_name="Текст")

    class Meta:
        verbose_name = "Дополнительная информация о проекте"
        verbose_name_plural = "Дополнительная информация о проектах"

    def __str__(self):
        return f"{self.project.title} - {self.get_type_display()}"


class ProjectEnrollment(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="enrollments"
    )
    student = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="project_enrollments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на проект"
        verbose_name_plural = "Заявки на проекты"
        constraints = [
            models.UniqueConstraint(
                fields=["student"],
                name="unique_project_enrollment_per_student",
            )
        ]

    def __str__(self):
        return f"{self.student} -> {self.project}"
