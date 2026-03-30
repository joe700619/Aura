from django.urls import path
from . import views
from .views import DocumentReceiptListView, DocumentReceiptCreateView, DocumentReceiptUpdateView, DocumentReceiptDeleteView, SendDocumentReceiptLineView

app_name = 'administrative'

urlpatterns = [
    # Document Receipts
    path('document-receipts/', DocumentReceiptListView.as_view(), name='document_receipt_list'),
    path('document-receipts/add/', DocumentReceiptCreateView.as_view(), name='document_receipt_create'),
    path('document-receipts/<int:pk>/edit/', DocumentReceiptUpdateView.as_view(), name='document_receipt_update'),
    path('document-receipts/<int:pk>/delete/', DocumentReceiptDeleteView.as_view(), name='document_receipt_delete'),
    path('document-receipts/<int:pk>/send-line/', SendDocumentReceiptLineView.as_view(), name='document_receipt_send_line'),
    
    # IRS Audit Notices
    path('irs-audit-notices/', views.IrsAuditNoticeListView.as_view(), name='irs_audit_notice_list'),
    path('irs-audit-notices/add/', views.IrsAuditNoticeCreateView.as_view(), name='irs_audit_notice_create'),
    path('irs-audit-notices/<int:pk>/edit/', views.IrsAuditNoticeUpdateView.as_view(), name='irs_audit_notice_update'),
    path('irs-audit-notices/<int:pk>/delete/', views.IrsAuditNoticeDeleteView.as_view(), name='irs_audit_notice_delete'),

    # 系統公佈欄 System Bulletin Board
    path('system_bulletin/', views.SystemBulletinListView.as_view(), name='system_bulletin_list'),
    path('system_bulletin/add/', views.SystemBulletinCreateView.as_view(), name='system_bulletin_create'),
    path('system_bulletin/<int:pk>/edit/', views.SystemBulletinUpdateView.as_view(), name='system_bulletin_update'),
    path('system_bulletin/<int:pk>/delete/', views.SystemBulletinDeleteView.as_view(), name='system_bulletin_delete'),
    
    # API endpoints
    path('api/get-customer-tax-id/', views.get_customer_tax_id, name='get_customer_tax_id'),
    
    # Document Dispatch
    path('document-dispatches/', views.DocumentDispatchListView.as_view(), name='document_dispatch_list'),
    path('document-dispatches/add/', views.DocumentDispatchCreateView.as_view(), name='document_dispatch_create'),
    path('document-dispatches/<int:pk>/edit/', views.DocumentDispatchUpdateView.as_view(), name='document_dispatch_update'),
    path('document-dispatches/<int:pk>/delete/', views.DocumentDispatchDeleteView.as_view(), name='document_dispatch_delete'),
    path('document-dispatches/item-list/', views.DocumentDispatchItemListView.as_view(), name='document_dispatch_item_list'),
    path('document-dispatches/<int:pk>/transfer/', views.document_dispatch_transfer_to_advance_payment, name='document_dispatch_transfer'),
    path('document-dispatches/items/<int:item_pk>/label/', views.document_dispatch_item_label, name='document_dispatch_item_label'),
    
    # Approval Actions
    path('irs-audit-notices/<int:pk>/submit-approval/', views.irs_audit_notice_submit_approval, name='irsauditnotice_submit_approval'),
    path('irs-audit-notices/<int:pk>/approve/', views.irs_audit_notice_approve, name='irsauditnotice_approve'),
    path('irs-audit-notices/<int:pk>/reject/', views.irs_audit_notice_reject, name='irsauditnotice_reject'),
    path('irs-audit-notices/<int:pk>/return/', views.irs_audit_notice_return, name='irsauditnotice_return'),
    path('irs-audit-notices/<int:pk>/cancel-approval/', views.irs_audit_notice_cancel_approval, name='irsauditnotice_cancel_approval'),

    # Seal Procurement
    path('seal-procurements/', views.SealProcurementListView.as_view(), name='seal_procurement_list'),
    path('seal-procurements/add/', views.SealProcurementCreateView.as_view(), name='seal_procurement_create'),
    path('seal-procurements/<int:pk>/edit/', views.SealProcurementUpdateView.as_view(), name='seal_procurement_update'),
    path('seal-procurements/<int:pk>/delete/', views.SealProcurementDeleteView.as_view(), name='seal_procurement_delete'),
    path('seal-inventory-report/', views.SealInventoryReportView.as_view(), name='seal_inventory_report'),
    
    # Advance Payment
    path('advance-payments/', views.AdvancePaymentListView.as_view(), name='advance_payment_list'),
    path('advance-payments/add/', views.AdvancePaymentCreateView.as_view(), name='advance_payment_create'),
    path('advance-payments/<int:pk>/edit/', views.AdvancePaymentUpdateView.as_view(), name='advance_payment_update'),
    path('advance-payments/<int:pk>/delete/', views.AdvancePaymentDeleteView.as_view(), name='advance_payment_delete'),
    
    # Advance Payment Approval Actions
    path('advance-payments/<int:pk>/submit-approval/', views.advance_payment_submit_approval, name='advancepayment_submit_approval'),
    path('advance-payments/<int:pk>/approve/', views.advance_payment_approve, name='advancepayment_approve'),
    path('advance-payments/<int:pk>/reject/', views.advance_payment_reject, name='advancepayment_reject'),
    path('advance-payments/<int:pk>/return/', views.advance_payment_return, name='advancepayment_return'),
    path('advance-payments/<int:pk>/cancel-approval/', views.advance_payment_cancel_approval, name='advancepayment_cancel_approval'),
]
