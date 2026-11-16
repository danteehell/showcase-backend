import json
import os
import random
from datetime import timedelta

import django
from django.db import transaction
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.contrib.auth import get_user_model
from showcase.models import (
    FilterCategory,
    FilterOption,
    Partner,
    Project,
    ProjectEnrollment,
    ProjectListItem,
    ProjectApplication, # Добавили новую модель
)
from tasks.models import Task, TaskCategory, TaskAssignment
from users.models import CuratorProfile, Department, Specialty, StudentProfile

User = get_user_model()

MALE_NAMES = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Иван", "Михаил", "Егор", "Артем"]
FEMALE_NAMES = ["Анна", "Мария", "Елена", "Дарья", "Анастасия", "Екатерина", "Ольга", "Наталья", "Виктория", "Ксения"]
LAST_NAMES = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Волков"]
MIDDLE_NAMES_M = ["Александрович", "Дмитриевич", "Сергеевич", "Андреевич", "Алексеевич", "Иванович", "Михайлович"]
MIDDLE_NAMES_F = ["Александровна", "Дмитриевна", "Сергеевна", "Андреевна", "Алексеевна", "Ивановна", "Михайловна"]

@transaction.atomic
def run():
    print("=== ОЧИСТКА СТАРЫХ ДАННЫХ ===")
    TaskAssignment.objects.all().delete()
    ProjectEnrollment.objects.all().delete()
    ProjectApplication.objects.all().delete()
    ProjectListItem.objects.all().delete()
    Task.objects.all().delete()
    TaskCategory.objects.all().delete()
    Project.objects.all().delete()
    FilterOption.objects.all().delete()
    FilterCategory.objects.all().delete()
    Partner.objects.all().delete()
    Specialty.objects.all().delete()
    Department.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()

    print("=== СОЗДАНИЕ СПРАВОЧНИКОВ ===")
    dep_names = ["Кафедра ИТ", "Кафедра Информационной безопасности", "Кафедра Дизайна", "Кафедра Робототехники", "Кафедра Экономики"]
    departments = [Department.objects.create(name=n) for n in dep_names]

    specialties_data = [
        ("09.03.01", "Информатика и вычислительная техника"),
        ("09.03.02", "Программная инженерия"),
        ("09.03.03", "Прикладная информатика"),
        ("09.03.04", "Программное обеспечение игровой индустрии"),
        ("54.03.01", "Дизайн"),
        ("15.03.01", "Машиностроение"),
    ]
    specialties = [Specialty.objects.create(code=c, name=n) for c, n in specialties_data]

    print("=== СОЗДАНИЕ ФИЛЬТРОВ ===")
    cat_theme = FilterCategory.objects.create(name="Тематика")
    cat_campus = FilterCategory.objects.create(name="Корпус")
    cat_course = FilterCategory.objects.create(name="Курс")
    cat_diff = FilterCategory.objects.create(name="Сложность")

    campuses = [FilterOption.objects.create(category=cat_campus, name=n) for n in ["Автозаводская", "Прянишникова", "Большая Семеновская"]]
    courses = [FilterOption.objects.create(category=cat_course, name=n) for n in ["1 курс", "2 курс", "3 курс", "4 курс"]]
    diffs = [FilterOption.objects.create(category=cat_diff, name=n) for n in ["Низкая", "Средняя", "Высокая"]]
    partners = [Partner.objects.create(name=n) for n in ["Яндекс", "VK", "Сбер", "Ростелеком", "Астра", "Тинькофф"]]
  

    with open("filters.json", "r", encoding="utf-8") as f:
        filters_data = json.load(f)

    theme_options = [FilterOption.objects.create(category=cat_theme, name=t["value"]) for t in filters_data["filters"][0]["values"]]

    print("=== СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ===")
    curators = []
    for i in range(1, 6):
        is_female = random.choice([True, False])
        c = User.objects.create(
            email=f"curator{i}@mospolytech.ru", role="curator",
            first_name=random.choice(FEMALE_NAMES if is_female else MALE_NAMES),
            last_name=random.choice(LAST_NAMES) + ("а" if is_female else ""),
            middle_name=random.choice(MIDDLE_NAMES_F if is_female else MIDDLE_NAMES_M),
        )
        c.set_password("123456")
        c.save()
        CuratorProfile.objects.create(user=c, department=random.choice(departments))
        curators.append(c)

    students = []
    for i in range(1, 11):
        is_female = random.choice([True, False])
        s = User.objects.create(
            email=f"student{i}@mospolytech.ru", role="student",
            first_name=random.choice(FEMALE_NAMES if is_female else MALE_NAMES),
            last_name=random.choice(LAST_NAMES) + ("а" if is_female else ""),
            middle_name=random.choice(MIDDLE_NAMES_F if is_female else MIDDLE_NAMES_M),
        )
        s.set_password("123456")
        s.save()
        StudentProfile.objects.create(user=s, course=random.randint(1, 4), specialty=random.choice(specialties))
        students.append(s)

    print("=== ГЕНЕРАЦИЯ ПРОЕКТОВ ===")
    project_pool = {
        "IT": [("Разработка платформы для стажировок", "Создание веб-сервиса."), ("Мобильное приложение", "Разработка кроссплатформенного приложения."), ("Система распознавания лиц", "Использование CV.")],
        "Дизайн": [("Редизайн личного кабинета", "Создание новых макетов в Figma."), ("Фирменный стиль клуба", "Создание логотипа.")],
        "Мультимедиа": [("Видеоподкаст", "Организация съемок."), ("3D-модели для музея", "Оцифровка экспонатов.")],
        "Технология": [("Умный дом", "Сборка IoT-устройства."), ("Расчет корпуса", "CAD-моделирование.")],
        "Транспорт": [("Беспилотный ровер", "Сборка шасси."), ("Логистика кампуса", "Разработка аренды самокатов.")],
        "Химбиотех": [("Биосенсор для воды", "Лабораторный прототип.")],
        "Научные проекты": [("Анализ данных", "Построение ML-моделей.")],
        "Соцтех": [("Волонтерские проекты", "Сайт для НКО.")],
    }

    projects = []
    for _ in range(20):
        theme = random.choice(theme_options)
        title, short_desc = random.choice(project_pool.get(theme.name, [("Проект", "Описание.")]))
        
        project = Project.objects.create(
            title=title, 
            short_description=short_desc, 
            relevance=short_desc,
            problem="Проблема проекта",
            goal="Цель проекта",
            tasks="Задача 1\nЗадача 2",
            expected_result="Готовый продукт",
            theme=theme,
            campus=random.choice(campuses), 
            difficulty=random.choice(diffs), 
            partner=random.choice(partners),
            curator=random.choice(curators), 
            internship=random.choice([True, False]),
            spots_remaining=random.randint(1, 10), 
            is_active=True,
        )
        project.specialties.set(random.sample(specialties, k=random.randint(1, 3)))
        project.courses.add(random.choice(courses))
        projects.append(project)

    print("=== ГЕНЕРАЦИЯ ЗАДАЧ ДЛЯ БИРЖИ ===")
    task_cats = ["Frontend", "Backend", "Дизайн", "Аналитика"]
    task_categories = [TaskCategory.objects.create(name=c) for c in task_cats]

    tasks_to_create = []
    for proj in projects[:10]:
        for _ in range(2):
            tasks_to_create.append(Task(
                project=proj, curator=proj.curator, category=random.choice(task_categories),
                title="Тестовая задача", short_description="Описание задачи", 
                description="Полное описание задачи",
                difficulty=random.choice(Task.Difficulty.values), points=random.randint(5, 50),
                status=Task.Status.PUBLISHED, required_people=random.randint(1, 3),
                deadline=timezone.now() + timedelta(days=30)
            ))
    
    Task.objects.bulk_create(tasks_to_create)

    print(f"=== ГОТОВО! Создано проектов: {len(projects)}, пользователей: {len(curators) + len(students)} ===")

if __name__ == "__main__":
    run()