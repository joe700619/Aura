from django.urls import path
from .views import (
    CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDeleteView,
    ContactListView, ContactCreateView, ContactUpdateView, ContactDeleteView, ContactHistoryView,
    ServiceItemListView, ServiceItemCreateView, ServiceItemUpdateView, ServiceItemDeleteView
)
from .views.api import CustomerSearchApiView, CustomerSearchForProgressApiView, ContactSearchForProgressApiView, ServiceItemSearchApiView

urlpatterns = [
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer_delete'),
    
    # API
    path('api/customers/search/', CustomerSearchApiView.as_view(), name='customer_search_api'),
    path('api/customers/search/progress/', CustomerSearchForProgressApiView.as_view(), name='customer_search_progress_api'),
    path('api/contacts/search/progress/', ContactSearchForProgressApiView.as_view(), name='contact_search_progress_api'),
    path('api/service-items/search/', ServiceItemSearchApiView.as_view(), name='service_item_search_api'),

    # Contacts
    path('contacts/', ContactListView.as_view(), name='contact_list'),
    path('contacts/add/', ContactCreateView.as_view(), name='contact_create'),
    path('contacts/<int:pk>/edit/', ContactUpdateView.as_view(), name='contact_update'),
    path('contacts/<int:pk>/delete/', ContactDeleteView.as_view(), name='contact_delete'),
    path('contacts/<int:pk>/history/', ContactHistoryView.as_view(), name='contact_history'),

    # Service Items
    path('service-items/', ServiceItemListView.as_view(), name='service_item_list'),
    path('service-items/add/', ServiceItemCreateView.as_view(), name='service_item_create'),
    path('service-items/<int:pk>/edit/', ServiceItemUpdateView.as_view(), name='service_item_update'),
    path('service-items/<int:pk>/delete/', ServiceItemDeleteView.as_view(), name='service_item_delete'),
]
