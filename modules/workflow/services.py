"""
Workflow Services
核准工作流程的業務邏輯
"""
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from .models import (
    WorkflowTemplate,
    WorkflowStep,
    ApprovalRequest,
    ApprovalHistory,
    ApproverDelegate
)
from .utils import send_approval_notification


def initiate_approval(obj, workflow_code, requester):
    """
    為物件啟動核准流程
    
    Args:
        obj: 需要核准的物件 (任何 Django model instance)
        workflow_code: 工作流程代碼
        requester: 申請人 (User instance)
    
    Returns:
        ApprovalRequest instance
        
    Raises:
        WorkflowTemplate.DoesNotExist: 如果流程模板不存在
    """
    template = WorkflowTemplate.objects.get(code=workflow_code, is_active=True)
    
    content_type = ContentType.objects.get_for_model(obj)
    
    # 檢查是否已經有進行中的核准請求
    existing = ApprovalRequest.objects.filter(
        content_type=content_type,
        object_id=obj.pk,
        status__in=['DRAFT', 'PENDING', 'RETURNED']
    ).first()
    
    if existing:
        return existing
    
    # 建立新的核准請求
    approval_request = ApprovalRequest.objects.create(
        content_object=obj,
        workflow_template=template,
        requester=requester,
        status='DRAFT'
    )
    
    return approval_request


@transaction.atomic
def submit_for_approval(approval_request, comments=''):
    """
    送出核准申請
    
    Args:
        approval_request: ApprovalRequest instance
        comments: 送出備註
        
    Returns:
        bool: 是否成功
    """
    if approval_request.status not in ['DRAFT', 'RETURNED']:
        raise ValueError(f"無法送出狀態為 {approval_request.get_status_display()} 的申請")
    
    # 取得第一個步驟
    first_step = approval_request.workflow_template.steps.first()
    
    if not first_step:
        raise ValueError("工作流程沒有定義步驟")
    
    # 更新狀態
    approval_request.status = 'PENDING'
    approval_request.current_step = first_step
    approval_request.submit_date = timezone.now()
    approval_request.save()
    
    # 記錄歷史
    action = 'RESUBMIT' if ApprovalHistory.objects.filter(
        approval_request=approval_request,
        action='SUBMIT'
    ).exists() else 'SUBMIT'
    
    ApprovalHistory.objects.create(
        approval_request=approval_request,
        action=action,
        actor=approval_request.requester,
        comments=comments
    )
    
    # 取得下一位核准者 (用於通知)
    next_approver, _ = get_effective_approver(first_step.approver_user, approval_request)
    
    # 發送通知
    send_approval_notification(
        approval_request, 
        'SUBMIT', 
        comments=comments,
        next_approver=next_approver
    )
    
    return True


@transaction.atomic
def approve(approval_request, approver, comments='', as_delegate_for=None):
    """
    核准申請
    
    Args:
        approval_request: ApprovalRequest instance
        approver: 核准者 (User instance)
        comments: 核准意見
        as_delegate_for: 如果是代理人操作，原核准者 (User instance)
        
    Returns:
        bool: 是否成功
    """
    if approval_request.status != 'PENDING':
        raise ValueError("只能核准待核准的申請")
    
    if not approval_request.current_step:
        raise ValueError("沒有當前步驟")
    
    # 記錄歷史
    ApprovalHistory.objects.create(
        approval_request=approval_request,
        step=approval_request.current_step,
        action='APPROVE',
        actor=approver,
        actor_as_delegate=as_delegate_for,
        comments=comments
    )
    
    # 檢查是否為最後一步
    if approval_request.is_final_step():
        # 完成核准
        approval_request.status = 'APPROVED'
        approval_request.current_step = None
        approval_request.completed_date = timezone.now()
        approval_request.save()
        
        # 發送最終核准通知
        send_approval_notification(
            approval_request, 
            'APPROVE', 
            comments=comments
        )
    else:
        # 前進到下一步
        next_step = approval_request.get_next_step()
        approval_request.current_step = next_step
        approval_request.save()
        
        # 取得下一位核准者 (用於通知)
        next_approver, _ = get_effective_approver(next_step.approver_user, approval_request)

        # 發送下一步通知
        send_approval_notification(
            approval_request, 
            'APPROVE', 
            comments=comments,
            next_approver=next_approver
        )
    
    return True


@transaction.atomic
def reject(approval_request, approver, comments='', as_delegate_for=None):
    """
    拒絕申請
    
    Args:
        approval_request: ApprovalRequest instance
        approver: 核准者 (User instance)
        comments: 拒絕理由
        as_delegate_for: 如果是代理人操作，原核准者 (User instance)
        
    Returns:
        bool: 是否成功
    """
    if approval_request.status != 'PENDING':
        raise ValueError("只能拒絕待核准的申請")
    
    # 記錄歷史
    ApprovalHistory.objects.create(
        approval_request=approval_request,
        step=approval_request.current_step,
        action='REJECT',
        actor=approver,
        actor_as_delegate=as_delegate_for,
        comments=comments
    )
    
    # 更新狀態
    approval_request.status = 'REJECTED'
    approval_request.current_step = None
    approval_request.completed_date = timezone.now()
    approval_request.save()
    
    # 發送通知
    send_approval_notification(
        approval_request, 
        'REJECT', 
        comments=comments
    )
    
    return True


