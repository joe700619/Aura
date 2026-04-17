from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
from core.mixins import HRRequiredMixin, OwnEmployeeDataMixin, CopyMixin, PrevNextMixin, ListActionMixin, SearchMixin, SoftDeleteMixin, _HR_ATTENDANCE_ACCESS_GROUPS
from ..models import AttendanceRecord
from ..forms import AttendanceRecordForm, ClockInOutForm


class AttendanceListView(OwnEmployeeDataMixin, SearchMixin, ListActionMixin, HRRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = 'attendance/list.html'
    context_object_name = 'items'
    paginate_by = 25
    create_button_label = '新增紀錄'
    search_fields = ['employee__name', 'employee__employee_number']
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False).select_related('employee')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '出勤紀錄'
        context['custom_create_url'] = reverse_lazy('hr:attendance_create')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class AttendanceCreateView(CopyMixin, HRRequiredMixin, CreateView):
    model = AttendanceRecord
    form_class = AttendanceRecordForm
    template_name = 'attendance/form.html'

    def get_success_url(self):
        return reverse_lazy('hr:attendance_update', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '新增出勤紀錄'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '出勤紀錄已建立。')
        return redirect(self.get_success_url())


class AttendanceUpdateView(OwnEmployeeDataMixin, PrevNextMixin, HRRequiredMixin, UpdateView):
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS
    model = AttendanceRecord
    form_class = AttendanceRecordForm
    template_name = 'attendance/form.html'
    prev_next_order_field = '-date'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'編輯出勤紀錄 - {self.object.employee.name} ({self.object.date})'
        if hasattr(self.object, 'history'):
            history_list = []
            for record in self.object.history.all().select_related('history_user').order_by('-history_date')[:10]:
                history_list.append({
                    'history_user': record.history_user,
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_change_reason': record.history_change_reason or '資料變更',
                })
            context['history'] = history_list
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, '出勤紀錄已更新。')
        return redirect('hr:attendance_update', pk=self.object.pk)


class AttendanceDeleteView(OwnEmployeeDataMixin, SoftDeleteMixin, HRRequiredMixin, DeleteView):
    full_access_groups = _HR_ATTENDANCE_ACCESS_GROUPS
    model = AttendanceRecord
    success_url = reverse_lazy('hr:attendance_list')


class ClockInOutView(HRRequiredMixin, View):
    """員工自助打卡頁面"""
    template_name = 'attendance/clock_in_out.html'

    def get(self, request):
        form = ClockInOutForm()
        today = timezone.localdate()
        # Try to find today's record for the current user's employee
        employee = getattr(request.user, 'employee_profile', None)
        today_record = None
        if employee:
            today_record = AttendanceRecord.objects.filter(
                employee=employee, date=today, is_deleted=False
            ).first()

        return render(request, self.template_name, {
            'form': form,
            'today_record': today_record,
            'employee': employee,
            'today': today,
            'page_title': '打卡',
        })

    def post(self, request):
        form = ClockInOutForm(request.POST)
        employee = getattr(request.user, 'employee_profile', None)
        today = timezone.localdate()
        now = timezone.localtime().time()

        if not employee:
            messages.error(request, '您的帳號尚未綁定員工資料，無法打卡。')
            return redirect('hr:clock_in_out')

        if form.is_valid():
            clock_type = form.cleaned_data['clock_type']
            record, created = AttendanceRecord.objects.get_or_create(
                employee=employee,
                date=today,
                defaults={'source': 'web'},
            )

            if clock_type == 'in':
                if record.clock_in:
                    messages.warning(request, f'您今天已經打過上班卡了（{record.clock_in.strftime("%H:%M")}）。')
                else:
                    record.clock_in = now
                    record.source = 'web'
                    record.save()
                    messages.success(request, f'上班打卡成功！時間：{now.strftime("%H:%M")}')
            else:
                if record.clock_out:
                    messages.warning(request, f'您今天已經打過下班卡了（{record.clock_out.strftime("%H:%M")}）。')
                else:
                    record.clock_out = now
                    record.save()
                    messages.success(request, f'下班打卡成功！時間：{now.strftime("%H:%M")}')

        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('hr:clock_in_out')
