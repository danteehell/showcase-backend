
import json
import os
import random
from datetime import timedelta
from pathlib import Path

import django
from django.db import transaction
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.contrib.auth import get_user_model
from showcase.models import (
    FilterCategory,
    FilterOption,
    Project,
    ProjectEnrollment,
    ProjectListItem,
    ProjectApplication,
)
from tasks.models import Task, TaskCategory, TaskAssignment
from users.models import (
    CuratorProfile,
    Department,
    Faculty,
    Group,
    Partner,
    PartnerRepresentative,
    Specialty,
    StudentProfile,
)

User = get_user_model()

MALE_NAMES = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей",
    "Алексей", "Иван", "Михаил", "Егор", "Артем",
]

FEMALE_NAMES = [
    "Анна", "Мария", "Елена", "Дарья", "Анастасия",
    "Екатерина", "Ольга", "Наталья", "Виктория", "Ксения",
]

LAST_NAMES = [
    "Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов",
    "Лебедев", "Козлов", "Новиков", "Морозов", "Волков",
]

MIDDLE_NAMES_M = [
    "Александрович", "Дмитриевич", "Сергеевич",
    "Андреевич", "Алексеевич", "Иванович", "Михайлович",
]

MIDDLE_NAMES_F = [
    "Александровна", "Дмитриевна", "Сергеевна",
    "Андреевна", "Алексеевна", "Ивановна", "Михайловна",
]


