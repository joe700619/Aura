from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
import pandas as pd
from io import BytesIO
from collections import defaultdict
from django.db.models import Q
from ..models import Collection
from core.notifications.models import EmailTemplate
from core.notifications.services import EmailService

def get_withholding_summary_queryset(year, q=None, tax_status=None):
    qs = Collection.objects.filter(
        date__year=year,
        receivable__unified_business_no__isnull=False
    ).exclude(
        receivable__unified_business_no=''
    ).values(
        'receivable__unified_business_no',
        'receivable__company_name',
        'receivable__email'
    ).annotate(
        total_amount=Sum('amount'),
        total_tax=Sum('tax'),
        total_reporting_amount=Sum('reporting_amount')
    )
    
    if q:
        qs = qs.filter(
            Q(receivable__company_name__icontains=q) |
            Q(receivable__unified_business_no__icontains=q)
        )
        
    if tax_status == 'has_tax':
        qs = qs.filter(total_tax__gt=0)
    elif tax_status == 'no_tax':
        qs = qs.filter(total_tax=0)
        
    return qs.order_by('receivable__unified_business_no')

class WithholdingTaxSummaryView(LoginRequiredMixin, TemplateView):
    template_name = 'report/withholding_tax.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get year from request, default to current year
        current_year = timezone.now().year
        year = self.request.GET.get('year')
        try:
            year = int(year) if year else current_year
        except ValueError:
            year = current_year

        # Get available years from database
        year_dates = Collection.objects.exclude(date__isnull=True).dates('date', 'year')
        available_years = list(set([d.year for d in year_dates]))
        if not available_years:
            available_years = [current_year]
        if year not in available_years:
            available_years.append(year)
        available_years.sort(reverse=True)

        q = self.request.GET.get('q', '')
        tax_status = self.request.GET.get('tax_status', 'all')

        # Query collections for the selected year
        summary_data = get_withholding_summary_queryset(year, q, tax_status)
        
        # Convert to list and attach details
        summary_list = list(summary_data)
        
        detailed_collections = Collection.objects.filter(
            date__year=year,
            receivable__unified_business_no__isnull=False
        ).exclude(
            receivable__unified_business_no=''
        ).select_related('receivable').order_by('receivable__unified_business_no', 'date', 'collection_no')
        
        details_map = defaultdict(list)
        for c in detailed_collections:
            details_map[c.receivable.unified_business_no].append(c)
            
        for item in summary_list:
            item['details'] = details_map[item['receivable__unified_business_no']]

        context['year'] = year
        context['q'] = q
        context['tax_status'] = tax_status
        context['available_years'] = available_years
        context['summary_data'] = summary_list
        context['email_templates'] = EmailTemplate.objects.filter(is_active=True).order_by('name')

        # Calculate totals
        context['grand_total_amount'] = sum(item['total_amount'] for item in summary_list if item['total_amount'])
        context['grand_total_tax'] = sum(item['total_tax'] for item in summary_list if item['total_tax'])
        context['grand_total_reporting'] = sum(item['total_reporting_amount'] for item in summary_list if item['total_reporting_amount'])

        return context

class WithholdingTaxExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        current_year = timezone.now().year
        year = request.GET.get('year')
        try:
            year = int(year) if year else current_year
        except ValueError:
            year = current_year

        q = request.GET.get('q', '')
        tax_status = request.GET.get('tax_status', 'all')

        summary_data = get_withholding_summary_queryset(year, q, tax_status)

        data_list = list(summary_data)
        df = pd.DataFrame(data_list)
        
        if not df.empty:
            df.rename(columns={
                'receivable__unified_business_no': '統一編號',
                'receivable__company_name': '公司名稱',
                'receivable__email': '客戶Email',
                'total_amount': '收款合計',
                'total_tax': '扣繳稅款',
                'total_reporting_amount': '扣繳申報金額'
            }, inplace=True)
            
            df = df.fillna({
                '客戶Email': '',
                '收款合計': 0,
                '扣繳稅款': 0,
                '扣繳申報金額': 0
            })
            
            totals = {
                '統一編號': '總計',
                '公司名稱': '',
                '客戶Email': '',
                '收款合計': df['收款合計'].sum(),
                '扣繳稅款': df['扣繳稅款'].sum(),
                '扣繳申報金額': df['扣繳申報金額'].sum()
            }
            df_total = pd.DataFrame([totals])
            df = pd.concat([df, df_total], ignore_index=True)
        else:
            df = pd.DataFrame(columns=['統一編號', '公司名稱', '客戶Email', '收款合計', '扣繳稅款', '扣繳申報金額'])

        # Build detail data
        detail_qs = Collection.objects.filter(
            date__year=year,
            receivable__unified_business_no__isnull=False
        ).exclude(
            receivable__unified_business_no=''
        ).select_related('receivable').order_by('receivable__unified_business_no', 'date')

        if q:
            detail_qs = detail_qs.filter(
                Q(receivable__company_name__icontains=q) |
                Q(receivable__unified_business_no__icontains=q)
            )
        if tax_status == 'has_tax':
            detail_qs = detail_qs.filter(tax__gt=0)
        elif tax_status == 'no_tax':
            detail_qs = detail_qs.filter(tax=0)

        detail_rows = []
        for c in detail_qs:
            detail_rows.append({
                '統一編號': c.receivable.unified_business_no,
                '公司名稱': c.receivable.company_name,
                '收款單號': c.collection_no,
                '收款日期': c.date.strftime('%Y/%m/%d') if c.date else '',
                '收款方式': c.get_method_display(),
                '收款金額': float(c.amount),
                '扣繳稅款': float(c.tax),
                '手續費': float(c.fee),
                '壞帳折讓': float(c.allowance),
                '收款合計': float(c.total),
                '扣繳申報金額': float(c.reporting_amount),
            })
        df_detail = pd.DataFrame(detail_rows) if detail_rows else pd.DataFrame(
            columns=['統一編號', '公司名稱', '收款單號', '收款日期', '收款方式', '收款金額', '扣繳稅款', '手續費', '壞帳折讓', '收款合計', '扣繳申報金額']
        )

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=Withholding_Tax_Summary_{year}.xlsx'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            # Sheet 1: Summary
            df.to_excel(writer, index=False, sheet_name='扣繳彙總報表')
            worksheet = writer.sheets['扣繳彙總報表']
            for col in worksheet.columns:
                max_length = 0
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                worksheet.column_dimensions[col[0].column_letter].width = (max_length + 2)

            # Sheet 2: Detail
            df_detail.to_excel(writer, index=False, sheet_name='收款明細')
            ws_detail = writer.sheets['收款明細']
            for col in ws_detail.columns:
                max_length = 0
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws_detail.column_dimensions[col[0].column_letter].width = (max_length + 2)

        return response

