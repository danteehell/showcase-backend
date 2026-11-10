import json
import os
import random
from django.utils import timezone
import django

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
    ScheduleItem,
)
from tasks.models import Task, TaskCategory
from users.models import CuratorProfile, Department, Specialty, StudentProfile

User = get_user_model()

MALE_NAMES = [
    "Александр",
    "Дмитрий",
    "Максим",
    "Сергей",
    "Андрей",
    "Алексей",
    "Иван",
    "Михаил",
    "Егор",
    "Артем",
    "Никита",
    "Матвей",
    "Роман",
    "Даниил",
    "Кирилл",
]
FEMALE_NAMES = [
    "Анна",
    "Мария",
    "Елена",
    "Дарья",
    "Анастасия",
    "Екатерина",
    "Ольга",
    "Наталья",
    "Виктория",
    "Ксения",
    "Полина",
    "Алиса",
    "Валерия",
    "Вероника",
    "Софья",
]
LAST_NAMES = [
    "Иванов",
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Соколов",
    "Лебедев",
    "Козлов",
    "Новиков",
    "Морозов",
    "Волков",
    "Петров",
    "Соловьев",
    "Васильев",
    "Зайцев",
    "Павлов",
    "Семенов",
    "Голубев",
    "Виноградов",
    "Богданов",
    "Воробьев",
]
MIDDLE_NAMES_M = [
    "Александрович",
    "Дмитриевич",
    "Сергеевич",
    "Андреевич",
    "Алексеевич",
    "Иванович",
    "Михайлович",
    "Максимович",
    "Петрович",
]
MIDDLE_NAMES_F = [
    "Александровна",
    "Дмитриевна",
    "Сергеевна",
    "Андреевна",
    "Алексеевна",
    "Ивановна",
    "Михайловна",
    "Максимовна",
    "Петровна",
]


