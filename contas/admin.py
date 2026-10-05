from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # Acrescenta o campo "papel" ao admin padrão de usuário.
    fieldsets = UserAdmin.fieldsets + (("Papel no sistema", {"fields": ("papel",)}),)
    list_display = ("username", "first_name", "last_name", "papel", "is_staff")
    list_filter = UserAdmin.list_filter + ("papel",)
