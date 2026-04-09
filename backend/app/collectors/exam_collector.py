from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, RawActivity

logger = logging.getLogger(__name__)

# Comprehensive exam catalog with multi-session support
# Each entry can have multiple sessions per year (e.g. 四六级 has June and December)
EXAM_CATALOG: list[dict] = [
    # ---- 全国性考试（对住宿需求拉动最大）----
    {
        "name": "全国硕士研究生招生考试",
        "short": "考研",
        "sessions": [{"month": 12, "day": 23}],
        "attendees": 4_500_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["学历", "研究生"],
    },
    {
        "name": "全国公务员考试",
        "short": "国考",
        "sessions": [{"month": 11, "day": 26}],
        "attendees": 2_500_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["公务员"],
    },
    {
        "name": "各省公务员联考",
        "short": "省考",
        "sessions": [{"month": 3, "day": 22}],
        "attendees": 5_000_000,
        "scope": "provincial",
        "duration_days": 1,
        "tags": ["公务员"],
    },
    {
        "name": "全国大学英语四级考试",
        "short": "英语四级",
        "sessions": [{"month": 6, "day": 15}, {"month": 12, "day": 14}],
        "attendees": 10_000_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["外语", "大学"],
    },
    {
        "name": "全国大学英语六级考试",
        "short": "英语六级",
        "sessions": [{"month": 6, "day": 15}, {"month": 12, "day": 14}],
        "attendees": 6_000_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["外语", "大学"],
    },
    {
        "name": "注册会计师全国统一考试",
        "short": "CPA",
        "sessions": [{"month": 8, "day": 25}],
        "attendees": 1_800_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["财会"],
    },
    {
        "name": "全国法律职业资格考试",
        "short": "法考",
        "sessions": [{"month": 9, "day": 16}],
        "attendees": 700_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["法律"],
    },
    {
        "name": "一级建造师执业资格考试",
        "short": "一建",
        "sessions": [{"month": 9, "day": 10}],
        "attendees": 1_200_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["工程"],
    },
    {
        "name": "全国计算机等级考试",
        "short": "NCRE",
        "sessions": [{"month": 3, "day": 25}, {"month": 9, "day": 23}],
        "attendees": 5_000_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["计算机"],
    },
    {
        "name": "全国护士执业资格考试",
        "short": "护考",
        "sessions": [{"month": 4, "day": 15}],
        "attendees": 800_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["医学"],
    },
    {
        "name": "二级建造师执业资格考试",
        "short": "二建",
        "sessions": [{"month": 6, "day": 1}],
        "attendees": 3_500_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["工程"],
    },
    {
        "name": "执业药师职业资格考试",
        "short": "执业药师",
        "sessions": [{"month": 10, "day": 21}],
        "attendees": 600_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["医学"],
    },
    # ---- 新增热门考试 ----
    {
        "name": "中小学教师资格考试",
        "short": "教资",
        "sessions": [{"month": 3, "day": 9}, {"month": 10, "day": 28}],
        "attendees": 10_000_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["教育", "教师"],
    },
    {
        "name": "PMP项目管理专业人士资格认证考试",
        "short": "PMP",
        "sessions": [{"month": 3, "day": 18}, {"month": 6, "day": 15}, {"month": 8, "day": 19}, {"month": 11, "day": 18}],
        "attendees": 500_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["管理"],
    },
    {
        "name": "中级会计职称考试",
        "short": "中级会计",
        "sessions": [{"month": 9, "day": 7}],
        "attendees": 2_000_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["财会"],
    },
    {
        "name": "全国税务师职业资格考试",
        "short": "税务师",
        "sessions": [{"month": 11, "day": 11}],
        "attendees": 900_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["财会"],
    },
    {
        "name": "中国精算师考试",
        "short": "精算师",
        "sessions": [{"month": 10, "day": 14}],
        "attendees": 50_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["金融"],
    },
    {
        "name": "全国翻译专业资格（水平）考试",
        "short": "CATTI",
        "sessions": [{"month": 6, "day": 17}],
        "attendees": 300_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["外语"],
    },
    {
        "name": "一级注册消防工程师考试",
        "short": "消防工程师",
        "sessions": [{"month": 11, "day": 5}],
        "attendees": 800_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["工程"],
    },
    {
        "name": "全国卫生专业技术资格考试",
        "short": "卫生资格",
        "sessions": [{"month": 4, "day": 13}],
        "attendees": 1_500_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["医学"],
    },
    {
        "name": "初级会计职称考试",
        "short": "初级会计",
        "sessions": [{"month": 5, "day": 13}],
        "attendees": 4_000_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["财会"],
    },
    {
        "name": "经济专业技术资格考试",
        "short": "经济师",
        "sessions": [{"month": 11, "day": 2}],
        "attendees": 1_000_000,
        "scope": "national",
        "duration_days": 1,
        "tags": ["经济"],
    },
    {
        "name": "注册安全工程师考试",
        "short": "注安",
        "sessions": [{"month": 10, "day": 26}],
        "attendees": 700_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["工程"],
    },
    {
        "name": "房地产估价师考试",
        "short": "房估",
        "sessions": [{"month": 10, "day": 19}],
        "attendees": 200_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["房产"],
    },
    {
        "name": "造价工程师考试",
        "short": "造价师",
        "sessions": [{"month": 10, "day": 26}],
        "attendees": 600_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["工程"],
    },
    {
        "name": "全国成人高校招生统一考试",
        "short": "成人高考",
        "sessions": [{"month": 10, "day": 21}],
        "attendees": 3_000_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["学历"],
    },
    {
        "name": "全国高等教育自学考试",
        "short": "自考",
        "sessions": [{"month": 4, "day": 13}, {"month": 10, "day": 26}],
        "attendees": 6_000_000,
        "scope": "national",
        "duration_days": 2,
        "tags": ["学历"],
    },
]

