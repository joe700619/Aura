import json
from core.mixins import BusinessRequiredMixin
import openpyxl
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from ..models import BookkeepingYear, CorporateTaxFiling, TaxAdjustmentEntry

class CorporateTaxDraftAPIView(BusinessRequiredMixin, View):
    """
    營所稅試算 API
    GET: 取得該年度 (BookkeepingYear) 的申報主檔及調整明細
    POST: 儲存申報主檔及調整明細
    """
    def get(self, request, year_id):
        year_record = get_object_or_404(BookkeepingYear, id=year_id)
        
        filing, created = CorporateTaxFiling.objects.get_or_create(year_record=year_record)
        
        adjustments = filing.adjustments.all()

        items_data = []
        for adj in adjustments:
            items_data.append({
                'id': adj.id,
                'code': adj.account_code,
                'name': adj.account_name,
                'book': float(adj.book_amount),
                'exclude': float(adj.excluded_amount),
            })
            
        data = {
            'profitRate': float(filing.industry_profit_rate),
            'incomeStandardRate': float(filing.income_standard_rate),
            'netProfitRate': float(filing.net_profit_rate),
            'taxRate': float(filing.tax_rate),
            'industryCd': filing.industry_code,
            'industryNm': filing.industry_name,
            'items': items_data,
        }
        return JsonResponse(data)
        
    def post(self, request, year_id):
        year_record = get_object_or_404(BookkeepingYear, id=year_id)
        try:
            data = json.loads(request.body)
            filing, _ = CorporateTaxFiling.objects.get_or_create(year_record=year_record)
            
            # 更新主表參數
            if 'profitRate' in data:
                filing.industry_profit_rate = data['profitRate']
            if 'incomeStandardRate' in data:
                filing.income_standard_rate = data['incomeStandardRate']
            if 'netProfitRate' in data:
                filing.net_profit_rate = data['netProfitRate']
            if 'industryCd' in data:
                filing.industry_code = data['industryCd']
            if 'industryNm' in data:
                filing.industry_name = data['industryNm']
            filing.save()
            
            # 更新明細
            if 'items' in data:
                for item in data['items']:
                    adj = filing.adjustments.filter(account_code=item.get('code')).first()
                    if adj:
                        if 'exclude' in item:
                            adj.excluded_amount = item['exclude']
                        if 'book' in item:
                            adj.book_amount = item['book']
                        adj.save()
                        
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

class ImportCorporateTaxExcelAPIView(BusinessRequiredMixin, View):
    """
    匯入試算表 Excel
    """
    def post(self, request, year_id):
        year_record = get_object_or_404(BookkeepingYear, id=year_id)
        
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': '請上傳檔案'}, status=400)
            
        excel_file = request.FILES['file']
        
        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            sheet = wb.active
            
            # Dictionary to accumulate amounts by account code
            # Key: code, Value: {'name': name, 'amount': amount}
            accounts = {}
            
            def process_row_cell(code_val, name_val, amount_val, is_debit):
                if not code_val:
                    return
                code_str = str(code_val).strip()
                # 我們只關心 4, 5, 6, 7, 8 開頭的科目
                if code_str and code_str[0] in ['4', '5', '6', '7', '8']:
                    try:
                        amt = Decimal(str(amount_val).replace(',', '').strip() or '0')
                    except Exception:
                        amt = Decimal('0')
                    
                    if amt == 0:
                        return
                        
                    # 決定正負號
                    # 4, 7 (收入類): 貸方為正, 借方為負
                    # 5, 6, 8 (成本費用類): 借方為正, 貸方為負
                    if code_str[0] in ['4', '7']:
                        final_amt = -amt if is_debit else amt
                    else:
                        final_amt = amt if is_debit else -amt
                        
                    if code_str in accounts:
                        accounts[code_str]['amount'] += final_amt
                    else:
                        accounts[code_str] = {
                            'name': str(name_val).strip() if name_val else '',
                            'amount': final_amt
                        }
            
            # 遍歷所有列 (假設第一列是表頭，我們從第2列開始，或是直接判定資料即可)
            for row in sheet.iter_rows(values_only=True):
                if len(row) >= 6:
                    # 借方: code, name, amount = row[0], row[1], row[2]
                    process_row_cell(row[0], row[1], row[2], is_debit=True)
                    # 貸方: code, name, amount = row[3], row[4], row[5]
                    process_row_cell(row[3], row[4], row[5], is_debit=False)
                    
            if not accounts:
                return JsonResponse({'success': False, 'error': '找不到符合的 4~8 開頭科目，請確認 Excel 格式。'}, status=400)
                
            # 清除舊的調整明細
            filing, _ = CorporateTaxFiling.objects.get_or_create(year_record=year_record)
            filing.adjustments.all().delete()
            
            # 建立新的明細
            entries = []
            for code, data in accounts.items():
                entries.append(TaxAdjustmentEntry(
                    filing=filing,
                    account_code=code,
                    account_name=data['name'],
                    book_amount=data['amount'],
                    excluded_amount=0,
                ))
            
            TaxAdjustmentEntry.objects.bulk_create(entries)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': f"解析錯誤: {str(e)}"}, status=400)
