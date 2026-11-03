from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from .models import Task, TaskAssignment

MAX_REVISIONS = 3


def is_curator_of(user, task) -> bool:
    return task.curator_id == user.id


def check_student_matches(student, task) -> tuple[bool, str]:
    profile = getattr(student, "student_profile", None)
    if profile is None:
        return False, "У пользователя нет профиля студента"

    if task.required_course_min and profile.course < task.required_course_min:
        return False, f"Требуется курс не ниже {task.required_course_min}"
    if task.required_course_max and profile.course > task.required_course_max:
        return False, f"Требуется курс не выше {task.required_course_max}"
    if task.required_specialty and profile.specialty != task.required_specialty:
        return False, f"Требуется специальность «{task.required_specialty}»"

    return True, ""


def _require_student(assignment, user):
    if assignment.student_id != user.id:
        raise PermissionDenied("Это не ваша запись на задачу")


def _require_curator(assignment, user):
    if not is_curator_of(user, assignment.task):
        raise PermissionDenied("Только куратор задачи может выполнить это действие")


@transaction.atomic
def take_task(task_id: int, student) -> TaskAssignment:
    task = Task.objects.select_for_update().get(pk=task_id)

    if task.status != Task.Status.PUBLISHED:
        raise ValidationError("Задача недоступна для взятия")
    if task.filled_people >= task.required_people:
        raise ValidationError("Свободных мест нет")

    ok, reason = check_student_matches(student, task)
    if not ok:
        raise ValidationError(reason)

    Task.objects.filter(pk=task_id).update(filled_people=F("filled_people") + 1)
    task.refresh_from_db(fields=["filled_people", "required_people", "status"])

    assignment = TaskAssignment.objects.create(
        task=task,
        student=student,
        status=TaskAssignment.Status.TAKEN,
    )

    if (
        task.filled_people >= task.required_people
        and task.status == Task.Status.PUBLISHED
    ):
        task.transition_to(
            Task.Status.TAKEN,
            by=student,
            comment="Все места заняты",
        )

    return assignment


@transaction.atomic
def start_work(assignment_id: int, student) -> TaskAssignment:
    assignment = (
        TaskAssignment.objects.select_for_update()
        .select_related("task")
        .get(pk=assignment_id)
    )
    _require_student(assignment, student)

    assignment.transition_to(
        TaskAssignment.Status.IN_PROGRESS,
        by=student,
        comment="Студент приступил к работе",
    )

    task = assignment.task
    if task.status == Task.Status.TAKEN:
        task.transition_to(
            Task.Status.IN_PROGRESS,
            by=student,
            comment="Первый исполнитель приступил",
        )

    return assignment


@transaction.atomic
def submit_work(assignment_id: int, student) -> TaskAssignment:
    assignment = TaskAssignment.objects.select_for_update().get(pk=assignment_id)
    _require_student(assignment, student)
    return assignment.transition_to(
        TaskAssignment.Status.SUBMITTED,
        by=student,
        comment="Отправлено на проверку",
    )


@transaction.atomic
def return_for_revision(
    assignment_id: int, curator, comment: str = ""
) -> TaskAssignment:
    assignment = (
        TaskAssignment.objects.select_for_update()
        .select_related("task")
        .get(pk=assignment_id)
    )
    _require_curator(assignment, curator)

    if assignment.revision_count >= MAX_REVISIONS:
        raise ValidationError(f"Лимит возвратов исчерпан ({MAX_REVISIONS})")

    return assignment.transition_to(
        TaskAssignment.Status.RETURNED,
        by=curator,
        comment=comment,
    )


@transaction.atomic
def accept_work(assignment_id: int, curator) -> TaskAssignment:
    assignment = (
        TaskAssignment.objects.select_for_update()
        .select_related("task")
        .get(pk=assignment_id)
    )
    _require_curator(assignment, curator)

    assignment.transition_to(
        TaskAssignment.Status.COMPLETED,
        by=curator,
        comment="Работа принята",
    )

    task = assignment.task
    still_open = task.assignments.exclude(
        status__in=[
            TaskAssignment.Status.COMPLETED,
            TaskAssignment.Status.REMOVED_BY_CURATOR,
        ]
    ).exists()
    if not still_open and task.status in (Task.Status.IN_PROGRESS, Task.Status.TAKEN):
        task.transition_to(
            Task.Status.COMPLETED,
            by=curator,
            comment="Все исполнители приняты",
        )

    return assignment


@transaction.atomic
def remove_assignment_by_curator(
    assignment_id: int, curator, reason: str
) -> TaskAssignment:
    if not reason:
        raise ValidationError("Укажите причину снятия")

    assignment = (
        TaskAssignment.objects.select_for_update()
        .select_related("task")
        .get(pk=assignment_id)
    )
    _require_curator(assignment, curator)

    assignment.transition_to(
        TaskAssignment.Status.REMOVED_BY_CURATOR,
        by=curator,
        reason=reason,
        comment=reason,
    )

    Task.objects.filter(pk=assignment.task_id).update(
        filled_people=Greatest(F("filled_people") - 1, 0)
    )
    task = Task.objects.select_for_update().get(pk=assignment.task_id)

    if task.status == Task.Status.TAKEN:
        task.transition_to(
            Task.Status.PUBLISHED,
            by=curator,
            comment="Освободилось место после снятия",
        )
    elif task.status == Task.Status.IN_PROGRESS:
        has_active = task.assignments.filter(
            status__in=[
                TaskAssignment.Status.IN_PROGRESS,
                TaskAssignment.Status.SUBMITTED,
                TaskAssignment.Status.RETURNED,
            ]
        ).exists()
        if not has_active:
            task.transition_to(
                Task.Status.PUBLISHED,
                by=curator,
                comment="Не осталось работающих исполнителей",
            )

    return assignment


@transaction.atomic
def expire_outdated_tasks() -> int:
    now = timezone.now()
    count = 0
    for task in Task.objects.select_for_update().filter(
        status=Task.Status.PUBLISHED,
        deadline__lt=now,
    ):
        task.transition_to(
            Task.Status.EXPIRED,
            comment="Истёк срок",
        )
        count += 1
    return count
