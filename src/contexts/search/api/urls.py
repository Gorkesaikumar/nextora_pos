from django.urls import path

from .views import UniversalSearchView

app_name = "search"

urlpatterns = [
    path("", UniversalSearchView.as_view(), name="universal-search"),
]
