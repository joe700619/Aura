import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from core.mixins import BusinessRequiredMixin, ListActionMixin, SearchMixin, PrevNextMixin, SoftDeleteMixin, HistoryMixin
from ..models.fixed_asset import FixedAsset
from ..forms import FixedAssetForm


@login_required
@require_POST
def create_fixed_asset_api(request):
    try:
        data = json.loads(request.body)
        asset_no = data.get('asset_no')
        name = data.get('name')

        if not asset_no or not name:
            return JsonResponse({'success': False, 'message': '財產編號與名稱為必填項目'}, status=400)

        if FixedAsset.objects.filter(asset_no=asset_no).exists():
            return JsonResponse({'success': False, 'message': f'財產編號 {asset_no} 已存在'}, status=400)

        asset = FixedAsset.objects.create(
            asset_no=asset_no,
            name=name,
            cost=data.get('cost') or 0,
            salvage_value=data.get('salvage_value') or 0,
            useful_life_months=data.get('useful_life_months') or 36,
            purchase_date=data.get('purchase_date'),
        )
        return JsonResponse({'success': True, 'asset_no': asset.asset_no, 'name': asset.name})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '無效的資料格式'}, status=400)


class FixedAssetListView(ListActionMixin, SearchMixin, BusinessRequiredMixin, ListView):
    model = FixedAsset
    template_name = 'fixed_asset/list.html'
    context_object_name = 'assets'
    paginate_by = 25
    search_fields = ['asset_no', 'name']

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '財產目錄'
        return context


class FixedAssetCreateView(BusinessRequiredMixin, CreateView):
    model = FixedAsset
    form_class = FixedAssetForm
    template_name = 'fixed_asset/form.html'

    def get_success_url(self):
        messages.success(self.request, "儲存成功！")
        return reverse_lazy('internal_accounting:fixed_asset_update', kwargs={'pk': self.object.pk})


class FixedAssetUpdateView(HistoryMixin, PrevNextMixin, BusinessRequiredMixin, UpdateView):
    model = FixedAsset
    form_class = FixedAssetForm
    template_name = 'fixed_asset/form.html'

    def get_success_url(self):
        messages.success(self.request, "儲存成功！")
        return reverse_lazy('internal_accounting:fixed_asset_update', kwargs={'pk': self.object.pk})


class FixedAssetDeleteView(SoftDeleteMixin, BusinessRequiredMixin, DeleteView):
    model = FixedAsset
    template_name = 'fixed_asset/confirm_delete.html'
    success_url = reverse_lazy('internal_accounting:fixed_asset_list')
