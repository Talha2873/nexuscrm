"""Project-wide choice sets and constants.

Keeping every enumeration in one module prevents the same strings drifting apart
between models, serializers, seed data and the frontend.
"""
from django.db import models


class OrganizationRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Administrator"
    MANAGER = "manager", "Manager"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


#: Ordered from most to least privileged. Used for hierarchy comparisons.
ROLE_HIERARCHY = {
    OrganizationRole.OWNER: 50,
    OrganizationRole.ADMIN: 40,
    OrganizationRole.MANAGER: 30,
    OrganizationRole.MEMBER: 20,
    OrganizationRole.VIEWER: 10,
}


class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class ActivityVerb(models.TextChoices):
    CREATED = "created", "Created"
    UPDATED = "updated", "Updated"
    DELETED = "deleted", "Deleted"
    ASSIGNED = "assigned", "Assigned"
    STATUS_CHANGED = "status_changed", "Status changed"
    STAGE_CHANGED = "stage_changed", "Stage changed"
    COMMENTED = "commented", "Commented"
    EMAILED = "emailed", "Emailed"
    CALLED = "called", "Called"
    MET = "met", "Met"
    NOTE_ADDED = "note_added", "Note added"
    FILE_UPLOADED = "file_uploaded", "File uploaded"
    LOGGED_IN = "logged_in", "Logged in"


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    READ = "read", "Read"
    LOGIN = "login", "Login"
    LOGIN_FAILED = "login_failed", "Login failed"
    LOGOUT = "logout", "Logout"
    PASSWORD_CHANGE = "password_change", "Password change"
    PERMISSION_CHANGE = "permission_change", "Permission change"
    EXPORT = "export", "Export"


class Currency(models.TextChoices):
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"
    GBP = "GBP", "British Pound"
    PKR = "PKR", "Pakistani Rupee"
    INR = "INR", "Indian Rupee"
    AED = "AED", "UAE Dirham"
    CAD = "CAD", "Canadian Dollar"
    AUD = "AUD", "Australian Dollar"
    JPY = "JPY", "Japanese Yen"
    SGD = "SGD", "Singapore Dollar"


class Industry(models.TextChoices):
    TECHNOLOGY = "technology", "Technology"
    FINANCE = "finance", "Finance & Banking"
    HEALTHCARE = "healthcare", "Healthcare"
    MANUFACTURING = "manufacturing", "Manufacturing"
    RETAIL = "retail", "Retail & E-commerce"
    EDUCATION = "education", "Education"
    REAL_ESTATE = "real_estate", "Real Estate"
    CONSULTING = "consulting", "Consulting"
    MEDIA = "media", "Media & Entertainment"
    TRANSPORT = "transport", "Transport & Logistics"
    ENERGY = "energy", "Energy & Utilities"
    HOSPITALITY = "hospitality", "Hospitality & Travel"
    NONPROFIT = "nonprofit", "Non-profit"
    GOVERNMENT = "government", "Government"
    OTHER = "other", "Other"


class CompanySize(models.TextChoices):
    SOLO = "1", "1 employee"
    MICRO = "2-10", "2-10 employees"
    SMALL = "11-50", "11-50 employees"
    MEDIUM = "51-200", "51-200 employees"
    LARGE = "201-500", "201-500 employees"
    XLARGE = "501-1000", "501-1000 employees"
    ENTERPRISE = "1000+", "1000+ employees"


class NotificationChannel(models.TextChoices):
    IN_APP = "in_app", "In-app"
    EMAIL = "email", "Email"
    PUSH = "push", "Push"
    SMS = "sms", "SMS"


#: Websocket group name templates.
WS_USER_GROUP = "user_{user_id}"
WS_ORGANIZATION_GROUP = "org_{organization_id}"
WS_AI_SESSION_GROUP = "ai_session_{session_id}"

#: Header the frontend uses to switch the active tenant for a single request.
ORGANIZATION_HEADER = "HTTP_X_ORGANIZATION_ID"
REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"

#: Field names that must never be written to audit logs in clear text.
SENSITIVE_FIELDS = frozenset(
    {
        "password", "password1", "password2", "new_password", "old_password",
        "current_password", "token", "access", "refresh", "secret", "api_key",
        "client_secret", "authorization", "credit_card", "cvv", "card_number",
    }
)
