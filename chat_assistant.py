"""
Claude-powered chat assistant for Zebra Tur managers.
Translates natural-language queries into SHS searches and formats results
as ready-to-copy offer messages.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

import config
from shs_client import client, SHSError

log = logging.getLogger("chat")


# ============================ Mapping tables ============================

STAR_MAP = {"3": 7, "4": 5, "5": 6}
MEAL_MAP = {
    "breakfast": 7, "half_board": 8, "full_board": 13,
    "all_inclusive": 6, "ultra_all_inclusive": 20,
}
MEAL_LABEL = {
    7: "Mic dejun", 8: "Demi-pensiune", 13: "Full Board",
    6: "All Inclusive", 20: "Ultra All Inclusive",
}
FACILITY_MAP = {
    "first_line": 39, "pool": 21, "aquapark": 33,
    "beach_loungers": 8, "adult_only": 41, "wifi": 24, "parking": 27,
}
PACKAGE_HOTEL_ONLY = 87
PACKAGE_WITH_BUS = 73
TERMINAL_CHISINAU = 114


# ============================ Tool: search_offers ============================

SEARCH_TOOL = {
    "name": "search_offers",
    "description": (
        "Search Bulgaria vacation offers in SHS booking system. "
        "Returns a list of available packages with hotel, room, dates, price, and share URL. "
        "Use this whenever a manager describes what they're looking for. "
        "Always use it instead of guessing — only this tool has real prices and availability."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_date": {"type": "string", "description": "Earliest departure date in YYYY-MM-DD"},
            "to_date": {"type": "string", "description": "Latest departure date in YYYY-MM-DD"},
            "nights": {"type": "integer", "description": "Nights, default 7"},
            "adults": {"type": "integer", "description": "Number of adults, default 2"},
            "children_ages": {
                "type": "array", "items": {"type": "integer"},
                "description": "Ages of children, e.g. [4, 8]. Empty if no children."
            },
            "star_categories": {
                "type": "array", "items": {"type": "string", "enum": ["3", "4", "5"]},
                "description": "Required hotel stars. ['5']=5* only, ['4','5']=4-5*. Default ['4','5']."
            },
            "meal_types": {
                "type": "array",
                "items": {"type": "string", "enum": ["breakfast", "half_board", "full_board", "all_inclusive", "ultra_all_inclusive"]},
                "description": "Allowed meal types. Default ['all_inclusive','ultra_all_inclusive']."
            },
            "facilities": {
                "type": "array",
                "items": {"type": "string", "enum": ["first_line", "pool", "aquapark", "beach_loungers", "adult_only", "wifi", "parking"]},
                "description": "Required hotel facilities. first_line=beachfront."
            },
            "resort_names": {
                "type": "array", "items": {"type": "string"},
                "description": "Preferred resorts e.g. ['Sunny Beach', 'Golden Sands', 'Nessebar', 'Albena']."
            },
            "hotel_names": {
                "type": "array", "items": {"type": "string"},
                "description": "Specific hotel names to search, e.g. ['ADMIRAL', 'PALMA']."
            },
            "trip_type": {
                "type": "string", "enum": ["hotel_only", "with_bus"],
                "description": "hotel_only=client own car (default); with_bus=charter Chișinău incl. transfer+insurance"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of offers to return, default 5, max 15"
            }
        },
        "required": ["from_date", "to_date"]
    }
}


def execute_search_offers(args: dict) -> dict:
    """Execute the search with mapped parameters and format results."""
    try:
        from_date = args.get("from_date") or (date.today() + timedelta(days=30)).isoformat()
        to_date = args.get("to_date") or (date.today() + timedelta(days=60)).isoformat()
        nights = int(args.get("nights") or 7)
        adults = int(args.get("adults") or 2)
        children = [int(x) for x in (args.get("children_ages") or []) if isinstance(x, (int, float))]

        star_ids = [STAR_MAP[s] for s in (args.get("star_categories") or ["4", "5"]) if s in STAR_MAP]
        meal_ids = [MEAL_MAP[m] for m in (args.get("meal_types") or ["all_inclusive", "ultra_all_inclusive"]) if m in MEAL_MAP]
        facility_ids = [FACILITY_MAP[f] for f in (args.get("facilities") or []) if f in FACILITY_MAP]

        trip_type = args.get("trip_type", "hotel_only")
        if trip_type == "with_bus":
            package_id = PACKAGE_WITH_BUS
            terminal_id = TERMINAL_CHISINAU
        else:
            package_id = PACKAGE_HOTEL_ONLY
            terminal_id = 0

        # Resolve city names → ids
        city_ids: list[int] = []
        resort_names = args.get("resort_names") or []
        if resort_names:
            try:
                cities = client.get_cities(country_id=1) or []
                for name in resort_names:
                    nlow = name.lower().strip()
                    for c in cities:
                        cname = (c.get("city_name") or "").lower()
                        if nlow in cname or cname in nlow:
                            cid = c.get("city_id")
                            if cid and cid not in city_ids:
                                city_ids.append(cid)
            except Exception as exc:
                log.warning("city resolve failed: %s", exc)

        # Resolve hotel names → ids
        hotel_ids: list[int] = []
        hotel_names = args.get("hotel_names") or []
        if hotel_names:
            try:
                hotels = client.get_hotel_list(country_id=1) or []
                for name in hotel_names:
                    nlow = name.lower().strip()
                    for h in hotels:
                        hname = (h.get("name") or "").lower()
                        if nlow in hname:
                            hid = h.get("id")
                            if hid and hid not in hotel_ids:
                                hotel_ids.append(hid)
            except Exception as exc:
                log.warning("hotel resolve failed: %s", exc)

        # SHS requires city_ids ALWAYS (even when hotel_ids is set), so auto-fill from package
        if not city_ids:
            try:
                pkg_list = client.get_package_list(1) or []
                pkg = next((x for x in pkg_list if int(x.get("id", -1)) == package_id), None)
                if pkg and pkg.get("city_ids"):
                    city_ids = pkg["city_ids"]
            except Exception:
                pass

        # Convert date to dd.mm.yyyy for SHS
        def fmt(d: str) -> str:
            if "." in d: return d
            y, m, dd = d.split("-")
            return f"{dd}.{m}.{y}"

        data = client.search_packages(
            departure_terminal_id=terminal_id,
            package_id=package_id,
            country_id=1,
            from_date=fmt(from_date), to_date=fmt(to_date),
            from_nights=nights, to_nights=nights,
            adults=adults, children=children,
            meal_ids=meal_ids or None,
            star_ids=star_ids or None,
            facility_ids=facility_ids or None,
            city_ids=city_ids or None,
            hotel_ids=hotel_ids or None,
            grouped=True,
        ) or {}

        if isinstance(data, dict) and data.get("status") == "error":
            return {
                "error": data.get("message", "search failed"),
                "offers": [], "total_found": 0,
                "_debug_filters": {"hotel_ids": hotel_ids, "city_ids_count": len(city_ids), "meal_ids": meal_ids, "star_ids": star_ids, "trip_type": trip_type},
                "_hint": "Search failed at SHS level — error is technical, not 'no results'. Try without filters or with different package_id.",
            }

        prices = data.get("prices", []) or []
        prices.sort(key=lambda x: x.get("brut_zebra") or x.get("gross_amount") or 9e9)
        max_results = min(int(args.get("max_results") or 5), 15)
        top = prices[:max_results]

        # Best-effort enrich with city + photo (single batched call)
        if top:
            try:
                hids = list({p.get("hotel_id") for p in top if p.get("hotel_id")})
                if hids:
                    sample = top[0]
                    hd = client.search_hotels(
                        adults=adults, children=children,
                        from_date=sample["check_in"], to_date=sample["check_in"],
                        from_nights=nights, to_nights=nights,
                        hotel_ids=hids,
                        with_description=False, show_stops=True,
                    ) or {}
                    meta = {h["hotel_id"]: h for h in (hd.get("hotels") or []) if h.get("hotel_id")}
                    for p in top:
                        m = meta.get(p.get("hotel_id"))
                        if m:
                            if not p.get("city"):
                                p["city"] = m.get("city")
                            if not p.get("star"):
                                p["star"] = m.get("star")
            except Exception as exc:
                log.warning("enrichment failed: %s", exc)

        offers = []
        for p in top:
            price = p.get("brut_zebra") or p.get("gross_amount") or 0
            offers.append({
                "hotel_name": p.get("hotel_name"),
                "star": p.get("star", ""),
                "city": p.get("city", "Bulgaria"),
                "check_in": p["check_in"],
                "check_out": p["check_out"],
                "nights": p.get("nights", nights),
                "meal": p.get("meal", ""),
                "room_type": p.get("room_type", ""),
                "placement": p.get("placement", ""),
                "price_eur": round(float(price)),
                "hotel_id": p.get("hotel_id"),
                "share_url": _build_share_url(p, adults, children, nights, trip_type),
            })

        return {
            "offers": offers,
            "total_found": len(prices),
            "shown": len(offers),
            "trip_type_used": trip_type,
            "package_id_used": package_id,
        }

    except SHSError as e:
        return {"error": f"SHS error: {e}", "offers": [], "total_found": 0}
    except Exception as e:
        log.exception("search_offers failed")
        return {"error": str(e), "offers": [], "total_found": 0}


def _build_share_url(p: dict, adults: int, children: list, nights: int, trip_type: str) -> str:
    hid = p.get("hotel_id")
    parts = [
        f"h={hid}",
        f"in={p.get('check_in','')}",
        f"out={p.get('check_out','')}",
        f"n={nights}",
        f"a={adults}",
        f"t={'bus' if trip_type == 'with_bus' else 'self'}",
    ]
    if children:
        parts.append(f"c={','.join(map(str, children))}")
    return "https://zebratur.md/bulgaria#zt:" + "&".join(parts)


# ============================ System prompt ============================

def system_prompt() -> str:
    today = date.today().isoformat()
    return f"""Ești asistent intern pentru managerii agenției Zebra Tur (operator turistic din Moldova specializat pe vacanțe în Bulgaria).

