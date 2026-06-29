from django.contrib import admin

from contexts.features.models import FeatureFlag, FeatureRule


class FeatureRuleInline(admin.TabularInline):
    model = FeatureRule
    extra = 0
    fields = ("priority", "rule_type", "target_value", "is_enabled")


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "default_state", "is_kill_switch", "created_at")
    list_filter = ("default_state", "is_kill_switch")
    search_fields = ("key", "name")
    inlines = [FeatureRuleInline]
    
    fieldsets = (
        (None, {
            "fields": ("key", "name", "description")
        }),
        ("State", {
            "fields": ("default_state", "is_kill_switch")
        }),
    )
