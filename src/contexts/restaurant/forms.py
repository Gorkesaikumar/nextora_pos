from django import forms
from contexts.restaurant.models.layout import DiningTable

from contexts.employees.models import EmployeeProfile
from contexts.restaurant.models.branch import Branch

class DiningTableForm(forms.ModelForm):
    assigned_waiter_id = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assigned Waiter"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        waiter_choices = [('', '--- Unassigned ---')]
        waiters = EmployeeProfile.objects.filter(is_active=True)
        for w in waiters:
            name = w.user.get_full_name() or w.user.email
            waiter_choices.append((str(w.id), name))
        self.fields['assigned_waiter_id'].choices = waiter_choices
        
        if self.instance and self.instance.assigned_waiter_id:
            self.initial['assigned_waiter_id'] = str(self.instance.assigned_waiter_id)
            
    def clean_assigned_waiter_id(self):
        val = self.cleaned_data.get('assigned_waiter_id')
        if not val:
            return None
        return val
    
    class Meta:
        model = DiningTable
        fields = ['number', 'capacity', 'shape', 'assigned_waiter_id', 'status', 'position_x', 'position_y', 'rotation', 'is_active']
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., T12'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'shape': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'position_x': forms.NumberInput(attrs={'class': 'form-input'}),
            'position_y': forms.NumberInput(attrs={'class': 'form-input'}),
            'rotation': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'max': '359'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class BranchForm(forms.ModelForm):
    manager_id = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Branch Manager"
    )

    class Meta:
        model = Branch
        fields = [
            'name', 'code', 'status', 'address_line1', 'address_line2', 
            'city', 'state', 'pincode', 'country', 'phone', 'email', 
            'timezone', 'currency', 'latitude', 'longitude', 'manager_id', 
            'logo', 'is_default', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Downtown Branch'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'DT-01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-input'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-input'}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'state': forms.TextInput(attrs={'class': 'form-input'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input'}),
            'country': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'timezone': forms.TextInput(attrs={'class': 'form-input'}),
            'currency': forms.TextInput(attrs={'class': 'form-input'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        manager_choices = [('', '--- Unassigned ---')]
        employees = EmployeeProfile.objects.filter(is_active=True).select_related('user')
        for emp in employees:
            name = emp.user.get_full_name() or emp.user.email
            manager_choices.append((str(emp.user.id), name))
        self.fields['manager_id'].choices = manager_choices
        if self.instance and self.instance.manager_id:
            self.initial['manager_id'] = str(self.instance.manager_id)

    def clean_manager_id(self):
        val = self.cleaned_data.get('manager_id')
        if not val:
            return None
        import uuid
        return uuid.UUID(val)


from contexts.catalog.models.routing import Printer

class PrinterForm(forms.ModelForm):
    location_id = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Branch Assignment"
    )

    class Meta:
        model = Printer
        fields = [
            'name', 'code', 'kind', 'brand', 'model', 'connection_type',
            'ip_address', 'port', 'paper_width', 'is_default', 'status', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Kitchen Slip Printer'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'PRN-KIT-01'}),
            'kind': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-input'}),
            'model': forms.TextInput(attrs={'class': 'form-input'}),
            'connection_type': forms.Select(attrs={'class': 'form-select'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '192.168.1.100'}),
            'port': forms.NumberInput(attrs={'class': 'form-input'}),
            'paper_width': forms.Select(attrs={'class': 'form-select'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        branch_choices = [('', '--- Global / All Branches ---')]
        for b in Branch.objects.filter(is_active=True, is_deleted=False):
            branch_choices.append((str(b.id), b.name))
        self.fields['location_id'].choices = branch_choices
        if self.instance and self.instance.location_id:
            self.initial['location_id'] = str(self.instance.location_id)

    def clean_location_id(self):
        val = self.cleaned_data.get('location_id')
        if not val:
            return None
        import uuid
        return uuid.UUID(val)