Data curentă: {today}

ROLUL TĂU: managerii îți scriu în română sau rusă ce caută clienții, iar tu cauți oferte concrete în sistemul SHS și le returnezi formatat pentru copy-paste imediat la client.

TIPURI DE PACHETE:
- hotel_only (default) — clientul vine cu mașina personală sau își aranjează singur transportul
- with_bus — pachet complet cu autocar charter Chișinău ⇄ Bulgaria + asigurare + transfer aeroport (mai scump dar transport inclus)

VALORI IMPLICITE când managerul nu specifică:
- adults: 2
- nights: 7
- meal_types: ["all_inclusive", "ultra_all_inclusive"]
- star_categories: ["4", "5"]
- trip_type: "hotel_only"
- max_results: 5
- Dacă nu spune luna: presupune lunile sezon (iunie–septembrie), preferabil cea care urmează

FORMAT RĂSPUNS (mereu în această formă, gata de copy-paste în WhatsApp/Telegram):

```
1. 🏨 NUME HOTEL X*
📍 STAȚIUNE
📅 DD.MM.YYYY → DD.MM.YYYY (N nopți)
🍽️ Tip masă
🛏️ Tip cameră
💶 PREȚ € pentru N adulți[ + M copii]
🔗 https://zebratur.md/bulgaria#zt:h=...


2. ...
```

