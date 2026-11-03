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
    email = models.EmailField(unique=True, verbose_name="Логин")

    class Roles(models.TextChoices):
        ADMIN = "admin", "Администратор"
        CURATOR = "curator", "Куратор"
        STUDENT = "student", "Студент"

    # TODO: Продумать, студент может быть куратором вроде
    role = models.CharField(
        max_length=20, choices=Roles.choices, default=Roles.STUDENT, verbose_name="Роль"
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
        return self.role == self.Roles.CURATOR or self.is_superuser

    def is_student(self):
        return self.role == self.Roles.STUDENT

    def __str__(self):
        return self.get_full_name()


class Specialty(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Код направления")
    name = models.CharField(max_length=255, verbose_name="Название направления")

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


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name="Пользователь",
    )

    course = models.PositiveSmallIntegerField(
        verbose_name="Курс", choices=[(i, f"{i} курс") for i in range(1, 7)]
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
