from datetime import datetime, timedelta
import json
import logging

from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import AIReport, AlertRecord, AlertRule, CompetitorHotel, PriceTimeSeries, PushDelivery, SurroundingActivity, User

logger = logging.getLogger(__name__)


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
                    # Push alert notification
                    _push_alert_now(
                        user_id,
                        "price_drop",
                        f"竞品 {comp.name} 降价 {drop_pct:.1f}%，低于阈值 {float(rule.threshold):.1f}%，请及时关注并调整定价。",
                    )
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


def _build_ai_report(payload: dict, user: User) -> tuple[str, str]:
    """Generate AI-powered weekly report using DeepSeek or other LLM."""
    from app.config import settings
    from app.services.llm import call_llm_json

    system_prompt = (
        "你是一位专业的酒店收益管理顾问。根据提供的监控数据，生成简明专业的周报分析和定价建议。"
        "必须返回JSON格式，包含两个字段：\n"
        "- summary_text: 市场分析摘要（200-400字，包含数据引用、趋势判断、异常说明）\n"
        "- recommendation_text: 定价策略建议（150-300字，具体可操作，包含时间节点和幅度）"
    )

    user_prompt = (
        f"## 酒店监控周报数据\n\n"
        f"**酒店名称**: {user.hotel_name}\n"
        f"**报告周期**: 近7天\n\n"
        f"### 竞品价格数据\n"
        f"- 监控竞品数量: {payload['total_competitors']}家\n"
        f"- 采集价格记录: {payload['price_points']}条\n"
        f"- 竞品均价: ¥{payload['avg_price']}\n"
    )

    # Add per-competitor details if available
    comp_details = payload.get("competitor_details", [])
    if comp_details:
        user_prompt += "\n#### 各竞品详情\n"
        for cd in comp_details:
            user_prompt += f"- {cd['name']}: 最新价¥{cd['latest_price']}"
            if cd.get("price_change_pct") is not None:
                arrow = "↑" if cd["price_change_pct"] > 0 else "↓"
                user_prompt += f"（周{arrow}{abs(cd['price_change_pct']):.1f}%）"
            user_prompt += "\n"

    # Add alerts
    user_prompt += f"\n### 告警情况\n- 本周告警: {payload['alerts_count']}条\n"
    alert_details = payload.get("alert_details", [])
    if alert_details:
        for ad in alert_details[:5]:
            user_prompt += f"  - {ad}\n"

    # Add activities
    user_prompt += f"\n### 周边活动\n- 相关活动: {payload['activities_count']}个\n"
    activity_details = payload.get("activity_details", [])
    if activity_details:
        for ad in activity_details[:8]:
            user_prompt += f"  - {ad}\n"

    user_prompt += (
        "\n---\n"
        "请基于以上数据，生成JSON格式的周报。注意：\n"
        "1. summary_text 要有数据支撑，指出关键变化和趋势\n"
        "2. recommendation_text 要给出具体可执行的定价建议，包含调整时间、幅度、房型\n"
        "3. 如果有高热度活动，结合活动给出提价建议\n"
    )

    try:
        result = call_llm_json(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            model=settings.ai_model,
            temperature=0.5,
            max_tokens=1500,
        )
        summary = result.get("summary_text", "")
        recommendation = result.get("recommendation_text", "")
        if not summary or not recommendation:
            logger.warning("LLM returned empty fields, falling back to mock")
            return _build_report_text(payload)
        return summary, recommendation
    except Exception as e:
        logger.warning("AI report generation failed, falling back to mock: %s", e)
        return _build_report_text(payload)


