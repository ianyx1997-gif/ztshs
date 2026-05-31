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
        "IMPORTANT: if a child age >= 12, set `auto_adjust_teens` to true — most Bulgarian hotels "
        "charge children >= 12 as adults (CHD category ends at 11.99). Tool auto-retries with adjusted counts."
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
            "auto_adjust_teens": {
                "type": "boolean",
                "description": "If true and original search returns < 3 results, automatically retry treating children >= 12 as adults (most Bulgarian hotels price them as adults). Default true."
            },
            "star_categories": {
                "type": "array", "items": {"type": "string", "enum": ["3", "4", "5"]},
                "description": "Required hotel stars. ['5']=5* only, ['4','5']=4-5*. Default ['3','4','5'] (show all from 3 stars up). Only restrict if manager explicitly asks for specific stars."
            },
            "meal_types": {
                "type": "array",
                "items": {"type": "string", "enum": ["breakfast", "half_board", "full_board", "all_inclusive", "ultra_all_inclusive"]},
                "description": "Allowed meal types. Default ['all_inclusive','ultra_all_inclusive']."
            },
            "facilities": {
                "type": "array",
                "items": {"type": "string", "enum": ["pool", "aquapark", "adult_only", "wifi", "parking"]},
                "description": "Required hotel facilities. DO NOT use 'first_line' or 'beach_loungers' here — they're too restrictive. For first-line hotels, prefer beachfront resorts (Sunny Beach, Golden Sands, Albena) and verify via get_hotel_info if specific hotel."
            },
            "resort_names": {
                "type": "array", "items": {"type": "string"},
                "description": "Preferred resorts e.g. ['Sunny Beach', 'Golden Sands', 'Nessebar', 'Albena']. Top first-line resorts: Sunny Beach, Golden Sands, Albena, Elenite, Sveti Vlas."
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
            },
            "max_budget_eur": {
                "type": "integer",
                "description": "Optional max price filter in EUR. Tool returns only offers <= this price. Use when manager mentions a budget ceiling."
            },
            "min_budget_eur": {
                "type": "integer",
                "description": "Optional min price filter in EUR. Use when manager specifies a budget range (e.g. 1000-1500)."
            }
        },
        "required": ["from_date", "to_date"]
    }
}


HOTEL_INFO_TOOL = {
    "name": "get_hotel_info",
    "description": (
        "Get detailed hotel description, facilities list, and photos for a specific hotel. "
        "Use this when manager asks about a hotel's amenities, beach proximity (first line), "
        "or to verify a feature like 'has aquapark' / 'is adults only'. Description text often "
        "mentions 'first line', 'beachfront', distance to beach, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "hotel_name": {"type": "string", "description": "Hotel name to search (e.g. 'MERCURY', 'ADMIRAL')"},
            "hotel_id": {"type": "integer", "description": "SHS hotel ID if known (e.g. 12122 for ADMIRAL Golden Sands)"}
        }
    }
}


def execute_search_offers(args: dict) -> dict:
    """Execute the search with mapped parameters and format results. Auto-retries with teens-as-adults."""
    # Pre-process: auto-adjust teens (children >= 12) on retry
    children_orig = [int(x) for x in (args.get("children_ages") or []) if isinstance(x, (int, float))]
    teens = [c for c in children_orig if c >= 12]
    auto_adjust = args.get("auto_adjust_teens", True)

    result = _execute_search_internal(args, children_orig)
    if (result.get("offers") and len(result["offers"]) >= 3) or not auto_adjust or not teens:
        return result

    # Retry with teens promoted to adults
    log.info("Auto-adjusting: %d teens >= 12 promoted to adults", len(teens))
    children_adj = [c for c in children_orig if c < 12]
    adults_adj = int(args.get("adults", 2)) + len(teens)
    args2 = dict(args)
    args2["adults"] = adults_adj
    args2["children_ages"] = children_adj
    retry = _execute_search_internal(args2, children_orig)
    retry["_auto_adjusted"] = {
        "original_setup": f"{args.get('adults', 2)} adulți + {len(children_orig)} copii ({','.join(map(str, children_orig))} ani)",
        "adjusted_setup": f"{adults_adj} adulți + {len(children_adj)} copii ({','.join(map(str, children_adj)) if children_adj else 'fără'} ani)",
        "reason": f"Hotelurile bulgare tarifează copilul >= 12 ani ca adult (categoria CHD până la 11.99). Promovat: {len(teens)} copil(i) de {','.join(map(str, teens))} ani.",
        "original_results": len(result.get("offers", [])),
    }
    return retry


