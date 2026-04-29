from io import BytesIO

from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from core.models import DocumentTemplate
from core.services.document import DocumentService
from modules.bookkeeping.models import ServiceRemuneration, ServiceRemunerationTaxRate, NHIConfig
from modules.client_portal.forms_remuneration import ServiceRemunerationForm
from modules.client_portal.mixins import ClientRequiredMixin


class ServiceRemunerationView(ClientRequiredMixin, TemplateView):
    """勞務報酬單主頁 — 兩個 tab：表單 / 歷史紀錄。"""
    template_name = 'client_portal/service_remuneration.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.bookkeeping_client_profile
        context['client'] = client

        # 編輯模式 / 複製模式 / 新增模式
        edit_pk = self.request.GET.get('edit')
        source_pk = self.request.GET.get('source_id')
        instance = None
        if edit_pk:
            instance = ServiceRemuneration.objects.filter(pk=edit_pk, client=client, is_deleted=False).first()
        elif source_pk:
            src = ServiceRemuneration.objects.filter(pk=source_pk, client=client, is_deleted=False).first()
            if src:
                src.pk = None
                src.confirm_token = None
                src.confirmation_status = ServiceRemuneration.ConfirmationStatus.PENDING
                src.payment_status = ServiceRemuneration.PaymentStatus.UNPAID
                src.confirmed_at = None
                src.email_sent_at = None
                src.skip_email_confirm = False
                src.signature_image = None
                src.id_front_image = None
                src.id_back_image = None
                src.withholding_payment_slip = None
                src.supplementary_payment_slip = None
                instance = src

        context['form'] = ServiceRemunerationForm(instance=instance)
        context['editing_pk'] = instance.pk if instance and instance.pk else None
        context['active_tab'] = self.request.GET.get('tab', 'form')

        # 預覽用：稅率與 NHI 設定（JS 端即時試算）
        context['tax_rates_json'] = {
            r.code: {
                'withholding_rate': float(r.withholding_rate),
                'expense_rate': float(r.expense_rate),
                'label': r.label,
            }
            for r in ServiceRemunerationTaxRate.objects.filter(is_active=True)
        }
        nhi = NHIConfig.get_solo()
        context['nhi_config_json'] = {
            'threshold': float(nhi.threshold),
            'rate': float(nhi.rate),
        }

        # 歷史紀錄
        context['history_records'] = ServiceRemuneration.objects.filter(
            client=client, is_deleted=False,
        ).order_by('-filing_date', '-created_at')
        return context


class ServiceRemunerationSaveView(ClientRequiredMixin, View):
    """處理表單儲存：建立 / 編輯，並依按鈕決定是否寄信。"""

    def post(self, request, *args, **kwargs):
        client = request.user.bookkeeping_client_profile
        edit_pk = request.POST.get('edit_pk') or None
        instance = None
        if edit_pk:
            instance = ServiceRemuneration.objects.filter(
                pk=edit_pk, client=client, is_deleted=False,
            ).first()

        form = ServiceRemunerationForm(request.POST, request.FILES, instance=instance)
        if not form.is_valid():
            messages.error(request, '表單內容有誤，請檢查後再試。')
            context = {
                'client': client,
                'form': form,
                'editing_pk': edit_pk,
                'active_tab': 'form',
                'history_records': ServiceRemuneration.objects.filter(
                    client=client, is_deleted=False,
                ).order_by('-filing_date', '-created_at'),
            }
            return render(request, 'client_portal/service_remuneration.html', context)

        obj = form.save(commit=False)
        obj.client = client
        obj.save()

        action = request.POST.get('action', 'save')
        if action == 'send':
            if not obj.recipient_email:
                messages.error(request, '所得人 Email 未填寫，無法寄送確認信。')
            else:
                from modules.client_portal.services_remuneration import send_confirmation_email
                ok = send_confirmation_email(request, obj)
                if ok:
                    obj.email_sent_at = timezone.now()
                    obj.skip_email_confirm = False
                    obj.save(update_fields=['email_sent_at', 'skip_email_confirm'])
                    messages.success(request, f'已寄送確認信至 {obj.recipient_email}')
                else:
                    messages.error(request, '寄送 Email 失敗，請稍後再試或聯絡管理員。')
        elif action == 'skip':
            obj.skip_email_confirm = True
            obj.save(update_fields=['skip_email_confirm'])
            messages.success(request, '已儲存（跳過 Email 確認）')
        else:
            messages.success(request, '已儲存')

        return redirect(reverse('client_portal:service_remuneration') + '?tab=history')


