from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from .models import EmailTemplate, LineMessageTemplate
from .services import EmailService, LineService
from core.services.document import DocumentService

# ── Line Webhook 需要的額外 imports ──
import re
import json
import hashlib
import hmac
import base64
import logging
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

# 群組綁定暗號格式：「綁定 #12345678」
_BIND_ROOM_RE = re.compile(r'^綁定\s*#(\d{8})$')

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
        # 先找 room_id (群組優先)，再找 line_id (個人)
        recipient_id = getattr(obj, 'room_id', None)
        if not recipient_id:
            recipient_id = getattr(obj, 'line_id', None)
            
        if not recipient_id and hasattr(obj, 'contacts'):
            # Try first contact's line_id
            first_contact = obj.contacts.first()
            if first_contact:
                recipient_id = getattr(first_contact, 'line_id', None)

        if not recipient_id and hasattr(obj, 'customer') and obj.customer:
            customer = obj.customer
            recipient_id = getattr(customer, 'room_id', None) or getattr(customer, 'line_id', None)

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
            recipient_id = getattr(obj, 'room_id', None)
            if not recipient_id:
                recipient_id = getattr(obj, 'line_id', None)
                
            if not recipient_id and hasattr(obj, 'contacts'):
                 first_contact = obj.contacts.first()
                 if first_contact:
                     recipient_id = getattr(first_contact, 'line_id', None)

            if not recipient_id and hasattr(obj, 'customer') and obj.customer:
                customer = obj.customer
                recipient_id = getattr(customer, 'room_id', None) or getattr(customer, 'line_id', None)

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


def _get_system_param(key):
    """從 SystemParameter 取得系統設定值"""
    from modules.system_config.models import SystemParameter
    try:
        return SystemParameter.objects.get(key=key).value
    except SystemParameter.DoesNotExist:
        return None


@method_decorator(csrf_exempt, name='dispatch')
class LineWebhookView(View):
    """
    接收 Line Platform 的所有 Webhook Events（統一入口）。

    支援指令：
    - 群組 / 聊天室：「綁定 #統一編號」→ 寫入 BookkeepingClient.room_id
    - 個人訊息：「綁定」       → 引導 LIFF 綁定流程 (Route A，待實作)
    - 個人訊息：「打卡 / 上班 / 下班」→ 呼叫 HR 打卡模組
    """

    def post(self, request):
        # 1. 驗證 Line 簽名
        channel_secret = _get_system_param('LINE_CHANNEL_SECRET')
        if channel_secret:
            signature = request.headers.get('X-Line-Signature', '')
            body = request.body
            mac = hmac.new(
                channel_secret.encode('utf-8'),
                body,
                hashlib.sha256,
            ).digest()
            expected = base64.b64encode(mac).decode('utf-8')
            if signature != expected:
                logger.warning("Line webhook: signature mismatch")
                return HttpResponse(status=403)

        # 2. 解析 events
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        for event in data.get('events', []):
            if event.get('type') != 'message':
                continue
            if event.get('message', {}).get('type') != 'text':
                continue

            text = event['message']['text'].strip()
            source = event.get('source', {})
            source_type = source.get('type', '')   # 'user' / 'group' / 'room'
            user_id = source.get('userId', '')
            reply_token = event.get('replyToken', '')

            # ── 路線 B：群組 / 聊天室暗號 → 綁定 room_id ──
            if source_type in ('group', 'room'):
                room_id = source.get('groupId') or source.get('roomId', '')
                m = _BIND_ROOM_RE.match(text)
                if m:
                    tax_id = m.group(1)
                    reply_msg = self._bind_room(tax_id, room_id)
                    if reply_token:
                        self._reply(reply_token, [reply_msg])
                continue  # 群組的其他訊息不處理

            # ── 以下為個人訊息 ──

            # 路線 A：引導 LIFF 綁定
            if text == '綁定':
                if reply_token:
                    liff_id = _get_system_param('LINE_LIFF_ID')
                    if liff_id:
                        liff_url = f"https://liff.line.me/{liff_id}"
                        text_msg = f"請點選以下連結，完成帳號綁定：\n{liff_url}"
                    else:
                        text_msg = "系統尚未設定 LIFF ID，無法進行綁定作業。"
                    
                    self._reply(reply_token, [{
                        'type': 'text',
                        'text': text_msg,
                    }])
                continue

            # 員工打卡指令（委派給 HR 模組）
            if text in ('打卡', '上班', '下班', 'clock', 'punch'):
                try:
                    from modules.hr.services.line_clock import process_line_clock, build_reply_message
                    result = process_line_clock(user_id)
                    reply_msg = build_reply_message(result)
                    if reply_token:
                        self._reply(reply_token, [reply_msg])
                except Exception as e:
                    logger.error(f"Line clock error: {e}")

        return HttpResponse(status=200)

    def _bind_room(self, tax_id: str, room_id: str) -> dict:
        """
        以統一編號找 Customer（基本資料，主資料來源），寫入 room_id。
        BookkeepingClient / Registration 等資料衍生自 Customer，不需要單獨更新。
        """
        from modules.basic_data.models import Customer
        try:
            cust = Customer.objects.get(tax_id=tax_id)
            cust.room_id = room_id
            cust.save(update_fields=['room_id', 'updated_at'])
            logger.info(f"[Line綁定] Customer room_id 綁定成功：{cust.name}（{tax_id}）→ {room_id}")
            return {
                'type': 'text',
                'text': f'✅ 群組已綁定\n公司：{cust.name}\n統編：{tax_id}\n往後本群組可接收通知訊息。',
            }
        except Customer.DoesNotExist:
            logger.warning(f"[Line綁定] 找不到統編 {tax_id}")
            return {'type': 'text', 'text': f'❌ 找不到統編 {tax_id} 的客戶資料，請確認統一編號是否正確。'}
        except Exception as e:
            logger.error(f"[Line綁定] 寫入 room_id 失敗：{e}")
            return {'type': 'text', 'text': '❌ 綁定失敗，請聯絡系統管理員。'}

    def _reply(self, reply_token: str, messages: list):
        """透過 Line Reply Message API 回覆。"""
        access_token = _get_system_param('LINE_CHANNEL_ACCESS_TOKEN')
        if not access_token:
            logger.error("LINE_CHANNEL_ACCESS_TOKEN not configured")
            return
        try:
            resp = requests.post(
                'https://api.line.me/v2/bot/message/reply',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}',
                },
                json={'replyToken': reply_token, 'messages': messages},
                timeout=5
            )
            if resp.status_code != 200:
                logger.error(f"Line reply failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Line reply error: {e}")

