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
    list_display = ('username', 'get_full_name', 'course', 'specialty', 'email')
    list_filter = ('course', 'specialty', 'is_active')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'middle_name', 'email')}),
        ('Учеба', {'fields': ('course', 'specialty')}),
        ('Права', {'fields': ('is_active', 'is_staff', 'role', 'keycloak_id')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='student')
# TODO: Закастомить отображение для остальных ролей как для студента
# TODO: В админке некрасиво отображается ФИО(Get full name), поправить на "ФИО" или еще чет
@admin.register(CuratorProxy)
class CuratorAdmin(CustomUserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='curator')

@admin.register(AdminProxy)
class AdminRoleAdmin(CustomUserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='admin')