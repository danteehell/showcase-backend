from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
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
    specialty = models.ForeignKey(
        'showcase.FilterOption',
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'category__name': 'Специальность'},
        related_name="students",
        verbose_name="Направление подготовки"
    )
    keycloak_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    def is_admin(self):
        return self.role == self.Roles.ADMIN or self.is_superuser

    def is_curator(self):
        return self.role == self.Roles.CURATOR or self.is_superuser

    def is_student(self):
        return self.role == self.Roles.STUDENT
    
    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.last_name} {self.first_name}".strip()
        return self.username


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