def run():
    print("=== ОЧИСТКА СТАРЫХ ДАННЫХ ===")
    ProjectEnrollment.objects.all().delete()
    Project.objects.all().delete()
    FilterOption.objects.all().delete()
    FilterCategory.objects.all().delete()
    Partner.objects.all().delete()
    Task.objects.all().delete()
    TaskCategory.objects.all().delete()
    Specialty.objects.all().delete()
    Department.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()

    print("=== СОЗДАНИЕ СПРАВОЧНИКОВ (Кафедры и Направления) ===")
    dep_names = [
        "Кафедра ИТ",
        "Кафедра Информационной безопасности",
        "Кафедра Дизайна",
        "Кафедра Робототехники",
        "Кафедра Экономики",
        "Кафедра Машиностроения",
        "Кафедра Управления",
    ]
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
    specialties = [
        Specialty.objects.create(code=c, name=n) for c, n in specialties_data
    ]

    print("=== СОЗДАНИЕ БАЗОВЫХ ФИЛЬТРОВ ===")
    cat_theme = FilterCategory.objects.create(name="Тематика")
    cat_campus = FilterCategory.objects.create(name="Корпус")
    cat_course = FilterCategory.objects.create(name="Курс")
    cat_diff = FilterCategory.objects.create(name="Сложность")

    campuses = [
        FilterOption.objects.create(category=cat_campus, name=n)
        for n in [
            "Автозаводская",
            "Прянишникова",
            "Большая Семеновская",
            "Павла Корчагина",
        ]
    ]
    courses = [
        FilterOption.objects.create(category=cat_course, name=n)
        for n in ["1 курс", "2 курс", "3 курс", "4 курс"]
    ]
    diffs = [
        FilterOption.objects.create(category=cat_diff, name=n)
        for n in ["Низкая", "Средняя", "Высокая"]
    ]
    partners = [
        Partner.objects.create(name=n)
        for n in [
            "Яндекс",
            "VK",
            "Сбер",
            "Ростелеком",
            "Астра",
            "Тинькофф",
            "1С",
            "СберМаркет",
            "Авито",
        ]
    ]
    schedules = [
        ScheduleItem.objects.create(day_of_week=i, start_time="10:00", end_time="12:00")
        for i in range(3)
    ]

    print("=== ЧТЕНИЕ ТЕМАТИК ИЗ JSON ===")
    with open("filters.json", "r", encoding="utf-8") as f:
        filters_data = json.load(f)

    theme_options = []
    for t in filters_data["filters"][0]["values"]:
        opt = FilterOption.objects.create(category=cat_theme, name=t["value"])
        theme_options.append(opt)

    print("=== СОЗДАНИЕ КУРАТОРОВ (15 шт) ===")
    curators = []
    for i in range(1, 16):
        is_female = random.choice([True, False])
        first_name = random.choice(FEMALE_NAMES if is_female else MALE_NAMES)
        last_name = random.choice(LAST_NAMES) + ("а" if is_female else "")
        middle_name = random.choice(MIDDLE_NAMES_F if is_female else MIDDLE_NAMES_M)

        c = User.objects.create(
            email=f"curator{i}@mospolytech.ru",
            role="curator",
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )
        c.set_password("123456")
        c.save()

        CuratorProfile.objects.create(user=c, department=random.choice(departments))
        curators.append(c)

    print("=== СОЗДАНИЕ СТУДЕНТОВ (50 шт) ===")
    students = []
    for i in range(1, 51):
        is_female = random.choice([True, False])
        first_name = random.choice(FEMALE_NAMES if is_female else MALE_NAMES)
        last_name = random.choice(LAST_NAMES) + ("а" if is_female else "")
        middle_name = random.choice(MIDDLE_NAMES_F if is_female else MIDDLE_NAMES_M)

        s = User.objects.create(
            email=f"student{i}@mospolytech.ru",
            role="student",
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )
        s.set_password("123456")
        s.save()
        students.append(s)

    print("=== СОЗДАНИЕ ПРОФИЛЕЙ СТУДЕНТОВ ===")
    for s in students:
        StudentProfile.objects.create(
            user=s, course=random.randint(1, 4), specialty=random.choice(specialties)
        )

    print("=== ГЕНЕРАЦИЯ ПРОЕКТОВ (40 шт) ===")
    project_pool = {
        "IT": [
            (
                "Разработка платформы для стажировок",
                "Создание веб-сервиса, который агрегирует вакансии для студентов и позволяет отправлять отклики в один клик.",
            ),
            (
                "Мобильное приложение для расписания",
                "Разработка кроссплатформенного приложения с push-уведомлениями об изменениях в расписании и интеграцией с личным кабинетом.",
            ),
            (
                "Система распознавания лиц для проходной",
                "Использование компьютерного зрения для автоматизации доступа в корпуса университета.",
            ),
            (
                "Telegram-бот для абитуриентов",
                "Чат-бот с ответами на частые вопросы, интеграцией с базой знаний и навигацией по сайту.",
            ),
            (
                "Парсер вакансий для стажеров",
                "Написание скраперов на BeautifulSoup и Selenium, структурирование данных и вывод в удобный дашборд.",
            ),
        ],
        "Дизайн": [
            (
                "Редизайн интерфейса личного кабинета",
                "Анализ пользовательских путей, создание новых макетов в Figma и проведение юзабилити-тестирования.",
            ),
            (
                "Разработка фирменного стиля для студенческого клуба",
                "Создание логотипа, брендбука и макетов мерча для нового объединения.",
            ),
            (
                "UI/UX редизайн сайта вуза",
                "Обновление интерфейса и повышение конверсии. Создание прототипов и UI-kit.",
            ),
        ],
        "Мультимедиа": [
            (
                "Видеоподкаст о студенческой жизни",
                "Организация съемок, написание сценариев и монтаж видео для продвижения проектной деятельности.",
            ),
            (
                "Создание 3D-моделей для виртуального музея",
                "Оцифровка экспонатов и создание интерактивного тура по музею университета.",
            ),
            (
                "Анимационный ролик для Дня открытых дверей",
                "Разработка сценария, раскадровки и создание 2D-анимации.",
            ),
        ],
        "Технология": [
            (
                "Разработка прототипа умного дома",
                "Проектирование и сборка IoT-устройства для мониторинга микроклимата в аудиториях.",
            ),
            (
                "Инженерный расчет нового корпуса",
                "Использование CAD-систем для моделирования и расчета нагрузок на конструкции.",
            ),
            (
                "Система контроля доступа на базе Arduino",
                "Сборка макета, программирование контроллера и настройка RFID-считывателя.",
            ),
        ],
        "Транспорт": [
            (
                "Создание прототипа беспилотного ровера",
                "Сборка шасси, настройка сенсоров и программирование алгоритмов объезда препятствий.",
            ),
            (
                "Оптимизация логистики внутри кампуса",
                "Анализ перемещений студентов и разработка системы аренды самокатов.",
            ),
            (
                "Разработка системы мониторинга транспорта",
                "Создание GPS-трекера и веб-панели для отслеживания перемещений.",
            ),
        ],
        "Химбиотех": [
            (
                "Разработка биосенсора для контроля воды",
                "Создание лабораторного прототипа для быстрого анализа качества воды.",
            ),
            (
                "Моделирование химических процессов",
                "Использование Python для симуляции химических реакций и визуализации данных.",
            ),
        ],
        "Научные проекты": [
            (
                "Анализ больших данных в экологии",
                "Сбор и обработка датасетов по загрязнению воздуха, построение ML-моделей.",
            ),
            (
                "Исследование свойств новых материалов",
                "Компьютерное моделирование и лабораторные испытания прототипов.",
            ),
        ],
        "Соцтех": [
            (
                "Платформа для волонтерских проектов",
                "Создание сайта, где НКО могут находить волонтеров среди студентов.",
            ),
            (
                "Приложение для инклюзивного образования",
                "Разработка сервиса с аудио-описаниями для слабовидящих студентов.",
            ),
        ],
    }

    count = 0
    for i in range(40):
        theme = random.choice(theme_options)
        templates = project_pool.get(
            theme.name,
            [
                (
                    "Исследовательский проект в области {}",
                    "Выполнение научных исследований под руководством опытных наставников.",
                )
            ],
        )
        title_template, short_desc = random.choice(templates)
        title = (
            title_template.format(theme.name)
            if "{}" in title_template
            else title_template
        )
        long_desc = f"Цель проекта: {short_desc}\n\nВ рамках проекта студентам предстоит пройти полный цикл разработки: от анализа требований до защиты готового результата. Работа ведется в командах под руководством опытных наставников."

        project = Project.objects.create(
            title=title,
            short_description=short_desc,
            long_description=long_desc,
            theme=theme,
            campus=random.choice(campuses),
            difficulty=random.choice(diffs),
            partner=random.choice(partners),
            curator=random.choice(curators),
            shedule=random.choice(schedules),
            internship=random.choice([True, False]),
            spots_remaining=random.randint(1, 10),
            is_active=True,
        )

        # Привязываем РЕАЛЬНЫЕ специальности (объекты Specialty)
        project.specialties.set(random.sample(specialties, k=random.randint(1, 3)))
        project.courses.add(random.choice(courses))
        count += 1
    print("=== ДОБАВЛЕНИЕ ТЕХНОЛОГИЙ (через ProjectListItem) ===")
    tech_names = ["React", "TypeScript", "Python", "Django", "PostgreSQL", "Docker", "Figma", "C++", "Arduino", "Kotlin", "Swift", "Unity", "Unreal Engine"]
    
    all_projects = Project.objects.all()
    for proj in all_projects:
        # Выбираем от 2 до 5 случайных технологий для каждого проекта
        selected_techs = random.sample(tech_names, k=random.randint(2, 5))
        for tech in selected_techs:
            ProjectListItem.objects.create(
                project=proj,
                type='technology', # <--- Тот самый тип
                text=tech
            )
            
    # Добавим пару "задач" (tasks) в описание, чтобы блок "Что предстоит делать" не был пустым
    tasks_texts = ["Разработка интерфейсов", "Создание макетов", "Работа с API", "Тестирование", "Участие в командных встречах", "Защита результата"]
    for proj in all_projects:
        selected_tasks = random.sample(tasks_texts, k=random.randint(2, 4))
        for task in selected_tasks:
            ProjectListItem.objects.create(
                project=proj,
                type='tasks', # <--- Тип "Основные задачи"
                text=task
            )


    print("=== ГЕНЕРАЦИЯ ЗАДАЧ ДЛЯ БИРЖИ ===")
    task_cats = ["Frontend", "Backend", "Дизайн", "Аналитика", "Тестирование", "DevOps"]
    task_categories = [TaskCategory.objects.create(name=c) for c in task_cats]

    task_templates = [
        ("Разработка главной страницы", "Необходимо сверстать адаптивный интерфейс по макету в Figma."),
        ("Настройка базы данных", "Спроектировать ER-диаграмму и написать миграции для PostgreSQL."),
        ("Создание API эндпоинтов", "Разработать REST API на Django REST Framework для мобильного приложения."),
        ("Юзабилити-тестирование", "Провести тестирование прототипа, собрать обратную связь и составить отчет."),
        ("Настройка CI/CD", "Написать Dockerfile и настроить GitHub Actions для автоматической сборки."),
        ("Сборка макета устройства", "Спаять прототип на макетной плате и запрограммировать контроллер."),
        ("Анализ конкурентов", "Собрать данные о конкурентах и визуализировать их в виде графиков."),
        ("Написание документации", "Составить подробное руководство пользователя и API документацию."),
    ]

    task_count = 0
    for proj in all_projects[:15]:
        for _ in range(3):
            title, short_desc = random.choice(task_templates)
            
            task = Task.objects.create(
                project=proj,
                curator=proj.curator, 
                category=random.choice(task_categories),
                title=title,
                short_description=short_desc,
                description=f"Подробное описание задачи: {short_desc}\n\nТребования к исполнителю: ответственность, умение работать в команде.",
                difficulty=random.choice(Task.Difficulty.values),
                points=random.randint(5, 50),
                status=Task.Status.PUBLISHED, 
                required_people=random.randint(1, 3),
                deadline=timezone.now() + timezone.timedelta(days=random.randint(10, 60))
            )
            task_count += 1

    print(f"Создано задач для биржи: {task_count}")
    print(f"=== ГОТОВО! Сгенерировано проектов: {count} ===")
    print(f"Кураторы (пароль '123456'): создано {len(curators)} шт.")
    print(f"Студенты (пароль '123456'): создано {len(students)} шт.")


if __name__ == "__main__":
    run()
