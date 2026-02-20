from django.views.generic import ListView
from django.db.models import Q
from ..models import Employee

class EmployeeSearchApiView(ListView):
    model = Employee
    template_name = 'hr/partials/employee_search_results.html'
    context_object_name = 'employees'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Employee.objects.filter(
                Q(name__icontains=query) | 
                Q(employee_number__icontains=query) |
                Q(id_number__icontains=query)
            ).filter(is_active=True)
        return Employee.objects.none()
