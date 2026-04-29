from django.shortcuts import render
from django.apps import apps
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from import_export.resources import modelresource_factory
from core.resources import DynamicResource
from core.models import DocumentTemplate
from django.contrib.contenttypes.models import ContentType
from django.db import models
import json

@login_required
def dashboard(request):
    if getattr(request.user, 'role', None) == 'EXTERNAL':
        from django.shortcuts import redirect
        return redirect('client_portal:dashboard')

    context = {}
    if request.user.is_authenticated:
        from modules.workflow.services import get_pending_approvals
        pending_approvals = get_pending_approvals(request.user)
        context['pending_approvals'] = pending_approvals
        context['pending_count'] = pending_approvals.count()
        
        # ── 員工個人資料區（打卡、記帳件數等）──
        employee = getattr(request.user, 'employee_profile', None)
        context['employee'] = employee

        if employee:
            try:
                from modules.bookkeeping.models import BookkeepingClient
                context['bookkeeping_count'] = BookkeepingClient.objects.filter(bookkeeping_assistant=employee).count()
            except Exception:
                context['bookkeeping_count'] = 0

            context['registration_count'] = 0

            try:
                from modules.bookkeeping.models import ClientBill
                from django.db.models import Sum
                draft_total = ClientBill.objects.filter(
                    status=ClientBill.BillStatus.DRAFT,
                    client__bookkeeping_assistant=employee,
                    is_deleted=False,
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                context['unbilled_amount'] = draft_total
            except Exception:
                context['unbilled_amount'] = 0

            try:
                from modules.bookkeeping.models import BookkeepingPeriod
                context['not_started_periods'] = BookkeepingPeriod.objects.filter(
                    year_record__client__bookkeeping_assistant=employee,
                    account_status=BookkeepingPeriod.AccountStatus.NOT_STARTED
                ).select_related('year_record__client').order_by('year_record__year', 'period_start_month')
            except Exception:
                context['not_started_periods'] = []

            try:
                from modules.hr.models import AttendanceRecord
                from django.utils import timezone
                today = timezone.localdate()
                context['today'] = today
                context['today_record'] = AttendanceRecord.objects.filter(
                    employee=employee, date=today, is_deleted=False
                ).first()
            except Exception:
                from django.utils import timezone
                context['today'] = timezone.localdate()
                context['today_record'] = None
        else:
            context['bookkeeping_count'] = 0
            context['registration_count'] = 0
            context['unbilled_amount'] = 0
            context['not_started_periods'] = []
            from django.utils import timezone
            context['today'] = timezone.localdate()
            context['today_record'] = None

        # ── 記帳進度圖初始參數 ──
        from datetime import date as _date
        _today = _date.today()
        context['roc_year']   = _today.year - 1911
        context['roc_month']  = _today.month

        # ── 系統布告欄（所有登入者皆顯示）──
        try:
            from modules.administrative.models.bulletin import SystemBulletin
            context['system_bulletins'] = SystemBulletin.objects.filter(
                status='active'
            ).order_by('-publish_date', '-created_at')[:5]
        except Exception:
            context['system_bulletins'] = []

        # ── 年度稅務行事曆（所有登入者皆顯示）──
        try:
            from datetime import date
            from modules.administrative.models.tax_timeline import TaxTaskInstance
            current_year = date.today().year
            current_month = date.today().month
            tasks = TaxTaskInstance.objects.filter(year=current_year).select_related('template')
            timeline_data = []
            for m in range(1, 13):
                month_tasks = tasks.filter(month=m)
                has_alert = any(not t.is_completed and t.deadline < date.today() for t in month_tasks)
                tasks_info = []
                for t in month_tasks:
                    progress = (t.completed_clients / t.total_clients * 100) if t.total_clients > 0 else 0
                    progress = max(0, min(100, progress))
                    tasks_info.append({
                        "id": t.id,
                        "title": t.title,
                        "progress": round(progress, 1),
                        "deadline": t.deadline,
                        "is_completed": t.is_completed,
                        "remarks": t.remarks,
                    })
                timeline_data.append({
                    "month": m,
                    "is_current": m == current_month,
                    "has_alert": has_alert,
                    "tasks": tasks_info,
                    "uncompleted_count": sum(1 for t in month_tasks if not t.is_completed),
                })
            context['timeline'] = timeline_data
        except Exception:
            context['timeline'] = []
        
    return render(request, 'dashboard.html', context)

class ExportFieldsView(LoginRequiredMixin, View):
    def get(self, request, app_label, model_name):
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return JsonResponse({'error': 'Model not found'}, status=404)

        # Create a temporary resource to introspect fields
        resource_factory = modelresource_factory(model=model, resource_class=DynamicResource)
        resource = resource_factory()
        
        fields = []
        for field in resource.get_export_fields():
            # Try to get the verbose name from the model field
            label = field.column_name
            try:
                model_field = model._meta.get_field(field.attribute)
                label = getattr(model_field, 'verbose_name', field.column_name)
            except Exception:
                pass
            
            fields.append({
                'name': field.attribute,
                'label': str(label)
            })

        return JsonResponse({'fields': fields})

class ExportDataView(LoginRequiredMixin, View):
    def post(self, request, app_label, model_name):
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return JsonResponse({'error': 'Model not found'}, status=404)

        # Handle both JSON and Form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            selected_fields = data.get('fields', [])
            ids = data.get('ids', [])
        else:
            # Try various formats for fields and ids
            selected_fields = request.POST.getlist('fields[]') or request.POST.getlist('fields')
            ids = request.POST.getlist('ids[]') or request.POST.getlist('ids')
            
        try:
            resource_class = modelresource_factory(model=model, resource_class=DynamicResource)
            resource = resource_class(fields_to_export=selected_fields if selected_fields else None)
            
            queryset = model.objects.all()
            if ids:
                queryset = queryset.filter(pk__in=ids)

            import io
            import urllib.parse
            # Export data
            dataset = resource.export(queryset)
            
            # Use xlsx format
            xlsx_data = dataset.xlsx
            
            response = HttpResponse(
                xlsx_data,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            filename = f"{model_name}_export.xlsx"
            encoded_filename = urllib.parse.quote(filename)
            response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}; filename=\"{filename}\""
            
            return response
        except Exception as e:
            import traceback
            traceback.print_exc()
            return HttpResponse(f"Error exporting data: {str(e)}", status=500)

class GetTemplatesView(LoginRequiredMixin, View):
    def get(self, request, app_label, model_name):
        try:
            model = apps.get_model(app_label, model_name)
            content_type = ContentType.objects.get_for_model(model)
        except (LookupError, ContentType.DoesNotExist):
            return JsonResponse({'error': 'Model not found'}, status=404)

        # Get templates for this model OR global templates (null content_type)
        templates = DocumentTemplate.objects.filter(
            models.Q(model_content_type=content_type) | models.Q(model_content_type__isnull=True)
        ).values('id', 'name', 'description')

        return JsonResponse({'templates': list(templates)})


class GenerateDocumentView(LoginRequiredMixin, View):
    def post(self, request, template_id, app_label, model_name, object_id):
        try:
            template = DocumentTemplate.objects.get(pk=template_id)
        except DocumentTemplate.DoesNotExist:
            return JsonResponse({'error': 'Template not found'}, status=404)
            
        try:
            model = apps.get_model(app_label, model_name)
            obj = model.objects.get(pk=object_id)
        except (LookupError, model.DoesNotExist):
            return JsonResponse({'error': 'Object not found'}, status=404)
        
        output_format = request.POST.get('format', 'docx')
        
        try:
            from core.services.document import DocumentService
            buffer = DocumentService.render_template(template, obj, output_format=output_format)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        filename = f"{template.name}_{object_id}.{output_format}"
        # Handle non-ascii filenames
        import urllib.parse
        filename = urllib.parse.quote(filename)
        
        content_type = 'application/pdf' if output_format == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type=content_type
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

def get_model_variables(request, app_label, model_name):
    from core.services.document import DocumentService
    variables = DocumentService.get_model_variables(app_label, model_name)
    return JsonResponse({'variables': variables})
