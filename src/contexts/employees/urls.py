from django.urls import path
from contexts.employees import views

app_name = "employees"

urlpatterns = [
    path("directory/", views.EmployeeListView.as_view(), name="employee_list"),
    path("<uuid:tenant_id>/directory/", views.EmployeeListView.as_view(), name="employee_list_tenant"),
    path("directory/create/", views.EmployeeCreateView.as_view(), name="employee_create"),
    path("<uuid:tenant_id>/directory/create/", views.EmployeeCreateView.as_view(), name="employee_create_tenant"),
    path("directory/<uuid:pk>/edit/", views.EmployeeUpdateView.as_view(), name="employee_update"),
    path("<uuid:tenant_id>/directory/<uuid:pk>/edit/", views.EmployeeUpdateView.as_view(), name="employee_update_tenant"),
    path("directory/<uuid:pk>/delete/", views.EmployeeDeleteView.as_view(), name="employee_delete"),
    path("<uuid:tenant_id>/directory/<uuid:pk>/delete/", views.EmployeeDeleteView.as_view(), name="employee_delete_tenant"),
    path("directory/<uuid:pk>/status/", views.EmployeeToggleStatusView.as_view(), name="employee_toggle_status"),
    path("<uuid:tenant_id>/directory/<uuid:pk>/status/", views.EmployeeToggleStatusView.as_view(), name="employee_toggle_status_tenant"),
    path("directory/<uuid:pk>/lock/", views.EmployeeToggleLockView.as_view(), name="employee_toggle_lock"),
    path("<uuid:tenant_id>/directory/<uuid:pk>/lock/", views.EmployeeToggleLockView.as_view(), name="employee_toggle_lock_tenant"),
    path("directory/<uuid:pk>/reset-password/", views.EmployeeResetPasswordView.as_view(), name="employee_reset_password"),
    path("<uuid:tenant_id>/directory/<uuid:pk>/reset-password/", views.EmployeeResetPasswordView.as_view(), name="employee_reset_password_tenant"),
    
    path("roles/", views.RoleListView.as_view(), name="role_list"),
    path("<uuid:tenant_id>/roles/", views.RoleListView.as_view(), name="role_list_tenant"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role_create"),
    path("<uuid:tenant_id>/roles/create/", views.RoleCreateView.as_view(), name="role_create_tenant"),
    path("roles/<uuid:pk>/edit/", views.RoleUpdateView.as_view(), name="role_update"),
    path("<uuid:tenant_id>/roles/<uuid:pk>/edit/", views.RoleUpdateView.as_view(), name="role_update_tenant"),
    path("roles/<uuid:pk>/delete/", views.RoleDeleteView.as_view(), name="role_delete"),
    path("<uuid:tenant_id>/roles/<uuid:pk>/delete/", views.RoleDeleteView.as_view(), name="role_delete_tenant"),
    path("roles/matrix/", views.RolePermissionMatrixView.as_view(), name="role_matrix"),
    path("<uuid:tenant_id>/roles/matrix/", views.RolePermissionMatrixView.as_view(), name="role_matrix_tenant"),
]
