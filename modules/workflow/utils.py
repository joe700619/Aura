from django.conf import settings
from core.notifications.models import EmailLog
from core.notifications.services import EmailService
import logging

logger = logging.getLogger(__name__)

def send_approval_notification(approval_request, action_type, comments='', next_approver=None):
    """
    發送核准流程相關通知
    
    Args:
        approval_request: ApprovalRequest instance
        action_type: 'SUBMIT', 'APPROVE', 'REJECT', 'RETURN', 'CANCEL'
        comments: 相關意見
        next_approver: 下一位核准者 (User instance)，僅在 action_type 為 SUBMIT 或 APPROVE 時可能用到
    """
    subject = ""
    message = ""
    recipient_list = []
    
    requester_name = approval_request.requester.get_full_name()
    workflow_name = approval_request.workflow_template.name
    obj_desc = str(approval_request.content_object)
    
    try:
        if action_type == 'SUBMIT':
            # 通知第一位核准者
             if next_approver and next_approver.email:
                subject = f"[待核准] {workflow_name} - {requester_name}"
                message = f"""
                您好 {next_approver.get_full_name()}，
                
                {requester_name} 提交了一份 {workflow_name} 申請，需要您的核准。
                
                項目：{obj_desc}
                備註：{comments}
                
                請登入系統進行審核。
                """
                recipient_list = [next_approver.email]
                
        elif action_type == 'APPROVE':
            if approval_request.status == 'APPROVED':
                # 最終核准，通知申請人
                if approval_request.requester.email:
                    subject = f"[已核准] {workflow_name} - {obj_desc}"
                    message = f"""
                    您好 {requester_name}，
                    
                    恭喜！您的 {workflow_name} 申請已完成最終核准。
                    
                    項目：{obj_desc}
                    核准意見：{comments}
                    """
                    recipient_list = [approval_request.requester.email]
            elif next_approver and next_approver.email:
                # 通知下一位核准者
                subject = f"[待核准] {workflow_name} - {requester_name}"
                message = f"""
                您好 {next_approver.get_full_name()}，
                
                {requester_name} 的 {workflow_name} 申請已通過上一級核准，現在需要您的核准。
                
                項目：{obj_desc}
                上一級意見：{comments}
                
                請登入系統進行審核。
                """
                recipient_list = [next_approver.email]
                
        elif action_type == 'REJECT':
            # 通知申請人
            if approval_request.requester.email:
                subject = f"[已駁回] {workflow_name} - {obj_desc}"
                message = f"""
                您好 {requester_name}，
                
                很遺憾，您的 {workflow_name} 申請已被駁回。
                
                項目：{obj_desc}
                駁回原因：{comments}
                """
                recipient_list = [approval_request.requester.email]
                
        elif action_type == 'RETURN':
            # 通知申請人
            if approval_request.requester.email:
                subject = f"[需補件/修改] {workflow_name} - {obj_desc}"
                message = f"""
                您好 {requester_name}，
                
                您的 {workflow_name} 申請已被退回，請修改後重新提交。
                
                項目：{obj_desc}
                退回原因：{comments}
                """
                recipient_list = [approval_request.requester.email]

        elif action_type == 'CANCEL':
            # 通知當前核准者（可選，視需求而定）
            pass

        if recipient_list:
            # 改為使用 EmailLog 記錄並發送
            for recipient in recipient_list:
                log = EmailLog.objects.create(
                    recipient=recipient,
                    subject=subject,
                    body=message, # 這裡使用 text 作為 body，服務層會根據內容決定是否為 HTML Message (目前 _send_from_log 使用 html_message=log.body)
                    # 為了兼容性，建議將純文字轉換為簡單的 HTML 格式
                    status='pending'
                )
                
                # 簡單將換行轉換為 <br> 以便在 HTML email 中顯示
                log.body = message.replace('\n', '<br>')
                log.save()
                
                # 嘗試立即發送
                EmailService._send_from_log(log)
                
                logger.info(f"Created EmailLog {log.id} for {action_type} notification to {recipient}")
            
    except Exception as e:
        logger.error(f"Failed to process approval notification: {e}")
