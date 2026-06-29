from django.urls import path

from .views import PrivateFileDownloadView

app_name = "storage"

urlpatterns = [
    path("private/<str:token>/", PrivateFileDownloadView.as_view(), name="private-download"),
]
