from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class StaffUser(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_STAFF = 'staff'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_STAFF, 'Staff'),
    ]

    username = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    total_logins = models.IntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return f"@{self.username} ({self.role})"
