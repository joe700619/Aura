from modules.bookkeeping.models.income_tax import IncomeTaxFiling


class IncomeTaxService:
    def calculate_tax(self, income, brackets):
        """Simple progressive tax calculation"""
        # Logic considering brackets would go here
        return income * 0.2  # Placeholder flat rate
