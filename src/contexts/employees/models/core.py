from django.conf import settings
from django.db import models
from shared.tenancy.models import TenantAwareModel


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", "Full Time"
    PART_TIME = "part_time", "Part Time"
    CONTRACT = "contract", "Contract"
    INTERN = "intern", "Intern"


class SalaryType(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    HOURLY = "hourly", "Hourly"
    DAILY = "daily", "Daily Wage"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class EmployeeStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ON_LEAVE = "on_leave", "On Leave"
    SUSPENDED = "suspended", "Suspended"
    TERMINATED = "terminated", "Terminated"
    RESIGNED = "resigned", "Resigned"


class Department(TenantAwareModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_department"

    def __str__(self) -> str:
        return self.name


class Designation(TenantAwareModel):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="designations")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_designation"

    def __str__(self) -> str:
        return self.name


class EmployeeProfile(TenantAwareModel):
    # Core Details
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_profiles"
    )
    employee_code = models.CharField(max_length=50, blank=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_photo = models.ImageField(upload_to="employees/photos/", null=True, blank=True)
    
    # Personal Info
    mobile_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Employment Info
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    hire_date = models.DateField()
    status = models.CharField(max_length=20, choices=EmployeeStatus.choices, default=EmployeeStatus.ACTIVE)
    notes = models.TextField(blank=True)

    # Financial & KYC Info
    salary_type = models.CharField(max_length=20, choices=SalaryType.choices, default=SalaryType.MONTHLY)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Monthly salary or flat base")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="For hourly/daily employees")
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    upi_id = models.CharField(max_length=100, blank=True)
    aadhaar_number = models.CharField(max_length=20, blank=True)
    pan_number = models.CharField(max_length=20, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"],
                name="uq_employee_profile__tenant_user",
                condition=models.Q(user__isnull=False),
            )
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        code = f" [{self.employee_code}]" if self.employee_code else ""
        return f"{self.full_name}{code}"


class DocumentType(models.TextChoices):
    RESUME = "resume", "Resume"
    JOINING_LETTER = "joining_letter", "Joining Letter"
    ID_PROOF = "id_proof", "Identity Proof"
    CERTIFICATE = "certificate", "Certificate"
    BANK_DOCUMENT = "bank", "Bank Document"
    MEDICAL = "medical", "Medical Document"
    OTHER = "other", "Other"


class EmployeeDocument(TenantAwareModel):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to="employees/documents/")
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_document"

    def __str__(self) -> str:
        return f"{self.employee.full_name} - {self.title}"
