from modules.bookkeeping.models.vat import VAT

class VATService:
    def calculate_vat(self, amount, rate=0.05):
        """Calculate VAT for a given amount"""
        return amount * rate

    def create_vat_record(self, period, amount, status='DRAFT'):
        return VAT.objects.create(
            period=period,
            amount=amount,
            status=status
        )
