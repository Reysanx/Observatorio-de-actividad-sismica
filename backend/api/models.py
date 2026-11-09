"""Stable, immutable response DTOs for the public local API contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer


class APIModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    @field_serializer("*", when_used="json")
    def serialize_utc_datetimes(self, value: object) -> object:
        if isinstance(value, datetime) and value.tzinfo is not None:
            return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return value


class HealthResponse(APIModel):
    status: Literal["ok"] = "ok"
    database_status: Literal["ok"] = "ok"
    api_time: datetime
    last_successful_poll_at: datetime | None
    last_event_ingested_at: datetime | None
    latest_event_updated_at: datetime | None
    ingestion_delay_seconds: float | None


class EarthquakeDTO(APIModel):
    event_id: str
    mag: float | None
    mag_type: str | None
    depth_km: float
    time_utc: datetime
    updated_utc: datetime
    ingested_at: datetime
    adm0_a3: str
    country_name: str
    continent: str | None
    subregion: str | None
    place: str | None
    geom_lon: float
    geom_lat: float
    source: str


class EarthquakePage(APIModel):
    items: list[EarthquakeDTO]
    total: int
    limit: int
    offset: int
    scope: Literal["live", "replay"]
    run_id: str | None


class GeoStatDTO(APIModel):
    adm0_a3: str
    country_name: str
    continent: str | None
    subregion: str | None
    event_count: int
    magnitude_count: int
    average_magnitude: float | None
    maximum_magnitude: float | None


class GeoStatsResponse(APIModel):
    items: list[GeoStatDTO]
    scope: Literal["live", "replay"]
    run_id: str | None


class HourlyStatDTO(APIModel):
    hour_utc: datetime
    event_count: int
    magnitude_count: int
    average_magnitude: float | None


class HourlyStatsResponse(APIModel):
    items: list[HourlyStatDTO]
    scope: Literal["live", "replay"]
    run_id: str | None


class HistogramBinDTO(APIModel):
    bin_start: float
    bin_end: float
    count: int


class DistributionResponse(APIModel):
    magnitude_bins: list[HistogramBinDTO]
    depth_bins: list[HistogramBinDTO]
    magnitude_null_count: int
    depth_null_count: int
    depth_p90_km: float | None
    depth_population_count: int
    depth_percentile_method: Literal["hyndman_fan_type_7"] = "hyndman_fan_type_7"
    depth_period_start_utc: datetime
    depth_period_end_utc: datetime
    scope: Literal["live", "replay"]
    run_id: str | None


class HistoricalComparisonResponse(APIModel):
    calculated_at: datetime
    window_start_utc: datetime
    window_end_utc: datetime
    magnitude_threshold: float
    recent_event_count: int
    historical_2025_event_count: int
    historical_days: int
    historical_daily_average: float
    historical_daily_population_stddev: float
    recent_standard_deviations_from_mean: float | None
    deviation_band: Literal[
        "within_1_sd", "between_1_and_2_sd", "beyond_2_sd", "unavailable"
    ]
    ratio_to_historical_daily_average: float | None
    adm0_a3: str | None
    continent: str | None
    subregion: str | None
    scope: Literal["live"] = "live"


class ReplayStateResponse(APIModel):
    run_id: str | None
    active: bool
    status: Literal["idle", "starting", "running", "completed", "failed"]
    started_at: datetime | None
    finished_at: datetime | None
    events_received: int
    events_processed: int
    events_quarantined: int
