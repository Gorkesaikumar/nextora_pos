from django.urls import path
from contexts.identity import views

from django.views.generic import TemplateView

app_name = "identity"

urlpatterns = [
    path("login/", views.IdentityLoginView.as_view(), name="login"),
    path("logout/", views.IdentityLogoutView.as_view(), name="logout"),
    path("password-reset/", TemplateView.as_view(template_name="identity/password_reset.html"), name="password_reset"),
]