REGULI:
- Folosește TOTDEAUNA tool-ul search_offers — nu inventa prețuri sau date.
- Conversiile de stele: 3=trei stele, 4=patru stele, 5=cinci stele.
- Dacă managerul cere "5*" sau "5 stele", trimite ["5"] (NU ["3","4","5"]).
- Datele se formatează ca DD.MM.YYYY în răspuns (nu ISO).
- Mereu include link-ul share_url exact cum vine din tool.
- Răspunsul tău trebuie să conțină DOAR formatul de oferte de mai sus + opțional 1-2 propoziții scurte deasupra (ex: "Iată 3 opțiuni:") și ZERO text suplimentar dedesubt.
- Răspunde în aceeași limbă în care îți scrie managerul (RO sau RU).
- Pentru staționi populare: SUNNY BEACH, GOLDEN SANDS, NESSEBAR, POMORIE, ELENITE, ST. VLAS, ALBENA, BALCHIK, OBZOR.
- Pentru hoteluri specifice (când managerul spune "căută hotel X"): folosește parametrul hotel_names.

GESTIONARE REZULTATE GOALE:
- Dacă rezultatul are `error` field setat → este o ERORE TEHNICĂ la căutare, NU înseamnă că hotelul nu există. Re-încearcă cu filtre mai relaxate (ex. fără star_categories, fără meal_types).
- Dacă `offers` e gol DAR `error` nu e setat → atunci da, nu sunt rezultate pentru filtrele actuale. Sugerează: dată alternativă, alt buget, alt tip pachet (bus vs self).
- Când utilizatorul cere "în orice buget" / "fără limită" → nu folosi star_categories sau meal_types restrictive. Lasă toate la default.
- Înainte de a spune că un hotel "nu există", încearcă cu TOATE pachetele: dacă search nu găsește la package 87 (hotel only), încearcă cu trip_type="with_bus" (package 73). Hoteluri diferite sunt disponibile prin pachete diferite.
- Pentru același hotel pot exista mai multe ID-uri (ex. ADMIRAL = 12122 în Golden Sands, ADMIRAL PLAZA = 13390 în Sunny Beach). search_offers le caută pe toate cu același nume substring.

