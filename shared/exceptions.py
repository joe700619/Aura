class AuraException(Exception):
    """Base exception for Aura ERP"""
    pass

class BusinessRuleViolation(AuraException):
    """Raised when a business rule is violated"""
    pass
