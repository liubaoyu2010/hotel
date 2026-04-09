from datetime import datetime
from math import asin, cos, radians, sin, sqrt


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
