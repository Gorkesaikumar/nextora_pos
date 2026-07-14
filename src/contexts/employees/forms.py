from django import forms
from django.contrib.auth import get_user_model
from django.db import models
from contexts.employees.models import EmployeeProfile, Department, Designation, Shift, WeeklyOff, Attendance, LeaveRequest, SalaryPayout, PayoutComponent, EmployeeDocument
from contexts.identity.models.rbac import Role, Permission, Membership

User = get_user_model()


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'shift', 'date', 'check_in', 'check_out', 'break_start', 'break_end', 'status', 'is_late_entry', 'is_early_exit', 'is_manual', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'input'}),
            'shift': forms.Select(attrs={'class': 'input'}),
            'date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'check_in': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'check_out': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'break_start': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'break_end': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'input'}),
            'is_late_entry': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-neutral-300 text-brand-default focus:ring-brand-default'}),
            'is_early_exit': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-neutral-300 text-brand-default focus:ring-brand-default'}),
            'is_manual': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-neutral-300 text-brand-default focus:ring-brand-default'}),
            'notes': forms.Textarea(attrs={'class': 'input', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        tenant_id = kwargs.pop('tenant_id', None)
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields['employee'].queryset = EmployeeProfile.objects.filter(tenant_id=tenant_id)
            self.fields['shift'].queryset = Shift.objects.filter(tenant_id=tenant_id)


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason', 'status', 'rejection_reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'input'}),
            'leave_type': forms.Select(attrs={'class': 'input'}),
            'start_date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'input'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'input', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        tenant_id = kwargs.pop('tenant_id', None)
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields['employee'].queryset = EmployeeProfile.objects.filter(tenant_id=tenant_id)


class SalaryPayoutForm(forms.ModelForm):
    class Meta:
        model = SalaryPayout
        fields = ['employee', 'period_start', 'period_end', 'base_amount', 'total_earnings', 'total_deductions', 'net_payable', 'status', 'paid_at', 'payment_reference', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'input'}),
            'period_start': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'period_end': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'base_amount': forms.NumberInput(attrs={'class': 'input'}),
            'total_earnings': forms.NumberInput(attrs={'class': 'input'}),
            'total_deductions': forms.NumberInput(attrs={'class': 'input'}),
            'net_payable': forms.NumberInput(attrs={'class': 'input'}),
            'status': forms.Select(attrs={'class': 'input'}),
            'paid_at': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'payment_reference': forms.TextInput(attrs={'class': 'input'}),
            'notes': forms.Textarea(attrs={'class': 'input', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        tenant_id = kwargs.pop('tenant_id', None)
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields['employee'].queryset = EmployeeProfile.objects.filter(tenant_id=tenant_id)


class EmployeeDocumentForm(forms.ModelForm):
    class Meta:
        model = EmployeeDocument
        fields = ['employee', 'document_type', 'title', 'file', 'expiry_date']
        widgets = {
            'employee': forms.Select(attrs={'class': 'input'}),
            'document_type': forms.Select(attrs={'class': 'input'}),
            'title': forms.TextInput(attrs={'class': 'input'}),
            'file': forms.FileInput(attrs={'class': 'form-input file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100'}),
            'expiry_date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        tenant_id = kwargs.pop('tenant_id', None)
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields['employee'].queryset = EmployeeProfile.objects.filter(tenant_id=tenant_id)


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['name', 'start_time', 'end_time', 'grace_period_minutes', 'break_time_minutes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input'}),
            'start_time': forms.TimeInput(attrs={'class': 'input', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'input', 'type': 'time'}),
            'grace_period_minutes': forms.NumberInput(attrs={'class': 'input'}),
            'break_time_minutes': forms.NumberInput(attrs={'class': 'input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-neutral-300 text-brand-default focus:ring-brand-default'}),
        }


class WeeklyOffForm(forms.ModelForm):
    class Meta:
        model = WeeklyOff
        fields = ['department', 'employee', 'day_of_week', 'is_alternate']
        widgets = {
            'department': forms.Select(attrs={'class': 'input'}),
            'employee': forms.Select(attrs={'class': 'input'}),
            'day_of_week': forms.Select(attrs={'class': 'input'}),
            'is_alternate': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-neutral-300 text-brand-default focus:ring-brand-default'}),
        }
        
    def __init__(self, *args, **kwargs):
        tenant_id = kwargs.pop('tenant_id', None)
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields['department'].queryset = Department.objects.filter(tenant_id=tenant_id)
            self.fields['employee'].queryset = EmployeeProfile.objects.filter(tenant_id=tenant_id)


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Kitchen Staff'}),
            'description': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
        }


