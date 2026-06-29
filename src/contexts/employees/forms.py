from django import forms
from django.contrib.auth import get_user_model
from contexts.employees.models import EmployeeProfile
from contexts.identity.models.rbac import Role, Permission
from contexts.restaurant.models.branch import Branch

User = get_user_model()


class EmployeeForm(forms.ModelForm):
    # User account fields
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input'}))
    full_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-input'}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        required=False,
        help_text="Leave blank to keep existing password."
    )
    is_locked = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))
    
    # Membership assignments
    branches = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2', 'size': '5'}),
        label="Assigned Branches"
    )
    roles = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2', 'size': '5'}),
        label="Assigned Roles"
    )

    class Meta:
        model = EmployeeProfile
        fields = ['job_title', 'base_salary', 'hire_date', 'is_active']
        widgets = {
            'job_title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Cashier / Manager'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate branch choices
        self.fields['branches'].choices = [
            (str(b.id), b.name) for b in Branch.objects.filter(is_active=True, is_deleted=False)
        ]
        
        # Populate role choices
        self.fields['roles'].choices = [
            (str(r.id), r.name) for r in Role.objects.filter(models.Q(tenant__isnull=True) | models.Q(tenant=self.instance.tenant))
        ]
        
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.user.email
            self.fields['full_name'].initial = self.instance.user.full_name
            self.fields['is_locked'].initial = self.instance.user.is_locked
            
            # Load current memberships
            memberships = self.instance.user.memberships.filter(is_active=True)
            self.fields['branches'].initial = [str(m.location_id) for m in memberships if m.location_id]
            self.fields['roles'].initial = [str(m.role_id) for m in memberships]
            
            # If editing, password is not required
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True

    def save(self, commit=True):
        # We manually save user model first, then profile, then update memberships
        email = self.cleaned_data.get('email')
        full_name = self.cleaned_data.get('full_name')
        password = self.cleaned_data.get('password')
        is_locked = self.cleaned_data.get('is_locked')
        is_active = self.cleaned_data.get('is_active')
        
        if self.instance.pk:
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
                password=password,
                is_active=is_active,
                is_locked=is_locked
            )
            self.instance.user = user

        profile = super().save(commit=commit)
        
        # Update memberships
        from contexts.identity.models.rbac import Membership
        # Clear existing active memberships
        Membership.objects.filter(user=user, tenant=profile.tenant).update(is_active=False)
        
        selected_branches = self.cleaned_data.get('branches') or []
        selected_roles = self.cleaned_data.get('roles') or []
        
        # Bind user to roles and branches
        for role_id in selected_roles:
            role = Role.objects.get(id=role_id)
            if selected_branches:
                for br_id in selected_branches:
                    Membership.objects.update_or_create(
                        user=user,
                        tenant=profile.tenant,
                        role=role,
                        location_id=br_id,
                        defaults={'is_active': True}
                    )
            else:
                Membership.objects.update_or_create(
                    user=user,
                    tenant=profile.tenant,
                    role=role,
                    location_id=None,
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
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Custom Role Name'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'custom_role'}),
            'description': forms.Textarea(attrs={'class': 'form-input h-20', 'placeholder': 'Description...'}),
            'scope': forms.Select(attrs={'class': 'form-select'}),
        }
