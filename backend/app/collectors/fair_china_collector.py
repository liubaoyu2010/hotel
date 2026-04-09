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

# Major exhibition centers in China with city and coordinates
EXHIBITION_CENTERS: dict[str, list[dict]] = {
    "北京": [
        {"name": "中国国际展览中心（新馆）", "lat": 40.0594, "lng": 116.5497},
        {"name": "中国国际展览中心（老馆）", "lat": 39.9642, "lng": 116.4514},
        {"name": "国家会议中心", "lat": 39.9933, "lng": 116.3917},
        {"name": "北京展览馆", "lat": 39.9425, "lng": 116.3388},
    ],
    "上海": [
        {"name": "国家会展中心（上海）", "lat": 31.1867, "lng": 121.3178},
        {"name": "上海新国际博览中心", "lat": 31.2150, "lng": 121.5667},
        {"name": "上海世博展览馆", "lat": 31.1872, "lng": 121.4833},
    ],
    "广州": [
        {"name": "广交会展馆", "lat": 23.1000, "lng": 113.3583},
        {"name": "保利世贸博览馆", "lat": 23.1017, "lng": 113.3550},
    ],
    "深圳": [
        {"name": "深圳会展中心", "lat": 22.5317, "lng": 114.0567},
        {"name": "深圳国际会展中心", "lat": 22.6900, "lng": 113.8100},
    ],
    "成都": [
        {"name": "中国西部国际博览城", "lat": 30.5267, "lng": 104.0567},
        {"name": "成都世纪城新国际会展中心", "lat": 30.5700, "lng": 104.0650},
    ],
}

# Noise keywords to filter out
NOISE_KEYWORDS = frozenset({
    "关于我们", "公司简介", "联系方式", "帮助中心", "用户协议", "隐私政策",
    "登录", "注册", "广告", "友情链接", "网站地图", "备案号",
})


