from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class PlatformAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form for the Super Admin platform.
    Ensures that only superusers can establish a session through this portal.
    """
    error_messages = {
        'invalid_login': (
            "Please enter a correct %(username)s and password. Note that both "
            "fields may be case-sensitive."
        ),
        'inactive': "This account is inactive.",
        'not_superuser': "This portal is restricted to Super Administrators.",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError(
                self.error_messages['not_superuser'],
                code='not_superuser',
            )
