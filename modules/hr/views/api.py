from django.views.generic import ListView, View
from django.http import JsonResponse
from django.db.models import Q
from ..models import Employee, InsuranceBracket

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


class InsuranceBracketListAPIView(View):
    def get(self, request, *args, **kwargs):
        brackets = InsuranceBracket.objects.filter(is_deleted=False).order_by('insured_salary')
        data = []
        for bracket in brackets:
            data.append({
                'id': bracket.id,
                'level_name': bracket.level_name,
                'insured_salary': float(bracket.insured_salary),
                'labor_employee': float(bracket.labor_employee),
                'health_employee': float(bracket.health_employee),
                'labor_employer': float(bracket.labor_employer),
                'health_employer': float(bracket.health_employer),
                'pension_employer': float(bracket.pension_employer),
                'occupational_hazard': float(bracket.occupational_hazard),
                'wage_arrears': float(bracket.wage_arrears),
            })
        return JsonResponse(data, safe=False)
