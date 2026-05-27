"""
ZebraTur SHS API Client.

Wraps the entire SHS / Proxymo booking API surface used by Zebra Tur.
Handles JWT auto-refresh, retries on 401, and unified error handling.
"""
from __future__ import annotations

import json
import logging
import time
import threading
from typing import Any, Iterable
from urllib.parse import urljoin

import requests

import config

log = logging.getLogger("shs")


class SHSError(Exception):
    """Raised for any non-recoverable SHS API issue."""


class SHSClient:
    """Thread-safe SHS API client with automatic JWT refresh."""

    def __init__(
        self,
        base_url: str | None = None,
        report_base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        report_token: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or config.SHS_BASE_URL).rstrip("/")
        self.report_base_url = (report_base_url or config.SHS_REPORT_BASE_URL).rstrip("/")
        self.username = username or config.SHS_USERNAME
        self.password = password or config.SHS_PASSWORD
        self.report_token = report_token or config.SHS_REPORT_TOKEN
        self.timeout = timeout

        self._jwt: str | None = None
        self._jwt_expires_at: float = 0
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ZebraTur-SHS/1.0",
        })

    # ----------------------------- core HTTP -----------------------------

    def _url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _auth_header(self) -> dict[str, str]:
        token = self._get_jwt()
        if not token:
            return {}
        return {"X-JWTtoken": token}

    def _get_jwt(self, force: bool = False) -> str | None:
        with self._lock:
            now = time.time()
            if not force and self._jwt and now < self._jwt_expires_at:
                return self._jwt
            try:
                r = self._session.post(
                    self._url("/auth/get_jwt_token"),
                    params={"username": self.username, "password": self.password},
                    timeout=self.timeout,
                )
                data = self._safe_json(r)
                token = data.get("jwt_token") if isinstance(data, dict) else None
                if token:
                    self._jwt = token
                    self._jwt_expires_at = now + config.JWT_TTL_SECONDS
                    log.info("SHS JWT obtained (len=%s)", len(token))
                    return token
                err = (data or {}).get("error", "unknown")
                log.warning("SHS auth failed: %s", err)
                return None
            except Exception as exc:
                log.exception("SHS auth exception: %s", exc)
                return None

    @staticmethod
    def _safe_json(r: requests.Response) -> Any:
        try:
            return r.json()
        except Exception:
            return {"_raw": r.text[:2000], "_status": r.status_code}

    def _request(self, method: str, path: str, *, json_body: Any = None, params: dict | None = None,
                 retry_auth: bool = True) -> Any:
        url = self._url(path)
        headers = self._auth_header()
        try:
            r = self._session.request(
                method, url,
                json=json_body, params=params,
                headers=headers, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SHSError(f"network error: {exc}") from exc

        if r.status_code == 401 and retry_auth:
            # Force token refresh and retry once
            self._get_jwt(force=True)
            return self._request(method, path, json_body=json_body, params=params, retry_auth=False)

        data = self._safe_json(r)
        if isinstance(data, dict) and data.get("error"):
            msg = str(data.get("error"))
            if "jwt" in msg.lower() and retry_auth:
                self._get_jwt(force=True)
                return self._request(method, path, json_body=json_body, params=params, retry_auth=False)
        return data

    # ----------------------------- public introspection -----------------------------

    @property
    def has_valid_token(self) -> bool:
        return bool(self._get_jwt())

    def ping(self) -> dict:
        """Sanity check — returns auth status + reachable endpoints."""
        result = {"base_url": self.base_url, "auth_ok": False, "reachable": False}
        # Public endpoint test
        try:
            r = self._session.get(self._url("/transport/get_terminals"), timeout=10)
            result["reachable"] = r.status_code < 500
        except Exception:
            pass
        # Auth test
        tok = self._get_jwt(force=True)
        result["auth_ok"] = bool(tok)
        result["token_preview"] = (tok[:20] + "...") if tok else None
        return result

    # ----------------------------- geographic -----------------------------

    def get_countries(self) -> list[dict]:
        return self._request("POST", "/country/country_list") or []

    def get_cities(self, country_id: int | None = None) -> list[dict]:
        params = {"country_id": country_id} if country_id else None
        return self._request("POST", "/city/city_list", params=params) or []

    def get_terminals(self) -> list[dict]:
        return self._request("GET", "/transport/get_terminals") or []

    # ----------------------------- hotel directories -----------------------------

    def get_hotel_facilities(self) -> list[dict]:
        return self._request("POST", "/hotel/facilities") or []

    def get_hotel_categories(self) -> list[dict]:
        return self._request("POST", "/hotel/category_list") or []

    def get_meal_types(self) -> list[dict]:
        return self._request("POST", "/hotel/meal_list") or []

    def get_hotel_list(self, *, country_id: int | None = None, city_id: int | None = None,
                      category_id: int | None = None, meal_id: int | None = None) -> list[dict]:
        body = {k: v for k, v in {
            "country_id": country_id, "city_id": city_id,
            "category_id": category_id, "meal_id": meal_id,
        }.items() if v is not None}
        return self._request("POST", "/hotel/hotel_list", json_body=body) or []

    # ----------------------------- search: hotels -----------------------------

    def search_hotels(self, *,
                      adults: int,
                      children: list[int] | None = None,
                      from_date: str,
                      to_date: str,
                      from_nights: int,
                      to_nights: int,
                      hotel_ids: list[int] | None = None,
                      meal_ids: list[int] | None = None,
                      city_ids: list[int] | None = None,
                      category_ids: list[int] | None = None,
                      facility_ids: list[int] | None = None,
                      show_stops: bool = True,
                      with_description: bool = True) -> dict:
        body = {
            "adults": adults,
            "children": children or [],
            "from_nights": from_nights,
            "to_nights": to_nights,
            "from_date": from_date,
            "to_date": to_date,
            "show_stops": show_stops,
            "with_description": with_description,
        }
        for k, v in (("hotel_ids", hotel_ids), ("meal_ids", meal_ids),
                     ("city_ids", city_ids), ("category_ids", category_ids),
                     ("facility_ids", facility_ids)):
            if v:
                body[k] = v
        return self._request("POST", "/hotel/search", json_body=body) or {}

    # ----------------------------- search: transport -----------------------------

    def search_transport(self, *,
                         departure: str,
                         destinations: list[str],
                         from_date: str,
                         to_date: str,
                         adults: int,
                         children: list[int] | None = None,
                         period_type: str = "departure_range",
                         days_from: int = 7,
                         days_to: int = 7,
                         days_interval_type: str = "tour_days",
                         outbound: bool = True,
                         inbound: bool = True) -> list[dict]:
        body = {
            "departure": departure,
            "destinations": destinations,
            "from_date": from_date,
            "to_date": to_date,
            "period_type": period_type,
            "days_from": days_from,
            "days_to": days_to,
            "days_interval_type": days_interval_type,
            "adults": adults,
            "children": children or [],
            "outbound": outbound,
            "inbound": inbound,
        }
        return self._request("POST", "/transport/search", json_body=body) or []

    def check_transport_flights(self, *, session: str | int, price_id: int,
                                departure_places: list[int] | None = None,
                                retur_places: list[int] | None = None) -> dict:
        body = {"session": session, "price_id": price_id}
        if departure_places is not None:
            body["DeparturePlaces"] = departure_places
        if retur_places is not None:
            body["ReturPlaces"] = retur_places
        return self._request("POST", "/transport/check_flights", json_body=body) or {}

    def get_transport_available_dates(self, country_id: int) -> dict:
        return self._request("POST", "/v2/transport/available_dates",
                             json_body={"country_id": country_id}) or {}

    # ----------------------------- search: packages -----------------------------

    def get_package_list(self, country_id: int | None = None) -> list[dict]:
        params = {"country_id": country_id} if country_id else None
        return self._request("POST", "/packages/package_list", params=params) or []

    def search_packages(self, *,
                        departure_terminal_id: int,
                        package_id: int,
                        country_id: int,
                        from_date: str,
                        to_date: str,
                        from_nights: int,
                        to_nights: int,
                        adults: int,
                        children: list[int] | None = None,
                        meal_ids: list[int] | None = None,
                        star_ids: list[int] | None = None,
                        facility_ids: list[int] | None = None,
                        city_ids: list[int] | None = None,
                        hotel_ids: list[int] | None = None,
                        grouped: bool = True) -> dict:
        body = {
            "departure_terminal_id": departure_terminal_id,
            "package_id": package_id,
            "country_id": country_id,
            "from_date": from_date,
            "to_date": to_date,
            "from_nights": from_nights,
            "to_nights": to_nights,
            "adults": adults,
            "children": children or [],
            "grouped": grouped,
        }
        for k, v in (("meal_ids", meal_ids), ("star_ids", star_ids),
                     ("facility_ids", facility_ids), ("city_ids", city_ids),
                     ("hotel_ids", hotel_ids)):
            if v:
                body[k] = v
        return self._request("POST", "/packages/search", json_body=body) or {}

    def get_pricing_page(self, session: str | int, page: int) -> dict:
        return self._request("GET", "/packages/pricing_page",
                             params={"session": session, "page": page}) or {}

    # ----------------------------- search: excursions -----------------------------

    def get_excursion_countries(self, lang: str = "en") -> list[dict]:
        return self._request("GET", "/excursions/countries", params={"lang": lang}) or []

    def get_excursion_departures(self, lang: str = "en") -> list[dict]:
        return self._request("GET", "/excursions/departures", params={"lang": lang}) or []

    def get_excursion_programs(self, lang: str = "en") -> list[dict]:
        return self._request("GET", "/excursions/programs", params={"lang": lang}) or []

    def list_excursions(self, *,
                        country_ids: list[int] | None = None,
                        program_ids: list[int] | None = None,
                        departure_ids: list[int] | None = None,
                        lang: str = "en") -> list[dict]:
        params: dict[str, Any] = {"lang": lang}
        if country_ids: params["country_ids"] = ",".join(map(str, country_ids))
        if program_ids: params["program_ids"] = ",".join(map(str, program_ids))
        if departure_ids: params["departure_ids"] = ",".join(map(str, departure_ids))
        return self._request("GET", "/excursions/list", params=params) or []

    def get_excursion_dates(self, excursion_ids: list[int]) -> dict:
        return self._request("GET", "/excursions/dates",
                             params={"excursion_ids": ",".join(map(str, excursion_ids))}) or {}

    def search_excursions(self, *,
                          departure_id: int | None = None,
                          excursion_ids: list[int] | None = None,
                          date_from: str,
                          date_to: str,
                          adults: int,
                          children_ages: list[int] | None = None,
                          trip_type: str = "excursion",
                          lang: str = "en") -> dict:
        params: dict[str, Any] = {
            "date_from": date_from,
            "date_to": date_to,
            "adults": adults,
            "type": trip_type,
            "lang": lang,
        }
        if departure_id: params["departure_id"] = departure_id
        if excursion_ids: params["excursion_ids"] = ",".join(map(str, excursion_ids))
        if children_ages: params["children_ages"] = ",".join(map(str, children_ages))
        return self._request("GET", "/excursions/search", params=params) or {}

    def check_excursion_price(self, *, price_id: int, session: str | None = None) -> dict:
        params: dict[str, Any] = {"price_id": price_id}
        if session: params["session"] = session
        return self._request("GET", "/excursions/check_price", params=params) or {}

    # ----------------------------- transfers -----------------------------

    def search_transfers(self, *,
                         departure_id: int,
                         arrival_id: int,
                         date: str,
                         adults: int,
                         children: list[int] | None = None,
                         transfer_type: str | None = None) -> list[dict]:
        body: dict[str, Any] = {
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "date": date,
            "adults": adults,
            "children": children or [],
        }
        if transfer_type:
            body["transfer_type"] = transfer_type
        return self._request("POST", "/transfer/search", json_body=body) or []

    # ----------------------------- booking -----------------------------

    def save_package_booking(self, *,
                             session: str | int,
                             price_id: int,
                             customers: list[dict],
                             departure_places: list[int] | None = None,
                             retur_places: list[int] | None = None) -> dict:
        body: dict[str, Any] = {
            "Session": str(session),
            "PriceId": int(price_id),
            "Customers": customers,
        }
        if departure_places is not None or retur_places is not None:
            body["Transport"] = {
                "DeparturePlaces": departure_places or [],
                "ReturPlaces": retur_places or [],
            }
        return self._request("POST", "/booking/save_booking", json_body=body) or {}

    def create_remote_order(self, *,
                            price_id: int,
                            session: str | int,
                            customers: list[dict],
                            departure_places: list[int] | None = None,
                            retur_places: list[int] | None = None) -> dict:
        body = {
            "Transport": {
                "PriceId": int(price_id),
                "Session": str(session),
                "DeparturePlaces": departure_places or [],
                "ReturPlaces": retur_places or [],
            },
            "Customers": customers,
        }
        return self._request("POST", "/remote_order/create", json_body=body) or {}

    def get_order_status(self, order_ids: Iterable[int], *, show_message: bool = False) -> list[dict]:
        body = {"Ids": list(order_ids), "ShowMessage": show_message}
        return self._request("POST", "/remote_order/get_status", json_body=body) or []

    def create_order_message(self, *, order_id: int, message: str) -> dict:
        body = {"OrderId": int(order_id), "Message": message}
        return self._request("POST", "/remote_order/create_message", json_body=body) or {}

    # ----------------------------- order updates / reports -----------------------------

    def update_order(self, *, order_id: int, status: str, locked: bool | None = None) -> dict:
        body: dict[str, Any] = {
            "Token": self.report_token,
            "OrderId": int(order_id),
            "Status": status,
        }
        if locked is not None:
            body["Locked"] = bool(locked)
        return self._request("POST", "/book/bundle_request/remote_update_order",
                             json_body=body) or {}

    def fetch_report_xml(self, *, date_from: str, date_to: str, status: str = "all",
                         search_type: str = "") -> str:
        """Returns raw XML text from the SHS report endpoint.

        Format per docs: /book/report/xml/TOKEN/BEGIN_DATE/END_DATE/STATUS[/UPDATED]
        Dates separated by forward slash; uses report_base_url (different host from API).
        """
        path = f"/book/report/xml/{self.report_token}/{date_from}/{date_to}/{status}"
        if search_type:
            path += f"/{search_type}"
        url = self.report_base_url + path
        r = self._session.get(url, timeout=self.timeout * 2)
        return r.text


# Module-level singleton
client = SHSClient()
