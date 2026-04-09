from datetime import datetime
from math import asin, cos, radians, sin, sqrt


# Rough bounding-box mapping: city name → (lat_min, lat_max, lng_min, lng_max)
# Used to infer city from hotel coordinates when no explicit city is configured.
CITY_BOUNDS: list[tuple[str, float, float, float, float]] = [
    ("北京", 39.40, 41.10, 115.40, 117.50),
    ("上海", 30.70, 31.90, 120.80, 122.20),
    ("广州", 22.50, 23.90, 112.90, 114.60),
    ("深圳", 22.40, 22.90, 113.70, 114.70),
    ("成都", 30.30, 31.00, 103.50, 104.50),
    ("杭州", 29.90, 30.60, 119.50, 120.70),
    ("武汉", 29.90, 31.00, 113.50, 115.20),
    ("南京", 31.60, 32.60, 118.20, 119.30),
    ("重庆", 28.90, 32.20, 105.20, 110.20),
    ("西安", 33.80, 34.70, 108.60, 109.40),
    ("天津", 38.50, 40.30, 116.60, 118.10),
    ("苏州", 31.10, 32.00, 120.30, 121.20),
    ("长沙", 27.80, 28.60, 112.80, 113.40),
    ("郑州", 34.30, 35.00, 113.30, 114.00),
    ("青岛", 35.80, 36.40, 119.80, 120.80),
    ("大连", 38.60, 39.30, 121.00, 122.10),
    ("厦门", 24.20, 24.80, 117.80, 118.40),
    ("济南", 36.30, 36.90, 116.60, 117.30),
    ("沈阳", 41.50, 42.10, 123.00, 123.70),
    ("昆明", 24.60, 25.30, 102.30, 103.20),
]


def infer_city(lat: float, lng: float) -> str | None:
    """Infer city name from coordinates using bounding-box lookup."""
    for city, lat_min, lat_max, lng_min, lng_max in CITY_BOUNDS:
        if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
            return city
    return None


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine formula: calculate great-circle distance in km."""
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def filter_by_radius(
    center_lat: float,
    center_lng: float,
    activities: list,
    radius_km: float,
    lat_attr: str = "latitude",
    lng_attr: str = "longitude",
    include_no_coords: bool = False,
) -> list:
    """Filter activities within radius_km of center point.

    By default, activities without coordinates are EXCLUDED since we
    cannot verify they are within the radius. Set include_no_coords=True
    to include them (useful for backward compatibility or when location
    filtering is not critical).

    Returns list of (activity, distance_km) tuples, sorted by distance.
    """
    results = []
    for act in activities:
        lat = getattr(act, lat_attr, None)
        lng = getattr(act, lng_attr, None)
        if lat is None or lng is None:
            if include_no_coords:
                results.append((act, None))
            continue
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (ValueError, TypeError):
            if include_no_coords:
                results.append((act, None))
            continue
        dist = distance_km(center_lat, center_lng, lat_f, lng_f)
        if dist <= radius_km:
            results.append((act, dist))
    # Sort: with distance first (ascending), then without distance
    results.sort(key=lambda x: (x[1] is None, x[1] or 0))
    return results