def create_user(email, role, index):
    is_female = random.choice([True, False])

    user = User.objects.create(
        email=email,
        role=role,
        first_name=random.choice(FEMALE_NAMES if is_female else MALE_NAMES),
        last_name=random.choice(LAST_NAMES) + ("а" if is_female else ""),
        middle_name=random.choice(
            MIDDLE_NAMES_F if is_female else MIDDLE_NAMES_M
        ),
    )
    user.set_password("123456")
    user.save()

    return user


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

    PartnerRepresentative.objects.all().delete()
    StudentProfile.objects.all().delete()
    CuratorProfile.objects.all().delete()

    Group.objects.all().delete()
    Specialty.objects.all().delete()
    Faculty.objects.all().delete()
    Department.objects.all().delete()

    Partner.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()

    print("=== СОЗДАНИЕ ФАКУЛЬТЕТОВ ===")

    faculties = [
        Faculty.objects.create(name=name)
        for name in [
            "Информационные технологии",
            "Дизайн",
            "Машиностроение",
        ]
    ]

    print("=== СОЗДАНИЕ КАФЕДР ===")

    departments = [
        Department.objects.create(name=name)
        for name in [
            "Кафедра ИТ",
            "Кафедра информационной безопасности",
            "Кафедра дизайна",
            "Кафедра робототехники",
            "Кафедра экономики",
        ]
    ]

    print("=== СОЗДАНИЕ СПЕЦИАЛЬНОСТЕЙ ===")

    specialties_data = [
        ("09.03.01", "Информатика и вычислительная техника", faculties[0]),
        ("09.03.02", "Программная инженерия", faculties[0]),
        ("09.03.03", "Прикладная информатика", faculties[0]),
        ("09.03.04", "Программное обеспечение игровой индустрии", faculties[0]),
        ("54.03.01", "Дизайн", faculties[1]),
        ("15.03.01", "Машиностроение", faculties[2]),
    ]

    specialties = [
        Specialty.objects.create(code=code, name=name, faculty=faculty)
        for code, name, faculty in specialties_data
    ]

    print("=== СОЗДАНИЕ ГРУПП ===")

    groups = []

    for specialty in specialties:
        for year in range(1, 5):
            groups.append(
                Group.objects.create(
                    name=f"{specialty.code}-{year}А",
                    specialty=specialty,
                    year=year,
                )
            )

    print("=== СОЗДАНИЕ ПАРТНЕРОВ ===")

    partners_data = [
        {
            "name": "Яндекс",
            "short_name": "Yandex",
            "website": "https://yandex.ru",
            "email": "partners@yandex.ru",
            "phone": "+7 495 739-70-00",
            "contact_person": "Отдел сотрудничества",
            "internship": True,
        },
        {
            "name": "VK",
            "short_name": "VK",
            "website": "https://vk.com",
            "email": "partners@vk.company",
            "phone": "+7 495 725-63-57",
            "contact_person": "Отдел партнерских программ",
            "internship": True,
        },
        {
            "name": "Сбер",
            "short_name": "Сбер",
            "website": "https://sber.ru",
            "email": "partners@sber.ru",
            "phone": "+7 495 500-55-50",
            "contact_person": "Отдел взаимодействия с вузами",
            "internship": True,
        },
        {
            "name": "Ростелеком",
            "short_name": "РТК",
            "website": "https://rt.ru",
            "email": "partners@rt.ru",
            "phone": "+7 800 100-08-00",
            "contact_person": "Отдел партнерских проектов",
            "internship": True,
        },
        {
            "name": "Астра",
            "short_name": "Astra",
            "website": "https://astralinux.ru",
            "email": "partners@astralinux.ru",
            "phone": "+7 495 665-70-00",
            "contact_person": "Отдел сотрудничества",
            "internship": False,
        },
        {
            "name": "Т-Банк",
            "short_name": "Т-Банк",
            "website": "https://www.tbank.ru",
            "email": "partners@tbank.ru",
            "phone": "+7 800 333-33-33",
            "contact_person": "Отдел партнерских программ",
            "internship": True,
        },
    ]

    partners = [
        Partner.objects.create(
            **data,
            is_curator_contact=False,
            additional_contact=None,
        )
        for data in partners_data
    ]

    print("=== СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ===")

    curators = []

    for i in range(1, 6):
        curator = create_user(
            email=f"curator{i}@mospolytech.ru",
            role="curator",
            index=i,
        )

        CuratorProfile.objects.create(
            user=curator,
            department=random.choice(departments),
        )

        curators.append(curator)

    students = []

    for i in range(1, 11):
        student = create_user(
            email=f"student{i}@mospolytech.ru",
            role="student",
            index=i,
        )

        group = random.choice(groups)

        StudentProfile.objects.create(
            user=student,
            course=group.year,
            specialty=group.specialty,
            group=group,
        )

        students.append(student)

    print("=== СОЗДАНИЕ ПРЕДСТАВИТЕЛЕЙ ПАРТНЕРОВ ===")

    for i, partner in enumerate(partners, start=1):
        representative = create_user(
            email=f"partner{i}@mospolytech.ru",
            role="partner",
            index=i,
        )

        PartnerRepresentative.objects.create(
            user=representative,
            partner=partner,
        )

    print("=== СОЗДАНИЕ ФИЛЬТРОВ ===")

    cat_theme = FilterCategory.objects.create(name="Тематика")
    cat_campus = FilterCategory.objects.create(name="Корпус")
    cat_course = FilterCategory.objects.create(name="Курс")
    cat_diff = FilterCategory.objects.create(name="Сложность")

    campuses = [
        FilterOption.objects.create(category=cat_campus, name=name)
        for name in [
            "Автозаводская",
            "Прянишникова",
            "Большая Семеновская",
        ]
    ]

    courses = [
        FilterOption.objects.create(category=cat_course, name=f"{year} курс")
        for year in range(1, 5)
    ]

    difficulties = [
        FilterOption.objects.create(category=cat_diff, name=name)
        for name in ["Низкая", "Средняя", "Высокая"]
    ]

    filters_path = Path(__file__).with_name("filters.json")

    with filters_path.open("r", encoding="utf-8") as file:
        filters_data = json.load(file)

    theme_options = [
        FilterOption.objects.create(category=cat_theme, name=item["value"])
        for item in filters_data["filters"][0]["values"]
    ]

    print("=== ГЕНЕРАЦИЯ ПРОЕКТОВ ===")

    project_templates = [
        ("Разработка платформы для стажировок", "Создание веб-сервиса."),
        ("Мобильное приложение", "Разработка кроссплатформенного приложения."),
        ("Система распознавания лиц", "Использование компьютерного зрения."),
        ("Редизайн личного кабинета", "Создание новых макетов в Figma."),
        ("Фирменный стиль клуба", "Разработка визуальной идентичности."),
        ("Видеоподкаст", "Организация съемок и монтажа."),
        ("3D-модели для музея", "Оцифровка экспонатов."),
        ("Умный дом", "Разработка IoT-устройства."),
        ("Расчет корпуса", "CAD-моделирование."),
        ("Беспилотный ровер", "Разработка автономного устройства."),
        ("Логистика кампуса", "Оптимизация перемещения по кампусу."),
        ("Биосенсор для воды", "Разработка лабораторного прототипа."),
        ("Анализ данных", "Построение моделей машинного обучения."),
        ("Волонтерская платформа", "Разработка сайта для НКО."),
    ]

    projects = []

    for _ in range(20):
        title, short_description = random.choice(project_templates)

        project = Project.objects.create(
            title=title,
            short_description=short_description,
            relevance=short_description,
            problem="Проблема, которую необходимо решить в рамках проекта.",
            goal="Разработка и реализация проектного решения.",
            tasks="1. Анализ требований\n2. Разработка решения\n3. Тестирование",
            expected_result="Работающий прототип или готовый продукт.",
            theme=random.choice(theme_options),
            campus=random.choice(campuses),
            difficulty=random.choice(difficulties),
            partner=random.choice(partners),
            curator=random.choice(curators),
            internship=random.choice([True, False]),
            spots_remaining=random.randint(1, 10),
            is_active=True,
        )

        project.specialties.set(
            random.sample(specialties, k=random.randint(1, 3))
        )

        project.courses.add(random.choice(courses))
        projects.append(project)

    print("=== ГЕНЕРАЦИЯ ЗАДАЧ ДЛЯ БИРЖИ ===")

    task_categories = [
        TaskCategory.objects.create(name=name)
        for name in ["Frontend", "Backend", "Дизайн", "Аналитика"]
    ]

    tasks_to_create = []

    for project in projects[:10]:
        for _ in range(2):
            tasks_to_create.append(
                Task(
                    project=project,
                    curator=project.curator,
                    category=random.choice(task_categories),
                    title="Тестовая задача",
                    short_description="Краткое описание задачи.",
                    description="Полное описание задачи и ожидаемый результат.",
                    points=random.randint(5, 50),
                    status=Task.Status.PUBLISHED,
                    required_people=random.randint(1, 3),
                    deadline=timezone.now() + timedelta(days=30),
                )
            )

    Task.objects.bulk_create(tasks_to_create)

    print(
        "=== ГОТОВО! "
        f"Проектов: {len(projects)}, "
        f"кураторов: {len(curators)}, "
        f"студентов: {len(students)}, "
        f"партнеров: {len(partners)} ==="
    )


if __name__ == "__main__":
    run()