class FairChinaCollector(BaseCollector):
    """Collect exhibition/fair information from Chinese exhibition websites.

    Sources:
    1. czces.com (中展网) - exhibition schedule listings
    2. expo-ces.com (会展网) - exhibition calendar
    """

    name = "fair_china"
    display_name = "展会信息"
    priority = 15
    enabled_by_default = True

    def collect(self, city: str, radius_km: float = 3.0) -> list[RawActivity]:
        """Collect exhibition activities for the given city."""
        now = datetime.utcnow()
        activities: list[RawActivity] = []
        seen_ids: set[str] = set()

        # Try czces.com
        try:
            raw_list = self._fetch_czces(city, now)
            for raw in raw_list:
                if raw.source_id not in seen_ids:
                    seen_ids.add(raw.source_id)
                    activities.append(raw)
        except Exception as e:
            logger.warning("FairChinaCollector czces fetch failed: %s", e)

        # Try expo-ces.com as backup
        if len(activities) < 3:
            try:
                raw_list = self._fetch_expo_ces(city, now)
                for raw in raw_list:
                    if raw.source_id not in seen_ids:
                        seen_ids.add(raw.source_id)
                        activities.append(raw)
            except Exception as e:
                logger.warning("FairChinaCollector expo-ces fetch failed: %s", e)

        # Enrich coordinates from known exhibition centers
        activities = self._enrich_coordinates(activities, city)

        return activities

    def _fetch_czces(self, city: str, now: datetime) -> list[RawActivity]:
        """Fetch exhibitions from czces.com (中展网)."""
        results: list[RawActivity] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
            encoded_city = quote_plus(city)
            url = f"https://www.czces.com/search/?keyword={encoded_city}"
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    return results
            except httpx.HTTPError as e:
                logger.debug("czces request error: %s", e)
                return results

            soup = BeautifulSoup(resp.text, "lxml")

            # Look for exhibition entries
            for item in soup.select("tr, .exhi-item, .list-item, [class*=item], .exhibition-item"):
                text = item.get_text(separator=" ", strip=True)
                if not text or len(text) < 15:
                    continue
                if any(noise in text for noise in NOISE_KEYWORDS):
                    continue
                if not any(kw in text for kw in ["展", "会", "博览"]):
                    continue

                activity = self._parse_exhibition_text(text, city, now, "czces")
                if activity:
                    results.append(activity)

            # Also try finding links with exhibition info
            for link in soup.select("a[href]"):
                link_text = link.get_text(strip=True)
                href = link.get("href", "")
                if not link_text or len(link_text) < 6:
                    continue
                if any(noise in link_text for noise in NOISE_KEYWORDS):
                    continue
                if not any(kw in link_text for kw in ["展", "博览会"]):
                    continue

                full_url = href
                if href and not href.startswith("http"):
                    full_url = f"https://www.czces.com{href}"

                # Get context from parent
                parent = link.parent
                context = parent.get_text(separator=" ", strip=True) if parent else link_text
                activity = self._parse_exhibition_text(context, city, now, "czces")
                if activity and activity.source_url is None:
                    activity.source_url = full_url
                if activity:
                    results.append(activity)

        return results

    def _fetch_expo_ces(self, city: str, now: datetime) -> list[RawActivity]:
        """Fetch exhibitions from expo-ces.com as backup source."""
        results: list[RawActivity] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
            # Try calendar/schedule page
            for url in [
                "https://www.expo-ces.com/zhanhui/",
                f"https://www.expo-ces.com/zhanhui/{quote_plus(city)}/",
            ]:
                try:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        continue
                except httpx.HTTPError:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                for link in soup.select("a[href]"):
                    text = link.get_text(strip=True)
                    if not text or len(text) < 8:
                        continue
                    if any(noise in text for noise in NOISE_KEYWORDS):
                        continue
                    if not any(kw in text for kw in ["展", "博览会", "会展"]):
                        continue
                    if city not in text and city not in (link.get("href", "")):
                        continue

                    href = link.get("href", "")
                    full_url = href
                    if href and not href.startswith("http"):
                        full_url = f"https://www.expo-ces.com{href}"

                    parent = link.parent
                    context = parent.get_text(separator=" ", strip=True) if parent else text
                    activity = self._parse_exhibition_text(context, city, now, "expo-ces")
                    if activity and activity.source_url is None:
                        activity.source_url = full_url
                    if activity:
                        results.append(activity)

        return results

    def _parse_exhibition_text(
        self, text: str, city: str, now: datetime, sub_source: str
    ) -> RawActivity | None:
        """Parse an exhibition activity from raw text."""
        # Extract title (first meaningful line, typically contains "展")
        title = ""
        for segment in text.split():
            segment = segment.strip()
            if len(segment) >= 6 and any(kw in segment for kw in ["展", "博览会"]):
                title = segment[:200]
                break
        if not title:
            # Use first long segment
            for segment in text.split():
                segment = segment.strip()
                if len(segment) >= 8:
                    title = segment[:200]
                    break
        if not title or len(title) < 4:
            return None

        # Extract date
        start_time, end_time = self._extract_exhibition_date(text, now)
        if start_time is None:
            start_time = now + timedelta(days=14)
            end_time = start_time + timedelta(days=3)
        if end_time < now - timedelta(days=1):
            return None
        if start_time > now + timedelta(days=90):
            return None

        # Extract venue/address
        address = self._extract_venue(text, city)

        # Estimate attendees based on exhibition keywords
        attendees = self._estimate_exhibition_attendees(text)

        # Generate source_id
        source_id = hashlib.md5(f"{sub_source}:{title[:50]}:{start_time.strftime('%Y-%m')}".encode()).hexdigest()[:16]

        return RawActivity(
            title=title,
            description=text[:500] if len(text) > len(title) + 10 else None,
            start_time=start_time,
            end_time=end_time,
            address=address,
            source=self.name,
            source_id=source_id,
            source_url=None,
            activity_type="exhibition",
            latitude=None,
            longitude=None,
            estimated_attendees=attendees,
        )

    @staticmethod
    def _extract_exhibition_date(text: str, now: datetime) -> tuple[datetime | None, datetime | None]:
        """Extract exhibition date range from text."""
        # Pattern: 2026年04月15日-04月18日
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*[-~至到]\s*(\d{1,2})月(\d{1,2})日", text)
        if m:
            try:
                start = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                end = datetime(int(m.group(1)), int(m.group(4)), int(m.group(5)))
                return start, end
            except ValueError:
                pass

        # Pattern: 2026-04-15 至 2026-04-18
        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})\s*(?:[-~至到到])\s*(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if m:
            try:
                start = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                end = datetime(int(m.group(4)), int(m.group(5)), int(m.group(6)))
                return start, end
            except ValueError:
                pass

        # Pattern: 04月15日-18日
        m = re.search(r"(\d{1,2})月(\d{1,2})日\s*[-~至到]\s*(\d{1,2})日", text)
        if m:
            try:
                start = datetime(now.year, int(m.group(1)), int(m.group(2)))
                end = datetime(now.year, int(m.group(1)), int(m.group(3)))
                if start < now - timedelta(days=30):
                    start = start.replace(year=now.year + 1)
                    end = end.replace(year=now.year + 1)
                return start, end
            except ValueError:
                pass

        # Pattern: single date 2026年04月15日
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
        if m:
            try:
                start = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                end = start + timedelta(days=3)  # exhibitions typically last 3 days
                return start, end
            except ValueError:
                pass

        return None, None

    @staticmethod
    def _extract_venue(text: str, city: str) -> str | None:
        """Extract exhibition venue from text."""
        # Pattern: 地点/展馆/场馆：XXX
        m = re.search(r"(?:地点|展馆|场馆|地址|venue)[：:]\s*([^\n,，\|]{5,100})", text)
        if m:
            return m.group(1).strip()

        # Pattern: known exhibition center names
        m = re.search(r"([\u4e00-\u9fff]{2,10}(?:国际展览|会展中心|博览中心|展览中心|展览馆))", text)
        if m:
            return m.group(1).strip()

        return None

    @staticmethod
    def _estimate_exhibition_attendees(text: str) -> int | None:
        """Estimate exhibition attendee count from text."""
        # Look for explicit numbers
        m = re.search(r"(\d+)\s*(?:万)?(?:人|家|参展|观众|展商)", text)
        if m:
            num = int(m.group(1))
            if "万" in text[max(0, m.start() - 3):m.start()]:
                num *= 10000
            return num

        # Heuristic based on exhibition scale keywords
        if any(kw in text for kw in ["国际", "大型", "全国"]):
            return 50000
        if any(kw in text for kw in ["中国", "亚洲", "全球"]):
            return 100000
        return None

    def _enrich_coordinates(self, activities: list[RawActivity], city: str) -> list[RawActivity]:
        """Fill in coordinates based on exhibition center matching."""
        centers = EXHIBITION_CENTERS.get(city, [])
        if not centers:
            return activities

        for activity in activities:
            if activity.latitude is not None:
                continue
            addr = activity.address or activity.title or ""
            for center in centers:
                # Partial match on center name
                if center["name"][:4] in addr or any(kw in addr for kw in center["name"].split()):
                    activity.latitude = center["lat"]
                    activity.longitude = center["lng"]
                    break

        return activities
