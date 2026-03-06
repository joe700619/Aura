from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from core.mixins import CopyMixin, PrevNextMixin, ListActionMixin
from ..models import WorkCalendar
from ..forms import WorkCalendarForm


class WorkCalendarListView(ListActionMixin, LoginRequiredMixin, ListView):
    model = WorkCalendar
    template_name = 'work_calendar/list.html'
    context_object_name = 'items'
    paginate_by = 50
    create_button_label = '新增日曆'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        year = self.request.GET.get('year')
        day_type = self.request.GET.get('day_type')
        if year:
            qs = qs.filter(year=year)
        if day_type:
            qs = qs.filter(day_type=day_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '工作日曆'
        context['custom_create_url'] = reverse_lazy('hr:work_calendar_create')
        context['years'] = sorted(
            WorkCalendar.objects.filter(is_deleted=False)
            .values_list('year', flat=True).distinct(),
            reverse=True,
        )
        context['selected_year'] = self.request.GET.get('year', '')
        context['selected_day_type'] = self.request.GET.get('day_type', '')
        return context


class WorkCalendarCreateView(CopyMixin, LoginRequiredMixin, CreateView):
    model = WorkCalendar
    form_class = WorkCalendarForm
    template_name = 'work_calendar/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:work_calendar_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增工作日曆'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '工作日曆已建立。')
        return redirect(self.get_success_url())


class WorkCalendarUpdateView(PrevNextMixin, LoginRequiredMixin, UpdateView):
    model = WorkCalendar
    form_class = WorkCalendarForm
    template_name = 'work_calendar/form.html'
    prev_next_order_field = '-date'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯工作日曆 - {self.object.date}'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '工作日曆已更新。')
        return redirect('hr:work_calendar_update', pk=self.object.pk)


class WorkCalendarDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkCalendar
    success_url = reverse_lazy('hr:work_calendar_list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
