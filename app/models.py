from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class MonitorType(str, Enum):
    """Type of monitoring target"""

    HTTP = "http"
    HTTPS = "https"
    PING = "ping"
    TCP = "tcp"
    UDP = "udp"


class MonitorStatus(str, Enum):
    """Current status of a monitored item"""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"
    PENDING = "pending"


class NotificationType(str, Enum):
    """Type of notification"""

    STATUS_CHANGE = "status_change"
    DOWN_ALERT = "down_alert"
    UP_ALERT = "up_alert"
    TIMEOUT_ALERT = "timeout_alert"


class NotificationMethod(str, Enum):
    """Method of notification delivery"""

    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    """User account for the monitoring system"""

    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=100, unique=True)
    email: str = Field(max_length=255, unique=True, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    full_name: str = Field(max_length=200)
    is_active: bool = Field(default=True)
    email_notifications_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    monitored_items: List["MonitoredItem"] = Relationship(back_populates="user")
    notifications: List["Notification"] = Relationship(back_populates="user")
    notification_settings: List["NotificationSetting"] = Relationship(back_populates="user")


class MonitoredItem(SQLModel, table=True):
    """A link or host being monitored"""

    __tablename__ = "monitored_items"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    url: str = Field(max_length=2000)  # URL or hostname to monitor
    monitor_type: MonitorType = Field(default=MonitorType.HTTP)
    check_interval_seconds: int = Field(default=300)  # 5 minutes default
    timeout_seconds: int = Field(default=30)
    expected_status_code: Optional[int] = Field(default=200)
    expected_content: Optional[str] = Field(default=None, max_length=1000)
    current_status: MonitorStatus = Field(default=MonitorStatus.UNKNOWN)
    last_check_at: Optional[datetime] = Field(default=None)
    last_status_change_at: Optional[datetime] = Field(default=None)
    consecutive_failures: int = Field(default=0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default=[], sa_column=Column(JSON))
    custom_headers: Dict[str, str] = Field(default={}, sa_column=Column(JSON))
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="monitored_items")
    status_checks: List["StatusCheck"] = Relationship(back_populates="monitored_item")
    uptime_records: List["UptimeRecord"] = Relationship(back_populates="monitored_item")


class StatusCheck(SQLModel, table=True):
    """Individual status check result for a monitored item"""

    __tablename__ = "status_checks"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    monitored_item_id: int = Field(foreign_key="monitored_items.id")
    status: MonitorStatus
    response_time_ms: Optional[Decimal] = Field(default=None, decimal_places=3)
    status_code: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    response_headers: Dict[str, str] = Field(default={}, sa_column=Column(JSON))
    response_body_sample: Optional[str] = Field(default=None, max_length=5000)
    checked_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    monitored_item: MonitoredItem = Relationship(back_populates="status_checks")


class UptimeRecord(SQLModel, table=True):
    """Daily uptime statistics for monitored items"""

    __tablename__ = "uptime_records"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    monitored_item_id: int = Field(foreign_key="monitored_items.id")
    date: datetime = Field(index=True)  # Date for this uptime record
    total_checks: int = Field(default=0)
    successful_checks: int = Field(default=0)
    failed_checks: int = Field(default=0)
    average_response_time_ms: Optional[Decimal] = Field(default=None, decimal_places=3)
    uptime_percentage: Decimal = Field(default=Decimal("0"), decimal_places=2)
    downtime_duration_seconds: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    monitored_item: MonitoredItem = Relationship(back_populates="uptime_records")


class Notification(SQLModel, table=True):
    """Notifications sent to users about status changes"""

    __tablename__ = "notifications"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    monitored_item_id: int = Field(foreign_key="monitored_items.id")
    notification_type: NotificationType
    method: NotificationMethod
    title: str = Field(max_length=200)
    message: str = Field(max_length=2000)
    sent_at: Optional[datetime] = Field(default=None)
    delivery_status: str = Field(default="pending", max_length=50)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    notification_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="notifications")


class NotificationSetting(SQLModel, table=True):
    """User preferences for notifications"""

    __tablename__ = "notification_settings"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    notification_type: NotificationType
    method: NotificationMethod
    is_enabled: bool = Field(default=True)
    threshold_minutes: Optional[int] = Field(default=None)  # For delayed notifications
    webhook_url: Optional[str] = Field(default=None, max_length=2000)
    custom_template: Optional[str] = Field(default=None, max_length=5000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="notification_settings")


