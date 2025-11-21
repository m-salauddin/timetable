from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
  
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'department', 'semester')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'department', 'semester')}),
    )
    list_display = ('username', 'email', 'role', 'department', 'semester')
    list_filter = ('role', 'department', 'semester')