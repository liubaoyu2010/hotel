from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    code: int
    message: str
    data: dict[str, Any]


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    hotel_name: str
    hotel_location: dict[str, float]


class LoginRequest(BaseModel):
    username: str
    password: str


class ExtensionRegisterRequest(BaseModel):
    device_id: str
    version: str


class CompetitorCreateRequest(BaseModel):
    name: str
    platform: str = "meituan"
    external_id: str
    room_types: list[str] = Field(default_factory=list)


class CompetitorPayload(BaseModel):
    name: str
    room_type: str
    price: float
    availability: bool | None = None
    rating: str | None = None
    sales: str | None = None


class ExtensionReportData(BaseModel):
    competitors: list[CompetitorPayload] = Field(default_factory=list)
    business: dict[str, Any] = Field(default_factory=dict)
    benchmark: dict[str, Any] = Field(default_factory=dict)


class ExtensionReportRequest(BaseModel):
    type: str
    source: str
    data: ExtensionReportData
    url: str
    captured_at: datetime


class ActivityCreateRequest(BaseModel):
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    address: str | None = None
    source: str
    source_url: str | None = None
    activity_type: str
    demand_level: str
    demand_score: float | None = None


class AlertRuleCreateRequest(BaseModel):
    name: str
    rule_type: str = "price_drop"
    threshold: float = 15.0
    is_active: bool = True


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = None
    threshold: float | None = None
    is_active: bool | None = None


class CompetitorAliasUpsertRequest(BaseModel):
    alias_map: dict[str, str]


class UserRoleUpdateRequest(BaseModel):
    role: str
    is_active: bool | None = None


class DashboardSummaryRequest(BaseModel):
    days: int = 7
