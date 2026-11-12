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
    ProjectApplication,
    ProjectApplicationListItem,
)
from tasks.models import Task, TaskCategory, TaskAssignment
from users.models import CuratorProfile, Department, Specialty, StudentProfile

User = get_user_model()

MALE_NAMES = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Иван", "Михаил", "Егор", "Артем", "Никита", "Матвей", "Роман", "Даниил", "Кирилл"]
FEMALE_NAMES = ["Анна", "Мария", "Елена", "Дарья", "Анастасия", "Екатерина", "Ольга", "Наталья", "Виктория", "Ксения", "Полина", "Алиса", "Валерия", "Вероника", "Софья"]
LAST_NAMES = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Волков", "Петров", "Соловьев", "Васильев", "Зайцев", "Павлов", "Семенов", "Голубев", "Виноградов", "Богданов", "Воробьев"]
MIDDLE_NAMES_M = ["Александрович", "Дмитриевич", "Сергеевич", "Андреевич", "Алексеевич", "Иванович", "Михайлович", "Максимович", "Петрович"]
MIDDLE_NAMES_F = ["Александровна", "Дмитриевна", "Сергеевна", "Андреевна", "Алексеевна", "Ивановна", "Михайловна", "Максимовна", "Петровна"]


@transaction.atomic
def run():
    print("=== ОЧИСТКА СТАРЫХ ДАННЫХ ===")
    TaskAssignment.objects.all().delete()
    ProjectEnrollment.objects.all().delete()
    ProjectApplicationListItem.objects.all().delete()
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
    dep_names = ["Кафедра ИТ", "Кафедра Информационной безопасности", "Кафедра Дизайна", "Кафедра Робототехники", "Кафедра Экономики", "Кафедра Машиностроения", "Кафедра Управления"]
    departments = [Department.objects.create(name=n) for n in dep_names]

    specialties_data = [
        ("09.03.01", "Информатика и вычислительная техника"),
        ("09.03.02", "Программная инженерия"),
        ("09.03.03", "Прикладная информатика"),
        ("09.03.04", "Программное обеспечение игровой индустрии"),
        ("54.03.01", "Дизайн"),
        ("15.03.01", "Машиностроение"),
        ("27.03.04", "Управление в технических системах"),
        ("38.03.01", "Экономика"),
        ("10.03.01", "Информационная безопасность"),
        ("42.03.01", "Реклама и связи с общественностью"),
    ]
    specialties = [Specialty.objects.create(code=c, name=n) for c, n in specialties_data]

    print("=== СОЗДАНИЕ ФИЛЬТРОВ ===")
    cat_theme = FilterCategory.objects.create(name="Тематика")
    cat_campus = FilterCategory.objects.create(name="Корпус")
    cat_course = FilterCategory.objects.create(name="Курс")
    cat_diff = FilterCategory.objects.create(name="Сложность")

    campuses = [FilterOption.objects.create(category=cat_campus, name=n) for n in ["Автозаводская", "Прянишникова", "Большая Семеновская", "Павла Корчагина"]]
    courses = [FilterOption.objects.create(category=cat_course, name=n) for n in ["1 курс", "2 курс", "3 курс", "4 курс"]]
    diffs = [FilterOption.objects.create(category=cat_diff, name=n) for n in ["Низкая", "Средняя", "Высокая"]]
    partners = [Partner.objects.create(name=n) for n in ["Яндекс", "VK", "Сбер", "Ростелеком", "Астра", "Тинькофф", "1С", "СберМаркет", "Авито"]]
 
    with open("filters.json", "r", encoding="utf-8") as f:
        filters_data = json.load(f)

    theme_options = [FilterOption.objects.create(category=cat_theme, name=t["value"]) for t in filters_data["filters"][0]["values"]]

    print("=== СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ===")
    curators = []
    for i in range(1, 16):
        is_female = random.choice([True, False])
        c = User.objects.create(
            email=f"curator{i}@mospolytech.ru",
            role="curator",
            first_name=random.choice(FEMALE_NAMES if is_female else MALE_NAMES),
            last_name=random.choice(LAST_NAMES) + ("а" if is_female else ""),
            middle_name=random.choice(MIDDLE_NAMES_F if is_female else MIDDLE_NAMES_M),
        )
        c.set_password("123456")
        c.save()
        CuratorProfile.objects.create(user=c, department=random.choice(departments))
        curators.append(c)

    students = []
    for i in range(1, 51):
        is_female = random.choice([True, False])
        s = User.objects.create(
            email=f"student{i}@mospolytech.ru",
            role="student",
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
        "IT": [("Разработка платформы для стажировок", "Создание веб-сервиса, который агрегирует вакансии."), ("Мобильное приложение для расписания", "Разработка кроссплатформенного приложения с push-уведомлениями."), ("Система распознавания лиц", "Использование CV для автоматизации доступа."), ("Telegram-бот для абитуриентов", "Чат-бот с ответами на частые вопросы."), ("Парсер вакансий", "Написание скраперов и вывод в дашборд.")],
        "Дизайн": [("Редизайн личного кабинета", "Создание новых макетов в Figma."), ("Фирменный стиль клуба", "Создание логотипа и брендбука."), ("UI/UX редизайн сайта", "Обновление интерфейса и прототипов.")],
        "Мультимедиа": [("Видеоподкаст", "Организация съемок и монтаж видео."), ("3D-модели для музея", "Оцифровка экспонатов."), ("Анимационный ролик", "Создание 2D-анимации.")],
        "Технология": [("Умный дом", "Сборка IoT-устройства."), ("Расчет корпуса", "CAD-моделирование нагрузок."), ("Контроль доступа на Arduino", "Сборка макета и настройка RFID.")],
        "Транспорт": [("Беспилотный ровер", "Сборка шасси и настройка сенсоров."), ("Логистика кампуса", "Разработка аренды самокатов."), ("Мониторинг транспорта", "Создание GPS-трекера.")],
        "Химбиотех": [("Биосенсор для воды", "Лабораторный прототип."), ("Симуляция реакций", "Python-моделирование.")],
        "Научные проекты": [("Анализ данных в экологии", "Построение ML-моделей."), ("Свойства материалов", "Моделирование и испытания.")],
        "Соцтех": [("Волонтерские проекты", "Сайт для НКО."), ("Инклюзивное образование", "Сервис с аудио-описаниями.")],
    }

    projects = []
    for _ in range(40):
        theme = random.choice(theme_options)
        title_template, short_desc = random.choice(project_pool.get(theme.name, [("Исследовательский проект", "Научные исследования.")]))
        title = title_template.format(theme.name) if "{}" in title_template else title_template
        long_desc = f"Цель проекта: {short_desc}\n\nВ рамках проекта предстоит полный цикл разработки."
        
        project = Project.objects.create(
            title=title, short_description=short_desc, long_description=long_desc, theme=theme,
            campus=random.choice(campuses), difficulty=random.choice(diffs), partner=random.choice(partners),
            curator=random.choice(curators), internship=random.choice([True, False]),
            spots_remaining=random.randint(1, 10), is_active=True,
        )
        project.specialties.set(random.sample(specialties, k=random.randint(1, 3)))
        project.courses.add(random.choice(courses))
        projects.append(project)

    print("=== ДОБАВЛЕНИЕ ЭЛЕМЕНТОВ ПРОЕКТОВ (BULK) ===")
    tech_names = ["React", "TypeScript", "Python", "Django", "PostgreSQL", "Docker", "Figma", "C++", "Arduino", "Kotlin", "Swift", "Unity", "Unreal Engine"]
    tasks_texts = ["Разработка интерфейсов", "Создание макетов", "Работа с API", "Тестирование", "Участие в командных встречах", "Защита результата"]
    
    list_items_to_create = []
    for proj in projects:
        for tech in random.sample(tech_names, k=random.randint(2, 5)):
            list_items_to_create.append(ProjectListItem(project=proj, type='technologies', text=tech))
        for task in random.sample(tasks_texts, k=random.randint(2, 4)):
            list_items_to_create.append(ProjectListItem(project=proj, type='tasks', text=task))
    
    ProjectListItem.objects.bulk_create(list_items_to_create)

    print("=== ГЕНЕРАЦИЯ ЗАДАЧ ДЛЯ БИРЖИ (BULK) ===")
    task_cats = ["Frontend", "Backend", "Дизайн", "Аналитика", "Тестирование", "DevOps"]
    task_categories = [TaskCategory.objects.create(name=c) for c in task_cats]

    task_templates = [
        ("Разработка главной страницы", "Сверстать интерфейс по макету."), ("Настройка базы данных", "Спроектировать ER-диаграмму."),
        ("Создание API", "Разработать REST API."), ("Юзабилити-тестирование", "Провести тестирование."),
        ("Настройка CI/CD", "Настроить GitHub Actions."), ("Сборка макета", "Спаять прототип."),
        ("Анализ конкурентов", "Собрать данные."), ("Документация", "Составить руководство."),
    ]

    tasks_to_create = []
    for proj in projects[:15]:
        for _ in range(3):
            title, short_desc = random.choice(task_templates)
            tasks_to_create.append(Task(
                project=proj, curator=proj.curator, category=random.choice(task_categories),
                title=title, short_description=short_desc, 
                description=f"Описание: {short_desc}\n\nТребования: ответственность.",
                difficulty=random.choice(Task.Difficulty.values), points=random.randint(5, 50),
                status=Task.Status.PUBLISHED, required_people=random.randint(1, 3),
                deadline=timezone.now() + timedelta(days=random.randint(10, 60))
            ))
    
    Task.objects.bulk_create(tasks_to_create)

    print(f"=== ГОТОВО ===")
    print(f"Кураторы (пароль '123456'): {len(curators)}")
    print(f"Студенты (пароль '123456'): {len(students)}")
    print(f"Проекты: {len(projects)}")
    print(f"Задачи на бирже: {len(tasks_to_create)}")


if __name__ == "__main__":
    run()