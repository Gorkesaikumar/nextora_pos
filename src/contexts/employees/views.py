import datetime
from django.utils import timezone
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.db import models
from django.contrib.auth import get_user_model

from contexts.employees.models import (
    EmployeeProfile, 
    Department, 
    Designation,
    Shift,
    WeeklyOff,
    Attendance, 
    AttendanceStatus, 
    LeaveRequest, 
    LeaveStatus,
    SalaryPayout,
    PayoutStatus,
    EmployeeDocument
)
from contexts.employees.forms import (
    EmployeeForm, RoleForm, DepartmentForm, DesignationForm, 
    ShiftForm, WeeklyOffForm, AttendanceForm, LeaveRequestForm,
    SalaryPayoutForm, EmployeeDocumentForm
)
from contexts.identity.models.rbac import Role, Permission, Membership

User = get_user_model()

class HRMSDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "employees/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        current_month = today.replace(day=1)
        
        # Core Metrics
        context['total_employees'] = EmployeeProfile.objects.filter(status='active').count()
        context['departments_count'] = Department.objects.count()
        
        # Attendance today
        present_count = Attendance.objects.filter(date=today, status=AttendanceStatus.PRESENT).count()
        late_count = Attendance.objects.filter(date=today, status=AttendanceStatus.LATE).count()
        context['on_duty_today'] = present_count + late_count
        context['late_today'] = late_count
        context['absent_today'] = Attendance.objects.filter(date=today, status=AttendanceStatus.ABSENT).count()
        
        # Leaves
        context['pending_leaves'] = LeaveRequest.objects.filter(status__in=[LeaveStatus.PENDING_MANAGER, LeaveStatus.PENDING_OWNER]).count()
        
        # Payroll
        pending_payouts = SalaryPayout.objects.filter(status=PayoutStatus.PENDING)
        context['pending_payroll_amount'] = pending_payouts.aggregate(
            total=models.Sum('net_payable')
        )['total'] or 0
        
        # Upcoming Birthdays (next 30 days)
        # Note: handling month wrap-around is complex in SQL, we'll do a simple list here for demo
        profiles = EmployeeProfile.objects.filter(status='active', date_of_birth__isnull=False)
        upcoming_bdays = []
        for p in profiles:
            if p.date_of_birth:
                # Replace year with current year to see if it's upcoming
                try:
                    this_year_bday = p.date_of_birth.replace(year=today.year)
                except ValueError:
                    this_year_bday = p.date_of_birth.replace(year=today.year, day=28) # Leap year fallback
                days_until = (this_year_bday - today).days
                if 0 <= days_until <= 30:
                    upcoming_bdays.append((p, days_until))
        
        upcoming_bdays.sort(key=lambda x: x[1])
        context['upcoming_birthdays'] = [b[0] for b in upcoming_bdays[:5]]

        return context


class EmployeeListView(LoginRequiredMixin, ListView):
    model = EmployeeProfile
    template_name = "employees/employee_list.html"
    context_object_name = "employees"
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('user', 'department', 'designation')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                models.Q(user__email__icontains=q) | 
                models.Q(user__full_name__icontains=q) |
                models.Q(job_title__icontains=q)
            )
        role_filter = self.request.GET.get('role')
        if role_filter:
            qs = qs.filter(user__memberships__role_id=role_filter, user__memberships__is_active=True).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_profiles = list(self.get_queryset())
        
        # User Dashboard Counts
        total_users = len(all_profiles)
        active_users = sum(1 for p in all_profiles if p.is_active and not p.user.is_locked)
        inactive_users = sum(1 for p in all_profiles if not p.is_active)
        locked_users = sum(1 for p in all_profiles if p.user.is_locked)
        
        context.update({
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'locked_users': locked_users,
            'roles_list': Role.objects.filter(models.Q(tenant__isnull=True) | models.Q(tenant_id=self.request.tenant_id)),
        })
        return context


class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = EmployeeProfile
    form_class = EmployeeForm
    template_name = "employees/partials/employee_form_modal.html"
    success_url = reverse_lazy('employees:employee_list')

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'employeeListChanged'})
        return response


class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = EmployeeProfile
    form_class = EmployeeForm
    template_name = "employees/partials/employee_form_modal.html"
    success_url = reverse_lazy('employees:employee_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'employeeListChanged'})
        return response


class EmployeeDeleteView(LoginRequiredMixin, DeleteView):
    model = EmployeeProfile
    success_url = reverse_lazy('employees:employee_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = self.object.user
        self.object.is_deleted = True
        self.object.is_active = False
        self.object.save()
        user.is_active = False
        user.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'employeeListChanged'})
        return HttpResponseRedirect(self.get_success_url())