class WithholdingTaxSendEmailView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        current_year = timezone.now().year
        year = request.POST.get('year')
        template_code = request.POST.get('template_code')

        try:
            year = int(year) if year else current_year
        except ValueError:
            year = current_year

        if not template_code:
            messages.error(request, "請選擇信件模板")
            return redirect(f"{reverse('internal_accounting:report_withholding_tax')}?year={year}")

        q = request.POST.get('q', '')
        tax_status = request.POST.get('tax_status', 'all')

        summary_data = get_withholding_summary_queryset(year, q, tax_status)

        success_count = 0
        error_count = 0

        for item in summary_data:
            email = item.get('receivable__email')
            if not email:
                continue
                
            row = [{
                '統一編號': item['receivable__unified_business_no'],
                '公司名稱': item['receivable__company_name'],
                '客戶Email': email,
                '收款合計': item['total_amount'] or 0,
                '扣繳稅款': item['total_tax'] or 0,
                '扣繳申報金額': item['total_reporting_amount'] or 0
            }]
            df = pd.DataFrame(row)

            # Build detail rows for this customer
            customer_collections = Collection.objects.filter(
                date__year=year,
                receivable__unified_business_no=item['receivable__unified_business_no']
            ).select_related('receivable').order_by('date')

            detail_rows = []
            for c in customer_collections:
                detail_rows.append({
                    '收款單號': c.collection_no,
                    '收款日期': c.date.strftime('%Y/%m/%d') if c.date else '',
                    '收款方式': c.get_method_display(),
                    '收款金額': float(c.amount),
                    '扣繳稅款': float(c.tax),
                    '手續費': float(c.fee),
                    '壞帳折讓': float(c.allowance),
                    '收款合計': float(c.total),
                    '扣繳申報金額': float(c.reporting_amount),
                })
            df_detail = pd.DataFrame(detail_rows) if detail_rows else pd.DataFrame(
                columns=['收款單號', '收款日期', '收款方式', '收款金額', '扣繳稅款', '手續費', '壞帳折讓', '收款合計', '扣繳申報金額']
            )
            
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Sheet 1: Summary
                df.to_excel(writer, index=False, sheet_name='扣繳彙總')
                worksheet = writer.sheets['扣繳彙總']
                for col in worksheet.columns:
                    max_length = 0
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    worksheet.column_dimensions[col[0].column_letter].width = (max_length + 2)

                # Sheet 2: Detail
                df_detail.to_excel(writer, index=False, sheet_name='收款明細')
                ws_detail = writer.sheets['收款明細']
                for col in ws_detail.columns:
                    max_length = 0
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    ws_detail.column_dimensions[col[0].column_letter].width = (max_length + 2)
                    
            excel_data = excel_buffer.getvalue()
            filename = f"{item['receivable__company_name']}_{year}年度扣繳明細.xlsx"
            attachments = [(filename, excel_data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')]
            
            context = {
                'year': year,
                'company_name': item['receivable__company_name'],
                'unified_business_no': item['receivable__unified_business_no'],
                'total_amount': item['total_amount'] or 0,
                'total_tax': item['total_tax'] or 0,
                'total_reporting_amount': item['total_reporting_amount'] or 0,
            }
            
            if EmailService.send_email(template_code, [email], context, attachments=attachments):
                success_count += 1
            else:
                error_count += 1
                
        if success_count > 0:
            messages.success(request, f"成功寄出 {success_count} 封扣繳通知函。")
        if error_count > 0:
            messages.error(request, f"有 {error_count} 封扣繳通知函寄送失敗，請查看系統日誌。")
        if success_count == 0 and error_count == 0:
            messages.warning(request, "未找到符合的資料，或所有客戶皆未設定 Email。")

        return redirect(f"{reverse('internal_accounting:report_withholding_tax')}?year={year}")
