import datetime
import os
from typing import Any

import functions_framework
import requests


NHK_API_URL = "https://program-api.nhk.jp/v3/papiPgDateRadio"
RADIO_SERVICE = "r3"
AREA_ID = "130"
TARGET_SERIES_NAME = "ウィークエンドサンシャイン"
WEEKEND_SUNSHINE_NHK_IDENTIFIER_GROUPS_COLLECTION = (
    "weekendSunshineNhkIdentifierGroups"
)


def _jst_today() -> str:
    jst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(jst).date().isoformat()


def _validate_date(date_value: str) -> str:
    try:
        return datetime.date.fromisoformat(date_value).isoformat()
    except ValueError as error:
        raise ValueError("date must use YYYY-MM-DD format") from error


def _publication_identifier_groups(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    publication_items: list[Any] = []
    for service_payload in payload.values():
        if isinstance(service_payload, dict):
            publication = service_payload.get("publication")
            if isinstance(publication, list):
                publication_items.extend(publication)

    identifier_groups: list[dict[str, Any]] = []
    for publication_item in publication_items:
        if not isinstance(publication_item, dict):
            continue
        identifier_group = publication_item.get("identifierGroup")
        if isinstance(identifier_group, dict):
            identifier_groups.append(identifier_group)
    return identifier_groups


def _fetch_identifier_groups(date_value: str, api_key: str) -> list[dict[str, Any]]:
    response = requests.get(
        NHK_API_URL,
        params={
            "service": RADIO_SERVICE,
            "area": AREA_ID,
            "date": date_value,
            "key": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    return _publication_identifier_groups(response.json())


def _save_weekend_sunshine_identifier_groups(
    identifier_groups: list[dict[str, Any]],
) -> list[str]:
    from google.cloud import firestore

    database = firestore.Client()
    saved_radio_episode_ids: list[str] = []
    batch = database.batch()

    for identifier_group in identifier_groups:
        radio_episode_id = identifier_group.get("radioEpisodeId")
        if not isinstance(radio_episode_id, str) or not radio_episode_id:
            continue

        document = database.collection(
            WEEKEND_SUNSHINE_NHK_IDENTIFIER_GROUPS_COLLECTION
        ).document(radio_episode_id)
        batch.set(
            document,
            {
                **identifier_group,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        saved_radio_episode_ids.append(radio_episode_id)

    if saved_radio_episode_ids:
        batch.commit()
    return saved_radio_episode_ids


@functions_framework.http
def fetch_and_save_weekend_sunshine_nhk_identifier_groups(
    request: Any,
) -> tuple[dict[str, Any], int]:
    """Fetch a day's Weekend Sunshine broadcast metadata into Firestore."""
    api_key = os.environ.get("NHK_API_KEY")
    if not api_key:
        return {"error": "NHK_API_KEY is not configured"}, 500

    requested_date = request.args.get("date") or _jst_today()
    try:
        date_value = _validate_date(requested_date)
    except ValueError as error:
        return {"error": str(error)}, 400

    try:
        identifier_groups = _fetch_identifier_groups(date_value, api_key)
        weekend_sunshine_groups = [
            identifier_group
            for identifier_group in identifier_groups
            if identifier_group.get("radioSeriesName") == TARGET_SERIES_NAME
        ]
        saved_radio_episode_ids = _save_weekend_sunshine_identifier_groups(
            weekend_sunshine_groups
        )
    except requests.RequestException:
        return {"error": "NHK API request failed"}, 502
    except (ValueError, KeyError):
        return {"error": "NHK API returned an invalid response"}, 502

    return {
        "date": date_value,
        "saved_radio_episode_ids": saved_radio_episode_ids,
    }, 200
