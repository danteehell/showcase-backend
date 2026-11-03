from rest_framework.permissions import BasePermission

from .models import TaskAssignment


def is_curator_of(user, task):
    return task.curator_id == user.id


def available_actions(assignment, user):

    s = TaskAssignment.Status
    actions = []

    if user.id == assignment.student_id:
        if assignment.status == s.TAKEN:
            actions.append("start")
        if assignment.status in (s.IN_PROGRESS, s.RETURNED):
            actions.append("submit")

    elif is_curator_of(user, assignment.task):
        if assignment.status == s.SUBMITTED:
            if assignment.revisions_left > 0:
                actions.append("return")
            actions.append("accept")
        if assignment.status not in (s.COMPLETED, s.REMOVED_BY_CURATOR):
            actions.append("remove")

    return actions


class IsStudentOrCuratorOfAssignment(BasePermission):
    message = "Нет доступа к этой записи"

    def has_object_permission(self, request, view, obj):
        return request.user.id == obj.student_id or is_curator_of(
            request.user, obj.task
        )
