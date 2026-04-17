lines = open('modules/registration/views/progress.py', 'r', encoding='utf-8').readlines()

# Find start and end line indices (0-based)
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'class PaymentLinkGenerateView' in line:
        # Walk back to find the duplicate import block start
        j = i
        while j > 0 and lines[j-1].strip() != 'from django.views import View' and j > i - 15:
            j -= 1
        start_idx = j - 1 if j > 0 else i
        # Now find the line just before ProgressTransferToARView
    if 'class ProgressTransferToARView' in line:
        end_idx = i
        break

print(f'start_idx={start_idx}, end_idx={end_idx}')
print('=== Lines to replace ===')
for i, l in enumerate(lines[start_idx:end_idx], start=start_idx):
    print(f'{i}: {repr(l)}')

new_block = """\nfrom django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from modules.internal_accounting.services import ReceivableTransferService
from ..models.payment_request import ProgressPaymentRequest


class PaymentRequestCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        progress = get_object_or_404(Progress, pk=pk)
        amount_str = request.POST.get('amount', '').strip()
        description = request.POST.get('description', '').strip()

        if not amount_str or not amount_str.isdigit() or int(amount_str) <= 0:
            messages.error(request, '\u8acb\u8f38\u5165\u6709\u6548\u7684\u8acb\u6b3e\u91d1\u984d\u3002')
            return redirect('registration:progress_edit', pk=pk)

        ProgressPaymentRequest.objects.create(
            progress=progress,
            amount=int(amount_str),
            description=description,
        )
        messages.success(request, f'\u5df2\u5efa\u7acb\u4ed8\u6b3e\u8acb\u6c42\uff1a{description or "\u4ed8\u6b3e"} ${int(amount_str):,}')
        return redirect('registration:progress_edit', pk=pk)


class PaymentRequestCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        pr = get_object_or_404(ProgressPaymentRequest, pk=pk)
        if pr.status == ProgressPaymentRequest.Status.PAID:
            messages.error(request, '\u5df2\u4ed8\u6b3e\u7684\u8acb\u6c42\u7121\u6cd5\u53d6\u6d88\u3002')
        else:
            pr.status = ProgressPaymentRequest.Status.CANCELLED
            pr.save(update_fields=['status'])
            messages.success(request, '\u4ed8\u6b3e\u8acb\u6c42\u5df2\u53d6\u6d88\u3002')
        return redirect('registration:progress_edit', pk=pr.progress_id)


"""

if start_idx is not None and end_idx is not None:
    new_lines = lines[:start_idx] + [new_block] + lines[end_idx:]
    open('modules/registration/views/progress.py', 'w', encoding='utf-8').writelines(new_lines)
    print('Done')