class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = ['department', 'name', 'description']
        widgets = {
            'department': forms.Select(attrs={'class': 'input'}),
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Head Chef'}),
            'description': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        tenant_id = kwargs.pop('tenant_id', None)
        super().__init__(*args, **kwargs)
        if tenant_id:
            self.fields['department'].queryset = Department.objects.filter(tenant_id=tenant_id)


class EmployeeForm(forms.ModelForm):
    # User account fields
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input'}), required=False, help_text="Required if assigning roles.")
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input'}),
        required=False,
        help_text="Leave blank to keep existing password."
    )
    is_locked = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))
    
    # Membership assignments
    roles = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select w-full select2', 'size': '5'}),
        label="Assigned Roles"
    )

    class Meta:
        model = EmployeeProfile
        fields = ['first_name', 'last_name', 'employee_code', 'department', 'designation', 'status', 'employment_type', 'salary_type', 'base_salary', 'hourly_rate', 'hire_date']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input'}),
            'last_name': forms.TextInput(attrs={'class': 'input'}),
            'employee_code': forms.TextInput(attrs={'class': 'input'}),
            'department': forms.Select(attrs={'class': 'select'}),
            'designation': forms.Select(attrs={'class': 'select'}),
            'status': forms.Select(attrs={'class': 'select'}),
            'employment_type': forms.Select(attrs={'class': 'select'}),
            'salary_type': forms.Select(attrs={'class': 'select'}),
            'base_salary': forms.NumberInput(attrs={'class': 'input', 'step': '0.01'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'input', 'step': '0.01'}),
            'hire_date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate role choices
        if hasattr(self.instance, 'tenant'):
            self.fields['roles'].choices = [
                (str(r.id), r.name) for r in Role.objects.filter(models.Q(tenant__isnull=True) | models.Q(tenant=self.instance.tenant))
            ]
        else:
            self.fields['roles'].choices = [
                (str(r.id), r.name) for r in Role.objects.filter(models.Q(tenant__isnull=True))
            ]
        
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['is_locked'].initial = self.instance.user.is_locked
            
            # Load current memberships
            memberships = self.instance.user.memberships.filter(is_active=True)
            self.fields['roles'].initial = [str(m.role_id) for m in memberships]
            
            # If editing, password is not required
            self.fields['password'].required = False
        else:
            self.fields['password'].required = False

    def save(self, commit=True):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        is_locked = self.cleaned_data.get('is_locked')
        status = self.cleaned_data.get('status')
        is_active = status == 'active'
        full_name = f"{self.cleaned_data.get('first_name')} {self.cleaned_data.get('last_name')}".strip()
        
        user = None
        if email:
            if self.instance.pk and self.instance.user:
                user = self.instance.user
                user.email = email
                user.full_name = full_name
                user.is_locked = is_locked
                user.is_active = is_active
                if password:
                    user.set_password(password)
                user.save()
            else:
                user = User.objects.create_user(
                    email=email,
                    full_name=full_name,
                    password=password if password else User.objects.make_random_password(),
                    is_active=is_active,
                    is_locked=is_locked
                )
            self.instance.user = user

        profile = super().save(commit=commit)
        
        # Update memberships
        if user:
            from contexts.identity.models.rbac import Membership
            # Clear existing active memberships
            Membership.objects.filter(user=user, tenant=profile.tenant).update(is_active=False)
            
            selected_roles = self.cleaned_data.get('roles') or []
            
            # Bind user to roles
            for role_id in selected_roles:
                role = Role.objects.get(id=role_id)
                Membership.objects.update_or_create(
                    user=user,
                    tenant=profile.tenant,
                    role=role,
                    defaults={'is_active': True}
                )
                
        return profile


class RoleForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox'}),
        required=False,
        label="Grants / Permissions"
    )

    class Meta:
        model = Role
        fields = ['name', 'code', 'description', 'scope', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Custom Role Name'}),
            'code': forms.TextInput(attrs={'class': 'input', 'placeholder': 'custom_role'}),
            'description': forms.Textarea(attrs={'class': 'form-input h-20', 'placeholder': 'Description...'}),
            'scope': forms.Select(attrs={'class': 'select'}),
        }
