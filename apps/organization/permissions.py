from functools import wraps
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


class IsStaff(IsAuthenticated):
    """Requires the user to have a StaffProfile (is a SalamaPay staff member)."""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return hasattr(request.user, 'staff_profile')


class IsSuperAdmin(IsAuthenticated):
    """Requires the user to be a Super Admin."""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        profile = getattr(request.user, 'staff_profile', None)
        if not profile:
            return False
        return profile.role.name == Role.Builtin.SUPER_ADMIN.value or profile.role.name == 'Super Admin'


def require_permission(*perm_codes):
    """
    Decorator for view methods that checks if the staff user has the required permission.
    Usage:
        @action(detail=True, methods=['post'])
        @require_permission('refunds.approve')
        def approve(self, request, pk=None):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            profile = getattr(request.user, 'staff_profile', None)
            if not profile:
                return Response(
                    {'detail': 'Staff access required.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if profile.status != 'ACTIVE':
                return Response(
                    {'detail': 'Your staff account is not active.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Super Admin bypasses all permission checks
            if profile.role.name == 'Super Admin' or profile.role.name == Role.Builtin.SUPER_ADMIN.value:
                return func(self, request, *args, **kwargs)
            for perm in perm_codes:
                if profile.has_permission(perm):
                    return func(self, request, *args, **kwargs)
            return Response(
                {'detail': f'Permission denied. Required: {", ".join(perm_codes)}'},
                status=status.HTTP_403_FORBIDDEN
            )
        return wrapper
    return decorator


class PermissionRequiredMixin:
    """
    Class-based view mixin that checks permissions based on `required_permissions` dict.
    Maps DRF actions to permission codes:
        required_permissions = {
            'list': 'users.view',
            'retrieve': 'users.view',
            'create': 'users.create',
            'update': 'users.update',
            'partial_update': 'users.update',
            'destroy': 'users.delete',
        }
    """
    required_permissions = {}

    def check_permissions(self, request):
        super().check_permissions(request)
        profile = getattr(request.user, 'staff_profile', None)
        if not profile:
            self.permission_denied(request, message='Staff access required.')
        if profile.status != 'ACTIVE':
            self.permission_denied(request, message='Your staff account is not active.')

        # Super Admin bypasses
        if profile.role.name == 'Super Admin' or profile.role.name == Role.Builtin.SUPER_ADMIN.value:
            return

        action = getattr(self, 'action', None)
        if not action:
            return

        required = self.required_permissions.get(action)
        if required:
            if isinstance(required, str):
                required = [required]
            for perm in required:
                if profile.has_permission(perm):
                    return
            self.permission_denied(
                request,
                message=f'Permission denied. Required: {", ".join(required)}'
            )


def log_audit(actor, action, module, description, target_type=None, target_id=None,
              old_values=None, new_values=None, request=None):
    """Helper to create an AuditLog entry."""
    from .models import AuditLog
    ip = None
    ua = None
    if request:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')

    AuditLog.objects.create(
        actor=actor,
        action=action,
        module=module,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        description=description,
        old_values=old_values or {},
        new_values=new_values or {},
        ip_address=ip,
        user_agent=ua,
    )


# Import here to avoid circular import at module load
from .models import Role  # noqa: E402