class LineBindingPageView(View):
    """
    提供給 LIFF 的前端綁定頁面 (Route A)。
    此頁面不需要登入，靠 LIFF SDK 在前端取得使用者 line_user_id。
    """
    def get(self, request):
        liff_id = _get_system_param('LINE_LIFF_ID')
        return render(request, 'notifications/line_binding.html', {
            'liff_id': liff_id or ''
        })

class LineBindingSubmitView(View):
    """
    處理 LIFF 前端提交的綁定請求。
    接收 tax_id 和 line_user_id，找到 Customer 並更新 line_id。
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            tax_id = data.get('tax_id', '').strip()
            line_user_id = data.get('line_user_id', '').strip()

            if not tax_id or not line_user_id:
                return JsonResponse({'success': False, 'error': '資料不完整'})

            from modules.basic_data.models import Customer
            try:
                cust = Customer.objects.get(tax_id=tax_id)
                cust.line_id = line_user_id
                cust.save(update_fields=['line_id', 'updated_at'])
                logger.info(f"[Line綁定] line_id 綁定成功：{cust.name}（{tax_id}）→ {line_user_id}")
                
                # 發送 Push Message 通知成功
                try:
                    from linebot import LineBotApi
                    from linebot.models import TextSendMessage
                    access_token = _get_system_param('LINE_CHANNEL_ACCESS_TOKEN')
                    if access_token:
                        line_bot_api = LineBotApi(access_token)
                        line_bot_api.push_message(
                            line_user_id,
                            TextSendMessage(text=f"✅ 帳號綁定成功\n公司：{cust.name}\n統編：{tax_id}\n感謝您的綁定！")
                        )
                except Exception as e:
                    logger.error(f"[Line綁定] Push message failed: {e}")

                return JsonResponse({'success': True})
            except Customer.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'找不到統編 {tax_id} 的客戶資料'})
        except Exception as e:
            logger.error(f"[Line綁定] Submit API failed: {e}")
            return JsonResponse({'success': False, 'error': '系統錯誤'})

