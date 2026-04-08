from datetime import datetime, timedelta
import json

from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import AIReport, AlertRecord, AlertRule, CompetitorHotel, PriceTimeSeries, PushDelivery, SurroundingActivity, User


@celery_app.task(name="tasks.alert_check")
def alert_check_task(user_id: str, processed_count: int) -> dict:
    db = SessionLocal()
    alerts_triggered = 0
    try:
        rules = (
            db.query(AlertRule)
            .filter(AlertRule.user_id == user_id, AlertRule.is_active.is_(True), AlertRule.rule_type == "price_drop")
            .all()
        )
        competitors = db.query(CompetitorHotel).filter(CompetitorHotel.user_id == user_id).all()
        for comp in competitors:
            rows = (
                db.query(PriceTimeSeries)
                .filter(PriceTimeSeries.competitor_hotel_id == comp.id)
                .order_by(PriceTimeSeries.captured_at.desc())
                .limit(2)
                .all()
            )
            if len(rows) < 2:
                continue
            latest = float(rows[0].price)
            previous = float(rows[1].price)
            if previous <= 0:
                continue
            drop_pct = ((previous - latest) / previous) * 100
            for rule in rules:
                if drop_pct >= float(rule.threshold):
                    # Dedup window: avoid repeating same alert in 30 minutes.
                    dedup_since = datetime.utcnow() - timedelta(minutes=30)
                    recent = (
                        db.query(AlertRecord)
                        .filter(
                            AlertRecord.user_id == user_id,
                            AlertRecord.alert_rule_id == rule.id,
                            AlertRecord.competitor_hotel_id == comp.id,
                            AlertRecord.trigger_type == "price_drop",
                            AlertRecord.created_at >= dedup_since,
                        )
                        .first()
                    )
                    if recent:
                        break
                    rec = AlertRecord(
                        user_id=user_id,
                        alert_rule_id=rule.id,
                        competitor_hotel_id=comp.id,
                        trigger_type="price_drop",
                        message=f"{comp.name} price dropped {drop_pct:.2f}%, threshold {float(rule.threshold):.2f}%",
                    )
                    db.add(rec)
                    alerts_triggered += 1
                    break
        db.commit()
    finally:
        db.close()

    return {
        "user_id": user_id,
        "processed_count": processed_count,
        "alerts_triggered": alerts_triggered,
    }


def _build_report_text(payload: dict) -> tuple[str, str]:
    summary = (
        f"近7天共监控{payload['total_competitors']}家竞品，采集{payload['price_points']}条价格记录，"
        f"均价{payload['avg_price']}，新增告警{payload['alerts_count']}条，相关活动{payload['activities_count']}个。"
    )
    recommendation = (
        "建议：对高频降价竞品设置更细分房型阈值，并结合未来7天高热度活动提前2-3天进行阶梯提价；"
        "若活动热度为低且竞品持续降价，优先通过权益包而非直接降价应对。"
    )
    return summary, recommendation


@celery_app.task(name="tasks.generate_weekly_report")
def generate_weekly_report_task(user_id: str) -> dict:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        period_start = now - timedelta(days=7)
        competitors = db.query(CompetitorHotel).filter(CompetitorHotel.user_id == user_id).all()
        competitor_ids = [c.id for c in competitors]
        prices_q = db.query(PriceTimeSeries)
        if competitor_ids:
            prices_q = prices_q.filter(PriceTimeSeries.competitor_hotel_id.in_(competitor_ids))
        prices_q = prices_q.filter(PriceTimeSeries.captured_at >= period_start)
        prices = prices_q.all()
        values = [float(p.price) for p in prices]
        alerts_count = (
            db.query(AlertRecord)
            .filter(AlertRecord.user_id == user_id, AlertRecord.created_at >= period_start)
            .count()
        )
        activities_count = db.query(SurroundingActivity).count()
        report_payload = {
            "total_competitors": len(competitors),
            "price_points": len(values),
            "avg_price": round(sum(values) / len(values), 2) if values else 0.0,
            "alerts_count": alerts_count,
            "activities_count": activities_count,
        }
        summary_text, recommendation_text = _build_report_text(report_payload)
        row = AIReport(
            user_id=user_id,
            period_type="weekly",
            period_start=period_start,
            period_end=now,
            summary_text=summary_text,
            recommendation_text=recommendation_text,
            raw_json=json.dumps(report_payload, ensure_ascii=False),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"report_id": row.id, "user_id": user_id, "period_type": row.period_type}
    finally:
        db.close()


@celery_app.task(name="tasks.generate_weekly_reports_all_users")
def generate_weekly_reports_all_users() -> dict:
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        for user in users:
            generate_weekly_report_task.delay(user.id)
        return {"queued_users": len(users)}
    finally:
        db.close()


@celery_app.task(name="tasks.push_daily_digest_all_users")
def push_daily_digest_all_users() -> dict:
    db = SessionLocal()
    sent = 0
    try:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        for user in users:
            latest = (
                db.query(AIReport)
                .filter(AIReport.user_id == user.id)
                .order_by(AIReport.created_at.desc())
                .first()
            )
            if not latest:
                continue
            delivery = PushDelivery(
                user_id=user.id,
                channel="console",
                title="每日监控摘要",
                content=f"{latest.summary_text}\n{latest.recommendation_text}",
                status="sent",
            )
            db.add(delivery)
            sent += 1
        db.commit()
        return {"sent": sent}
    finally:
        db.close()
