from django.shortcuts import render
from django.apps import apps
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from import_export.resources import modelresource_factory
from core.resources import DynamicResource
from core.models import DocumentTemplate
from django.contrib.contenttypes.models import ContentType
from django.db import models
import json

def dashboard(request):
    context = {}
    if request.user.is_authenticated:
        from modules.workflow.services import get_pending_approvals
        pending_approvals = get_pending_approvals(request.user)
        context['pending_approvals'] = pending_approvals
        context['pending_count'] = pending_approvals.count()
        
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
