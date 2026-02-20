from django.views.generic import ListView
from django.db.models import Q
from ..models import ClientAssessment, Progress, Shareholder, ShareholderRegister

class ClientAssessmentSearchApiView(ListView):
    model = ClientAssessment
    template_name = 'registration/partials/client_assessment_search_results.html'
    context_object_name = 'client_assessments'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return ClientAssessment.objects.filter(
                Q(company_name__icontains=query) |
                Q(unified_business_no__icontains=query) |
                Q(main_contact__icontains=query)
            ).order_by('-created_at')
        return ClientAssessment.objects.none()

class ProgressSearchApiView(ListView):
    model = Progress
    template_name = 'registration/partials/progress_search_results.html'
    context_object_name = 'progress_list'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Progress.objects.filter(
                Q(registration_no__icontains=query) |
                Q(company_name__icontains=query) |
                Q(unified_business_no__icontains=query)
            ).order_by('-created_at')
        return Progress.objects.none()

class ShareholderSearchApiView(ListView):
    model = Shareholder
    template_name = 'registration/partials/shareholder_search_results.html'
    context_object_name = 'shareholders'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Shareholder.objects.filter(
                Q(name__icontains=query) |
                Q(id_number__icontains=query)
            ).order_by('name')
        return Shareholder.objects.none()

class ShareholderRegisterSearchApiView(ListView):
    model = ShareholderRegister
    template_name = 'registration/partials/shareholder_register_search_results.html'
    context_object_name = 'registers'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return ShareholderRegister.objects.filter(
                Q(company_name__icontains=query) |
                Q(unified_business_no__icontains=query)
            ).order_by('company_name')
        return ShareholderRegister.objects.none()
