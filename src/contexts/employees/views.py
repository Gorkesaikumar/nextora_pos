import uuid
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.db import models
from django.contrib.auth import get_user_model

from contexts.employees.models import EmployeeProfile
from contexts.employees.forms import EmployeeForm, RoleForm
from contexts.identity.models.rbac import Role, Permission, Membership

User = get_user_model()

class EmployeeListView(LoginRequiredMixin, ListView):
    model = EmployeeProfile
    template_name = "employees/employee_list.html"
    context_object_name = "employees"
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
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
