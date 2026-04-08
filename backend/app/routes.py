import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_admin
from app.models import CompetitorHotel, ExtensionDevice, PriceTimeSeries, User
from app.schemas import (
    ActivityCreateRequest,
    AlertRuleCreateRequest,
    AlertRuleUpdateRequest,
    CompetitorAliasUpsertRequest,
    CompetitorCreateRequest,
    ExtensionRegisterRequest,
    ExtensionReportRequest,
    LoginRequest,
    RegisterRequest,
    UserRoleUpdateRequest,
)
from app.models import AIReport, AlertRecord, AlertRule, AuditLog, CompetitorAlias, PushDelivery, SurroundingActivity
from app.security import create_access_token, hash_password, verify_password
from app.tasks import alert_check_task, generate_weekly_report_task, push_daily_digest_all_users
from app.celery_app import celery_app

router = APIRouter(prefix="/api/v1")


def ok(data: dict) -> dict:
    return {"code": 200, "message": "success", "data": data}


def normalize_name(name: str) -> str:
    return str(name or "").strip().lower()


def write_audit_log(
    db: Session,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    row = AuditLog(
        actor_user_id=actor.id,
        actor_role=actor.role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(row)


@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    exists = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if exists:
        raise HTTPException(status_code=409, detail="User already exists")
    lat = str(payload.hotel_location.get("lat", ""))
    lng = str(payload.hotel_location.get("lng", ""))
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="manager",
        hotel_name=payload.hotel_name,
        hotel_lat=lat,
        hotel_lng=lng,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"code": 201, "message": "created", "data": {"id": user.id, "username": user.username, "role": user.role}}


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.username == payload.username, User.is_active.is_(True)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user.id, user.username, user.role)
    return ok(
        {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user.id, "username": user.username, "role": user.role},
        }
    )


