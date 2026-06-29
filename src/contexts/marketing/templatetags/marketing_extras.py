"""Template helpers for the onboarding wizard."""
from django import template

register = template.Library()


@register.simple_tag
def choices_for(form, field_name):
    """Return a Django form field's choices as an iterable of (value, label).

    Used by the wizard's _select.html partial so step templates can render
    ChoiceField options without hand-rolling each <option>.
    """
    field = form.fields.get(field_name)
    if field is None or not hasattr(field, "choices"):
        return []
    return list(field.choices)
