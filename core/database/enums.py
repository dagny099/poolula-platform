"""
Enum definitions for Poolula Platform

All enums are string-based for database compatibility and readability

Author: Poolula Platform
Date: 2025-11-13
"""

from enum import Enum


class TransactionCategory(str, Enum):
    """
    Chart of Accounts for transaction categorization

    Aligned with IRS Schedule E and standard LLC accounting

    Categories are hierarchical using colon notation:
    - Top level: rental_income, utilities, repairs_maintenance
    - Sub-categories: utilities:gas, utilities:water, etc.
    """

    # ==========================================================================
    # REVENUE
    # ==========================================================================
    RENTAL_INCOME = "rental_income"  # Airbnb bookings, traditional rent

    # ==========================================================================
    # OPERATING EXPENSES (Schedule E, Line 5-19)
    # ==========================================================================

    # Utilities
    UTILITIES_GAS = "utilities:gas"  # Black Hills Energy
    UTILITIES_WATER = "utilities:water"  # City of Montrose Water
    UTILITIES_ELECTRIC = "utilities:electric"  # DMEA / Delta-Montrose Electric
    UTILITIES_INTERNET = "utilities:internet"  # Elevate Internet
    UTILITIES_OTHER = "utilities:other"  # Trash, sewer, etc.

    # Repairs & Maintenance (ordinary, necessary, does not add value)
    REPAIRS_MAINTENANCE = "repairs_maintenance"  # Plumbing, HVAC service, etc.
    CLEANING = "cleaning"  # Professional cleaning between guests
    SUPPLIES = "supplies"  # Toilet paper, soap, light bulbs

    # Insurance
    INSURANCE_PROPERTY = "insurance:property"  # Homeowner/rental insurance
    INSURANCE_LIABILITY = "insurance:liability"  # Liability coverage
    INSURANCE_OTHER = "insurance:other"

    # Property Taxes
    PROPERTY_TAXES = "property_taxes"  # County/city property taxes

    # Property Management
    PROPERTY_MANAGEMENT = "property_management"  # PM fees, Airbnb service fees

    # Professional Fees
    PROFESSIONAL_ACCOUNTING = "professional:accounting"  # CPA, bookkeeper
    PROFESSIONAL_LEGAL = "professional:legal"  # Attorney fees
    PROFESSIONAL_OTHER = "professional:other"  # Consultants

    # Banking & Financial
    BANK_FEES = "bank_fees"  # Service charges, wire fees
    INTEREST_EXPENSE = "interest:expense"  # Mortgage interest (if applicable)
    CREDIT_CARD_FEES = "credit_card_fees"  # Merchant fees

    # HOA / Condo Fees (if applicable)
    HOA_FEES = "hoa_fees"

    # Other Operating Expenses
    ADVERTISING = "advertising"  # Marketing, listing fees
    LICENSES_PERMITS = "licenses_permits"  # Business licenses
    OFFICE_EXPENSE = "office_expense"  # Software, subscriptions
    TRAVEL = "travel"  # Travel to property for maintenance

    # ==========================================================================
    # CAPITAL EXPENSES (Not deductible, add to basis)
    # ==========================================================================
    CAPITAL_IMPROVEMENT = "capital_improvement"  # Adds value, prolongs life (roof, HVAC replacement)
    FURNITURE_FIXTURES = "furniture_fixtures"  # FF&E purchases
    BASIS_ADJUSTMENT = "basis_adjustment"  # Corrections to property basis

    # ==========================================================================
    # MEMBER TRANSACTIONS (Equity, not P&L)
    # ==========================================================================
    MEMBER_CONTRIBUTION = "member_contribution"  # Capital injected by member
    MEMBER_DISTRIBUTION = "member_distribution"  # Profits distributed to member

    # ==========================================================================
    # OTHER
    # ==========================================================================
    UNCATEGORIZED = "uncategorized"  # Default for imports, needs review

    def __str__(self) -> str:
        """Return the value for string representation"""
        return self.value

    @classmethod
    def from_description(cls, description: str) -> "TransactionCategory":
        """
        Attempt to categorize from transaction description

        Basic keyword matching, can be enhanced with AI later

        Args:
            description: Transaction description text

        Returns:
            Best-guess category, defaults to UNCATEGORIZED

        Example:
            >>> TransactionCategory.from_description("Black Hills Energy - Gas Bill")
            TransactionCategory.UTILITIES_GAS
        """
        desc_lower = description.lower()

        # Revenue keywords
        if any(word in desc_lower for word in ["airbnb", "booking", "reservation", "rental income"]):
            return cls.RENTAL_INCOME

        # Utilities
        if "black hills" in desc_lower or "gas" in desc_lower:
            return cls.UTILITIES_GAS
        if "water" in desc_lower or "montrose water" in desc_lower:
            return cls.UTILITIES_WATER
        if "electric" in desc_lower or "dmea" in desc_lower:
            return cls.UTILITIES_ELECTRIC
        if "internet" in desc_lower or "elevate" in desc_lower:
            return cls.UTILITIES_INTERNET

        # Repairs
        if any(word in desc_lower for word in ["repair", "fix", "maintenance", "plumb", "hvac"]):
            return cls.REPAIRS_MAINTENANCE

        # Insurance
        if "insurance" in desc_lower or "travelers" in desc_lower:
            return cls.INSURANCE_PROPERTY

        # Default
        return cls.UNCATEGORIZED


class TransactionType(str, Enum):
    """
    High-level transaction type classification

    Used for filtering and reporting
    """
    REVENUE = "revenue"  # Money in
    EXPENSE = "expense"  # Money out (operating)
    CAPITAL = "capital"  # Money out (capital expenditures)
    EQUITY = "equity"  # Member contributions/distributions
    TRANSFER = "transfer"  # Between accounts (net zero)

    def __str__(self) -> str:
        return self.value


