from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin, StackedInline
from .models import *


class StudentProfileInline(StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Учебная информация (Студент)'
    extra = 0


class CuratorProfileInline(StackedInline):
    model = CuratorProfile
    can_delete = False
    verbose_name_plural = 'Рабочая информация (Куратор)'
    extra = 0


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = (
        'username', 
        'display_full_name', 
        'email', 
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
        'middle_name', 
        'email'
    )
    
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Права в системе', {'fields': ('role',)}),
        ('Личные данные', {'fields': ('middle_name',)}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'email', 'first_name', 'last_name', 'middle_name')}),
    )

    @admin.display(description="ФИО")
    def display_full_name(self, obj):
        return obj.get_full_name()
    
    def get_inlines(self, request, obj):
        return [StudentProfileInline, CuratorProfileInline]


@admin.register(StudentProxy)
class StudentAdmin(CustomUserAdmin):
    list_display = ('username', 'display_full_name', 'email', 'is_active')
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='student')
    
    def get_inlines(self, request, obj):
        return [StudentProfileInline]


@admin.register(CuratorProxy)
class CuratorAdmin(CustomUserAdmin):
    list_display = ('username', 'display_full_name', 'email', 'is_active')
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='curator')

    def get_inlines(self, request, obj):
        return [CuratorProfileInline]


@admin.register(AdminProxy)
class AdminRoleAdmin(CustomUserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='admin')