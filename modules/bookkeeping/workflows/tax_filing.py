class TaxFilingWorkflow:
    def __init__(self, record):
        self.record = record

    def submit_for_review(self):
        """Transition status to REVIEW"""
        if self.record.status == 'DRAFT':
            self.record.status = 'REVIEW'
            self.record.save()
            # Trigger notification here
            return True
        return False

    def approve(self):
        """Transition status to APPROVED"""
        if self.record.status == 'REVIEW':
            self.record.status = 'APPROVED'
            self.record.save()
            return True
        return False
