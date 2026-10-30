from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from .models import *

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'role', 
        'is_staff', 
        'is_active'
    )
    
    list_filter = (
        'role', 
        'is_staff', 
        'is_superuser', 
        'is_active'
    )
    
    search_fields = (
        'username', 
        'first_name', 
        'last_name', 
        'email'
    )
    
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Права в системе', {'fields': ('role', 'keycloak_id')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'email', 'first_name', 'last_name')}),
    )
# Показываем пользователей в админки, разделяя их по ролям на сайте
@admin.register(StudentProxy)
class StudentAdmin(CustomUserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='student')

@admin.register(CuratorProxy)
class CuratorAdmin(CustomUserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='curator')

@admin.register(AdminProxy)
class AdminRoleAdmin(CustomUserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='admin')