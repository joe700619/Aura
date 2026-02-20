from django.db import models

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    MANAGER = 'MANAGER', 'Manager'
    USER = 'USER', 'User'
    EXTERNAL = 'EXTERNAL', 'External'