class ServiceRemunerationDeleteView(ClientRequiredMixin, View):
    """軟刪除一筆勞務報酬單。"""

    def post(self, request, pk, *args, **kwargs):
        client = request.user.bookkeeping_client_profile
        obj = get_object_or_404(ServiceRemuneration, pk=pk, client=client, is_deleted=False)
        obj.is_deleted = True
        obj.save(update_fields=['is_deleted'])
        messages.success(request, '已刪除')
        return redirect(reverse('client_portal:service_remuneration') + '?tab=history')


class ServiceRemunerationUploadSlipView(ClientRequiredMixin, View):
    """上傳扣繳繳款單或補充保費繳款單。
    上傳扣繳繳款單即將 payment_status 設為已繳納。
    """

    def post(self, request, pk, *args, **kwargs):
        client = request.user.bookkeeping_client_profile
        obj = get_object_or_404(ServiceRemuneration, pk=pk, client=client, is_deleted=False)
        slip_type = request.POST.get('slip_type', 'withholding')
        f = request.FILES.get('slip')
        if not f:
            return HttpResponseBadRequest('未選擇檔案')

        if slip_type == 'supplementary':
            obj.supplementary_payment_slip = f
            update_fields = ['supplementary_payment_slip']
        else:
            obj.withholding_payment_slip = f
            obj.payment_status = ServiceRemuneration.PaymentStatus.PAID
            update_fields = ['withholding_payment_slip', 'payment_status']

        obj.save(update_fields=update_fields)
        messages.success(request, '繳款單已上傳')
        return redirect(reverse('client_portal:service_remuneration') + '?tab=history')


class ServiceRemunerationDownloadSlipView(ClientRequiredMixin, View):
    """下載扣繳繳款書（套用 docx 模板產出）。

    管理員需於 Django admin 的「文件模板」中上傳 .docx 模板，
    並將「適用模型」設為 ServiceRemuneration。
    """

    def get(self, request, pk, *args, **kwargs):
        from django.contrib.contenttypes.models import ContentType
        client = request.user.bookkeeping_client_profile
        obj = get_object_or_404(ServiceRemuneration, pk=pk, client=client, is_deleted=False)
        ct = ContentType.objects.get_for_model(ServiceRemuneration)
        template = DocumentTemplate.objects.filter(model_content_type=ct).first()
        if not template:
            messages.error(request, '尚未上傳「勞務報酬單」的 Word 模板，請聯絡管理員。')
            return redirect(reverse('client_portal:service_remuneration') + '?tab=history')

        output: BytesIO = DocumentService.render_template(template, obj, output_format='docx')
        filename = f"扣繳繳款書_{obj.recipient_name}_{obj.filing_date or obj.created_at.date()}.docx"
        return FileResponse(output, as_attachment=True, filename=filename)


