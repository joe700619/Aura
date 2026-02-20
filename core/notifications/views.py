from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from .models import EmailTemplate, LineMessageTemplate
from .services import EmailService, LineService
from core.services.document import DocumentService

class GetEmailTemplatesView(LoginRequiredMixin, View):
    def get(self, request):
        # Filter templates by content_type if provided
        app_label = request.GET.get('app_label')
        model_name = request.GET.get('model_name')
        
        queryset = EmailTemplate.objects.filter(is_active=True)
        
        if app_label and model_name:
            try:
                # Get the ContentType for the specified model
                content_type = ContentType.objects.get(app_label=app_label, model=model_name)
                # Filter: either this specific content_type OR null (global templates)
                queryset = queryset.filter(Q(model_content_type=content_type) | Q(model_content_type__isnull=True))
            except ContentType.DoesNotExist:
                pass  # If model doesn't exist, return all templates
        
        templates = queryset.values('id', 'code', 'name', 'subject')
        return JsonResponse({'templates': list(templates)})

class SendEmailView(LoginRequiredMixin, View):
    def post(self, request, app_label, model_name, object_id):
        template_id = request.POST.get('template_id')
        
        try:
            template = EmailTemplate.objects.get(pk=template_id)
        except EmailTemplate.DoesNotExist:
            return JsonResponse({'error': 'Template not found'}, status=404)

        try:
            model = apps.get_model(app_label, model_name)
            obj = model.objects.get(pk=object_id)
        except LookupError:
             return JsonResponse({'error': 'Model not found'}, status=404)
        except model.DoesNotExist:
             return JsonResponse({'error': 'Object not found'}, status=404)

        # Build Context (Reuse DocumentService's logic)
        context = DocumentService._build_context(obj)
        
        # recipient resolution
        # Try to find an email field
        recipient = getattr(obj, 'email', None)
        if not recipient and hasattr(obj, 'contacts'):
             # Try first contact
            first_contact = obj.contacts.first()
            if first_contact:
                recipient = getattr(first_contact, 'email', None)

        if not recipient:
             return JsonResponse({'error': 'No email address found for this object'}, status=400)

        # Get Schedule Time
        schedule_time_str = request.POST.get('schedule_time')
        schedule_time = None
        
        if schedule_time_str:
            try:
                
                # Parse the string "YYYY-MM-DDTHH:MM" to a naive datetime
                naive_dt = parse_datetime(schedule_time_str)
                
                if naive_dt:
                    # Make it aware (assume current active timezone, which is usually set by middleware or settings)
                    # If USE_TZ is True, make_aware converts naive to aware in default timezone (or current activated one)
                    schedule_time = timezone.make_aware(naive_dt)
            except Exception as e:
                pass # Invalid format, ignore or handle error

        # Send
        success = EmailService.send_email(template.code, [recipient], context, schedule_time=schedule_time)
        
        if success:
            msg = 'Email scheduled successfully' if schedule_time else 'Email sent successfully'
            return JsonResponse({'message': msg})
        else:
            return JsonResponse({'error': 'Failed to send email'}, status=500)

class GetLineTemplatesView(LoginRequiredMixin, View):
    def get(self, request):
        # Filter templates by content_type if provided
        app_label = request.GET.get('app_label')
        model_name = request.GET.get('model_name')
        
        queryset = LineMessageTemplate.objects.filter(is_active=True)
        
        if app_label and model_name:
            try:
                # Get the ContentType for the specified model
                content_type = ContentType.objects.get(app_label=app_label, model=model_name)
                # Filter: either this specific content_type OR null (global templates)
                queryset = queryset.filter(Q(model_content_type=content_type) | Q(model_content_type__isnull=True))
            except ContentType.DoesNotExist:
                pass  # If model doesn't exist, return all templates
        
        templates = queryset.values('id', 'code', 'name', 'message_type')
        return JsonResponse({'templates': list(templates)})

