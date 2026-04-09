from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, RawActivity

logger = logging.getLogger(__name__)

# Activity type mapping from keywords
CATEGORY_MAP: dict[str, str] = {
    "互联网": "conference",
    "科技": "conference",
    "创业": "conference",
    "教育": "conference",
    "金融": "conference",
    "设计": "conference",
    "营销": "conference",
    "电商": "conference",
    "展览": "exhibition",
    "展会": "exhibition",
    "音乐": "concert",
    "演出": "concert",
    "体育": "sports",
    "运动": "sports",
    "文化": "festival",
    "节庆": "festival",
    "亲子": "festival",
    "沙龙": "conference",
    "讲座": "conference",
    "培训": "conference",
    "分享": "conference",
    "峰会": "conference",
    "论坛": "conference",
}

# Navigation/footer noise to filter
NOISE_KEYWORDS = frozenset({
    "关于我们", "公司简介", "联系方式", "帮助中心", "用户协议", "隐私政策",
    "广告服务", "首次发活动", "热门站点", "精选推荐", "更多服务",
    "主办方中心", "登录", "注册", "找回密码", "意见反馈", "APP下载",
    "关注我们", "友情链接", "合作伙伴", "服务条款", "网站地图",
})

# City name -> huodongxing city code mapping
CITY_CODES: dict[str, str] = {
    "北京": "010", "上海": "021", "广州": "020", "深圳": "0755",
    "杭州": "0571", "成都": "028", "武汉": "027", "南京": "025",
    "西安": "029", "重庆": "023", "长沙": "0731", "天津": "022",
    "苏州": "0512", "厦门": "0592", "青岛": "0532", "郑州": "0371",
    "大连": "0411", "宁波": "0574", "昆明": "0871", "合肥": "0551",
    "福州": "0591", "济南": "0531", "珠海": "0756", "东莞": "0769",
}