class EmployeeToggleStatusView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(EmployeeProfile, id=pk)
        emp.is_active = not emp.is_active
        emp.save()
        user = emp.user
        user.is_active = emp.is_active
        user.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'employeeListChanged'})
        return HttpResponseRedirect(reverse_lazy('employees:employee_list'))


class EmployeeToggleLockView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(EmployeeProfile, id=pk)
        user = emp.user
        user.is_locked = not user.is_locked
        user.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'employeeListChanged'})
        return HttpResponseRedirect(reverse_lazy('employees:employee_list'))


class EmployeeResetPasswordView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(EmployeeProfile, id=pk)
        return render(request, "employees/partials/reset_password_modal.html", {"employee": emp})

    def post(self, request, pk, *args, **kwargs):
        emp = get_object_or_404(EmployeeProfile, id=pk)
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password and password == confirm_password:
            emp.user.set_password(password)
            emp.user.save()
            if request.htmx:
                return HttpResponse(status=204, headers={'HX-Trigger': 'employeeListChanged'})
            return HttpResponseRedirect(reverse_lazy('employees:employee_list'))
        else:
            return render(request, "employees/partials/reset_password_modal.html", {
                "employee": emp,
                "error": "Passwords do not match!"
            })


class RoleListView(LoginRequiredMixin, ListView):
    model = Role
    template_name = "employees/role_list.html"
    context_object_name = "roles"

    def get_queryset(self):
        return super().get_queryset().filter(
            models.Q(tenant_id=self.request.tenant_id) | models.Q(tenant__isnull=True)
        ).prefetch_related('permissions')


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = "employees/partials/role_form_modal.html"
    success_url = reverse_lazy('employees:role_list')

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'roleListChanged'})
        return response


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = "employees/partials/role_form_modal.html"
    success_url = reverse_lazy('employees:role_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'roleListChanged'})
        return response


class RoleDeleteView(LoginRequiredMixin, DeleteView):
    model = Role
    success_url = reverse_lazy('employees:role_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_system:
            return HttpResponse(status=403, content="System roles cannot be deleted.")
        self.object.delete()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'roleListChanged'})
        return HttpResponseRedirect(self.get_success_url())


class RolePermissionMatrixView(LoginRequiredMixin, TemplateView):
    template_name = "employees/role_matrix.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        roles = list(Role.objects.filter(
            models.Q(tenant_id=self.request.tenant_id) | models.Q(tenant__isnull=True)
        ).prefetch_related('permissions'))
        
        permissions = list(Permission.objects.all().order_by('module', 'code'))
        
        matrix = []
        for p in permissions:
            row = {
                'permission': p,
                'role_grants': []
            }
            for r in roles:
                row['role_grants'].append({
                    'role_id': str(r.id),
                    'granted': p in r.permissions.all(),
                    'is_system': r.is_system
                })
            matrix.append(row)
            
        context.update({
            'roles': roles,
            'matrix': matrix,
        })
        return context

    def post(self, request, *args, **kwargs):
        role_id = request.POST.get('role_id')
        permission_id = request.POST.get('permission_id')
        granted = request.POST.get('granted') == 'true'
        
        role = get_object_or_404(Role, id=role_id)
        if role.is_system:
            return HttpResponse(status=403, content="Cannot modify system roles.")
            
        permission = get_object_or_404(Permission, id=permission_id)
        
        if granted:
            role.permissions.add(permission)
        else:
            role.permissions.remove(permission)
            
        return HttpResponse(status=200)

# -----------------------------------------------------------------------------
# Departments
# -----------------------------------------------------------------------------

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = "employees/department_list.html"
    context_object_name = "departments"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id)


class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = "employees/partials/department_form_modal.html"
    success_url = reverse_lazy('employees:department_list')

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'departmentListChanged'})
        return response


class DepartmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = "employees/partials/department_form_modal.html"
    success_url = reverse_lazy('employees:department_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'departmentListChanged'})
        return response


class DepartmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Department
    success_url = reverse_lazy('employees:department_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'departmentListChanged'})
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# Designations
# -----------------------------------------------------------------------------

class DesignationListView(LoginRequiredMixin, ListView):
    model = Designation
    template_name = "employees/designation_list.html"
    context_object_name = "designations"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id).select_related('department')


class DesignationCreateView(LoginRequiredMixin, CreateView):
    model = Designation
    form_class = DesignationForm
    template_name = "employees/partials/designation_form_modal.html"
    success_url = reverse_lazy('employees:designation_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'designationListChanged'})
        return response


class DesignationUpdateView(LoginRequiredMixin, UpdateView):
    model = Designation
    form_class = DesignationForm
    template_name = "employees/partials/designation_form_modal.html"
    success_url = reverse_lazy('employees:designation_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'designationListChanged'})
        return response


class DesignationDeleteView(LoginRequiredMixin, DeleteView):
    model = Designation
    success_url = reverse_lazy('employees:designation_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# Shifts
# -----------------------------------------------------------------------------

class ShiftListView(LoginRequiredMixin, ListView):
    model = Shift
    template_name = "employees/shift_list.html"
    context_object_name = "shifts"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id)


class ShiftCreateView(LoginRequiredMixin, CreateView):
    model = Shift
    form_class = ShiftForm
    template_name = "employees/partials/shift_form_modal.html"
    success_url = reverse_lazy('employees:shift_list')

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'shiftListChanged'})
        return response


class ShiftUpdateView(LoginRequiredMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    template_name = "employees/partials/shift_form_modal.html"
    success_url = reverse_lazy('employees:shift_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'shiftListChanged'})
        return response


class ShiftDeleteView(LoginRequiredMixin, DeleteView):
    model = Shift
    success_url = reverse_lazy('employees:shift_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'shiftListChanged'})
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# Weekly Offs
# -----------------------------------------------------------------------------

class WeeklyOffListView(LoginRequiredMixin, ListView):
    model = WeeklyOff
    template_name = "employees/weeklyoff_list.html"
    context_object_name = "weekly_offs"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id).select_related('department', 'employee')


class WeeklyOffCreateView(LoginRequiredMixin, CreateView):
    model = WeeklyOff
    form_class = WeeklyOffForm
    template_name = "employees/partials/weeklyoff_form_modal.html"
    success_url = reverse_lazy('employees:weeklyoff_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'weeklyOffListChanged'})
        return response


class WeeklyOffUpdateView(LoginRequiredMixin, UpdateView):
    model = WeeklyOff
    form_class = WeeklyOffForm
    template_name = "employees/partials/weeklyoff_form_modal.html"
    success_url = reverse_lazy('employees:weeklyoff_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'weeklyOffListChanged'})
        return response


class WeeklyOffDeleteView(LoginRequiredMixin, DeleteView):
    model = WeeklyOff
    success_url = reverse_lazy('employees:weeklyoff_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# Attendance Logs
# -----------------------------------------------------------------------------

class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = "employees/attendance_list.html"
    context_object_name = "attendance_logs"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id).select_related('employee', 'shift').order_by('-date', '-check_in')


class AttendanceCreateView(LoginRequiredMixin, CreateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = "employees/partials/attendance_form_modal.html"
    success_url = reverse_lazy('employees:attendance_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'attendanceListChanged'})
        return response


class AttendanceUpdateView(LoginRequiredMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = "employees/partials/attendance_form_modal.html"
    success_url = reverse_lazy('employees:attendance_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'attendanceListChanged'})
        return response


class AttendanceDeleteView(LoginRequiredMixin, DeleteView):
    model = Attendance
    success_url = reverse_lazy('employees:attendance_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'attendanceListChanged'})
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# Leave Requests
# -----------------------------------------------------------------------------

class LeaveRequestListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = "employees/leave_list.html"
    context_object_name = "leave_requests"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id).select_related('employee').order_by('-created_at')


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = "employees/partials/leave_form_modal.html"
    success_url = reverse_lazy('employees:leave_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'leaveListChanged'})
        return response


class LeaveRequestUpdateView(LoginRequiredMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = "employees/partials/leave_form_modal.html"
    success_url = reverse_lazy('employees:leave_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Send notification if status changed
        if 'status' in form.changed_data:
            from contexts.notifications.services import create_in_app_notification
            employee = form.instance.employee
            if employee.user_id:
                create_in_app_notification(
                    tenant_id=self.request.tenant_id,
                    user_id=employee.user_id,
                    title="Leave Request Update",
                    body_template=f"Your leave request from {form.instance.start_date} to {form.instance.end_date} is now {form.instance.get_status_display()}.",
                    context_data={}
                )

        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'leaveListChanged'})
        return response


class LeaveRequestDeleteView(LoginRequiredMixin, DeleteView):
    model = LeaveRequest
    success_url = reverse_lazy('employees:leave_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# Payroll Processing & Payouts
# -----------------------------------------------------------------------------

class SalaryPayoutListView(LoginRequiredMixin, ListView):
    model = SalaryPayout
    template_name = "employees/payroll_list.html"
    context_object_name = "payouts"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id).select_related('employee').order_by('-period_start')


class SalaryPayoutCreateView(LoginRequiredMixin, CreateView):
    model = SalaryPayout
    form_class = SalaryPayoutForm
    template_name = "employees/partials/payroll_form_modal.html"
    success_url = reverse_lazy('employees:payroll_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        
        # Send notification if status is PAID
        if form.instance.status == PayoutStatus.PAID:
            from contexts.notifications.services import create_in_app_notification
            employee = form.instance.employee
            if employee.user_id:
                create_in_app_notification(
                    tenant_id=self.request.tenant_id,
                    user_id=employee.user_id,
                    title="Salary Payout Processed",
                    body_template=f"Your salary for {form.instance.period_start} to {form.instance.period_end} has been processed. Net Payable: ${form.instance.net_payable}.",
                    context_data={}
                )

        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'payrollListChanged'})
        return response


class SalaryPayoutUpdateView(LoginRequiredMixin, UpdateView):
    model = SalaryPayout
    form_class = SalaryPayoutForm
    template_name = "employees/partials/payroll_form_modal.html"
    success_url = reverse_lazy('employees:payroll_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Send notification if status changed to PAID
        if 'status' in form.changed_data and form.instance.status == PayoutStatus.PAID:
            from contexts.notifications.services import create_in_app_notification
            employee = form.instance.employee
            if employee.user_id:
                create_in_app_notification(
                    tenant_id=self.request.tenant_id,
                    user_id=employee.user_id,
                    title="Salary Payout Processed",
                    body_template=f"Your salary for {form.instance.period_start} to {form.instance.period_end} has been processed. Net Payable: ${form.instance.net_payable}.",
                    context_data={}
                )

        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'payrollListChanged'})
        return response


class SalaryPayoutDeleteView(LoginRequiredMixin, DeleteView):
    model = SalaryPayout
    success_url = reverse_lazy('employees:payroll_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# Staff Documents
# -----------------------------------------------------------------------------

class EmployeeDocumentListView(LoginRequiredMixin, ListView):
    model = EmployeeDocument
    template_name = "employees/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=self.request.tenant_id).select_related('employee').order_by('-uploaded_at')


class EmployeeDocumentCreateView(LoginRequiredMixin, CreateView):
    model = EmployeeDocument
    form_class = EmployeeDocumentForm
    template_name = "employees/partials/document_form_modal.html"
    success_url = reverse_lazy('employees:document_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'documentListChanged'})
        return response


class EmployeeDocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = EmployeeDocument
    form_class = EmployeeDocumentForm
    template_name = "employees/partials/document_form_modal.html"
    success_url = reverse_lazy('employees:document_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'documentListChanged'})
        return response


class EmployeeDocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = EmployeeDocument
    success_url = reverse_lazy('employees:document_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

# -----------------------------------------------------------------------------
# HR Reports
# -----------------------------------------------------------------------------

from django.views.generic import TemplateView
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

class HRReportsView(LoginRequiredMixin, TemplateView):
    template_name = "employees/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = self.request.tenant_id
        
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Attendance Summary for Current Month
        attendance_stats = Attendance.objects.filter(
            tenant_id=tenant_id,
            date__gte=start_of_month.date()
        ).aggregate(
            total_present=Count('id', filter=Q(status=AttendanceStatus.PRESENT)),
            total_absent=Count('id', filter=Q(status=AttendanceStatus.ABSENT)),
            total_late=Count('id', filter=Q(status=AttendanceStatus.HALF_DAY)), # Approximation
        )
        context['attendance_stats'] = attendance_stats
        
        # Payroll Summary
        payroll_stats = SalaryPayout.objects.filter(
            tenant_id=tenant_id,
            status=PayoutStatus.PAID
        ).aggregate(
            total_paid=Sum('net_payable'),
            total_deductions=Sum('total_deductions')
        )
        context['payroll_stats'] = payroll_stats
        
        # Leave Requests Pending
        pending_leaves = LeaveRequest.objects.filter(
            tenant_id=tenant_id,
            status__in=[LeaveStatus.PENDING_MANAGER, LeaveStatus.PENDING_OWNER]
        ).count()
        context['pending_leaves_count'] = pending_leaves

        return context


class DepartmentQuickCreateView(LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = "employees/partials/department_quick_form_modal.html"
    success_url = "/"
    
    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            import json
            trigger_data = {
                'closeSecondaryModal': '',
                'departmentAdded': {
                    'id': str(self.object.id),
                    'name': self.object.name
                }
            }
            return HttpResponse(status=204, headers={'HX-Trigger': json.dumps(trigger_data)})
        return response


class DesignationQuickCreateView(LoginRequiredMixin, CreateView):
    model = Designation
    form_class = DesignationForm
    template_name = "employees/partials/designation_quick_form_modal.html"
    success_url = "/"
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant_id'] = self.request.tenant_id
        return kwargs
        
    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        response = super().form_valid(form)
        if self.request.htmx:
            import json
            trigger_data = {
                'closeSecondaryModal': '',
                'designationAdded': {
                    'id': str(self.object.id),
                    'name': self.object.name
                }
            }
            return HttpResponse(status=204, headers={'HX-Trigger': json.dumps(trigger_data)})
        return response
