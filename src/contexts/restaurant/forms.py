from django import forms
from contexts.restaurant.models.layout import DiningTable

from contexts.employees.models import EmployeeProfile, EmployeeStatus

class DiningTableForm(forms.ModelForm):
    assigned_waiter_id = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assigned Waiter"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        waiter_choices = [('', '--- Unassigned ---')]
        waiters = EmployeeProfile.objects.filter(status=EmployeeStatus.ACTIVE)
        for w in waiters:
            name = w.user.full_name or w.user.email
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


from contexts.catalog.models.routing import Printer

class PrinterForm(forms.ModelForm):
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

