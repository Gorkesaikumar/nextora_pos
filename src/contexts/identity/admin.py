"""Minimal admin for ops. Business workflows live in services, not admin."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Membership, Permission, Role, RolePermission, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-created_at"]
    list_display = ["email", "full_name", "is_active", "is_staff", "created_at"]
    search_fields = ["email", "full_name"]
    readonly_fields = ["created_at", "updated_at", "last_login", "last_login_ip"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",
                                    "groups", "user_permissions")}),
        ("Audit", {"fields": ("created_at", "updated_at", "last_login",
                              "last_login_ip")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2"),
        }),
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "module"]
    list_filter = ["module"]
    search_fields = ["code", "name"]


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ["permission"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "scope", "tenant", "is_system"]
    list_filter = ["scope", "is_system"]
    search_fields = ["code", "name"]
    inlines = [RolePermissionInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "tenant", "role", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["user__email"]
    autocomplete_fields = ["user", "role"]