# Common navigation/footer noise words to filter out
NOISE_KEYWORDS = {"关于我们", "公司简介", "联系方式", "帮助中心", "用户协议", "隐私政策", "广告服务", "首次发活动", "热门站点", "精选推荐", "更多服务", "主办方中心"}


class ExamCollector(BaseCollector):
    """Collect upcoming exam schedules from public exam calendars."""

    name = "exam"
    display_name = "考试信息"
    priority = 10
    enabled_by_default = True

    def collect(self, city: str, radius_km: float = 3.0) -> list[RawActivity]:
        """Generate upcoming exams from catalog for current and next year."""
        now = datetime.utcnow()
        activities: list[RawActivity] = []

        for exam in EXAM_CATALOG:
            for session in exam["sessions"]:
                for year_offset in (0, 1):
                    year = now.year + year_offset
                    try:
                        start = datetime(year, session["month"], session["day"])
                    except ValueError:
                        continue
                    duration = exam.get("duration_days", 2)
                    end = start + timedelta(days=duration - 1)

                    # Only include future exams within 90 days
                    if end < now - timedelta(days=1):
                        continue
                    if start > now + timedelta(days=90):
                        continue

                    source_id = self._make_source_id(exam["short"], start.strftime("%Y-%m-%d"))
                    tag_str = "、".join(exam.get("tags", []))
                    activities.append(
                        RawActivity(
                            title=f"{year}年{exam['name']}({exam['short']})",
                            description=f"{exam['name']}（{tag_str}），预计报考人数{exam['attendees']:,}人，考试时长{duration}天",
                            start_time=start,
                            end_time=end,
                            address=f"{city}各考点",
                            source=self.name,
                            source_id=source_id,
                            source_url="https://neea.edu.cn/",
                            activity_type="exam",
                            latitude=None,
                            longitude=None,
                            estimated_attendees=exam["attendees"],
                        )
                    )

        # Try to fetch additional exam info from public sources
        try:
            fetched = self._fetch_online_exams(city, now)
            activities.extend(fetched)
        except Exception as e:
            logger.warning("ExamCollector online fetch failed: %s", e)

        return activities

    def _fetch_online_exams(self, city: str, now: datetime) -> list[RawActivity]:
        """Attempt to scrape exam schedules from public education sites."""
        results: list[RawActivity] = []
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                # Try NEEA exam calendar page
                resp = client.get(
                    "https://neea.edu.cn/",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    },
                )
                if resp.status_code != 200:
                    return results
                soup = BeautifulSoup(resp.text, "lxml")

                # Look for exam schedule links in specific content areas
                for link in soup.select(".content a[href], .news-list a[href], .exam-list a[href], #content a[href]"):
                    text = link.get_text(strip=True)
                    href = link.get("href", "")

                    # Filter noise
                    if not text or len(text) < 8:
                        continue
                    if any(noise in text for noise in NOISE_KEYWORDS):
                        continue
                    if not any(kw in text for kw in ["考试", "报名", "成绩", "准考证", "通知"]):
                        continue

                    # Try to extract date from text
                    date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
                    if not date_match:
                        continue
                    try:
                        start = datetime(
                            int(date_match.group(1)),
                            int(date_match.group(2)),
                            int(date_match.group(3)),
                        )
                    except ValueError:
                        continue

                    if start < now - timedelta(days=1) or start > now + timedelta(days=90):
                        continue

                    # Filter out noise that passed keyword check
                    if any(noise in text for noise in NOISE_KEYWORDS):
                        continue

                    source_id = self._make_source_id("neea", start.strftime("%Y-%m-%d"), text[:30])
                    full_url = href
                    if href and not href.startswith("http"):
                        full_url = f"https://neea.edu.cn/{href}"

                    results.append(
                        RawActivity(
                            title=text[:200],
                            description=f"来源：中国教育考试网",
                            start_time=start,
                            end_time=start + timedelta(days=1),
                            address=f"{city}",
                            source=self.name,
                            source_id=source_id,
                            source_url=full_url or None,
                            activity_type="exam",
                            estimated_attendees=None,
                        )
                    )
        except Exception as e:
            logger.debug("ExamCollector _fetch_online_exams error: %s", e)
        return results

    @staticmethod
    def _make_source_id(*parts) -> str:
        str_parts = [str(p) for p in parts]
        raw = ":".join(str_parts)
        return hashlib.md5(raw.encode()).hexdigest()[:16]
