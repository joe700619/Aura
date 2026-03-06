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
    
    # API endpoints
    path('api/get-customer-tax-id/', views.get_customer_tax_id, name='get_customer_tax_id'),
    
    # Document Dispatch
    path('document-dispatches/', views.DocumentDispatchListView.as_view(), name='document_dispatch_list'),
    path('document-dispatches/add/', views.DocumentDispatchCreateView.as_view(), name='document_dispatch_create'),
    path('document-dispatches/<int:pk>/edit/', views.DocumentDispatchUpdateView.as_view(), name='document_dispatch_update'),
    path('document-dispatches/<int:pk>/delete/', views.DocumentDispatchDeleteView.as_view(), name='document_dispatch_delete'),
    path('document-dispatches/item-list/', views.DocumentDispatchItemListView.as_view(), name='document_dispatch_item_list'),
    
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
]