class DocumentType(str, Enum):
    """
    Document classification categories

    Used for organizing and filtering documents
    """
    # Formation & Governance
    FORMATION = "formation"  # Articles of Organization
    AUTHORITY = "authority"  # Statement of Authority
    OPERATING_AGREEMENT = "operating_agreement"
    MINUTES = "minutes"  # Meeting minutes
    CONSENT = "consent"  # Written consents/resolutions

    # Property
    DEED = "deed"  # Property deed, title
    CLOSING = "closing"  # Settlement statements, HUD-1

    # Financial
    BANK_STATEMENT = "bank_statement"
    CREDIT_CARD_STATEMENT = "credit_card_statement"
    INVOICE = "invoice"
    RECEIPT = "receipt"

    # Insurance
    INSURANCE_POLICY = "insurance:policy"
    INSURANCE_DECLARATION = "insurance:declaration"
    INSURANCE_CLAIM = "insurance:claim"

    # Compliance
    TAX_RETURN = "tax:return"  # Form 1065, Schedule E
    TAX_EXTENSION = "tax:extension"
    TAX_NOTICE = "tax:notice"  # IRS/state notices
    PERIODIC_REPORT = "compliance:periodic_report"  # CO periodic report

    # Contracts
    LEASE = "lease"  # Rental agreements
    VENDOR_CONTRACT = "vendor:contract"  # Service contracts

    # Other
    CORRESPONDENCE = "correspondence"  # Letters, emails
    OTHER = "other"

    def __str__(self) -> str:
        return self.value


class DocumentVersion(str, Enum):
    """Document version status"""
    DRAFT = "draft"  # Work in progress
    FINAL = "final"  # Approved, current version
    SUPERSEDED = "superseded"  # Replaced by newer version
    ARCHIVED = "archived"  # Historical, no longer relevant

    def __str__(self) -> str:
        return self.value


class DocumentConfidentiality(str, Enum):
    """Document confidentiality levels"""
    PUBLIC = "public"  # Can be shared externally
    INTERNAL = "internal"  # Internal use only (default)
    RESTRICTED = "restricted"  # Sensitive (SSN, bank accounts, etc.)

    def __str__(self) -> str:
        return self.value


class ObligationType(str, Enum):
    """Types of compliance obligations"""
    TAX_FILING = "tax:filing"  # Federal/state tax returns
    TAX_PAYMENT = "tax:payment"  # Estimated tax payments
    PERIODIC_REPORT = "compliance:periodic_report"  # CO periodic report
    INSURANCE_RENEWAL = "insurance:renewal"
    LICENSE_RENEWAL = "license:renewal"
    RENT_PAYMENT = "rent:payment"  # If property has ground rent
    OTHER = "other"

    def __str__(self) -> str:
        return self.value


class ObligationStatus(str, Enum):
    """Status of an obligation"""
    PENDING = "pending"  # Not yet due
    DUE_SOON = "due_soon"  # Due within 7 days
    OVERDUE = "overdue"  # Past due date
    COMPLETED = "completed"  # Satisfied
    CANCELLED = "cancelled"  # No longer applicable

    def __str__(self) -> str:
        return self.value


class PropertyStatus(str, Enum):
    """Status of a property"""
    ACTIVE = "active"  # Currently owned and operated
    UNDER_CONTRACT = "under_contract"  # In process of acquisition
    SOLD = "sold"  # Disposed of
    INACTIVE = "inactive"  # Temporarily not operating

    def __str__(self) -> str:
        return self.value


class ProvenanceSourceType(str, Enum):
    """Type of data source for provenance tracking"""
    MANUAL_ENTRY = "manual_entry"  # Typed in by user
    CSV_IMPORT = "csv_import"  # Imported from CSV file
    PDF_EXTRACT = "pdf_extract"  # Extracted from PDF
    OCR = "ocr"  # Optical character recognition
    API_FETCH = "api_fetch"  # Retrieved from external API
    CALCULATION = "calculation"  # Computed from other data
    AI_GENERATED = "ai_generated"  # Generated by AI (Claude, etc.)
    MIGRATION = "migration"  # Migrated from legacy system

    def __str__(self) -> str:
        return self.value


class VerificationStatus(str, Enum):
    """Verification status for provenance"""
    UNVERIFIED = "unverified"  # Not yet checked
    VERIFIED = "verified"  # Confirmed accurate
    DISPUTED = "disputed"  # Questioned, needs review
    CORRECTED = "corrected"  # Was wrong, now fixed

    def __str__(self) -> str:
        return self.value


# Mapping helpers for quick lookups
EXPENSE_CATEGORIES = [
    cat for cat in TransactionCategory
    if cat not in [
        TransactionCategory.RENTAL_INCOME,
        TransactionCategory.CAPITAL_IMPROVEMENT,
        TransactionCategory.FURNITURE_FIXTURES,
        TransactionCategory.BASIS_ADJUSTMENT,
        TransactionCategory.MEMBER_CONTRIBUTION,
        TransactionCategory.MEMBER_DISTRIBUTION,
    ]
]

CAPITAL_CATEGORIES = [
    TransactionCategory.CAPITAL_IMPROVEMENT,
    TransactionCategory.FURNITURE_FIXTURES,
    TransactionCategory.BASIS_ADJUSTMENT,
]

EQUITY_CATEGORIES = [
    TransactionCategory.MEMBER_CONTRIBUTION,
    TransactionCategory.MEMBER_DISTRIBUTION,
]