def _execute_search_internal(args: dict, original_children: list) -> dict:
    """Run one search iteration without retry logic."""
    try:
        from_date = args.get("from_date") or (date.today() + timedelta(days=30)).isoformat()
        to_date = args.get("to_date") or (date.today() + timedelta(days=60)).isoformat()
        nights = int(args.get("nights") or 7)
        adults = int(args.get("adults") or 2)
        children = [int(x) for x in (args.get("children_ages") or []) if isinstance(x, (int, float))]

        star_ids = [STAR_MAP[s] for s in (args.get("star_categories") or ["3", "4", "5"]) if s in STAR_MAP]
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
        # Filter by budget if specified — with flexible window: -7% on min, +10% on max
        # (managers' budgets are approximate; clients accept slightly cheaper or a bit more expensive)
        min_b = args.get("min_budget_eur")
        max_b = args.get("max_budget_eur")
        eff_min = round(min_b * 0.93) if min_b else None   # allow 7% under the stated minimum
        eff_max = round(max_b * 1.10) if max_b else None   # allow 10% over the stated maximum
        if eff_min or eff_max:
            def in_budget(p):
                price = p.get("brut_zebra") or p.get("gross_amount") or 0
                if eff_min and price < eff_min: return False
                if eff_max and price > eff_max: return False
                return True
            filtered = [p for p in prices if in_budget(p)]
        else:
            filtered = prices
        filtered.sort(key=lambda x: x.get("brut_zebra") or x.get("gross_amount") or 9e9)
        max_results = min(int(args.get("max_results") or 5), 15)
        top = filtered[:max_results]

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
                "share_url": _build_share_url(p, adults, original_children or children, nights, trip_type),
            })

        return {
            "offers": offers,
            "total_found_no_budget_filter": len(prices),
            "total_in_budget": len(filtered),
            "shown": len(offers),
            "trip_type_used": trip_type,
            "package_id_used": package_id,
            "budget_applied": {
                "requested_min": min_b, "requested_max": max_b,
                "effective_min": eff_min, "effective_max": eff_max,
                "note": "Fereastră flexibilă aplicată: -7% sub minim, +10% peste maxim",
            } if (min_b or max_b) else None,
        }

    except SHSError as e:
        return {"error": f"SHS error: {e}", "offers": [], "total_found": 0}
    except Exception as e:
        log.exception("search_offers failed")
        return {"error": str(e), "offers": [], "total_found": 0}