class ServiceRemunerationTax152PdfView(ClientRequiredMixin, View):
    """從勞務報酬單產生 Tax 152 各類所得扣繳稅額繳款書 PDF。"""

    # 申報類別 → Tax152 tran_type；50 薪資不產生
    CATEGORY_TO_TRAN_TYPE = {
        '9B': '156',
        '9A': '156',
        '92': '15B',
        '51': '152',
    }

    def get(self, request, pk, *args, **kwargs):
        import datetime
        from django.http import HttpResponse
        from modules.bookkeeping.models.tax_unit import TaxUnit
        from modules.bookkeeping.services.tax152_service import Tax152Input, generate_pdf_bytes

        client = request.user.bookkeeping_client_profile
        obj = get_object_or_404(ServiceRemuneration, pk=pk, client=client, is_deleted=False)

        tran_type = self.CATEGORY_TO_TRAN_TYPE.get(obj.income_category)
        if not tran_type:
            messages.error(request, f'{obj.get_income_category_display()} 類別不需產生扣繳稅額繳款書。')
            return redirect(reverse('client_portal:service_remuneration') + '?tab=history')

        # 稅籍單位
        auth_code = (client.tax_authority_code or '').strip()
        if len(auth_code) != 5:
            messages.error(request, '客戶尚未設定國稅局轄區代碼（如 A0300），請聯絡事務所。')
            return redirect(reverse('client_portal:service_remuneration') + '?tab=history')
        try:
            tax_unit = TaxUnit.objects.get(city_id=auth_code[0], unit_code=auth_code[1:])
        except TaxUnit.DoesNotExist:
            messages.error(request, f'找不到轄區代碼「{auth_code}」，請聯絡事務所設定對照表。')
            return redirect(reverse('client_portal:service_remuneration') + '?tab=history')

        # 統一編號
        company_no = (client.tax_id or '').strip()
        if not company_no:
            messages.error(request, '客戶資料中缺少統一編號，請聯絡事務所。')
            return redirect(reverse('client_portal:service_remuneration') + '?tab=history')

        # 給付日期（支付日期）：優先用 filing_date，其次 service_end_date，最後今天
        give_date = obj.filing_date or obj.service_end_date or datetime.date.today()
        roc_year = str(give_date.year - 1911)
        roc_month = str(give_date.month)
        roc_day = str(give_date.day)

        # 所得所屬年月
        income_dt = obj.service_start_date or obj.service_end_date or obj.filing_date or give_date
        income_year = str(income_dt.year - 1911)
        income_month = f"{income_dt.month:02d}"

        pw_amt = int(obj.withholding_tax or 0)
        if pw_amt <= 0:
            messages.error(request, '此筆記錄的扣繳稅額為 0，無需產生繳款書。')
            return redirect(reverse('client_portal:service_remuneration') + '?tab=history')

        tax = Tax152Input(
            city_id=tax_unit.city_id,
            unit_code=tax_unit.unit_code,
            company_no=company_no,
            tran_type=tran_type,
            pw_amt=pw_amt,
            owner_cat='0' if obj.nationality == 'local' else '1',
            give_year=roc_year,
            give_month=roc_month,
            give_day=roc_day,
            unit_name=tax_unit.bureau_name or tax_unit.unit_name,
            company_name=client.name,
            withholding_person=client.name,
            withholding_address=(client.registered_address or client.correspondence_address or ''),
            withholding_phone=client.phone or '',
            income_year=income_year,
            income_month=income_month,
            gross_income=int(obj.amount or 0),
            taxable_income=int(obj.amount or 0),
        )

        pdf_bytes = generate_pdf_bytes(tax)
        filing_date_str = (obj.filing_date or datetime.date.today()).strftime('%Y%m%d')
        filename = f"扣繳稅額繳款書_{obj.recipient_name}_{filing_date_str}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{filename}"
        )
        return response


class ServiceRemunerationPdfView(ClientRequiredMixin, View):
    """下載勞務報酬單 PDF（含身分證圖片、已確認則顯示確認日期）。"""

    def get(self, request, pk, *args, **kwargs):
        from django.http import HttpResponse
        from modules.client_portal.pdf_service_remuneration import generate_service_remuneration_pdf

        client = request.user.bookkeeping_client_profile
        obj = get_object_or_404(ServiceRemuneration, pk=pk, client=client, is_deleted=False)

        pdf_bytes = generate_service_remuneration_pdf(obj)
        filing_str = (obj.filing_date or obj.created_at.date()).strftime('%Y%m%d')
        filename = f"勞務報酬單_{obj.recipient_name}_{filing_str}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="{filename}"; '
            f"filename*=UTF-8''{filename}"
        )
        return response


class ServiceRemunerationConfirmView(View):
    """公開確認頁（不需登入）— 所得人從 Email 連結進入。"""
    template_name = 'client_portal/service_remuneration_confirm.html'

    def get(self, request, token, *args, **kwargs):
        try:
            obj = ServiceRemuneration.objects.get(confirm_token=token, is_deleted=False)
        except (ServiceRemuneration.DoesNotExist, ValueError):
            raise Http404('連結無效或已失效')
        return render(request, self.template_name, {'obj': obj})

    def post(self, request, token, *args, **kwargs):
        try:
            obj = ServiceRemuneration.objects.get(confirm_token=token, is_deleted=False)
        except (ServiceRemuneration.DoesNotExist, ValueError):
            raise Http404('連結無效或已失效')
        if obj.confirmation_status != ServiceRemuneration.ConfirmationStatus.CONFIRMED:
            obj.confirmation_status = ServiceRemuneration.ConfirmationStatus.CONFIRMED
            obj.confirmed_at = timezone.now()
            obj.save(update_fields=['confirmation_status', 'confirmed_at'])
        return render(request, self.template_name, {'obj': obj, 'just_confirmed': True})
