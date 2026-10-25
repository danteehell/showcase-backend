from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.utils import timezone

class User(AbstractUser):
    
    class Roles(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        CURATOR = 'curator', 'Куратор'
        STUDENT = 'student', 'Студент'

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT,
    )
    keycloak_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    def is_admin(self):
        return self.role == self.Roles.ADMIN or self.is_superuser

    def is_curator(self):
        return self.role == self.Roles.CURATOR or self.is_superuser

    def is_student(self):
        return self.role == self.Roles.STUDENT

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name='Пользователь',
    )
    course = models.PositiveSmallIntegerField(
        verbose_name='Курс',
        help_text='Текущий курс обучения',
    )
    specialty = models.CharField(
        max_length=100,
        verbose_name='Специальность',
        help_text='Например, ИВТ, Экономика',
    )

    class Meta:
        verbose_name = 'Профиль студента'
        verbose_name_plural = 'Профили студентов'