@celery_app.task(name="tasks.generate_weekly_report")
def generate_weekly_report_task(user_id: str) -> dict:
    db = SessionLocal()
    try:
        from app.config import settings

        now = datetime.utcnow()
        period_start = now - timedelta(days=7)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"user_id": user_id, "error": "user not found"}

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
        activities = (
            db.query(SurroundingActivity)
            .filter(SurroundingActivity.start_time >= period_start)
            .all()
        )
        activities_count = len(activities)

        # Build per-competitor details
        competitor_details = []
        for comp in competitors:
            comp_prices = [float(p.price) for p in prices if p.competitor_hotel_id == comp.id]
            latest_price = comp_prices[-1] if comp_prices else 0.0
            price_change_pct = None
            if len(comp_prices) >= 2:
                first, last = comp_prices[0], comp_prices[-1]
                if first > 0:
                    price_change_pct = round(((last - first) / first) * 100, 1)
            competitor_details.append({
                "name": comp.name,
                "latest_price": latest_price,
                "price_change_pct": price_change_pct,
            })

        # Build alert details
        alert_rows = (
            db.query(AlertRecord)
            .filter(AlertRecord.user_id == user_id, AlertRecord.created_at >= period_start)
            .order_by(AlertRecord.created_at.desc())
            .limit(10)
            .all()
        )
        alert_details = [a.message[:100] for a in alert_rows]

        # Build activity details
        activity_details = []
        for act in activities[:10]:
            detail = f"{act.title}（{act.activity_type}，热度{act.demand_level}，{act.start_time.strftime('%m/%d')}~{act.end_time.strftime('%m/%d')}）"
            activity_details.append(detail)

        report_payload = {
            "total_competitors": len(competitors),
            "price_points": len(values),
            "avg_price": round(sum(values) / len(values), 2) if values else 0.0,
            "alerts_count": alerts_count,
            "activities_count": activities_count,
            "competitor_details": competitor_details,
            "alert_details": alert_details,
            "activity_details": activity_details,
        }

        # Choose report generation method
        if settings.ai_provider in ("deepseek", "openai") and settings.ai_api_key:
            summary_text, recommendation_text = _build_ai_report(report_payload, user)
        else:
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
        return {
            "report_id": row.id,
            "user_id": user_id,
            "period_type": row.period_type,
            "ai_provider": settings.ai_provider,
        }
    except Exception as e:
        logger.error("generate_weekly_report_task error: %s", e, exc_info=True)
        return {"user_id": user_id, "error": str(e)}
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
    from app.config import settings as _settings
    from app.services.push import push_message, format_daily_digest

    db = SessionLocal()
    sent = 0
    failed = 0
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

            alerts_count = db.query(AlertRecord).filter(AlertRecord.user_id == user.id).count()
            activities_count = db.query(SurroundingActivity).count()

            title, content = format_daily_digest(
                user_name=user.hotel_name or user.username,
                summary_text=latest.summary_text,
                recommendation_text=latest.recommendation_text,
                alerts_count=alerts_count,
                activities_count=activities_count,
            )

            result = push_message(
                title=title,
                content=content,
                channel=_settings.push_channel,
                serverchan_key=_settings.push_serverchan_key,
                wxpusher_token=_settings.push_wxpusher_token,
                wxpusher_uids=_settings.push_wxpusher_uids,
                webhook_url=_settings.push_webhook_url,
            )

            delivery = PushDelivery(
                user_id=user.id,
                channel=_settings.push_channel,
                title=title,
                content=content,
                status="sent" if result.success else "failed",
                provider_message_id=result.provider_message_id,
                error_message=result.error_message,
            )
            db.add(delivery)

            if result.success:
                sent += 1
            else:
                failed += 1
                logger.warning("Push failed for user %s: %s", user.id, result.error_message)

        db.commit()
        return {"sent": sent, "failed": failed, "channel": _settings.push_channel}
    finally:
        db.close()


def _push_alert_now(user_id: str, alert_type: str, message: str) -> None:
    """Send an alert push notification immediately."""
    from app.config import settings as _settings
    from app.services.push import push_message, format_alert_message

    if _settings.push_channel == "console":
        return

    db = SessionLocal()
    try:
        title, content = format_alert_message(alert_type, message)

        result = push_message(
            title=title,
            content=content,
            channel=_settings.push_channel,
            serverchan_key=_settings.push_serverchan_key,
            wxpusher_token=_settings.push_wxpusher_token,
            wxpusher_uids=_settings.push_wxpusher_uids,
            webhook_url=_settings.push_webhook_url,
        )

        delivery = PushDelivery(
            user_id=user_id,
            channel=_settings.push_channel,
            title=title,
            content=content,
            status="sent" if result.success else "failed",
            provider_message_id=result.provider_message_id,
            error_message=result.error_message,
        )
        db.add(delivery)
        db.commit()
    except Exception as e:
        logger.warning("_push_alert_now failed: %s", e)
    finally:
        db.close()


