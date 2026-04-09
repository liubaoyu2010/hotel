from __future__ import annotations

import logging
from functools import lru_cache

import httpx

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid repeated API calls for same address
_geocode_cache: dict[str, tuple[float, float] | None] = {}


def geocode_address(address: str, city: str = "", api_key: str = "") -> tuple[float, float] | None:
    """Geocode an address using Amap (高德地图) API.

    Returns (latitude, longitude) or None if geocoding fails.
    Requires AMAP_API_KEY to be configured; returns None gracefully if not set.
    """
    if not address:
        return None

    # Check cache
    cache_key = f"{city}:{address}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    if not api_key:
        logger.debug("Geocode skipped: no AMAP_API_KEY configured")
        _geocode_cache[cache_key] = None
        return None

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://restapi.amap.com/v3/geocode/geo",
                params={
                    "key": api_key,
                    "address": address,
                    "city": city,
                    "output": "JSON",
                },
            )
            if resp.status_code != 200:
                logger.debug("Geocode HTTP %d for '%s'", resp.status_code, address)
                _geocode_cache[cache_key] = None
                return None

            data = resp.json()
            if data.get("status") != "1" or not data.get("geocodes"):
                logger.debug("Geocode no result for '%s': %s", address, data.get("info", ""))
                _geocode_cache[cache_key] = None
                return None

            location = data["geocodes"][0].get("location", "")
            if not location or "," not in location:
                _geocode_cache[cache_key] = None
                return None

            lng_str, lat_str = location.split(",", 1)
            lat = float(lat_str)
            lng = float(lng_str)

            _geocode_cache[cache_key] = (lat, lng)
            logger.debug("Geocode '%s' -> (%.6f, %.6f)", address, lat, lng)
            return (lat, lng)

    except Exception as e:
        logger.debug("Geocode error for '%s': %s", address, e)
        _geocode_cache[cache_key] = None
        return None


def batch_geocode(
    activities: list, city: str = "", api_key: str = ""
) -> list:
    """Geocode multiple activities that are missing coordinates.

    Modifies activities in-place and returns them.
    Rate-limited: max 5 QPS for free Amap tier.
    """
    if not api_key:
        return activities

    import time

    count = 0
    for activity in activities:
        if activity.latitude is not None and activity.longitude is not None:
            continue
        if not activity.address:
            continue

        result = geocode_address(activity.address, city=city, api_key=api_key)
        if result:
            activity.latitude = result[0]
            activity.longitude = result[1]
            count += 1
            # Rate limit: 5 QPS for free tier
            if count % 5 == 0:
                time.sleep(1.1)

    if count:
        logger.info("batch_geocode: enriched %d activities with coordinates", count)
    return activities
