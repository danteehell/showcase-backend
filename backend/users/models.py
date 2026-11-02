from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


# TODO: Надо продумать данные для каждой роли
# Например у студента будет специальность, у куратора кафедра итд.
class User(AbstractUser):
    
    class Roles(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        CURATOR = 'curator', 'Куратор'
        STUDENT = 'student', 'Студент'

    middle_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Отчество")

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT,
    )
    def get_full_name(self):
        if self.last_name and self.first_name and self.middle_name:
            return f"{self.last_name} {self.first_name} {self.middle_name}"
        elif self.last_name and self.first_name:
            return f"{self.last_name} {self.first_name}"
        elif self.first_name:
            return self.first_name
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
    
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    course = models.PositiveSmallIntegerField(verbose_name="Курс")
    specialty = models.ForeignKey('showcase.FilterOption', on_delete=models.SET_NULL, null=True, verbose_name="Специальность")

# ASK: Нам нужно знать какие данные есть в лк у преподавателей.
class CuratorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='curator_profile')
    department = models.CharField(max_length=255, verbose_name="Кафедра")

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