@transaction.atomic
def return_for_revision(approval_request, approver, comments='', as_delegate_for=None):
    """
    退回給申請人修正
    
    Args:
        approval_request: ApprovalRequest instance
        approver: 核准者 (User instance)
        comments: 退回理由
        as_delegate_for: 如果是代理人操作，原核准者 (User instance)
        
    Returns:
        bool: 是否成功
    """
    if approval_request.status != 'PENDING':
        raise ValueError("只能退回待核准的申請")
    
    # 記錄歷史
    ApprovalHistory.objects.create(
        approval_request=approval_request,
        step=approval_request.current_step,
        action='RETURN',
        actor=approver,
        actor_as_delegate=as_delegate_for,
        comments=comments
    )
    
    # 更新狀態
    approval_request.status = 'RETURNED'
    approval_request.current_step = None
    approval_request.save()
    
    # 發送通知
    send_approval_notification(
        approval_request, 
        'RETURN', 
        comments=comments
    )
    
    return True


@transaction.atomic
def cancel_approval(approval_request, requester, comments=''):
    """
    撤回申請
    
    Args:
        approval_request: ApprovalRequest instance
        requester: 申請人 (User instance)
        comments: 撤回原因
        
    Returns:
        bool: 是否成功
    """
    if approval_request.status not in ['PENDING', 'RETURNED']:
        raise ValueError("只能撤回待核准或已退回的申請")
    
    if approval_request.requester != requester:
        raise PermissionError("只有申請人可以撤回")
    
    # 記錄歷史
    ApprovalHistory.objects.create(
        approval_request=approval_request,
        action='CANCEL',
        actor=requester,
        comments=comments
    )
    
    # 更新狀態
    approval_request.status = 'CANCELLED'
    approval_request.current_step = None
    approval_request.save()
    
    # 發送通知
    send_approval_notification(
        approval_request, 
        'CANCEL', 
        comments=comments
    )
    
    return True


def get_effective_approver(user, approval_request, date=None):
    """
    取得有效的核准者（考慮代理人設定）
    
    Args:
        user: 原核准者
        approval_request: ApprovalRequest instance
        date: 檢查日期，預設為今天
        
    Returns:
        tuple: (effective_approver, original_approver)
               如果沒有代理人，返回 (user, None)
               如果有代理人，返回 (delegate, user)
    """
    if date is None:
        date = timezone.now().date()
    
    # 查找有效的代理設定
    delegation = ApproverDelegate.objects.filter(
        user=user,
        start_date__lte=date,
        end_date__gte=date,
        is_active=True
    ).filter(
        Q(workflow_template=approval_request.workflow_template) |
        Q(workflow_template__isnull=True)
    ).first()
    
    if delegation:
        return delegation.delegate, user
    
    return user, None


def get_pending_approvals(user):
    """
    取得使用者的待核准項目（包含代理）
    
    Args:
        user: User instance
        
    Returns:
        QuerySet of ApprovalRequest
    """
    from django.contrib.auth.models import User
    from django.db.models import Q
    
    today = timezone.now().date()
    
    # 1. 直接指派給我的
    my_approvals = ApprovalRequest.objects.filter(
        status='PENDING',
        current_step__approver_user=user
    )
    
    # 2. 指派給我的角色的
    my_groups = user.groups.all()
    role_approvals = ApprovalRequest.objects.filter(
        status='PENDING',
        current_step__approver_role__in=my_groups
    )
    
    # 3. 我作為代理人的
    delegations = ApproverDelegate.objects.filter(
        delegate=user,
        start_date__lte=today,
        end_date__gte=today,
        is_active=True
    )
    
    delegated_users = [d.user for d in delegations]
    
    delegated_groups = []
    for d in delegations:
        delegated_groups.extend(d.user.groups.all())

    delegated_approvals = ApprovalRequest.objects.filter(
        status='PENDING'
    ).filter(
        Q(current_step__approver_user__in=delegated_users) |
        Q(current_step__approver_role__in=delegated_groups)
    )
    
    # 合併並去重（先收集 pk 避免 unique/non-unique queryset 合併問題）
    all_pks = set()
    all_pks.update(my_approvals.values_list('pk', flat=True))
    all_pks.update(role_approvals.values_list('pk', flat=True))
    all_pks.update(delegated_approvals.values_list('pk', flat=True))

    # 4. approver_field 動態欄位（例如 employee.supervisor）
    field_steps = WorkflowStep.objects.filter(
        approver_field__isnull=False
    ).exclude(approver_field='')
    if field_steps.exists():
        pending_field_reqs = (
            ApprovalRequest.objects
            .filter(status='PENDING', current_step__in=field_steps)
            .exclude(pk__in=all_pks)
            .select_related('current_step')
        )
        for req in pending_field_reqs:
            approver = req.current_step.get_approver(req.content_object)
            if approver == user:
                all_pks.add(req.pk)

    return ApprovalRequest.objects.filter(pk__in=all_pks)


def get_approval_request(obj):
    """
    取得物件的當前核准請求
    
    Args:
        obj: Django model instance
        
    Returns:
        ApprovalRequest instance or None
    """
    content_type = ContentType.objects.get_for_model(obj)
    
    # 取得最新的核准請求（包含所有狀態，以便顯示已完成的核准）
    return ApprovalRequest.objects.filter(
        content_type=content_type,
        object_id=obj.pk
    ).order_by('-request_date').first()
