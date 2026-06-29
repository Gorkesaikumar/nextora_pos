from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.employees"
    label = "employees"
    verbose_name = "Employee & HR Management"
