from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from backend import settings


class TaskCategory(models.Model):
    name = models.CharField(
        max_length=255, unique=True, verbose_name="Название категории"
    )
    slug = models.SlugField(unique=True, verbose_name="Slug", blank=True)

    class Meta:
        verbose_name = "Категория задачи"
        verbose_name_plural = "Категории задач"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while TaskCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Task(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Лёгкая"
        MEDIUM = "medium", "Средняя"
        HARD = "hard", "Сложная"

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликована (доступна)"
        TAKEN = "taken", "Все места заняты"
        IN_PROGRESS = "in_progress", "В работе"
        COMPLETED = "completed", "Завершена"
        WITHDRAWN = "withdrawn", "Снята куратором"
        EXPIRED = "expired", "Истёк срок"

    class RemovalReason(models.TextChoices):
        CUSTOMER_CANCELLED = "customer_cancelled", "Отменена заказчиком"
        MODERATION = "moderation", "Снята модератором"
        DEADLINE_PASSED = "deadline_passed", "Истёк дедлайн"
        NO_EXECUTORS = "no_executors", "Не нашлось исполнителей"
        OTHER = "other", "Другое"

    title = models.CharField(max_length=255, verbose_name="Название задачи")
    short_description = models.TextField(verbose_name="Краткое описание")
    description = models.TextField(
        blank=True, null=True, verbose_name="Полное описание"
    )

    project = models.ForeignKey(
        "showcase.Project",
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Проект",
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"role": "curator"},
        related_name="curated_tasks",
        verbose_name="Куратор",
    )
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name="Категория",
    )

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
        db_index=True,
        verbose_name="Сложность",
    )

    points = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Баллы")
    start_date = models.DateTimeField(
        blank=True, null=True, verbose_name="Начало работы"
    )
    deadline = models.DateTimeField(blank=True, null=True, verbose_name="Дедлайн")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Статус",
    )
    required_people = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Нужно исполнителей",
    )
    filled_people = models.PositiveIntegerField(
        default=0,
        verbose_name="Уже набрано",
    )
    required_course_min = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name="Мин. курс",
        help_text="Пусто — без нижней границы",
    )
    required_course_max = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name="Макс. курс",
        help_text="Пусто — без верхней границы",
    )
    required_specialty = models.ForeignKey(
        "showcase.FilterOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"category__name": "Специальность"},
        verbose_name="Требуемая специальность",
    )
    removed_at = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Дата снятия с биржи",
    )
    removal_reason = models.CharField(
        max_length=32,
        choices=RemovalReason.choices,
        blank=True,
        verbose_name="Причина снятия",
    )
    removal_comment = models.TextField(
        blank=True,
        verbose_name="Комментарий к снятию",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")
    published_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name="Дата публикации"
    )
    taken_at = models.DateTimeField(
        blank=True, null=True, db_index=True, verbose_name="Дата заполнения мест"
    )
    completed_at = models.DateTimeField(
        blank=True, null=True, db_index=True, verbose_name="Дата завершения"
    )
    withdrawn_at = models.DateTimeField(
        blank=True, null=True, db_index=True, verbose_name="Дата снятия с биржи"
    )
    expired_at = models.DateTimeField(
        blank=True, null=True, db_index=True, verbose_name="Дата истечения срока"
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["status", "published_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def free_slots(self):
        return max(self.required_people - self.filled_people, 0)

    @property
    def is_full(self):
        return self.filled_people >= self.required_people


class TaskSkill(models.Model):
    class SkillLevel(models.TextChoices):
        BEGINNER = "beginner", "Начальный"
        INTERMEDIATE = "intermediate", "Средний"
        ADVANCED = "advanced", "Продвинутый"

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="task_skills",
        verbose_name="Задача",
    )
    skill = models.CharField(max_length=250, verbose_name="Навык")
    level_required = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.BEGINNER,
        verbose_name="Уровень",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Навык задачи"
        verbose_name_plural = "Навыки задач"
        unique_together = ("task", "skill")

    def __str__(self):
        return f"{self.task} - {self.skill}"


class TaskAssignment(models.Model):
    class Status(models.TextChoices):
        TAKEN = "taken", "Взял (ещё не начал)"
        IN_PROGRESS = "in_progress", "В работе"
        SUBMITTED = "submitted", "Сдал на проверку"
        RETURNED = "returned", "Возвращена на доработку"
        COMPLETED = "completed", "Принята"
        REMOVED_BY_CURATOR = "removed_by_curator", "Снят куратором"

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="Задача",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name="Студент",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.TAKEN,
        db_index=True,
        verbose_name="Статус записи",
    )

    taken_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Дата взятия",
    )
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата начала работы",
    )
    submitted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата сдачи на проверку",
    )
    revision_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Возвратов на доработку",
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата приёмки",
    )
    removed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата снятия куратором",
    )
    removal_reason = models.TextField(
        blank=True,
        verbose_name="Причина снятия куратором",
    )
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="removed_assignments",
        verbose_name="Кем снят",
    )

    class Meta:
        verbose_name = "Запись на задачу"
        verbose_name_plural = "Записи на задачи"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "student"],
                condition=Q(
                    status__in=["taken", "in_progress", "submitted", "returned"]
                ),
                name="unique_active_assignment_per_student",
            ),
            models.CheckConstraint(
                condition=Q(revision_count__lte=3),
                name="revision_count_max_3",
            ),
        ]

    def __str__(self):
        return f"{self.student} → {self.task} ({self.get_status_display()})"