def execute_get_hotel_info(args: dict) -> dict:
    """Look up a specific hotel by name or id and return description + facilities."""
    try:
        hotel_id = args.get("hotel_id")
        hotel_name = (args.get("hotel_name") or "").strip()
        if not hotel_id and not hotel_name:
            return {"error": "provide hotel_name or hotel_id"}

        # Resolve hotel_id from name
        if not hotel_id and hotel_name:
            hotels = client.get_hotel_list(country_id=1) or []
            nlow = hotel_name.lower()
            matches = [h for h in hotels if nlow in (h.get("name") or "").lower()]
            if not matches:
                return {"error": f"no hotel matching '{hotel_name}'", "suggestions": []}
            if len(matches) > 1:
                # Multiple matches — return list for clarification
                return {
                    "multiple_matches": [
                        {"hotel_id": h["id"], "name": h["name"], "city": h.get("city_name"), "category": h.get("category")}
                        for h in matches[:6]
                    ],
                    "note": "Multiple hotels match the name. Pick one by hotel_id and call get_hotel_info again."
                }
            hotel_id = matches[0]["id"]

        # Fetch details via /hotel/search with description
        from datetime import date, timedelta
        future = (date.today() + timedelta(days=30)).isoformat()
        data = client.search_hotels(
            adults=2, children=[],
            from_date=future, to_date=future,
            from_nights=7, to_nights=7,
            hotel_ids=[int(hotel_id)],
            with_description=True, show_stops=True,
        ) or {}
        hotels = data.get("hotels") or []
        if not hotels:
            return {"error": f"hotel id {hotel_id} not found in inventory"}
        h = hotels[0]

        # Detect first-line mentions in description
        desc = (h.get("description") or "")
        desc_text = desc.replace("<", " <").lower()
        first_line_keywords = ["first line", "първа линия", "первая линия", "beachfront", "на берегу", "primul rând", "prima linie"]
        is_first_line = any(kw in desc_text for kw in first_line_keywords)

        # Map facility_ids to readable labels
        all_fac = client.get_hotel_facilities() or []
        fac_lookup = {f["id"]: f for f in all_fac if isinstance(f, dict)}
        fac_labels = []
        for fid in (h.get("facility_ids") or []):
            f = fac_lookup.get(fid)
            if f:
                tr = (f.get("translation") or {})
                fac_labels.append(tr.get("ro") or tr.get("ru") or f.get("name") or f"#{fid}")

        return {
            "hotel_id": h.get("hotel_id"),
            "hotel_name": h.get("hotel_name"),
            "star": h.get("star"),
            "city": h.get("city"),
            "country": h.get("country"),
            "is_first_line_per_description": is_first_line,
            "facilities": fac_labels,
            "description_excerpt": _strip_html(desc)[:1500],
            "has_full_description": bool(desc),
        }
    except Exception as e:
        log.exception("get_hotel_info failed")
        return {"error": str(e)}


def _strip_html(s: str) -> str:
    import re, html
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)  # decode &nbsp; &amp; &quot; etc.
    s = s.replace("\xa0", " ")  # non-breaking space → normal space
    s = re.sub(r"\s+", " ", s).strip()
    return s


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

ROLUL TĂU: managerii îți scriu în română sau rusă ce caută clienții, iar tu cauți oferte concrete în sistemul SHS și le returnezi formatat pentru copy-paste imediat la client prin WhatsApp/Telegram.

═══════════ INSTRUMENTELE TALE ═══════════

1. **search_offers** — caută oferte SHS cu filtre multiple. Returnează prețuri reale.
2. **get_hotel_info** — citește descrierea + facilitățile + locația unui hotel specific. Folosește pentru verificarea „prima linie", „aquapark", „adults only" etc.

═══════════ TIPURI DE PACHETE ═══════════

- **hotel_only** (default) — clientul vine cu mașina sau își aranjează singur transportul
- **with_bus** — pachet complet cu autocar charter Chișinău ⇄ Bulgaria + asigurare + transfer aeroport (cu ~300-500€ mai scump, dar transport inclus)

═══════════ ÎNAINTE DE A CĂUTA — CLARIFICĂRI ═══════════

**Pune întrebări de clarificare DACĂ lipsește info esențială și răspunsul ar fi prea generic.** Nu căuta cu defaulturi când e clar că lipsește info critică.

