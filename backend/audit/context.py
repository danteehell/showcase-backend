from contextvars import ContextVar


_current_user = ContextVar("audit_current_user", default=None)
_audit_suspended = ContextVar("audit_suspended", default=False)


def get_current_user():
    return _current_user.get()


def set_current_user(user):
    return _current_user.set(user)


def reset_current_user(token):
    _current_user.reset(token)


def is_audit_suspended():
    return _audit_suspended.get()


def suspend_audit():
    return _audit_suspended.set(True)


def resume_audit(token):
    _audit_suspended.reset(token)
