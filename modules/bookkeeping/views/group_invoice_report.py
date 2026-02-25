from django.views.generic import TemplateView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.db.models import Q
from io import BytesIO
from ..models import BookkeepingClient, GroupInvoice
from core.mixins import EmployeeDataIsolationMixin

# 發票代碼對照
INVOICE_CODE_MAP = {
    'two_copy': '20',       # 二聯
    'two_copy_sub': '21',   # 二聯副
    'three_copy': '10',     # 三聯
    'three_copy_sub': '11', # 三聯副
    'special': '40',        # 特種
    'two_cashier': '30',    # 二收銀
    'three_cashier': '60',  # 三收銀
    'three_cashier_sub': '',  # 三收銀副 (無代碼)
}

FIXED_SUFFIX = '82530323'


class GroupInvoiceReportView(EmployeeDataIsolationMixin, LoginRequiredMixin, ListView):
    template_name = 'bookkeeping/group_invoice_report.html'
    model = BookkeepingClient
    employee_filter_fields = ['group_assistant', 'bookkeeping_assistant']

    def get_queryset(self):
        # Base query handling the specific report requirements and mixin isolation
        qs = super().get_queryset().filter(
            is_deleted=False,
            has_group_invoice=True,
        ).select_related(
            'group_assistant', 'bookkeeping_assistant'
        ).prefetch_related('group_invoices')
        
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(tax_id__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clients = context['object_list'] # Use the filtered queryset from ListView

        # Flatten: one row per (client, invoice_type) where qty > 0
        report_rows = []
        for client in clients:
            for inv in client.group_invoices.filter(quantity__gt=0):
                code = INVOICE_CODE_MAP.get(inv.invoice_type, '')
                report_rows.append({
                    'client_name': client.name,
                    'tax_id': client.tax_id or '',
                    'invoice_type_display': inv.get_invoice_type_display(),
                    'invoice_code': code,
                    'quantity': inv.quantity,
                })

        context['report_rows'] = report_rows
        context['q'] = q
        return context


class GroupInvoiceExportView(EmployeeDataIsolationMixin, LoginRequiredMixin, ListView):
    """Excel export: only 媒體檔 column."""
    model = BookkeepingClient
    employee_filter_fields = ['group_assistant', 'bookkeeping_assistant']

    def get_queryset(self):
        qs = super().get_queryset().filter(
            is_deleted=False,
            has_group_invoice=True,
        ).prefetch_related('group_invoices')
        
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(tax_id__icontains=q)
            )
        return qs

    def get(self, request, *args, **kwargs):
        period = request.GET.get('period', '')
        clients = self.get_queryset()

        # Build media file lines
        media_lines = []
        for client in clients:
            tax_id = client.tax_id or ''
            for inv in client.group_invoices.filter(quantity__gt=0):
                code = INVOICE_CODE_MAP.get(inv.invoice_type, '')
                if not code:
                    continue  # skip types without a code
                qty = str(inv.quantity)
                media_line = tax_id + code + qty + period + FIXED_SUFFIX + ';'
                media_lines.append(media_line)

        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = '媒體檔'
            ws.append(['媒體檔'])
            for line in media_lines:
                ws.append([line])
            ws.column_dimensions['A'].width = 40

            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            response = HttpResponse(
                buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="group_invoice_media.xlsx"'
            return response
        except ImportError:
            # Fallback to CSV if openpyxl not available
            import csv
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="group_invoice_media.csv"'
            writer = csv.writer(response)
            writer.writerow(['媒體檔'])
            for line in media_lines:
                writer.writerow([line])
            return response
