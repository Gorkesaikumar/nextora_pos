from django.contrib import admin

from .models import InAppNotification, Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "channel", "language", "is_active", "created_at"]
    list_filter = ["channel", "language", "is_active"]
    search_fields = ["name", "subject", "body_template"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "tenant", "channel", "recipient", "status", "sent_at", "retry_count"]
    list_filter = ["channel", "status"]
    search_fields = ["recipient", "external_id", "last_error"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ["user_id", "tenant", "title", "is_read", "read_at", "created_at"]
    list_filter = ["is_read"]
    search_fields = ["user_id", "title", "body"]