class ImportExportLog(SQLModel, table=True):
    """Log of import/export operations"""

    __tablename__ = "import_export_logs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    operation_type: str = Field(max_length=50)  # "import" or "export"
    file_format: str = Field(max_length=20)  # "json", "csv", "yaml"
    items_count: int = Field(default=0)
    success_count: int = Field(default=0)
    error_count: int = Field(default=0)
    file_path: Optional[str] = Field(default=None, max_length=500)
    errors: List[str] = Field(default=[], sa_column=Column(JSON))
    status: str = Field(default="pending", max_length=20)  # pending, completed, failed
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    """Schema for creating a new user"""

    username: str = Field(max_length=100)
    email: str = Field(max_length=255)
    full_name: str = Field(max_length=200)
    email_notifications_enabled: bool = Field(default=True)


class UserUpdate(SQLModel, table=False):
    """Schema for updating user information"""

    username: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=200)
    email_notifications_enabled: Optional[bool] = Field(default=None)


class MonitoredItemCreate(SQLModel, table=False):
    """Schema for creating a new monitored item"""

    name: str = Field(max_length=200)
    url: str = Field(max_length=2000)
    monitor_type: MonitorType = Field(default=MonitorType.HTTP)
    check_interval_seconds: int = Field(default=300, ge=60)  # Minimum 1 minute
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    expected_status_code: Optional[int] = Field(default=200)
    expected_content: Optional[str] = Field(default=None, max_length=1000)
    tags: List[str] = Field(default=[])
    custom_headers: Dict[str, str] = Field(default={})
    user_id: int


class MonitoredItemUpdate(SQLModel, table=False):
    """Schema for updating a monitored item"""

    name: Optional[str] = Field(default=None, max_length=200)
    url: Optional[str] = Field(default=None, max_length=2000)
    monitor_type: Optional[MonitorType] = Field(default=None)
    check_interval_seconds: Optional[int] = Field(default=None, ge=60)
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    expected_status_code: Optional[int] = Field(default=None)
    expected_content: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    custom_headers: Optional[Dict[str, str]] = Field(default=None)


class MonitoredItemImport(SQLModel, table=False):
    """Schema for importing monitored items"""

    name: str = Field(max_length=200)
    url: str = Field(max_length=2000)
    monitor_type: str = Field(default="http")
    check_interval_seconds: int = Field(default=300)
    timeout_seconds: int = Field(default=30)
    expected_status_code: Optional[int] = Field(default=200)
    expected_content: Optional[str] = Field(default=None)
    tags: List[str] = Field(default=[])
    custom_headers: Dict[str, str] = Field(default={})


class NotificationSettingCreate(SQLModel, table=False):
    """Schema for creating notification settings"""

    user_id: int
    notification_type: NotificationType
    method: NotificationMethod
    is_enabled: bool = Field(default=True)
    threshold_minutes: Optional[int] = Field(default=None)
    webhook_url: Optional[str] = Field(default=None, max_length=2000)
    custom_template: Optional[str] = Field(default=None, max_length=5000)


class NotificationSettingUpdate(SQLModel, table=False):
    """Schema for updating notification settings"""

    is_enabled: Optional[bool] = Field(default=None)
    threshold_minutes: Optional[int] = Field(default=None)
    webhook_url: Optional[str] = Field(default=None, max_length=2000)
    custom_template: Optional[str] = Field(default=None, max_length=5000)


class UptimeStats(SQLModel, table=False):
    """Schema for uptime statistics response"""

    uptime_percentage: Decimal
    total_checks: int
    successful_checks: int
    failed_checks: int
    average_response_time_ms: Optional[Decimal]
    period_start: datetime
    period_end: datetime


class MonitoringSummary(SQLModel, table=False):
    """Schema for monitoring dashboard summary"""

    total_items: int
    active_items: int
    up_items: int
    down_items: int
    unknown_items: int
    recent_checks: int
    average_response_time_ms: Optional[Decimal]
    overall_uptime_percentage: Decimal
