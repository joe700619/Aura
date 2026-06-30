"""
Workflow 相關的可重用 View Mixin。
"""
from .services import abort_approval


class AbortApprovalOnDeleteMixin:
    """
    DeleteView 用：刪除一筆「有核准流程」的單據時，連帶撤銷仍在進行中的核准請求，
    避免留下指向已刪除單據的孤兒核准單卡在主管審核清單。

    需與會設定 self.object 的刪除流程並用（例如 core.mixins.SoftDeleteMixin），
    且 model 需實作 get_approval_request()。本 mixin 須排在 SoftDeleteMixin 之前，
    讓 super().form_valid() 先完成（軟）刪除，再收掉核准單。
    """

    def form_valid(self, form):
        response = super().form_valid(form)
        obj = getattr(self, 'object', None)
        if obj is not None and hasattr(obj, 'get_approval_request'):
            approval = obj.get_approval_request()
            if approval:
                abort_approval(approval)
        return response
