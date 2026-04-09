from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PushResult:
    """Result of a push attempt."""
    success: bool
    provider_message_id: str | None = None
    error_message: str | None = None


def push_message(
    title: str,
    content: str,
    channel: str = "console",
    *,
    serverchan_key: str = "",
    wxpusher_token: str = "",
    wxpusher_uids: str = "",
    webhook_url: str = "",
) -> PushResult:
    """Send a push notification through the specified channel.

    Supported channels:
    - console: log only (default, no actual push)
    - serverchan: Server酱 (sct.ftqq.com)
    - wxpusher: WxPusher (wxpusher.zjiecode.com)
    - webhook: generic webhook POST
    """
    if channel == "console":
        logger.info("[Push/console] %s: %s", title, content[:100])
        return PushResult(success=True)

    if channel == "serverchan":
        return _push_serverchan(title, content, serverchan_key)

    if channel == "wxpusher":
        return _push_wxpusher(title, content, wxpusher_token, wxpusher_uids)

    if channel == "webhook":
        return _push_webhook(title, content, webhook_url)

    logger.warning("Unknown push channel: %s", channel)
    return PushResult(success=False, error_message=f"Unknown channel: {channel}")


def _push_serverchan(title: str, content: str, key: str) -> PushResult:
    """Send via Server酱 (sct.ftqq.com).

    API docs: https://sct.ftqq.com/sendkey
    Requires PUSH_SERVERCHAN_KEY (SendKey).
    """
    if not key:
        return PushResult(success=False, error_message="PUSH_SERVERCHAN_KEY not configured")

    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, data={"title": title, "desp": content})
            if resp.status_code != 200:
                return PushResult(
                    success=False,
                    error_message=f"ServerChan HTTP {resp.status_code}: {resp.text[:200]}",
                )
            data = resp.json()
            if data.get("code") != 0:
                return PushResult(
                    success=False,
                    error_message=f"ServerChan error: {data.get('message', 'unknown')}",
                )
            msgid = str(data.get("data", {}).get("push_id", ""))
            logger.info("[Push/ServerChan] Sent: %s (id=%s)", title[:30], msgid)
            return PushResult(success=True, provider_message_id=msgid)

    except Exception as e:
        return PushResult(success=False, error_message=f"ServerChan exception: {e}")


def _push_wxpusher(title: str, content: str, token: str, uids: str) -> PushResult:
    """Send via WxPusher (wxpusher.zjiecode.com).

    API docs: https://wxpusher.zjiecode.com/docs/api
    Requires PUSH_WXPUSHER_TOKEN (App Token) and PUSH_WXPUSHER_UIDS (comma-separated UIDs).
    Content is sent as markdown.
    """
    if not token:
        return PushResult(success=False, error_message="PUSH_WXPUSHER_TOKEN not configured")
    if not uids:
        return PushResult(success=False, error_message="PUSH_WXPUSHER_UIDS not configured")

    uid_list = [u.strip() for u in uids.split(",") if u.strip()]
    if not uid_list:
        return PushResult(success=False, error_message="No valid UIDs in PUSH_WXPUSHER_UIDS")

    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = {
        "appToken": token,
        "content": f"## {title}\n\n{content}",
        "summary": title[:50],
        "contentType": 2,  # 2=markdown
        "uids": uid_list,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                return PushResult(
                    success=False,
                    error_message=f"WxPusher HTTP {resp.status_code}: {resp.text[:200]}",
                )
            data = resp.json()
            if data.get("code") != 1000:
                return PushResult(
                    success=False,
                    error_message=f"WxPusher error: {data.get('msg', 'unknown')}",
                )
            msgid = str(data.get("data", {}).get("messageId", ""))
            logger.info("[Push/WxPusher] Sent: %s (id=%s)", title[:30], msgid)
            return PushResult(success=True, provider_message_id=msgid)

    except Exception as e:
        return PushResult(success=False, error_message=f"WxPusher exception: {e}")


def _push_webhook(title: str, content: str, webhook_url: str) -> PushResult:
    """Send via generic webhook POST (JSON body)."""
    if not webhook_url:
        return PushResult(success=False, error_message="PUSH_WEBHOOK_URL not configured")

    payload = {"title": title, "content": content}
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(webhook_url, json=payload)
            if resp.status_code >= 400:
                return PushResult(
                    success=False,
                    error_message=f"Webhook HTTP {resp.status_code}: {resp.text[:200]}",
                )
            logger.info("[Push/Webhook] Sent: %s", title[:30])
            return PushResult(success=True, provider_message_id=f"webhook-{resp.status_code}")

    except Exception as e:
        return PushResult(success=False, error_message=f"Webhook exception: {e}")


# ---- Message formatting helpers ----

def format_daily_digest(
    user_name: str,
    summary_text: str,
    recommendation_text: str,
    alerts_count: int,
    activities_count: int,
) -> tuple[str, str]:
    """Format a daily digest push message.

    Returns (title, markdown_content).
    """
    title = f"酒店监控日报"
    content = (
        f"**{user_name}** 你好，以下是今日监控摘要：\n\n"
        f"### 市场分析\n{summary_text}\n\n"
        f"### 定价建议\n{recommendation_text}\n\n"
        f"---\n"
        f"📊 今日告警 {alerts_count} 条 | 📍 周边活动 {activities_count} 个\n"
    )
    return title, content


def format_alert_message(
    alert_type: str,
    message: str,
) -> tuple[str, str]:
    """Format an alert push message.

    Returns (title, markdown_content).
    """
    type_emoji = {
        "price_drop": "💰",
        "new_activity": "📢",
    }
    emoji = type_emoji.get(alert_type, "⚠️")
    title = f"{emoji} {alert_type_display(alert_type)}提醒"
    content = f"**{alert_type_display(alert_type)}**\n\n{message}"
    return title, content


def alert_type_display(alert_type: str) -> str:
    return {"price_drop": "竞品调价", "new_activity": "周边新活动"}.get(alert_type, alert_type)
