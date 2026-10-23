from functools import wraps
from django.shortcuts import redirect


def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('staff_logged_in'):
            return redirect('manage:login')

        # Re-verify against the database on every request (not just at login)
        # so a deactivated/deleted staff account loses access immediately,
        # rather than keeping whatever access their session already had.
        from .models import StaffUser
        staff_id = request.session.get('staff_id')
        if not staff_id or not StaffUser.objects.filter(pk=staff_id, is_active=True).exists():
            for key in ['staff_logged_in', 'staff_id', 'staff_username', 'staff_role']:
                request.session.pop(key, None)
            return redirect('manage:login')

        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Like staff_required, but only for accounts with the 'admin' role."""
    @staff_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('staff_role') != 'admin':
            from django.contrib import messages
            messages.error(request, 'Only admins can do that.')
            return redirect('manage:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
