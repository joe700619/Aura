import datetime

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.generic import TemplateView

from modules.client_portal.mixins import ClientRequiredMixin
from modules.bookkeeping.models.tax_unit import TaxUnit
from modules.bookkeeping.services.tax152_service import (
    Tax152Input, generate_pdf_bytes, INCOME_TYPE_MAP,
)

CURRENT_ROC_YEAR = datetime.date.today().year - 1911


class Tax152View(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/tax152.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['income_types'] = INCOME_TYPE_MAP
        context['current_roc_year'] = CURRENT_ROC_YEAR
        return context

    def post(self, request, *args, **kwargs):
        client = request.user.bookkeeping_client_profile

        # 取得稅籍單位資料
        auth_code = (client.tax_authority_code or '').strip()
        if len(auth_code) != 5:
            return HttpResponseBadRequest('客戶尚未設定國稅局轄區代碼（如 A0300），請聯絡事務所。')
        try:
            tax_unit = TaxUnit.objects.get(city_id=auth_code[0], unit_code=auth_code[1:])
        except TaxUnit.DoesNotExist:
            return HttpResponseBadRequest(
                f"找不到轄區代碼「{auth_code}」，請聯絡事務所設定對照表。"
            )

        # 取得統一編號（8碼）
        company_no = (client.tax_id or '').strip()
        if not company_no:
            return HttpResponseBadRequest("客戶資料中缺少統一編號，請聯絡事務所。")

        # 表單參數
        try:
            pw_amt = int(request.POST.get('pw_amt', '0').replace(',', ''))
            tran_type = request.POST.get('tran_type', '152').strip()
            give_year = request.POST.get('give_year', '').strip()
            give_month = request.POST.get('give_month', '').strip()
            give_day = request.POST.get('give_day', '1').strip() or '1'
            income_year = request.POST.get('income_year', give_year).strip()
            income_month = request.POST.get('income_month', give_month).strip()
            gross_income = int(request.POST.get('gross_income', '0').replace(',', ''))
            taxable_income = int(request.POST.get('taxable_income', '0').replace(',', ''))
            owner_cat = request.POST.get('owner_cat', '0').strip()
        except (ValueError, TypeError):
            return HttpResponseBadRequest("輸入資料格式錯誤，請重新確認。")

        if not give_year or not give_month:
            return HttpResponseBadRequest("請填寫給付年月。")
        if pw_amt <= 0:
            return HttpResponseBadRequest("應扣繳稅額必須大於 0。")

        tax = Tax152Input(
            city_id=tax_unit.city_id,
            unit_code=tax_unit.unit_code,
            company_no=company_no,
            tran_type=tran_type,
            pw_amt=pw_amt,
            owner_cat=owner_cat,
            give_year=give_year,
            give_month=give_month,
            give_day=give_day,
            unit_name=tax_unit.bureau_name or tax_unit.unit_name,
            company_name=client.name,
            withholding_person=client.name,
            withholding_address=(client.registered_address or
                                  client.correspondence_address or ''),
            withholding_phone=client.phone or '',
            income_year=income_year,
            income_month=income_month,
            gross_income=gross_income,
            taxable_income=taxable_income,
            is_auto_repay=request.POST.get('is_auto_repay') == '1',
        )

        pdf_bytes = generate_pdf_bytes(tax)

        filename = f"各類所得扣繳稅額繳款書_{give_year}{int(give_month):02d}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{filename}"
        )
        return response
