from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    email = models.EmailField(
        unique=True,
        blank=False,
        verbose_name="Логин (email)",
    )

    class Roles(models.TextChoices):
        ADMIN = "admin", "Начальник ЦПД"
        DIRECTION_HEAD = "direction_head", "Руководитель направления"
        DEAN = "dean", "Декан факультета"
        CURATOR = "curator", "Куратор"
        PARTNER = "partner", "Представитель партнёра"
        STUDENT = "student", "Студент"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT,
        verbose_name="Роль",
    )
    middle_name = models.CharField(max_length=150, blank=True, verbose_name="Отчество")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def get_full_name(self):
        if self.last_name and self.first_name and self.middle_name:
            return f"{self.last_name} {self.first_name} {self.middle_name}"
        elif self.last_name and self.first_name:
            return f"{self.last_name} {self.first_name}"
        elif self.first_name:
            return self.first_name
        elif self.email:
            return self.email
        return str(self.id)

    def is_admin(self):
        return self.role == self.Roles.ADMIN or self.is_superuser

    def is_curator(self):
        return self.role == self.Roles.CURATOR

    def is_student(self):
        return self.role == self.Roles.STUDENT

    def is_direction_head(self):
        return self.role == self.Roles.DIRECTION_HEAD

    def is_dean(self):
        return self.role == self.Roles.DEAN

    def is_partner(self):
        return self.role == self.Roles.PARTNER

    def __str__(self):
        return self.get_full_name()


class Faculty(models.Model):
    name = models.CharField(
        max_length=255, unique=True, verbose_name="Название факультета"
    )
    dean = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dean_of_faculties",
        limit_choices_to={"role": User.Roles.DEAN},
        verbose_name="Декан",
    )

    class Meta:
        verbose_name = "Факультет"
        verbose_name_plural = "Факультеты"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Specialty(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Код направления")
    name = models.CharField(max_length=255, verbose_name="Название направления")
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.PROTECT,
        related_name="specialties",
        verbose_name="Факультет",
    )
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_specialties",
        limit_choices_to={"role": User.Roles.DIRECTION_HEAD},
        verbose_name="Руководитель направления",
    )

    class Meta:
        verbose_name = "Направление подготовки"
        verbose_name_plural = "Направления подготовки"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Department(models.Model):
    name = models.CharField(
        max_length=255, unique=True, verbose_name="Название кафедры"
    )

    class Meta:
        verbose_name = "Кафедра"
        verbose_name_plural = "Кафедры"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField("Номер группы", max_length=20, unique=True)
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,
        related_name="groups",
        verbose_name="Направление подготовки",
    )
    year = models.PositiveSmallIntegerField("Год набора", null=True, blank=True)

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.specialty.code})"


class Partner(models.Model):
    name = models.CharField(max_length=200, verbose_name="Партнёр")
    short_name = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Сокращенное название"
    )
    website = models.URLField(blank=True, null=True, verbose_name="Сайт")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Телефон"
    )
    contact_person = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Контактное лицо"
    )
    is_curator_contact = models.BooleanField(
        default=False, verbose_name="Куратор проекта является контактным лицом"
    )
    additional_contact = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Доп. способ связи"
    )
    internship = models.BooleanField(default=False, verbose_name="Стажировка")

    class Meta:
        verbose_name = "Партнёр"
        verbose_name_plural = "Партнёры"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PartnerRepresentative(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="partner_roles",
        verbose_name="Пользователь",
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name="representatives",
        verbose_name="Партнёр",
    )

    class Meta:
        verbose_name = "Представитель партнёра"
        verbose_name_plural = "Представители партнёров"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "partner"],
                name="uniq_user_partner",
            ),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.partner.name}"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name="Пользователь",
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
        verbose_name="Группа",
    )
    course = models.PositiveSmallIntegerField(
        verbose_name="Курс",
        choices=[(i, f"{i} курс") for i in range(1, 7)],
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Направление подготовки",
    )

    class Meta:
        verbose_name = "Профиль студента"
        verbose_name_plural = "Профили студентов"

    def __str__(self):
        return f"Профиль: {self.user.get_full_name()}"


class CuratorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="curator_profile",
        verbose_name="Пользователь",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кафедра",
    )

    class Meta:
        verbose_name = "Профиль куратора"
        verbose_name_plural = "Профили кураторов"

    def __str__(self):
        return f"Куратор: {self.user.get_full_name()}"


class StudentProxy(User):
    class Meta:
        proxy = True
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"


class CuratorProxy(User):
    class Meta:
        proxy = True
        verbose_name = "Куратор"
        verbose_name_plural = "Кураторы"


class AdminProxy(User):
    class Meta:
        proxy = True
        verbose_name = "Администратор"
        verbose_name_plural = "Администраторы"


class DirectionHeadProxy(User):
    class Meta:
        proxy = True
        verbose_name = "Руководитель направления"
        verbose_name_plural = "Руководители направлений"


class DeanProxy(User):
    class Meta:
        proxy = True
        verbose_name = "Декан факультета"
        verbose_name_plural = "Деканы факультетов"


class PartnerProxy(User):
    class Meta:
        proxy = True
        verbose_name = "Представитель партнёра"
        verbose_name_plural = "Представители партнёров"