class HuodongxingCollector(BaseCollector):
    """Collect activities from huodongxing.com (活动行).

    Strategy:
    1. Use search page with keyword-based queries for more relevant results
    2. Parse event links (/event/NNNN) from any page area
    3. Visit individual event pages for richer data
    4. Fall back to listing page if search yields nothing
    """

    name = "huodongxing"
    display_name = "活动行"
    priority = 20
    enabled_by_default = True

    BASE_URL = "https://www.huodongxing.com"

    # Search keywords that yield high-demand activities for hotels
    SEARCH_KEYWORDS = [
        "展会", "展览", "峰会", "论坛", "演唱会", "赛事",
    ]

    def collect(self, city: str, radius_km: float = 3.0) -> list[RawActivity]:
        """Search huodongxing.com for upcoming activities in the given city."""
        activities: list[RawActivity] = []
        now = datetime.utcnow()
        seen_ids: set[str] = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
            # Strategy 1: Keyword search for high-demand events
            for keyword in self.SEARCH_KEYWORDS:
                try:
                    raw_list = self._search_keyword(client, keyword, city, now)
                    for raw in raw_list:
                        if raw.source_id not in seen_ids:
                            seen_ids.add(raw.source_id)
                            activities.append(raw)
                except Exception as e:
                    logger.debug("HuodongxingCollector keyword '%s' search error: %s", keyword, e)

            # Strategy 2: Browse event listing page
            if len(activities) < 5:
                try:
                    raw_list = self._browse_listing(client, city, now)
                    for raw in raw_list:
                        if raw.source_id not in seen_ids:
                            seen_ids.add(raw.source_id)
                            activities.append(raw)
                except Exception as e:
                    logger.debug("HuodongxingCollector listing browse error: %s", e)

            # Strategy 3: Enrich by visiting event detail pages (top 10 only)
            if activities:
                activities = self._enrich_from_details(client, activities, now)

        return activities

    def _search_keyword(
        self, client: httpx.Client, keyword: str, city: str, now: datetime
    ) -> list[RawActivity]:
        """Search by keyword on huodongxing."""
        encoded_kw = quote_plus(keyword)
        encoded_city = quote_plus(city)
        url = f"{self.BASE_URL}/search?city={encoded_city}&kw={encoded_kw}"
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        return self._parse_event_links(resp.text, city, now)

    def _browse_listing(
        self, client: httpx.Client, city: str, now: datetime
    ) -> list[RawActivity]:
        """Browse the event listing page for a city."""
        city_code = CITY_CODES.get(city, "")
        url = f"{self.BASE_URL}/eventlist"
        if city_code:
            url += f"?city={city_code}"
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        return self._parse_event_links(resp.text, city, now)

    def _parse_event_links(
        self, html: str, city: str, now: datetime
    ) -> list[RawActivity]:
        """Extract activities from any page by finding /event/NNNN links."""
        soup = BeautifulSoup(html, "lxml")
        results: list[RawActivity] = []

        # Find all event links
        event_links = soup.find_all("a", href=lambda h: h and "/event/" in str(h))
        for link in event_links:
            text = link.get_text(strip=True)
            href = link.get("href", "")

            # Filter noise
            if not text or len(text) < 6:
                continue
            if any(noise in text for noise in NOISE_KEYWORDS):
                continue

            # Extract event ID
            id_match = re.search(r"/event/(\d+)", href)
            if not id_match:
                continue
            source_id = id_match.group(1)

            # Get full URL
            full_url = href
            if href and not href.startswith("http"):
                full_url = f"{self.BASE_URL}{href}"

            # Get context from parent element for richer info
            parent = link.parent
            context_text = ""
            if parent:
                context_text = parent.get_text(separator=" ", strip=True)

            # Extract datetime from context
            start_time, end_time = self._extract_datetime(text + " " + context_text, now)
            if start_time is None:
                start_time = now + timedelta(days=7)
                end_time = start_time + timedelta(hours=3)
            if end_time < now - timedelta(days=1):
                continue
            if start_time > now + timedelta(days=90):
                continue

            # Classify
            full_text = text + " " + context_text
            activity_type = self._classify_type(full_text)
            address = self._extract_address(full_text, city)
            attendees = self._estimate_attendees(full_text)

            results.append(
                RawActivity(
                    title=text[:200],
                    description=context_text[:500] if len(context_text) > len(text) + 5 else None,
                    start_time=start_time,
                    end_time=end_time,
                    address=address,
                    source=self.name,
                    source_id=source_id,
                    source_url=full_url or None,
                    activity_type=activity_type,
                    latitude=None,
                    longitude=None,
                    estimated_attendees=attendees,
                )
            )

        return results

    def _enrich_from_details(
        self, client: httpx.Client, activities: list[RawActivity], now: datetime
    ) -> list[RawActivity]:
        """Visit event detail pages to enrich data (top activities only)."""
        # Only enrich activities that are missing time or have default time
        needs_enrichment = [
            a for a in activities
            if a.source_url and (a.start_time > now + timedelta(days=6))
        ][:10]

        for activity in needs_enrichment:
            try:
                resp = client.get(activity.source_url, timeout=10)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "lxml")

                # Try to extract richer data from detail page
                detail_text = soup.get_text(separator=" ", strip=True)

                # Better datetime extraction
                start, end = self._extract_datetime(detail_text, now)
                if start and start <= now + timedelta(days=90):
                    activity.start_time = start
                    activity.end_time = end or (start + timedelta(hours=3))

                # Better address extraction
                addr = self._extract_address(detail_text, "")
                if addr:
                    activity.address = addr

                # Better attendee count
                attendees = self._estimate_attendees(detail_text)
                if attendees:
                    activity.estimated_attendees = attendees

                # Better description
                desc_el = soup.select_one(".event-desc, .detail-content, .event-detail, [class*=detail]")
                if desc_el:
                    desc = desc_el.get_text(strip=True)[:500]
                    if len(desc) > 20:
                        activity.description = desc

            except Exception as e:
                logger.debug("Huodongxing detail fetch error for %s: %s", activity.source_url, e)

        return activities

    @staticmethod
    def _extract_datetime(text: str, now: datetime) -> tuple[datetime | None, datetime | None]:
        """Try to extract start and end datetime from text."""
        # Pattern: 2026年04月15日 14:00 - 17:00
        m = re.search(
            r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})\s*[-~至到]\s*(\d{1,2}):(\d{2})",
            text,
        )
        if m:
            try:
                start = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                 int(m.group(4)), int(m.group(5)))
                end = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                               int(m.group(6)), int(m.group(7)))
                return start, end
            except ValueError:
                pass

        # Pattern: 2026年04月15日 14:00
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})", text)
        if m:
            try:
                start = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                 int(m.group(4)), int(m.group(5)))
                end = start + timedelta(hours=3)
                return start, end
            except ValueError:
                pass

        # Pattern: 04月15日 14:00-17:00
        m = re.search(r"(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})\s*[-~至到]\s*(\d{1,2}):(\d{2})", text)
        if m:
            try:
                start = datetime(now.year, int(m.group(1)), int(m.group(2)),
                                 int(m.group(3)), int(m.group(4)))
                end = datetime(now.year, int(m.group(1)), int(m.group(2)),
                               int(m.group(5)), int(m.group(6)))
                if start < now - timedelta(days=30):
                    start = start.replace(year=now.year + 1)
                    end = end.replace(year=now.year + 1)
                return start, end
            except ValueError:
                pass

        # Pattern: 2026-04-15 14:00
        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{2})", text)
        if m:
            try:
                start = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                 int(m.group(4)), int(m.group(5)))
                end = start + timedelta(hours=3)
                return start, end
            except ValueError:
                pass

        # Pattern: 2026-04-15
        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if m:
            try:
                start = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                end = start + timedelta(hours=8)
                return start, end
            except ValueError:
                pass

        # Pattern: MM月DD日 (without year)
        m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
        if m:
            try:
                start = datetime(now.year, int(m.group(1)), int(m.group(2)))
                if start < now - timedelta(days=30):
                    start = start.replace(year=now.year + 1)
                end = start + timedelta(hours=3)
                return start, end
            except ValueError:
                pass

        return None, None

    @staticmethod
    def _extract_address(text: str, city: str) -> str | None:
        """Try to extract address from text."""
        # Pattern: 地点：XXX
        m = re.search(r"(?:地点|地址|场馆|场地|地点|location)[：:]\s*([^\n,，\|]{5,100})", text)
        if m:
            return m.group(1).strip()
        # Pattern: city name + road/district
        m = re.search(r"([\u4e00-\u9fff]{2,5}(?:市|区|路|街|大道|大厦|中心|广场|酒店|会展)[\u4e00-\u9fff]{0,20})", text)
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def _classify_type(text: str) -> str:
        """Classify activity type from text content."""
        for keyword, act_type in CATEGORY_MAP.items():
            if keyword in text:
                return act_type
        return "other"

    @staticmethod
    def _estimate_attendees(text: str) -> int | None:
        """Try to estimate attendee count from text."""
        m = re.search(r"(\d+)\s*人(?:参加|报名|已报|限额|已参加)", text)
        if m:
            return int(m.group(1))
        m = re.search(r"限额?(\d+)", text)
        if m:
            return int(m.group(1))
        m = re.search(r"仅限(\d+)", text)
        if m:
            return int(m.group(1))
        return None
