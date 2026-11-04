"""Download and cache the USGS 2025 M4+ baseline in monthly GeoJSON files."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

LOGGER = logging.getLogger(__name__)
USGS_FDSN_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
YEAR = 2025
MAX_RECORDS_PER_REQUEST = 18_000
MAX_ATTEMPTS = 4
MANIFEST_NAME = "2025_manifest.json"
QUERY_CONTRACT = {
    "format": "geojson",
    "minmagnitude": "4.0",
    "eventtype": "earthquake",
    "orderby": "time-asc",
}
Sleep = Callable[[float], Awaitable[None]]


class HistoricalDownloadError(RuntimeError):
    """Raised when a source response or cached baseline cannot be trusted."""


def build_month_intervals() -> tuple[tuple[datetime, datetime], ...]:
    """Return twelve adjacent half-open UTC intervals covering calendar 2025."""
    starts = [datetime(YEAR, month, 1, tzinfo=timezone.utc) for month in range(1, 13)]
    end_of_year = datetime(YEAR + 1, 1, 1, tzinfo=timezone.utc)
    boundaries = [*starts, end_of_year]
    return tuple(zip(boundaries, boundaries[1:]))


def month_key(start: datetime) -> str:
    return start.strftime("%Y-%m")


def _wire_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _feature_event_time(feature: Any) -> int:
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise HistoricalDownloadError("USGS response contains a malformed Feature")
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise HistoricalDownloadError("USGS Feature has no properties object")
    event_time = properties.get("time")
    if isinstance(event_time, bool) or not isinstance(event_time, int):
        raise HistoricalDownloadError("USGS Feature has an invalid UTC event timestamp")
    return event_time


def _filtered_interval_features(
    features: list[Any],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    selected: dict[str, dict[str, Any]] = {}
    for feature in features:
        event_time = _feature_event_time(feature)
        if not start_ms <= event_time < end_ms:
            # FDSNWS endpoints can include their exact end boundary. Keep
            # requests half-open so a boundary event belongs to one month.
            continue
        properties = feature["properties"]
        if properties.get("type") != "earthquake":
            continue
        magnitude = properties.get("mag")
        if (
            isinstance(magnitude, bool)
            or not isinstance(magnitude, (int, float))
            or magnitude < 4.0
        ):
            continue
        event_id = feature.get("id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise HistoricalDownloadError("USGS Feature has no event ID")
        selected.setdefault(event_id, feature)
    return sorted(
        selected.values(),
        key=lambda feature: (_feature_event_time(feature), feature["id"]),
    )


def _response_collection(response: httpx.Response) -> tuple[list[Any], int | None]:
    try:
        body = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HistoricalDownloadError("USGS returned invalid JSON") from exc
    if (
        not isinstance(body, dict)
        or body.get("type") != "FeatureCollection"
        or not isinstance(body.get("features"), list)
    ):
        raise HistoricalDownloadError("USGS response is not a GeoJSON FeatureCollection")
    count: int | None = None
    metadata = body.get("metadata")
    if isinstance(metadata, dict) and "count" in metadata:
        value = metadata["count"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise HistoricalDownloadError("USGS response has invalid metadata.count")
        count = value
    return body["features"], count


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


async def _request_collection(
    client: httpx.AsyncClient,
    start: datetime,
    end: datetime,
    *,
    base_url: str,
    sleep: Sleep,
) -> tuple[list[Any], int | None]:
    params = {
        **QUERY_CONTRACT,
        "starttime": _wire_time(start),
        "endtime": _wire_time(end),
    }
    for attempt in range(MAX_ATTEMPTS):
        response: httpx.Response | None = None
        retry_delay: float | None = None
        try:
            response = await client.get(base_url, params=params)
        except httpx.RequestError as exc:
            if attempt + 1 == MAX_ATTEMPTS:
                raise HistoricalDownloadError(
                    f"USGS request failed after {MAX_ATTEMPTS} attempts ({type(exc).__name__})"
                ) from exc
        if response is not None:
            if response.status_code == 429 or response.status_code >= 500:
                retry_delay = _retry_after_seconds(response.headers.get("Retry-After"))
                if attempt + 1 == MAX_ATTEMPTS:
                    raise HistoricalDownloadError(
                        f"USGS returned retryable HTTP {response.status_code}"
                    )
            elif response.is_error:
                raise HistoricalDownloadError(
                    f"USGS returned HTTP {response.status_code}"
                )
            else:
                return _response_collection(response)
        if retry_delay is None:
            retry_delay = 2.0 * (2**attempt)
        await sleep(min(retry_delay, 60.0))
    raise HistoricalDownloadError("USGS request failed")


async def fetch_interval(
    client: httpx.AsyncClient,
    start: datetime,
    end: datetime,
    *,
    base_url: str = USGS_FDSN_URL,
    sleep: Sleep = asyncio.sleep,
) -> list[dict[str, Any]]:
    """Fetch an interval and recursively split dense results before USGS limits."""
    features, reported_count = await _request_collection(
        client, start, end, base_url=base_url, sleep=sleep
    )
    effective_count = max(len(features), reported_count or 0)
    if effective_count > MAX_RECORDS_PER_REQUEST:
        midpoint = start + (end - start) / 2
        if end - start <= timedelta(days=1) or midpoint <= start or midpoint >= end:
            raise HistoricalDownloadError(
                "USGS interval still exceeds the safe response threshold after subdivision"
            )
        LOGGER.info(
            "Subdividing dense USGS interval %s to %s (%s records)",
            _wire_time(start),
            _wire_time(end),
            effective_count,
        )
        first = await fetch_interval(
            client, start, midpoint, base_url=base_url, sleep=sleep
        )
        second = await fetch_interval(
            client, midpoint, end, base_url=base_url, sleep=sleep
        )
        merged: dict[str, dict[str, Any]] = {}
        for feature in (*first, *second):
            merged.setdefault(feature["id"], feature)
        return sorted(
            merged.values(),
            key=lambda feature: (_feature_event_time(feature), feature["id"]),
        )
    return _filtered_interval_features(features, start, end)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(value, temporary, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_month(path: Path) -> dict[str, Any] | None:
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(body, dict)
        or body.get("type") != "FeatureCollection"
        or not isinstance(body.get("features"), list)
    ):
        return None
    return body


def load_complete_cache(output_dir: Path) -> dict[str, Any]:
    """Load and checksum-verify all twelve files from a completed cache."""
    manifest_path = output_dir / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalDownloadError("2025 baseline manifest is missing or invalid") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("year") != YEAR
        or manifest.get("query") != QUERY_CONTRACT
        or manifest.get("complete") is not True
        or not isinstance(manifest.get("months"), dict)
    ):
        raise HistoricalDownloadError("2025 baseline manifest is incomplete or incompatible")
    expected_months = {month_key(start) for start, _ in build_month_intervals()}
    if set(manifest["months"]) != expected_months:
        raise HistoricalDownloadError("2025 baseline manifest does not contain all 12 months")

    months: dict[str, dict[str, Any]] = {}
    for start, _ in build_month_intervals():
        key = month_key(start)
        file_name = f"2025_m{start.month:02d}.geojson"
        entry = manifest["months"][key]
        path = output_dir / file_name
        if not isinstance(entry, dict) or entry.get("file") != file_name:
            raise HistoricalDownloadError(f"cached file checksum mismatch: {file_name}")
        try:
            checksum = _file_sha256(path)
        except OSError as exc:
            raise HistoricalDownloadError(f"cached file is missing: {file_name}") from exc
        if entry.get("sha256") != checksum:
            raise HistoricalDownloadError(f"cached file checksum mismatch: {file_name}")
        collection = _read_month(path)
        if collection is None or entry.get("feature_count") != len(collection["features"]):
            raise HistoricalDownloadError(f"cached GeoJSON is invalid: {file_name}")
        months[key] = collection
    return {"manifest": manifest, "months": months}


def _load_resume_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "year": YEAR,
            "query": QUERY_CONTRACT,
            "complete": False,
            "months": {},
        }
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "schema_version": 1,
            "year": YEAR,
            "query": QUERY_CONTRACT,
            "complete": False,
            "months": {},
        }
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("year") != YEAR
        or manifest.get("query") != QUERY_CONTRACT
        or not isinstance(manifest.get("months"), dict)
    ):
        return {
            "schema_version": 1,
            "year": YEAR,
            "query": QUERY_CONTRACT,
            "complete": False,
            "months": {},
        }
    return {**manifest, "complete": False}


def _valid_cached_month(output_dir: Path, start: datetime, entry: Any) -> dict[str, Any] | None:
    file_name = f"2025_m{start.month:02d}.geojson"
    path = output_dir / file_name
    if not isinstance(entry, dict) or entry.get("file") != file_name:
        return None
    try:
        if entry.get("sha256") != _file_sha256(path):
            return None
    except OSError:
        return None
    collection = _read_month(path)
    if collection is None or entry.get("feature_count") != len(collection["features"]):
        return None
    return collection


async def download_historical_2025(
    output_dir: Path,
    *,
    client: httpx.AsyncClient | None = None,
    base_url: str = USGS_FDSN_URL,
    sleep: Sleep = asyncio.sleep,
) -> dict[str, Any]:
    """Download 12 monthly partitions, resuming verified files when possible."""
    output_dir = Path(output_dir)
    manifest_path = output_dir / MANIFEST_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        verified_cache = load_complete_cache(output_dir)
    except HistoricalDownloadError:
        verified_cache = None
    if verified_cache is not None:
        return {
            "cache_hit": True,
            "month_count": 12,
            "unique_event_count": verified_cache["manifest"].get("unique_event_count", 0),
        }

    manifest = _load_resume_manifest(manifest_path)
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
    try:
        for start, end in build_month_intervals():
            key = month_key(start)
            cached = _valid_cached_month(output_dir, start, manifest["months"].get(key))
            if cached is not None:
                LOGGER.info("Reusing verified historical cache for %s", key)
                continue
            features = await fetch_interval(
                client, start, end, base_url=base_url, sleep=sleep
            )
            file_name = f"2025_m{start.month:02d}.geojson"
            file_path = output_dir / file_name
            _atomic_json(
                file_path,
                {
                    "type": "FeatureCollection",
                    "metadata": {
                        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "source": USGS_FDSN_URL,
                        "year": YEAR,
                        "month": start.month,
                        "query": QUERY_CONTRACT,
                    },
                    "features": features,
                },
            )
            manifest["months"][key] = {
                "file": file_name,
                "sha256": _file_sha256(file_path),
                "feature_count": len(features),
            }
            manifest["complete"] = False
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            _atomic_json(manifest_path, manifest)
            LOGGER.info("Cached %s with %s unique events", file_name, len(features))

        # Verify every file and count unique IDs across month boundaries before
        # declaring the cache complete.
        unique_ids: set[str] = set()
        monthly_entries: dict[str, dict[str, Any]] = {}
        for start, _ in build_month_intervals():
            key = month_key(start)
            file_name = f"2025_m{start.month:02d}.geojson"
            file_path = output_dir / file_name
            collection = _read_month(file_path)
            if collection is None:
                raise HistoricalDownloadError(f"cached GeoJSON is invalid: {file_name}")
            entry = {
                "file": file_name,
                "sha256": _file_sha256(file_path),
                "feature_count": len(collection["features"]),
            }
            monthly_entries[key] = entry
            for feature in collection["features"]:
                event_id = feature.get("id") if isinstance(feature, dict) else None
                if not isinstance(event_id, str) or not event_id.strip():
                    raise HistoricalDownloadError(f"cached GeoJSON has an invalid ID: {file_name}")
                unique_ids.add(event_id)
        manifest = {
            "schema_version": 1,
            "year": YEAR,
            "query": QUERY_CONTRACT,
            "complete": True,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "months": monthly_entries,
            "unique_event_count": len(unique_ids),
        }
        _atomic_json(manifest_path, manifest)
        load_complete_cache(output_dir)
        return {
            "cache_hit": False,
            "month_count": 12,
            "unique_event_count": len(unique_ids),
        }
    finally:
        if owns_client:
            await client.aclose()


def _default_output_dir() -> Path:
    cache_root = Path(os.getenv("USGS_CACHE_DIR", "data"))
    return cache_root / "historical"


async def _run_cli(output_dir: Path) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        return await download_historical_2025(output_dir, client=client)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_default_output_dir(),
        help="cache directory (default: $USGS_CACHE_DIR/historical)",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    result = asyncio.run(_run_cli(args.output_dir))
    LOGGER.info(
        "2025 USGS baseline cache ready: months=%s unique_events=%s cache_hit=%s",
        result["month_count"],
        result["unique_event_count"],
        result["cache_hit"],
    )


if __name__ == "__main__":
    main()
