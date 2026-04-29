from .auth import (
    PortalLoginView,
    ClientPasswordResetView,
    ClientPasswordResetDoneView,
    ClientPasswordResetConfirmView,
    ClientPasswordResetCompleteView,
)
from .dashboard import DashboardView
from .documents import DocumentCenterView
from .shareholders import ShareholderManagementView
from .financial import FinancialAnalysisView
from .declarations import IncomeDeclarationView, DividendDeclarationView
from .service_remuneration import (
    ServiceRemunerationView,
    ServiceRemunerationSaveView,
    ServiceRemunerationDeleteView,
    ServiceRemunerationUploadSlipView,
    ServiceRemunerationDownloadSlipView,
    ServiceRemunerationTax152PdfView,
    ServiceRemunerationPdfView,
    ServiceRemunerationConfirmView,
)
from .settings import SettingsView
from .billing import BillingView, GeneratePaymentLinkView, DownloadBillPdfView
from .tax152 import Tax152View

__all__ = [
    'PortalLoginView',
    'ClientPasswordResetView',
    'ClientPasswordResetDoneView',
    'ClientPasswordResetConfirmView',
    'ClientPasswordResetCompleteView',
    'DashboardView',
    'DocumentCenterView',
    'ShareholderManagementView',
    'FinancialAnalysisView',
    'IncomeDeclarationView',
    'DividendDeclarationView',
    'ServiceRemunerationView',
    'ServiceRemunerationSaveView',
    'ServiceRemunerationDeleteView',
    'ServiceRemunerationUploadSlipView',
    'ServiceRemunerationDownloadSlipView',
    'ServiceRemunerationTax152PdfView',
    'ServiceRemunerationPdfView',
    'ServiceRemunerationConfirmView',
    'SettingsView',
    'BillingView',
    'GeneratePaymentLinkView',
    'DownloadBillPdfView',
    'Tax152View',
]
