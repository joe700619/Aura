from django.contrib.auth.models import AbstractUser
from django.db import models
from shared.constants import UserRole

class User(AbstractUser):
    """Custom user model for Aura ERP"""
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        help_text="User role in the system"
    )
    
    class Meta:
        db_table = 'auth_user'
