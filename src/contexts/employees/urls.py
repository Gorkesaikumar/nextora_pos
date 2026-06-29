from django.urls import path
from contexts.employees import views

app_name = "employees"

urlpatterns = [
    path("directory/", views.EmployeeListView.as_view(), name="employee_list"),
    path("directory/create/", views.EmployeeCreateView.as_view(), name="employee_create"),
    path("directory/<uuid:pk>/edit/", views.EmployeeUpdateView.as_view(), name="employee_update"),
    path("directory/<uuid:pk>/delete/", views.EmployeeDeleteView.as_view(), name="employee_delete"),
    path("directory/<uuid:pk>/status/", views.EmployeeToggleStatusView.as_view(), name="employee_toggle_status"),
    path("directory/<uuid:pk>/lock/", views.EmployeeToggleLockView.as_view(), name="employee_toggle_lock"),
    path("directory/<uuid:pk>/reset-password/", views.EmployeeResetPasswordView.as_view(), name="employee_reset_password"),
    
    path("roles/", views.RoleListView.as_view(), name="role_list"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role_create"),
    path("roles/<uuid:pk>/edit/", views.RoleUpdateView.as_view(), name="role_update"),
    path("roles/<uuid:pk>/delete/", views.RoleDeleteView.as_view(), name="role_delete"),
    path("roles/matrix/", views.RolePermissionMatrixView.as_view(), name="role_matrix"),
]