@celery_app.task(name="tasks.collect_activities")
def collect_activities_task(
    user_id: str,
    city: str | None = None,
    radius_km: float = 3.0,
    collector_name: str | None = None,
) -> dict:
    """Collect activities for a single user.

    Flow: get user info -> run collectors -> dedup -> evaluate demand -> filter by radius -> save -> alert
    """
    from app.collectors import get_all_collectors, get_collector
    from app.services.dedup import dedup_activities
    from app.services.demand_evaluator import evaluate_demand
    from app.services.geo import filter_by_radius

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"user_id": user_id, "error": "user not found"}

        # Determine city
        if not city:
            from app.config import settings
            city = settings.activity_city_override or user.hotel_name or "北京"

        # Run collectors
        if collector_name:
            collector = get_collector(collector_name)
            collectors = [collector] if collector else []
        else:
            collectors = get_all_collectors()

        all_raw: list = []
        errors: list[str] = []
        for collector in collectors:
            try:
                raw = collector.collect(city=city, radius_km=radius_km)
                logger.info("Collector %s returned %d activities", collector.name, len(raw))
                all_raw.extend(raw)
            except Exception as e:
                msg = f"{collector.name}: {e}"
                errors.append(msg)
                logger.warning("Collector %s failed: %s", collector.name, e)

        if not all_raw:
            return {
                "user_id": user_id,
                "total_collected": 0,
                "new_saved": 0,
                "duplicates": 0,
                "errors": errors,
            }

        # Dedup
        new_activities, dup_activities = dedup_activities(db, all_raw)

        # Geocode addresses for activities missing coordinates
        from app.config import settings as _settings
        from app.services.geocoder import batch_geocode
        batch_geocode(new_activities, city=city, api_key=_settings.amap_api_key)

        # Evaluate demand + filter by radius
        hotel_lat = None
        hotel_lng = None
        try:
            hotel_lat = float(user.hotel_lat) if user.hotel_lat else None
            hotel_lng = float(user.hotel_lng) if user.hotel_lng else None
        except (ValueError, TypeError):
            pass

        saved_count = 0
        alert_count = 0
        for raw in new_activities:
            # Evaluate demand
            demand_level, demand_score = evaluate_demand(
                activity_type=raw.activity_type,
                estimated_attendees=raw.estimated_attendees,
                start_time=raw.start_time,
                end_time=raw.end_time,
            )

            # Calculate distance if coordinates available
            distance_km_val = None
            has_coords = raw.latitude and raw.longitude
            if hotel_lat and hotel_lng and has_coords:
                try:
                    from app.services.geo import distance_km
                    distance_km_val = distance_km(
                        hotel_lat, hotel_lng,
                        float(raw.latitude), float(raw.longitude),
                    )
                except (ValueError, TypeError):
                    pass

            # When hotel coordinates are set, enforce radius filtering:
            if hotel_lat and hotel_lng:
                if distance_km_val is not None and distance_km_val > radius_km:
                    # Outside radius — skip
                    continue
                if distance_km_val is None:
                    # No coordinates — special handling for exam-type activities
                    if raw.activity_type == "exam" and raw.address:
                        # National exams have venues in every major city;
                        # if the address mentions the user's city (inferred from coords), include it
                        from app.services.geo import infer_city
                        city_name = infer_city(hotel_lat, hotel_lng)
                        if city_name and city_name in raw.address:
                            distance_km_val = 0.0  # Treat as within radius
                        else:
                            continue
                    else:
                        # Non-exam activity without coords — cannot verify, skip
                        continue

            row = SurroundingActivity(
                title=raw.title,
                description=raw.description,
                start_time=raw.start_time,
                end_time=raw.end_time,
                address=raw.address,
                source=raw.source,
                source_id=raw.source_id,
                source_url=raw.source_url,
                activity_type=raw.activity_type,
                demand_level=demand_level,
                demand_score=demand_score,
                latitude=str(raw.latitude) if raw.latitude else None,
                longitude=str(raw.longitude) if raw.longitude else None,
                estimated_attendees=raw.estimated_attendees,
            )
            db.add(row)
            saved_count += 1

            # Create alert for high/medium demand new activities
            if demand_level in ("high", "medium"):
                dedup_since = datetime.utcnow() - timedelta(hours=2)
                recent_alert = (
                    db.query(AlertRecord)
                    .filter(
                        AlertRecord.user_id == user_id,
                        AlertRecord.trigger_type == "new_activity",
                        AlertRecord.created_at >= dedup_since,
                    )
                    .first()
                )
                if not recent_alert:
                    rec = AlertRecord(
                        user_id=user_id,
                        trigger_type="new_activity",
                        message=f"新活动：{raw.title}（需求热度：{demand_level}，{raw.start_time.strftime('%m/%d')}开始）",
                    )
                    db.add(rec)
                    alert_count += 1
                    # Push activity alert notification
                    _push_alert_now(
                        user_id,
                        "new_activity",
                        f"新活动：{raw.title}\n类型：{raw.activity_type}\n热度：{demand_level}\n时间：{raw.start_time.strftime('%m/%d')}~{raw.end_time.strftime('%m/%d')}",
                    )

        db.commit()
        return {
            "user_id": user_id,
            "city": city,
            "total_collected": len(all_raw),
            "new_saved": saved_count,
            "duplicates": len(dup_activities),
            "alerts_created": alert_count,
            "errors": errors,
        }
    except Exception as e:
        logger.error("collect_activities_task error: %s", e, exc_info=True)
        return {"user_id": user_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="tasks.collect_activities_all_users")
def collect_activities_all_users() -> dict:
    """Trigger activity collection for all active users."""
    from app.config import settings
    if not settings.activity_collect_enabled:
        return {"skipped": True, "reason": "activity_collect_enabled is false"}

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        queued = 0
        for user in users:
            collect_activities_task.delay(
                user_id=user.id,
                radius_km=settings.activity_default_radius_km,
            )
            queued += 1
        return {"queued_users": queued}
    finally:
        db.close()