@router.post("/competitors")
def create_competitor(
    payload: CompetitorCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    if payload.platform != "meituan":
        raise HTTPException(status_code=422, detail="MVP supports platform=meituan only")
    exists = (
        db.query(CompetitorHotel)
        .filter(
            CompetitorHotel.user_id == user.id,
            CompetitorHotel.platform == payload.platform,
            CompetitorHotel.external_id == payload.external_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Competitor already exists")
    competitor = CompetitorHotel(
        user_id=user.id,
        name=payload.name,
        platform=payload.platform,
        external_id=payload.external_id,
        room_types=json.dumps(payload.room_types, ensure_ascii=False),
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return {
        "code": 201,
        "message": "created",
        "data": {
            "id": competitor.id,
            "name": competitor.name,
            "platform": competitor.platform,
            "external_id": competitor.external_id,
            "is_active": competitor.is_active,
        },
    }


@router.get("/competitors")
def list_competitors(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    competitors = db.query(CompetitorHotel).filter(CompetitorHotel.user_id == user.id).all()
    return ok(
        {
            "items": [
                {
                    "id": c.id,
                    "name": c.name,
                    "platform": c.platform,
                    "external_id": c.external_id,
                    "room_types": json.loads(c.room_types),
                    "is_active": c.is_active,
                }
                for c in competitors
            ]
        }
    )


@router.get("/competitors/{competitor_id}/price-history")
def competitor_price_history(
    competitor_id: str,
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    room_type: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    competitor = (
        db.query(CompetitorHotel)
        .filter(CompetitorHotel.id == competitor_id, CompetitorHotel.user_id == user.id)
        .first()
    )
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    query = db.query(PriceTimeSeries).filter(PriceTimeSeries.competitor_hotel_id == competitor.id)
    if room_type:
        query = query.filter(PriceTimeSeries.room_type == room_type)
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00")).replace(tzinfo=None)
            query = query.filter(PriceTimeSeries.captured_at >= start_dt)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid start_time format") from exc
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00")).replace(tzinfo=None)
            query = query.filter(PriceTimeSeries.captured_at <= end_dt)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid end_time format") from exc

    rows = query.order_by(PriceTimeSeries.captured_at.asc()).all()
    prices = [
        {
            "time": r.captured_at.isoformat() + "Z",
            "price": float(r.price),
            "availability": r.availability,
            "room_type": r.room_type,
        }
        for r in rows
    ]
    values = [float(r.price) for r in rows]
    return ok(
        {
            "competitor_id": competitor.id,
            "competitor_name": competitor.name,
            "room_type": room_type,
            "prices": prices,
            "statistics": {
                "avg_price": round(sum(values) / len(values), 2) if values else 0.0,
                "min_price": min(values) if values else 0.0,
                "max_price": max(values) if values else 0.0,
                "count": len(values),
            },
        }
    )


@router.post("/extension/register")
def extension_register(
    payload: ExtensionRegisterRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    token = f"ext-{uuid4()}"
    record = (
        db.query(ExtensionDevice)
        .filter(ExtensionDevice.user_id == user.id, ExtensionDevice.device_id == payload.device_id)
        .first()
    )
    if not record:
        record = ExtensionDevice(
            user_id=user.id,
            device_id=payload.device_id,
            extension_token_hash=hash_password(token),
            status="online",
            version=payload.version,
        )
        db.add(record)
    else:
        record.extension_token_hash = hash_password(token)
        record.status = "online"
        record.version = payload.version
    db.commit()
    return ok(
        {
            "extension_token": token,
            "selectors_config": {"meituan": {"competitor": {}, "business": {}, "benchmark": {}}},
        }
    )


@router.post("/extension/report")
def extension_report(
    payload: ExtensionReportRequest,
    x_extension_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not x_extension_token:
        raise HTTPException(status_code=401, detail="Missing X-Extension-Token")

    device = db.query(ExtensionDevice).all()
    matched = None
    for d in device:
        if verify_password(x_extension_token, d.extension_token_hash):
            matched = d
            break
    if not matched:
        raise HTTPException(status_code=401, detail="Invalid X-Extension-Token")

    competitors = db.query(CompetitorHotel).filter(CompetitorHotel.user_id == matched.user_id).all()
    competitor_map = {normalize_name(c.name): c for c in competitors}
    aliases = db.query(CompetitorAlias).filter(CompetitorAlias.user_id == matched.user_id).all()
    alias_map = {normalize_name(a.alias_name): normalize_name(a.canonical_name) for a in aliases}
    processed = 0
    unmatched_competitors = []
    for item in payload.data.competitors:
        item_name_norm = normalize_name(item.name)
        mapped_name_norm = alias_map.get(item_name_norm, item_name_norm)
        target = competitor_map.get(mapped_name_norm)
        if not target:
            unmatched_competitors.append(item.name)
            continue
        row = PriceTimeSeries(
            competitor_hotel_id=target.id,
            room_type=item.room_type,
            price=item.price,
            availability=item.availability,
            data_source="extension",
            captured_at=payload.captured_at.replace(tzinfo=None),
        )
        db.add(row)
        processed += 1
    matched.last_collect_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    job = alert_check_task.delay(user_id=matched.user_id, processed_count=processed)
    return ok(
        {
            "received": True,
            "processed_count": processed,
            "alerts_triggered": 0,
            "alert_task_id": job.id,
            "alert_task_status_endpoint": f"/api/v1/tasks/status/{job.id}",
            "unmatched_competitors": unmatched_competitors,
        }
    )


@router.get("/dashboard/price-overview")
def dashboard_price_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    competitors = db.query(CompetitorHotel).filter(CompetitorHotel.user_id == user.id).all()
    competitor_ids = [c.id for c in competitors]
    prices = []
    if competitor_ids:
        prices = db.query(PriceTimeSeries).filter(PriceTimeSeries.competitor_hotel_id.in_(competitor_ids)).all()
    values = [float(p.price) for p in prices]
    summary = {
        "total_competitors": len(competitors),
        "price_change_today": 0.0,
        "avg_price": round(sum(values) / len(values), 2) if values else 0.0,
        "lowest_price": min(values) if values else 0.0,
        "highest_price": max(values) if values else 0.0,
    }
    return ok(
        {
            "summary": summary,
            "trends": [],
            "competitors": [],
            "alerts": [],
            "extension_status": {"status": "online", "last_collect_at": None},
        }
    )


@router.get("/dashboard/overview")
def dashboard_overview(
    days: int = Query(default=7, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    competitors = db.query(CompetitorHotel).filter(CompetitorHotel.user_id == user.id).all()
    competitor_ids = [c.id for c in competitors]
    alerts_count = db.query(AlertRecord).filter(AlertRecord.user_id == user.id).count()
    activities_count = db.query(SurroundingActivity).count()
    device_count = db.query(ExtensionDevice).filter(ExtensionDevice.user_id == user.id).count()
    prices = []
    if competitor_ids:
        prices = db.query(PriceTimeSeries).filter(PriceTimeSeries.competitor_hotel_id.in_(competitor_ids)).all()
    values = [float(p.price) for p in prices]
    return ok(
        {
            "days": days,
            "summary": {
                "total_competitors": len(competitors),
                "total_alerts": alerts_count,
                "total_activities": activities_count,
                "total_devices": device_count,
                "avg_price": round(sum(values) / len(values), 2) if values else 0.0,
            },
            "latest_report": _latest_report(db, user.id),
            "push_stats": _push_stats(db, user.id),
        }
    )


def _latest_report(db: Session, user_id: str) -> dict | None:
    row = db.query(AIReport).filter(AIReport.user_id == user_id).order_by(AIReport.created_at.desc()).first()
    if not row:
        return None
    return {
        "id": row.id,
        "period_type": row.period_type,
        "summary_text": row.summary_text,
        "recommendation_text": row.recommendation_text,
        "created_at": row.created_at.isoformat() + "Z",
    }


def _push_stats(db: Session, user_id: str) -> dict:
    rows = db.query(PushDelivery).filter(PushDelivery.user_id == user_id).all()
    return {
        "total": len(rows),
        "sent": len([r for r in rows if r.status == "sent"]),
        "failed": len([r for r in rows if r.status == "failed"]),
        "latest_sent_at": (
            max([r.sent_at for r in rows]).isoformat() + "Z" if rows and max([r.sent_at for r in rows]) else None
        ),
    }


@router.get("/activities/calendar")
def activities_calendar(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    demand_level: str | None = Query(default=None),
    activity_type: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(SurroundingActivity)
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=None)
        query = query.filter(SurroundingActivity.start_time >= start_dt)
    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")).replace(tzinfo=None)
        query = query.filter(SurroundingActivity.end_time <= end_dt)
    if demand_level:
        query = query.filter(SurroundingActivity.demand_level == demand_level)
    if activity_type:
        query = query.filter(SurroundingActivity.activity_type == activity_type)
    rows = query.order_by(SurroundingActivity.start_time.asc()).all()
    items = [
        {
            "id": r.id,
            "title": r.title,
            "start_time": r.start_time.isoformat() + "Z",
            "end_time": r.end_time.isoformat() + "Z",
            "address": r.address,
            "source": r.source,
            "activity_type": r.activity_type,
            "demand_level": r.demand_level,
            "demand_score": float(r.demand_score) if r.demand_score is not None else None,
        }
        for r in rows
    ]
    return ok({"activities": items, "summary": {"total_activities": len(items), "user_id": user.id}})


@router.post("/activities")
def create_activity(
    payload: ActivityCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    row = SurroundingActivity(
        title=payload.title,
        description=payload.description,
        start_time=payload.start_time.replace(tzinfo=None),
        end_time=payload.end_time.replace(tzinfo=None),
        address=payload.address,
        source=payload.source,
        source_url=payload.source_url,
        activity_type=payload.activity_type,
        demand_level=payload.demand_level,
        demand_score=payload.demand_score,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"code": 201, "message": "created", "data": {"id": row.id, "title": row.title}}


@router.post("/alert-rules")
def create_alert_rule(
    payload: AlertRuleCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    if payload.rule_type != "price_drop":
        raise HTTPException(status_code=422, detail="Only price_drop is supported now")
    rule = AlertRule(
        user_id=user.id,
        name=payload.name,
        rule_type=payload.rule_type,
        threshold=payload.threshold,
        is_active=payload.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {
        "code": 201,
        "message": "created",
        "data": {
            "id": rule.id,
            "name": rule.name,
            "rule_type": rule.rule_type,
            "threshold": float(rule.threshold),
            "is_active": rule.is_active,
        },
    }


@router.get("/alert-rules")
def list_alert_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.query(AlertRule).filter(AlertRule.user_id == user.id).order_by(AlertRule.created_at.desc()).all()
    return ok(
        {
            "items": [
                {
                    "id": r.id,
                    "name": r.name,
                    "rule_type": r.rule_type,
                    "threshold": float(r.threshold),
                    "is_active": r.is_active,
                }
                for r in rows
            ]
        }
    )


@router.get("/alerts")
def list_alert_records(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(AlertRecord)
        .filter(AlertRecord.user_id == user.id)
        .order_by(AlertRecord.created_at.desc())
        .limit(100)
        .all()
    )
    return ok(
        {
            "items": [
                {
                    "id": r.id,
                    "alert_rule_id": r.alert_rule_id,
                    "competitor_hotel_id": r.competitor_hotel_id,
                    "trigger_type": r.trigger_type,
                    "message": r.message,
                    "created_at": r.created_at.isoformat() + "Z",
                }
                for r in rows
            ]
        }
    )


@router.put("/alert-rules/{rule_id}")
def update_alert_rule(
    rule_id: str,
    payload: AlertRuleUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.user_id == user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    if payload.name is not None:
        rule.name = payload.name
    if payload.threshold is not None:
        rule.threshold = payload.threshold
    if payload.is_active is not None:
        rule.is_active = payload.is_active
    db.commit()
    db.refresh(rule)
    return ok(
        {
            "id": rule.id,
            "name": rule.name,
            "rule_type": rule.rule_type,
            "threshold": float(rule.threshold),
            "is_active": rule.is_active,
        }
    )


@router.delete("/alert-rules/{rule_id}")
def delete_alert_rule(
    rule_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.user_id == user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    db.delete(rule)
    db.commit()
    return ok({"deleted": True, "id": rule_id})


@router.get("/notifications")
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    offset = (page - 1) * page_size
    total = db.query(AlertRecord).filter(AlertRecord.user_id == user.id).count()
    rows = (
        db.query(AlertRecord)
        .filter(AlertRecord.user_id == user.id)
        .order_by(AlertRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return ok(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "type": "alert",
                    "title": r.trigger_type,
                    "content": r.message,
                    "created_at": r.created_at.isoformat() + "Z",
                }
                for r in rows
            ]
        }
    )


@router.get("/reports/weekly")
def list_weekly_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    offset = (page - 1) * page_size
    query = db.query(AIReport).filter(AIReport.user_id == user.id, AIReport.period_type == "weekly")
    total = query.count()
    rows = query.order_by(AIReport.created_at.desc()).offset(offset).limit(page_size).all()
    return ok(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "period_start": r.period_start.isoformat() + "Z",
                    "period_end": r.period_end.isoformat() + "Z",
                    "summary_text": r.summary_text,
                    "recommendation_text": r.recommendation_text,
                    "created_at": r.created_at.isoformat() + "Z",
                }
                for r in rows
            ],
        }
    )


@router.post("/reports/weekly/generate")
def generate_weekly_report(user: User = Depends(get_current_user)) -> dict:
    result = generate_weekly_report_task(user.id)
    return {"code": 200, "message": "success", "data": result}


@router.post("/notifications/push-now")
def push_now(user: User = Depends(require_admin)) -> dict:
    result = push_daily_digest_all_users()
    return {"code": 200, "message": "success", "data": {"result": result, "operator_id": user.id}}


@router.get("/extension/devices")
def list_extension_devices(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.query(ExtensionDevice).filter(ExtensionDevice.user_id == user.id).order_by(ExtensionDevice.created_at.desc()).all()
    return ok(
        {
            "items": [
                {
                    "id": r.id,
                    "device_id": r.device_id,
                    "status": r.status,
                    "version": r.version,
                    "last_collect_at": r.last_collect_at.isoformat() + "Z" if r.last_collect_at else None,
                    "created_at": r.created_at.isoformat() + "Z",
                }
                for r in rows
            ]
        }
    )


@router.get("/extension/reports")
def list_extension_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    competitor_ids = [
        c.id for c in db.query(CompetitorHotel.id).filter(CompetitorHotel.user_id == user.id).all()
    ]
    if not competitor_ids:
        return ok({"page": page, "page_size": page_size, "total": 0, "items": []})
    offset = (page - 1) * page_size
    query = db.query(PriceTimeSeries).filter(PriceTimeSeries.competitor_hotel_id.in_(competitor_ids))
    total = query.count()
    rows = query.order_by(PriceTimeSeries.captured_at.desc()).offset(offset).limit(page_size).all()
    comp_name = {
        c.id: c.name
        for c in db.query(CompetitorHotel).filter(CompetitorHotel.id.in_(competitor_ids)).all()
    }
    return ok(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "competitor_id": r.competitor_hotel_id,
                    "competitor_name": comp_name.get(r.competitor_hotel_id, ""),
                    "room_type": r.room_type,
                    "price": float(r.price),
                    "availability": r.availability,
                    "captured_at": r.captured_at.isoformat() + "Z",
                }
                for r in rows
            ],
        }
    )


@router.get("/system/users")
def system_list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.query(User).order_by(User.created_at.desc()).all()
    return ok(
        {
            "items": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() + "Z",
                }
                for u in rows
            ],
            "operator_id": admin.id,
        }
    )


@router.put("/system/users/{user_id}")
def system_update_user(
    user_id: str,
    payload: UserRoleUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.query(User).filter(User.id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    before = {"role": row.role, "is_active": row.is_active}
    if payload.role:
        row.role = payload.role
    if payload.is_active is not None:
        row.is_active = payload.is_active
    write_audit_log(
        db=db,
        actor=admin,
        action="system.user.update",
        resource_type="user",
        resource_id=row.id,
        metadata={"before": before, "after": {"role": row.role, "is_active": row.is_active}},
    )
    db.commit()
    db.refresh(row)
    return ok(
        {
            "id": row.id,
            "username": row.username,
            "role": row.role,
            "is_active": row.is_active,
        }
    )


@router.get("/system/audit-logs")
def system_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    offset = (page - 1) * page_size
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    total = query.count()
    rows = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()
    return ok(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "actor_user_id": r.actor_user_id,
                    "actor_role": r.actor_role,
                    "action": r.action,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "metadata": json.loads(r.metadata_json or "{}"),
                    "created_at": r.created_at.isoformat() + "Z",
                }
                for r in rows
            ],
            "operator_id": admin.id,
        }
    )


@router.get("/competitor-aliases")
def list_competitor_aliases(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.query(CompetitorAlias).filter(CompetitorAlias.user_id == user.id).all()
    alias_map = {r.alias_name: r.canonical_name for r in rows}
    return ok({"alias_map": alias_map, "count": len(alias_map)})


@router.put("/competitor-aliases")
def upsert_competitor_aliases(
    payload: CompetitorAliasUpsertRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    db.query(CompetitorAlias).filter(CompetitorAlias.user_id == user.id).delete()
    cleaned = {}
    for alias_name, canonical_name in payload.alias_map.items():
        a = str(alias_name or "").strip()
        c = str(canonical_name or "").strip()
        if not a or not c:
            continue
        cleaned[a] = c
        row = CompetitorAlias(user_id=user.id, alias_name=a, canonical_name=c)
        db.add(row)
    db.commit()
    return ok({"alias_map": cleaned, "count": len(cleaned)})


@router.post("/tasks/alert-check")
def trigger_alert_check(
    processed_count: int = 0, user: User = Depends(get_current_user)
) -> dict:
    job = alert_check_task.delay(user_id=user.id, processed_count=processed_count)
    return {"code": 202, "message": "accepted", "data": {"task_id": job.id}}


@router.get("/tasks/status/{task_id}")
def task_status(task_id: str, user: User = Depends(get_current_user)) -> dict:
    result = celery_app.AsyncResult(task_id)
    payload = {"task_id": task_id, "state": result.state}
    if result.ready():
        try:
            json.dumps(result.result)
            payload["result"] = result.result
        except TypeError:
            payload["result"] = str(result.result)
    payload["user_id"] = user.id
    return ok(payload)
