from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy

class ClientRequiredMixin(AccessMixin):
    """
    Verify that the current user is authenticated, has the EXTERNAL role,
    and has a linked BookkeepingClient profile.
    """
    login_url = reverse_lazy('client_portal:login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        if request.user.role != 'EXTERNAL':
            # They are authenticated but not a client (e.g., staff/admin)
            # Redirect them away from the portal back to the main ERP
            return redirect('dashboard')
            
        if not hasattr(request.user, 'bookkeeping_client_profile') or not request.user.bookkeeping_client_profile:
            return redirect('client_portal:login')
            
        return super().dispatch(request, *args, **kwargs)