Întreabă DOAR atunci când:
- Lipsește **numărul de persoane** (adulți/copii + vârste) → întreabă: „Câți adulți + copii cu vârstele lor?"
- Lipsește **luna/perioada** dar mesajul are tone vagă („vacanță", „vară") → întreabă: „Pentru ce lună/dată?"
- Buget vag („ieftin", „mediu") fără sumă → întreabă: „Ce buget aveți în minte? Până la cât?"
- Mesaj de o singură propoziție generică („caut Bulgaria") → întreabă: „Pentru câți, când, ce stele, ce mese?"

**NU întreba dacă deja ai destul de info pentru o căutare bună.** Cu detalii minime (data + persoane + 1-2 preferințe), pornește direct la căutare.

Defaults când CHIAR lipsește info după clarificare:
- adults: 2, nights: 7, meal_types: ["all_inclusive", "ultra_all_inclusive"], star_categories: ["3", "4", "5"] (TOATE de la 3 stele în sus), trip_type: "hotel_only", max_results: 5

═══════════ COPII >= 12 ANI (FOARTE IMPORTANT) ═══════════

**Hotelurile bulgare tarifează copilul >= 12 ani ca ADULT.** Categoriile CHD se termină la 11.99 ani la 95% din hoteluri. Cu un copil de 12, 13, 14 ani primești de obicei 0-3 rezultate fiindcă puține hoteluri au CHD până la 13.99/15.99.

Cum gestionezi:
- **Setează `auto_adjust_teens: true`** (default deja) în search_offers. Tool-ul retry-uiește automat: dacă < 3 rezultate cu copilul mare, îl promovează la adult.
- Tool-ul returnează `_auto_adjusted` cu noul setup. **TREBUIE să menționezi managerului** că ai făcut promovarea. Format:

> *„Notă: copilul de 13 ani a fost tarifat ca al 3-lea adult (hotelurile bulgare consideră 12+ ca adult). Iată ofertele:"*

- În răspuns, **scrie persoanele așa cum sunt în realitate** (nu cum au fost ajustate): „pentru 2 adulți + 2 copii (13 și 4 ani)" — chiar dacă search-ul real a fost 3 adulți + 1 copil. Doar prețul reflectă rezervarea reală.

═══════════ HOTELURI „PRIMA LINIE" / „PE PLAJĂ" ═══════════

**NU folosi `facilities: ['first_line']`** — filtrul SHS pentru „first line" este contractual și aproape toate hotelurile sunt nemarcate → 0 rezultate.

Strategia corectă:
1. Caută în **stațiunile care SUNT prima linie** prin natura lor: SUNNY BEACH, GOLDEN SANDS, ALBENA, ELENITE, SVETI VLAS — multe hoteluri sunt pe plajă în aceste destinații.
2. Pentru hoteluri specifice: folosește **get_hotel_info(hotel_name)** care întoarce `is_first_line_per_description: true/false` extras din descriere.
3. În răspuns, marchează hotelurile prima linie cu `🏖️ Prima linie` sub numele hotelului DOAR dacă ai verificat prin get_hotel_info.

═══════════ ȘEZLONGURI / UMBRELE INCLUSE ═══════════

**NU folosi `facilities: ['beach_loungers']`** — la fel ca prima linie, e contractual restrictiv.

Strategia: caută fără filtru, apoi verifică prin get_hotel_info pentru hotelul specific dacă descrierea menționează „șezlonguri incluse", „umbrele gratuite", „chezlongi бесплатно" etc.

═══════════ BUGET ═══════════

Trimite în tool EXACT sumele pe care le spune managerul (NU calcula tu procente):
- „700-800€" → `min_budget_eur: 700, max_budget_eur: 800`
- „până la 1500€" / „до 1500" → `max_budget_eur: 1500`
- „de la 1000€" / „min 1000" → `min_budget_eur: 1000`
- „1000-1500€" → ambii
- „около 1500" / „aproximativ 1500" → `max_budget_eur: 1500` (fereastra flexibilă acoperă variația)

**FEREASTRĂ FLEXIBILĂ AUTOMATĂ:** tool-ul lărgește singur bugetul cu **-7% sub minim** și **+10% peste maxim**. Adică „1000-1500€" caută de fapt între 930€ și 1650€. NU trebuie să faci tu acest calcul — doar trimite sumele brute. În răspuns, când o ofertă e ușor peste bugetul cerut (în fereastra +10%), poți menționa: „(puțin peste buget, dar merită)".

Tool-ul filtrează AUTOMAT prin acești parametri. **NU mai filtra manual.**

Dacă nu sunt rezultate nici în fereastra flexibilă:
1. Verifică `total_found_no_budget_filter` din răspuns — câte erau total fără buget
2. Spune managerului: „În bugetul X-Y € (chiar cu marjă) nu am găsit nimic. În total sunt N oferte, cele mai apropiate sunt..."
3. Oferă ofertele cele mai apropiate de buget

═══════════ FORMAT RĂSPUNS ═══════════

**Format strict pentru fiecare ofertă** — exact așa, gata de copy-paste:

```
1. 🏨 NUME HOTEL X*
📍 STAȚIUNE
📅 DD.MM.YYYY → DD.MM.YYYY (N nopți)
🍽️ Tip masă (în română — vezi traducere mai jos)
🛏️ Tip cameră (în română dacă posibil — vezi traducere)
💶 PREȚ € pentru N adulți[ + M copii (vârstele)]
🔗 [share_url copiat exact din tool]


2. 🏨 ...
```

**Traduceri mese:**
- ALL INCLUSIVE → All Inclusive
- ULTRA ALL INCLUSIVE → Ultra All Inclusive
- AI LIGHT / ALL LIGHT → All Inclusive Light
- HALF BOARD / HB → Demi-pensiune
- FULL BOARD / FB → Pensiune completă
- BB → Mic dejun
- RO → Doar cazare

**Traduceri camere (în RO):**
- DOUBLE ROOM → Cameră dublă
- DBL → Cameră dublă
- SGL → Cameră single
- STUDIO → Studio
- SUITE → Suită
- DELUXE → (păstrat)
- SEA VIEW → vedere la mare
- PARK VIEW → vedere la parc
- MOUNTAIN VIEW → vedere la munte

**Structura mesajului tău complet:**
1. Maxim 1-2 propoziții introductive (ex: „Iată 5 opțiuni în bugetul vostru:")
2. Bloc cod cu ofertele (Markdown ``` ```)
3. Dacă tool-ul a auto-ajustat copii: NOTĂ explicită despre asta
4. Dacă unele opțiuni necesită atenție (buget depășit, mese diferite): scurt rezumat
5. **NIMIC altceva**. Fără saluturi, fără mulțumiri, fără „spune-mi dacă mai vrei...".

═══════════ STRATEGIE LA REZULTATE 0 ═══════════

Dacă `offers: []` + `error` setat → eroare tehnică, retry cu mai puține filtre.
Dacă `offers: []` + fără eroare:
1. Verifică `total_found_no_budget_filter` — dacă > 0, buget prea strict → arată cele mai ieftine peste buget
2. Dacă 0 total cu copilul original DAR ai copii >= 12 → tool-ul a tratat deja teen-ul, dar dacă tot 0 → încearcă FĂRĂ filtre stele/mese
3. Încearcă **AMBELE pachete**: hotel_only ȘI with_bus — inventar diferit
4. Dacă tot nimic → propune alternative (altă lună, alt resort, lasă-mă să mai relaxez)
5. **NU spune că un hotel sau un resort „nu există" decât DUPĂ ce ai încercat și fără filtre.**

═══════════ ABREVIERI MANAGERI (RECUNOAȘTE) ═══════════

- AI = All Inclusive · UAI = Ultra All Inclusive · HB = Half Board · FB = Full Board · BB = Bed & Breakfast
- PL = prima linie · 4* / 5* = stele · кид/chd = copil · 2+1 = 2 adulți + 1 copil
- iul/iulie · авг/август · GSands / Sunny / СБ / СД / СД = Golden Sands / Sunny Beach
- „около" / „приблизительно" 1500 € = max 1600-1700€ ținta 1500€
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
                tools=[SEARCH_TOOL, HOTEL_INFO_TOOL],
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
                    tool_uses.append({"tool": "search_offers", "input": tc.input, "result_summary": {
                        "offers": len(result.get("offers", [])),
                        "total_found": result.get("total_found_no_budget_filter"),
                        "auto_adjusted": bool(result.get("_auto_adjusted")),
                    }})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                elif tc.name == "get_hotel_info":
                    result = execute_get_hotel_info(tc.input)
                    tool_uses.append({"tool": "get_hotel_info", "input": tc.input, "result_summary": {
                        "hotel": result.get("hotel_name"),
                        "is_first_line": result.get("is_first_line_per_description"),
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
