from django.urls import path
from . import views
from .register_views import RegisterCompleteView, RegisterView

app_name = "marketing"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("register/", RegisterView.as_view(), name="register"),
    path("register/complete/", RegisterCompleteView.as_view(), name="register_complete"),
]