EXTRACT BUGET DIN MESAJ:
- Dacă managerul zice "700-800 €" / "до 1000" / "max 500" → filtrează MENTAL după primire rezultate, nu trimite buget la tool. Tool-ul nu acceptă filter buget; sortează ascendent. Tu alegi din rezultate pe cele care încap în buget. Dacă nu există în buget, spune asta și propune cele mai apropiate.
"""


# ============================ Main entry ============================

def run_chat(messages: list[dict], max_iterations: int = 5) -> dict:
    """Run a Claude conversation with tool use. Returns the final response + usage."""
    if not config.ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not configured", "text": ""}

    import anthropic
    cli = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    total_input_tokens = 0
    total_output_tokens = 0
    tool_uses = []

    for _ in range(max_iterations):
        try:
            response = cli.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt(),
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[SEARCH_TOOL],
                messages=messages,
            )
        except Exception as exc:
            log.exception("anthropic error")
            return {"error": f"Claude API error: {exc}", "text": ""}

        usage = getattr(response, "usage", None)
        if usage:
            total_input_tokens += getattr(usage, "input_tokens", 0)
            total_output_tokens += getattr(usage, "output_tokens", 0)

        # If Claude wants to use a tool, execute and continue
        if response.stop_reason == "tool_use":
            tool_calls = [b for b in response.content if b.type == "tool_use"]
            tool_results = []
            for tc in tool_calls:
                if tc.name == "search_offers":
                    result = execute_search_offers(tc.input)
                    tool_uses.append({"input": tc.input, "result_summary": {
                        "offers": len(result.get("offers", [])),
                        "total_found": result.get("total_found"),
                    }})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                else:
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": tc.id,
                        "content": "unknown tool",
                    })

            messages = messages + [
                {"role": "assistant", "content": [b.model_dump() for b in response.content]},
                {"role": "user", "content": tool_results},
            ]
            continue

        # Otherwise extract the text response
        text_parts = [b.text for b in response.content if b.type == "text"]
        return {
            "text": "\n".join(text_parts).strip(),
            "tool_uses": tool_uses,
            "usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "estimated_cost_usd": (total_input_tokens * 3 / 1_000_000) + (total_output_tokens * 15 / 1_000_000),
            },
        }

    return {"error": "max iterations exceeded", "text": "", "tool_uses": tool_uses}
