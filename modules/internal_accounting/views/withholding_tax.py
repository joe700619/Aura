from django.views.generic import TemplateView, View
from core.mixins import BusinessRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.core.paginator import Paginator
import pandas as pd
from io import BytesIO
from collections import defaultdict
from django.db.models import Q
from ..models import Collection
from core.notifications.models import EmailTemplate
from core.notifications.services import EmailService

_SORT_MAP = {
    'tax_no':          'receivable__unified_business_no',
    'company_name':    'receivable__company_name',
    'email':           'receivable__email',
    'total_amount':    'total_amount',
    'total_tax':       'total_tax',
    'total_reporting': 'total_reporting_amount',
}

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

class WithholdingTaxSummaryView(BusinessRequiredMixin, TemplateView):
    template_name = 'report/withholding_tax.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_year = timezone.now().year
        year = self.request.GET.get('year')
        try:
            year = int(year) if year else current_year
        except ValueError:
            year = current_year

        year_dates = Collection.objects.exclude(date__isnull=True).dates('date', 'year')
        available_years = sorted(set(d.year for d in year_dates), reverse=True)
        if not available_years:
            available_years = [current_year]
        if year not in available_years:
            available_years = sorted(available_years + [year], reverse=True)

        context['year'] = year
        context['q'] = self.request.GET.get('q', '')
        context['tax_status'] = self.request.GET.get('tax_status', 'all')
        context['available_years'] = available_years
        context['email_templates'] = EmailTemplate.objects.filter(is_active=True).order_by('name')
        return context


class WithholdingTaxDataView(BusinessRequiredMixin, View):
    """AJAX endpoint：分頁 + 排序 + 快速篩選，回傳 JSON"""

    def get(self, request):
        current_year = timezone.now().year
        try:
            year = int(request.GET.get('year', current_year))
        except (ValueError, TypeError):
            year = current_year

        q          = request.GET.get('q', '')
        tax_status = request.GET.get('tax_status', 'all')
        tax_filter = request.GET.get('tax_filter', 'all')
        sort_field = request.GET.get('sort_field', '')
        sort_dir   = request.GET.get('sort_dir', 'asc')
        try:
            page      = max(1, int(request.GET.get('page', 1)))
            page_size = min(100, max(10, int(request.GET.get('page_size', 25))))
        except (ValueError, TypeError):
            page, page_size = 1, 25

        # Base queryset（form 條件）
        base_qs = get_withholding_summary_queryset(year, q, tax_status)

        # 快速篩選按鈕的計數（不受 tax_filter 影響）
        counts = {
            'all':     base_qs.count(),
            'has_tax': base_qs.filter(total_tax__gt=0).count(),
            'no_tax':  base_qs.exclude(total_tax__gt=0).count(),
        }

        # 套用快速篩選
        qs = base_qs
        if tax_filter == 'has_tax':
            qs = qs.filter(total_tax__gt=0)
        elif tax_filter == 'no_tax':
            qs = qs.exclude(total_tax__gt=0)

        # 全頁合計（分頁前）
        agg = qs.aggregate(
            gt_amount=Sum('total_amount'),
            gt_tax=Sum('total_tax'),
            gt_reporting=Sum('total_reporting_amount'),
        )
        grand_totals = {
            'total_amount':    int(agg['gt_amount'] or 0),
            'total_tax':       int(agg['gt_tax'] or 0),
            'total_reporting': int(agg['gt_reporting'] or 0),
        }

        # 排序
        order_field = _SORT_MAP.get(sort_field, 'receivable__unified_business_no')
        if sort_dir == 'desc':
            order_field = f'-{order_field}'
        qs = qs.order_by(order_field)

        # 分頁
        paginator = Paginator(qs, page_size)
        page_obj  = paginator.get_page(page)
        page_list = list(page_obj.object_list)

        # 撈當頁明細
        tax_nos = [item['receivable__unified_business_no'] for item in page_list]
        detail_qs = (
            Collection.objects
            .filter(date__year=year, receivable__unified_business_no__in=tax_nos)
            .select_related('receivable')
            .order_by('receivable__unified_business_no', 'date', 'collection_no')
        )
        details_map = defaultdict(list)
        for c in detail_qs:
            details_map[c.receivable.unified_business_no].append({
                'id':                c.pk,
                'collection_no':     c.collection_no or '',
                'date':              c.date.strftime('%Y-%m-%d') if c.date else '',
                'amount':            int(c.amount or 0),
                'tax':               int(c.tax or 0),
                'reporting_amount':  int(c.reporting_amount or 0),
            })

        items = [
            {
                'tax_no':          item['receivable__unified_business_no'] or '',
                'company_name':    item['receivable__company_name'] or '',
                'email':           item['receivable__email'] or '',
                'total_amount':    int(item['total_amount'] or 0),
                'total_tax':       int(item['total_tax'] or 0),
                'total_reporting': int(item['total_reporting_amount'] or 0),
                'details':         details_map.get(item['receivable__unified_business_no'], []),
            }
            for item in page_list
        ]

        return JsonResponse({
            'items':        items,
            'page':         page_obj.number,
            'page_size':    page_size,
            'total_pages':  paginator.num_pages,
            'total_count':  paginator.count,
            'has_previous': page_obj.has_previous(),
            'has_next':     page_obj.has_next(),
            'counts':       counts,
            'grand_totals': grand_totals,
        })

class WithholdingTaxExportView(BusinessRequiredMixin, View):
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

class WithholdingTaxSendEmailView(BusinessRequiredMixin, View):
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

        # 限定已勾選的公司（逗號分隔的統編清單）
        selected_raw = request.POST.get('selected_tax_nos', '')
        selected_tax_nos = [t.strip() for t in selected_raw.split(',') if t.strip()]
        if selected_tax_nos:
            summary_data = summary_data.filter(
                receivable__unified_business_no__in=selected_tax_nos
            )

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
