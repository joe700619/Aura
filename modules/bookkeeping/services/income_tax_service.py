from modules.bookkeeping.models.income_tax import IncomeTax

class IncomeTaxService:
    def calculate_tax(self, income, brackets):
        """Simple progressive tax calculation"""
        # Logic considering brackets would go here
        return income * 0.2  # Placeholder flat rate

    def create_tax_record(self, year, taxable_income, tax_amount):
        return IncomeTax.objects.create(
            year=year,
            taxable_income=taxable_income,
            tax_amount=tax_amount
        )
