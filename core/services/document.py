from io import BytesIO
from django.db.models import Model
from docxtpl import DocxTemplate
from core.models import DocumentTemplate

class DocumentService:
    @staticmethod
    def render_template(template: DocumentTemplate, context_object: Model, output_format='docx') -> BytesIO:
        """
        Renders a Word document using the given template and context object.
        If output_format is 'pdf', calculates the pdf using docx2pdf.
        """
        doc = DocxTemplate(template.file)
        
        # Build context from the object
        context = DocumentService._build_context(context_object)
        
        doc.render(context)
        
        output = BytesIO()
        
        if output_format == 'pdf':
            import os
            import tempfile
            from docx2pdf import convert
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_docx:
                tmp_docx_path = tmp_docx.name
                doc.save(tmp_docx_path)
            
            tmp_pdf_path = tmp_docx_path.replace('.docx', '.pdf')
            
            try:
                # Convert to PDF
                # pythoncom is needed for some windows com interactions in threads, 
                # but docx2pdf handles some of it. 
                # If running in a server thread, might need pythoncom.CoInitialize()
                convert(tmp_docx_path, tmp_pdf_path)
                
                with open(tmp_pdf_path, 'rb') as f:
                    output.write(f.read())
            finally:
                # Cleanup
                if os.path.exists(tmp_docx_path):
                    os.remove(tmp_docx_path)
                if os.path.exists(tmp_pdf_path):
                    os.remove(tmp_pdf_path)
        else:
            doc.save(output)
            
        output.seek(0)
        return output

    @staticmethod
    def _build_context(obj: Model) -> dict:
        """
        Converts a model instance into a dictionary context.
        """
        context = {}
        
        # Add basic fields
        for field in obj._meta.fields:
            value = getattr(obj, field.name)
            
            # Handle choices display
            if field.choices:
                display_value = getattr(obj, f"get_{field.name}_display")()
                context[f"{field.name}_display"] = display_value
                
            context[field.name] = value

        # Handle related objects (simple ForwardManyToOne, e.g. customer.name)
        # docxtpl can handle access like {{ customer.name }} if passed the object itself?
        # Yes, commonly we can just pass the object itself?
        # But docxtpl uses jinja2, which might not like Django's lazy loading or some field types.
        # It's safer to convert to dict or rely on `docxtpl` handling.
        # Actually, passing the object directly usually works for simple access.
        # Let's pass the object as 'object' or 'obj' and also spread its fields.
        
        context['obj'] = obj

        # ClientBill: 帳單明細、代墊款明細、合計、支付網址
        if obj.__class__.__name__ == 'ClientBill':
            import json as _json

            # ── 帳單明細（bill_items）──
            try:
                quotation_data = obj.quotation_data or []
                if isinstance(quotation_data, str):
                    quotation_data = _json.loads(quotation_data)
                bill_items = []
                for i, item in enumerate(quotation_data, start=1):
                    if not isinstance(item, dict):
                        continue
                    amount = int(item.get('amount', 0) or 0)
                    bill_items.append({
                        'no':          i,
                        'service_code': item.get('service_code', ''),
                        'service_name': item.get('service_name', ''),
                        'amount':       amount,
                        'amount_fmt':   f"{amount:,}",
                        'remark':       item.get('remark', ''),
                    })
                context['bill_items'] = bill_items
                context['service_fee_total'] = sum(it['amount'] for it in bill_items)
                context['service_fee_total_fmt'] = f"{context['service_fee_total']:,}"
            except Exception:
                context['bill_items'] = []
                context['service_fee_total'] = 0
                context['service_fee_total_fmt'] = '0'

            # ── 代墊款明細（advance_items）──
            try:
                advance_data = obj.advance_payment_data or []
                if isinstance(advance_data, str):
                    advance_data = _json.loads(advance_data)
                advance_items = []
                for i, item in enumerate(advance_data, start=1):
                    if not isinstance(item, dict):
                        continue
                    amount = int(item.get('amount', 0) or 0)
                    advance_items.append({
                        'no':           i,
                        'advance_no':   item.get('advance_no', ''),
                        'date':         item.get('date', ''),
                        'reason':       item.get('reason', ''),
                        'payment_type': item.get('payment_type', ''),
                        'amount':       amount,
                        'amount_fmt':   f"{amount:,}",
                    })
                context['advance_items'] = advance_items
                context['advance_total'] = sum(it['amount'] for it in advance_items)
                context['advance_total_fmt'] = f"{context['advance_total']:,}"
            except Exception:
                context['advance_items'] = []
                context['advance_total'] = 0
                context['advance_total_fmt'] = '0'

            # ── 格式化合計 ──
            try:
                context['total_amount_fmt'] = f"{int(obj.total_amount):,}"
            except Exception:
                context['total_amount_fmt'] = str(obj.total_amount)

            # ── 第三方支付網址 ──
            try:
                from modules.payment.models import PaymentTransaction
                tx = PaymentTransaction.objects.filter(
                    related_app='bookkeeping',
                    related_model='ClientBill',
                    related_id=str(obj.pk),
                ).order_by('-created_at').first()
                if tx:
                    context['pay_url'] = f"/payment/bill/{tx.merchant_trade_no}/"
                else:
                    context['pay_url'] = ''
            except Exception:
                context['pay_url'] = ''

        # Receivable: 服務項目明細、收款記錄、計算屬性
        if obj.__class__.__name__ == 'Receivable':
            import json as _json

            # ── 服務項目明細（quotation_items）──
            try:
                quotation_data = obj.quotation_data or []
                if isinstance(quotation_data, str):
                    quotation_data = _json.loads(quotation_data)
                quotation_items = []
                for i, item in enumerate(quotation_data, start=1):
                    if not isinstance(item, dict):
                        continue
                    amount = int(item.get('amount', 0) or 0)
                    quotation_items.append({
                        'no':           i,
                        'service_code': item.get('service_code', ''),
                        'service_name': item.get('service_name', ''),
                        'amount':       amount,
                        'amount_fmt':   f"{amount:,}",
                        'remark':       item.get('remark', ''),
                    })
                context['quotation_items'] = quotation_items
            except Exception:
                context['quotation_items'] = []

            # ── 計算屬性（Python property → 展平為頂層變數）──
            try:
                context['total_amount']          = obj.total_amount
                context['total_amount_fmt']      = f"{int(obj.total_amount):,}"
                context['paid_amount']           = obj.paid_amount
                context['paid_amount_fmt']       = f"{int(obj.paid_amount):,}"
                context['outstanding_balance']   = obj.outstanding_balance
                context['outstanding_balance_fmt'] = f"{int(obj.outstanding_balance):,}"
                context['status']                = obj.status
            except Exception:
                pass

            # ── 收款紀錄（collections）──
            try:
                collections = []
                for i, c in enumerate(obj.collections.filter(is_deleted=False).order_by('created_at'), start=1):
                    collections.append({
                        'no':     i,
                        'date':   c.date,
                        'amount': int(c.total),
                        'amount_fmt': f"{int(c.total):,}",
                        'method': c.get_method_display() if hasattr(c, 'get_method_display') else c.method,
                    })
                context['collections'] = collections
            except Exception:
                context['collections'] = []

        # We can also add helpers or specific related data
        # For Customer, add contacts
        if hasattr(obj, 'contacts'):
            context['contacts'] = obj.contacts.all()

        # ShareholderRegister: serialize equity transactions for docxtpl loops
        if hasattr(obj, 'equity_transactions'):
            tx_list = []
            for tx in obj.equity_transactions.order_by('transaction_date', 'created_at'):
                tx_list.append({
                    'shareholder_name': tx.shareholder_name,
                    'shareholder_id_number': tx.shareholder_id_number,
                    'transaction_date': tx.transaction_date,
                    'transaction_reason': tx.transaction_reason,
                    'transaction_reason_display': tx.get_transaction_reason_display(),
                    'stock_type': tx.stock_type,
                    'stock_type_display': tx.get_stock_type_display(),
                    'share_count': int(tx.share_count),
                    'unit_price': float(tx.unit_price),
                    'total_amount': float(tx.total_amount),
                })
            context['equity_transactions'] = tx_list
            context['total_shares'] = sum(tx['share_count'] for tx in tx_list)
            context['total_amount'] = sum(tx['total_amount'] for tx in tx_list)

        # SealProcurement: items
        if hasattr(obj, 'items') and hasattr(obj, 'seal_cost_subtotal'):
            items_list = []
            for item in obj.items.filter(is_deleted=False):
                items_list.append({
                    'movement_type': item.movement_type,
                    'movement_type_display': item.get_movement_type_display(),
                    'seal_type': item.seal_type,
                    'seal_type_display': item.get_seal_type_display(),
                    'quantity': item.quantity,
                    'name_or_address': item.name_or_address,
                    'unit_price': int(item.unit_price),
                    'subtotal': int(item.subtotal),
                    'is_absorbed_by_customer': item.is_absorbed_by_customer,
                })
            context['items'] = items_list

        # ShareholderRegister: directors
        if hasattr(obj, 'directors'):
            director_list = []
            for d in obj.directors.order_by('order', 'id'):
                director_list.append({
                    'title': d.title,
                    'title_display': d.get_title_display(),
                    'name': d.name,
                    'id_number': d.id_number,
                    'nationality': d.nationality,
                    'birth_date': d.birth_date,
                    'shares_held': d.shares_held,
                    'entity_name': d.entity_name,
                    'entity_no': d.entity_no,
                })
            context['directors'] = director_list

        return context

    @staticmethod
    def get_model_variables(app_label: str, model_name: str) -> list:
        """
        Returns a list of available variables for a given model.
        """
        from django.apps import apps
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return []

        variables = []
        
        # Standard fields
        for field in model._meta.fields:
            variables.append({
                'name': field.name,
                'label': field.verbose_name,
                'type': field.get_internal_type()
            })
            
            # Add _display for choices
            if field.choices:
                variables.append({
                    'name': f"{field.name}_display",
                    'label': f"{field.verbose_name} (顯示名稱)",
                    'type': 'ChoiceDisplay'
                })

        # Related objects (reverse relations)
        for relation in model._meta.related_objects:
            if relation.one_to_many:
                variables.append({
                    'name': relation.get_accessor_name(),
                    'label': f"{relation.related_model._meta.verbose_name} (列表)",
                    'type': 'List'
                })
                
        return variables