class SendLineView(LoginRequiredMixin, View):
    def post(self, request, app_label, model_name, object_id):
        template_id = request.POST.get('template_id')
        
        try:
            template = LineMessageTemplate.objects.get(pk=template_id)
        except LineMessageTemplate.DoesNotExist:
            return JsonResponse({'error': 'Template not found'}, status=404)

        try:
            model = apps.get_model(app_label, model_name)
            obj = model.objects.get(pk=object_id)
        except LookupError:
             return JsonResponse({'error': 'Model not found'}, status=404)
        except model.DoesNotExist:
             return JsonResponse({'error': 'Object not found'}, status=404)

        # Build Context
        context = DocumentService._build_context(obj)
        
        # recipient resolution
        # Try to find a line_id field (e.g. 'line_id', 'line_user_id')
        recipient_id = getattr(obj, 'line_id', None)
        if not recipient_id and hasattr(obj, 'contacts'):
            # Try first contact's line_id
            first_contact = obj.contacts.first()
            if first_contact:
                recipient_id = getattr(first_contact, 'line_id', None)

        if not recipient_id:
             return JsonResponse({'error': 'No Line ID found for this object'}, status=400)

        # Send
        success = LineService.send_message(template.code, recipient_id, context)
        
        if success:
            return JsonResponse({'message': 'Line message sent successfully'})
        else:
            return JsonResponse({'error': 'Failed to send Line message'}, status=500)

class SendBulkEmailView(LoginRequiredMixin, View):
    def post(self, request, app_label, model_name):
        template_id = request.POST.get('template_id')
        object_ids_str = request.POST.get('object_ids', '')
        
        if not object_ids_str:
            return JsonResponse({'error': 'No objects selected'}, status=400)
            
        object_ids = [int(id) for id in object_ids_str.split(',') if id.isdigit()]
        
        if not object_ids:
             return JsonResponse({'error': 'Invalid object IDs'}, status=400)

        try:
            template = EmailTemplate.objects.get(pk=template_id)
        except EmailTemplate.DoesNotExist:
            return JsonResponse({'error': 'Template not found'}, status=404)

        try:
            model = apps.get_model(app_label, model_name)
            objects = model.objects.filter(pk__in=object_ids)
        except LookupError:
             return JsonResponse({'error': 'Model not found'}, status=404)

        # Get Schedule Time
        schedule_time_str = request.POST.get('schedule_time')
        schedule_time = None
        if schedule_time_str:
            try:
                from django.utils.dateparse import parse_datetime
                from django.utils import timezone
                naive_dt = parse_datetime(schedule_time_str)
                if naive_dt:
                    schedule_time = timezone.make_aware(naive_dt)
            except Exception:
                pass

        success_count = 0
        fail_count = 0
        
        for obj in objects:
            # Context and Recipient Logic (Duplicated from SendEmailView - ideally refactor to helper)
            context = DocumentService._build_context(obj)
            recipient = getattr(obj, 'email', None)
            if not recipient and hasattr(obj, 'contacts'):
                first_contact = obj.contacts.first()
                if first_contact:
                    recipient = getattr(first_contact, 'email', None)
            
            if recipient:
                if EmailService.send_email(template.code, [recipient], context, schedule_time=schedule_time):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                 fail_count += 1 # No recipient found counts as fail

        return JsonResponse({
            'message': f'Processed {len(object_ids)} items. Success: {success_count}, Failed: {fail_count}',
            'success_count': success_count,
            'fail_count': fail_count
        })

class SendBulkLineView(LoginRequiredMixin, View):
    def post(self, request, app_label, model_name):
        template_id = request.POST.get('template_id')
        object_ids_str = request.POST.get('object_ids', '')

        if not object_ids_str:
            return JsonResponse({'error': 'No objects selected'}, status=400)

        object_ids = [int(id) for id in object_ids_str.split(',') if id.isdigit()]

        if not object_ids:
             return JsonResponse({'error': 'Invalid object IDs'}, status=400)
        
        try:
            template = LineMessageTemplate.objects.get(pk=template_id)
        except LineMessageTemplate.DoesNotExist:
            return JsonResponse({'error': 'Template not found'}, status=404)

        try:
            model = apps.get_model(app_label, model_name)
            objects = model.objects.filter(pk__in=object_ids)
        except LookupError:
             return JsonResponse({'error': 'Model not found'}, status=404)

        success_count = 0
        fail_count = 0

        for obj in objects:
            context = DocumentService._build_context(obj)
            recipient_id = getattr(obj, 'line_id', None)
            if not recipient_id and hasattr(obj, 'contacts'):
                 first_contact = obj.contacts.first()
                 if first_contact:
                     recipient_id = getattr(first_contact, 'line_id', None)
            
            if recipient_id:
                if LineService.send_message(template.code, recipient_id, context):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1

        return JsonResponse({
            'message': f'Processed {len(object_ids)} items. Success: {success_count}, Failed: {fail_count}',
            'success_count': success_count,
            'fail_count': fail_count
        })
