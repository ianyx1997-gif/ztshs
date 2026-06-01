"""
ZebraTur SHS Integration — main Flask app.
All routes for UI + REST API used by the frontend.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Any

from functools import wraps
from flask import Flask, jsonify, render_template, request, send_from_directory, Response, session, redirect, url_for, make_response
import requests

import config
import database as db
from shs_client import client, SHSError

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["JSON_AS_ASCII"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 days

db.init_db()


# ============================ CORS for widget/embed ============================

@app.before_request
def handle_cors_preflight():
    """Handle OPTIONS preflight requests globally before any route matching."""
    if request.method == "OPTIONS":
        resp = make_response("")
        resp.status_code = 204
        return resp


@app.after_request
def apply_cors(resp):
    origin = request.headers.get("Origin", "")
    allowed = config.CORS_ALLOWED_ORIGINS
    if "*" in allowed or origin in allowed:
        resp.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Actor"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp


# ============================ B2B auth ============================

def b2b_required(f):
    """Protect operator routes — redirect to login page if not authenticated."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("b2b_authed"):
            if request.path.startswith("/api/"):
                return _json_error("authentication required", 401)
            return redirect(url_for("page_login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


# ============================ helpers ============================

def _json_error(msg: str, status: int = 400, **extra) -> tuple[Response, int]:
    payload = {"error": msg}
    payload.update(extra)
    return jsonify(payload), status


def _body() -> dict:
    return request.get_json(silent=True) or {}


def _actor() -> str:
    return request.headers.get("X-Actor", "agent")


# In-memory directory cache (countries, terminals, etc. don't change much)
_DIR_CACHE: dict[str, tuple[float, Any]] = {}
_DIR_TTL = 1800  # 30 min


def _cached(key: str, loader):
    now = time.time()
    item = _DIR_CACHE.get(key)
    if item and now - item[0] < _DIR_TTL:
        return item[1]
    try:
        data = loader()
        _DIR_CACHE[key] = (now, data)
        return data
    except Exception as exc:
        log.exception("cache loader %s failed: %s", key, exc)
        # Fall back to stale cache if any
        if item:
            return item[1]
        return []


# ============================ UI routes ============================

@app.route("/")
@b2b_required
def home():
    return render_template("index.html", agency=config.AGENCY_NAME)


@app.route("/search")
@b2b_required
def page_search():
    return render_template("search.html", agency=config.AGENCY_NAME)


@app.route("/orders")
@b2b_required
def page_orders():
    return render_template("orders.html", agency=config.AGENCY_NAME)


@app.route("/customers")
@b2b_required
def page_customers():
    return render_template("customers.html", agency=config.AGENCY_NAME)


@app.route("/quotes")
@b2b_required
def page_quotes():
    return render_template("quotes.html", agency=config.AGENCY_NAME)


@app.route("/reports")
@b2b_required
def page_reports():
    return render_template("reports.html", agency=config.AGENCY_NAME)


@app.route("/settings")
@b2b_required
def page_settings():
    return render_template("settings.html", agency=config.AGENCY_NAME)


@app.route("/login", methods=["GET", "POST"])
def page_login():
    err = None
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        pwd = request.form.get("password") or ""
        if u == config.B2B_USERNAME and pwd == config.B2B_PASSWORD:
            session.permanent = True
            session["b2b_authed"] = True
            session["b2b_user"] = u
            nxt = request.args.get("next") or "/"
            return redirect(nxt)
        err = "Date de autentificare incorecte"
    return render_template("login.html", agency=config.AGENCY_NAME, error=err)


@app.route("/logout")
def page_logout():
    session.clear()
    return redirect("/login")


# ============================ Chat (manager AI assistant) ============================

def chat_required(f):
    """Protect chat routes. Accepts either a logged-in session OR a valid X-API-Key
    header (for server-to-server callers like the Kommo bot)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 1. API key (server-to-server) — checked first
        api_key = request.headers.get("X-API-Key", "")
        if config.CHAT_API_KEY and api_key and api_key == config.CHAT_API_KEY:
            return f(*args, **kwargs)
        # 2. Session cookie (browser managers)
        if session.get("chat_authed"):
            return f(*args, **kwargs)
        # Reject
        if request.path.startswith("/api/"):
            return _json_error("authentication required", 401)
        return redirect(url_for("page_chat_login", next=request.path))
    return wrapper


@app.route("/chat-login", methods=["GET", "POST"])
def page_chat_login():
    err = None
    if request.method == "POST":
        pwd = request.form.get("password") or ""
        if pwd == config.CHAT_PASSWORD:
            session.permanent = True
            session["chat_authed"] = True
            session["chat_logged_at"] = int(time.time())
            nxt = request.args.get("next") or "/chat"
            return redirect(nxt)
        err = "Parolă incorectă"
    return render_template("chat_login.html", agency=config.AGENCY_NAME, error=err)


@app.route("/chat")
@chat_required
def page_chat():
    return render_template("chat.html", agency=config.AGENCY_NAME)


@app.route("/chat-logout")
def page_chat_logout():
    session.pop("chat_authed", None)
    session.pop("chat_logged_at", None)
    return redirect("/chat-login")


@app.route("/api/chat/query", methods=["POST"])
@chat_required
def api_chat_query():
    p = _body()
    messages = p.get("messages") or []
    if not isinstance(messages, list) or not messages:
        return _json_error("missing messages")

    from chat_assistant import run_chat
    result = run_chat(messages)
    db.audit("chat-manager", "chat.query", details={
        "msg_count": len(messages),
        "last_user_msg": (messages[-1].get("content", "") if isinstance(messages[-1].get("content"), str) else "complex")[:200],
        "tokens": result.get("usage", {}),
    })
    return jsonify(result)


@app.route("/turist")
@app.route("/cauta-vacanta")
def page_turist():
    embed = request.args.get("embed") == "1"
    return render_template("turist.html", agency=config.AGENCY_NAME, embed=embed)


@app.route("/turist/hotel/<int:hotel_id>")
@app.route("/turist/oferta/<int:hotel_id>")
def page_turist_hotel(hotel_id):
    embed = request.args.get("embed") == "1"
    return render_template("turist_hotel.html", agency=config.AGENCY_NAME, hotel_id=hotel_id, embed=embed)


@app.route("/embed.js")
def embed_js():
    """Inline widget (no iframe) — injects search UI directly into the host page."""
    resp = send_from_directory("static", "embed.js")
    resp.headers["Content-Type"] = "application/javascript; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def _public_base_url() -> str:
    """Return the public base URL with scheme guaranteed (defaults to https)."""
    base = (config.PUBLIC_BASE_URL or request.host_url).rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "https://" + base
    return base


@app.route("/embed-config.js")
def embed_config_js():
    """Configures the embed.js widget — sets the API base URL."""
    base = _public_base_url()
    js = f"window.ZEBRA_TUR_API = '{base}';"
    return js, 200, {
        "Content-Type": "application/javascript; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=60",
    }


@app.route("/widget.js")
def widget_js():
    """JavaScript widget that embeds the B2C search on partner sites (e.g. zebratur.md/bulgaria)."""
    base = _public_base_url()
    js = f"""(function() {{
  var BASE = "{base}";
  var SRC_URL = BASE + "/turist?embed=1";

  function ensureContainer() {{
    var el = document.getElementById('zebra-tur-widget') || document.getElementById('zebra-search-widget');
    if (!el) {{
      // Auto-create after the script tag if no explicit container
      var scripts = document.getElementsByTagName('script');
      var current = scripts[scripts.length - 1];
      el = document.createElement('div');
      el.id = 'zebra-tur-widget';
      current.parentNode.insertBefore(el, current.nextSibling);
    }}
    return el;
  }}

  function injectStyles() {{
    if (document.getElementById('zebra-tur-widget-style')) return;
    var s = document.createElement('style');
    s.id = 'zebra-tur-widget-style';
    s.textContent = '#zebra-tur-widget, #zebra-search-widget {{ width: 100%; min-height: 800px; }}' +
      '#zebra-tur-widget iframe, #zebra-search-widget iframe {{ width: 100%; border: 0; display: block; transition: height 0.2s; }}';
    document.head.appendChild(s);
  }}

  function mount() {{
    injectStyles();
    var container = ensureContainer();
    container.innerHTML = '';
    var iframe = document.createElement('iframe');
    iframe.src = SRC_URL;
    iframe.style.width = '100%';
    iframe.style.border = '0';
    iframe.style.minHeight = '800px';
    iframe.title = 'Zebra Tur — Caută vacanța ta';
    iframe.setAttribute('loading', 'lazy');
    iframe.setAttribute('referrerpolicy', 'no-referrer-when-downgrade');
    container.appendChild(iframe);

    // Auto-resize via postMessage from embedded page
    window.addEventListener('message', function(ev) {{
      try {{
        if (!ev.data || ev.data.type !== 'zebra-tur:height') return;
        var allowedOrigin = new URL(SRC_URL).origin;
        if (ev.origin !== allowedOrigin) return;
        var h = parseInt(ev.data.height || 0);
        if (h > 200) iframe.style.height = h + 'px';
      }} catch (e) {{}}
    }});
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', mount);
  }} else {{
    mount();
  }}
}})();
"""
    resp = make_response(js)
    resp.headers["Content-Type"] = "application/javascript; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


def _send_email(*, subject: str, html: str, to: str | None = None) -> dict:
    """Send notification email via Resend."""
    if not config.RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set, skipping email")
        return {"skipped": True}
    payload = {
        "from": config.RESEND_FROM,
        "to": [to or config.NOTIFY_EMAIL],
        "subject": subject,
        "html": html,
    }
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {config.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload, timeout=10,
        )
        result = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"_raw": r.text[:500]}
        if r.status_code >= 400:
            log.warning("Resend %s: %s", r.status_code, result)
        else:
            log.info("Email sent to %s (id=%s)", payload["to"], result.get("id"))
        return result
    except Exception as exc:
        log.exception("Resend exception: %s", exc)
        return {"error": str(exc)}


def _build_reservation_email_html(p: dict, offer: dict, quote_id: int) -> str:
    """HTML body for new temp reservation notification."""
    sale = offer.get("brut_zebra") or offer.get("gross_amount") or offer.get("sale_amount") or 0
    currency = offer.get("currency", "EUR")
    photo = offer.get("default_photo") or ""
    hotel_url = ""
    if offer.get("hotel_id"):
        from urllib.parse import urlencode
        params = urlencode({
            "in": offer.get("check_in", ""),
            "out": offer.get("check_out", ""),
            "n": offer.get("nights", 7),
            "a": p.get("adults", 2),
            "p": 87,
            "t": "self",
        })
        hotel_url = f"/turist/hotel/{offer['hotel_id']}?{params}"

    return f"""
    <div style="font-family: -apple-system, system-ui, Segoe UI, Arial, sans-serif; max-width: 600px; margin: 0 auto; background:#f5f7ff; padding: 24px;">
      <div style="background: linear-gradient(135deg, #3a48d0, #2f38aa); color: white; padding: 20px 24px; border-radius: 12px 12px 0 0;">
        <div style="font-size: 24px; font-weight: 800;">🦓 Zebra Tur</div>
        <div style="font-size: 14px; opacity: 0.9; margin-top: 4px;">📞 Rezervare temporară nouă</div>
      </div>

      <div style="background: white; padding: 24px; border-radius: 0 0 12px 12px;">
        <div style="background: #fff7ed; border-left: 4px solid #f97316; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
          <div style="font-size: 13px; color: #92400e;">Comandă internă</div>
          <div style="font-size: 18px; font-weight: 700; color: #c2410c;">#{quote_id}</div>
        </div>

        <h2 style="font-size: 18px; margin: 0 0 12px;">👤 Datele clientului</h2>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <tr><td style="padding: 6px 0; color: #64748b; width: 100px;">Nume:</td>
              <td style="padding: 6px 0; font-weight: 600;">{p.get('customer_name', '')}</td></tr>
          <tr><td style="padding: 6px 0; color: #64748b;">Telefon:</td>
              <td style="padding: 6px 0; font-weight: 600;"><a href="tel:{p.get('customer_phone', '')}" style="color: #3a48d0; text-decoration: none;">{p.get('customer_phone', '')}</a></td></tr>
          <tr><td style="padding: 6px 0; color: #64748b;">Email:</td>
              <td style="padding: 6px 0;">{p.get('customer_email') or '—'}</td></tr>
          <tr><td style="padding: 6px 0; color: #64748b;">Adulți:</td>
              <td style="padding: 6px 0;">{p.get('adults', '?')}</td></tr>
          <tr><td style="padding: 6px 0; color: #64748b;">Copii:</td>
              <td style="padding: 6px 0;">{p.get('children_ages') or '—'}</td></tr>
        </table>

        <h2 style="font-size: 18px; margin: 0 0 12px;">🏨 Oferta cerută</h2>
        {f'<img src="{photo}" style="width:100%; max-height:200px; object-fit:cover; border-radius:8px; margin-bottom:12px;">' if photo else ''}
        <div style="background: #f5f7ff; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
          <div style="font-size: 18px; font-weight: 700;">{offer.get('hotel_name', '')} <span style="color: #f59e0b;">{offer.get('star', '')}</span></div>
          <div style="color: #64748b; font-size: 14px; margin-top: 4px;">📍 {offer.get('city', 'Bulgaria')}</div>
          <table style="width: 100%; font-size: 14px; margin-top: 12px;">
            <tr><td style="padding: 3px 0;">📅 Perioadă:</td><td style="padding: 3px 0; font-weight: 600;">{offer.get('check_in', '?')} → {offer.get('check_out', '?')} ({offer.get('nights', '?')} nopți)</td></tr>
            <tr><td style="padding: 3px 0;">🍽️ Masă:</td><td style="padding: 3px 0; font-weight: 600;">{offer.get('meal', '?')}</td></tr>
            <tr><td style="padding: 3px 0;">🛏️ Cameră:</td><td style="padding: 3px 0; font-weight: 600;">{offer.get('room_type', '?')}</td></tr>
          </table>
        </div>

        <div style="background: linear-gradient(90deg, #3a48d0, #2f38aa); color: white; padding: 16px 20px; border-radius: 8px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size: 12px; opacity: 0.85; text-transform: uppercase;">Preț cerut</div>
            <div style="font-size: 11px; opacity: 0.7;">pentru {p.get('adults', '?')} adulți</div>
          </div>
          <div style="font-size: 26px; font-weight: 800;">{sale:.0f} {currency}</div>
        </div>

        {f'<a href="http://127.0.0.1:5050{hotel_url}" style="display: inline-block; margin-top: 16px; background: #f97316; color: white; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">🔗 Vezi oferta</a>' if hotel_url else ''}

        {f'<div style="background:#f1f5f9; padding:12px; border-radius:8px; margin-top:16px;"><div style="font-size:12px; color:#64748b; margin-bottom:4px;">💬 Mesaj de la client:</div><div style="font-size:14px;">{p.get("notes")}</div></div>' if p.get("notes") else ''}

        <div style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0;">
          🦓 Zebra Tur · Acest email a fost trimis automat din motorul de rezervări online
        </div>
      </div>
    </div>
    """


@app.route("/api/turist/reserve", methods=["POST"])
def turist_reserve():
    """Create a temporary reservation (a quote) from a tourist-facing form."""
    p = _body()
    required = ["customer_name", "customer_phone"]
    for k in required:
        if not p.get(k):
            return _json_error(f"missing: {k}")
    offer = p.get("offer") or {}
    title = (offer.get("hotel_name") or "Vacanță Bulgaria")
    if offer.get("check_in"):
        title += f" · {offer['check_in']}"
    summary_parts = []
    if offer.get("hotel_name"): summary_parts.append(f"Hotel: {offer['hotel_name']} ({offer.get('star','')})")
    if offer.get("city"): summary_parts.append(f"Stațiune: {offer['city']}")
    if offer.get("meal"): summary_parts.append(f"Masă: {offer['meal']}")
    if offer.get("room_type"): summary_parts.append(f"Cameră: {offer['room_type']}")
    if offer.get("check_in") and offer.get("check_out"):
        summary_parts.append(f"Perioadă: {offer['check_in']} → {offer['check_out']} ({offer.get('nights','?')} nopți)")
    if p.get("adults"): summary_parts.append(f"Adulți: {p['adults']}")
    if p.get("children_ages"): summary_parts.append(f"Copii: {p['children_ages']}")
    if p.get("notes"): summary_parts.append(f"Note client: {p['notes']}")
    summary = "\n".join(summary_parts)

    qid = db.create_quote({
        "customer_main": p["customer_name"].strip(),
        "customer_phone": p["customer_phone"].strip(),
        "title": title,
        "summary": summary,
        "options": [offer],
        "status": "open",
        "sale_amount": offer.get("brut_zebra") or offer.get("gross_amount") or offer.get("sale_amount"),
        "currency": offer.get("currency", "EUR"),
        "agent": "turist-b2c",
    })
    # Try also creating a customer entry if email/phone provided
    if p.get("customer_email") or p.get("customer_phone"):
        try:
            parts = p["customer_name"].strip().split(" ", 1)
            db.create_customer({
                "category": "Mr",
                "name": (parts[1] if len(parts) > 1 else parts[0]).upper(),
                "surname": parts[0].upper(),
                "telephone": p.get("customer_phone", ""),
                "email": p.get("customer_email", ""),
                "nationality": "MOLDOVA",
                "notes": f"Înregistrare automată din cautare turist (quote #{qid})",
            })
        except Exception:
            pass
    db.audit("turist-b2c", "turist.reserve", target=str(qid), details={
        "customer": p["customer_name"], "phone": p["customer_phone"],
        "hotel": offer.get("hotel_name"),
    })

    # Send notification email to agency via Resend (don't block response if email fails)
    try:
        subject = f"🦓 Rezervare nouă #{qid} · {offer.get('hotel_name', 'Zebra Tur')} · {p['customer_name']}"
        html = _build_reservation_email_html(p, offer, qid)
        threading.Thread(target=_send_email, kwargs={"subject": subject, "html": html}, daemon=True).start()
    except Exception as exc:
        log.warning("Failed to enqueue email: %s", exc)

    return jsonify({"ok": True, "quote_id": qid, "message": "Rezervarea temporară a fost trimisă. Un agent Zebra Tur te va contacta în maxim 2 ore."})


# ============================ API: health ============================

@app.route("/api/health")
def api_health():
    return jsonify({"ok": True, "ts": int(time.time()), "agency": config.AGENCY_NAME})


@app.route("/api/shs/ping")
def api_ping():
    return jsonify(client.ping())


# ============================ API: directories (cached) ============================

@app.route("/api/dir/countries")
def dir_countries():
    return jsonify(_cached("countries", client.get_countries))


@app.route("/api/dir/cities")
def dir_cities():
    country_id = request.args.get("country_id", type=int)
    key = f"cities:{country_id or 'all'}"
    return jsonify(_cached(key, lambda: client.get_cities(country_id)))


@app.route("/api/dir/terminals")
def dir_terminals():
    return jsonify(_cached("terminals", client.get_terminals))


@app.route("/api/dir/hotel_facilities")
def dir_facilities():
    return jsonify(_cached("facilities", client.get_hotel_facilities))


@app.route("/api/dir/hotel_categories")
def dir_categories():
    return jsonify(_cached("categories", client.get_hotel_categories))


@app.route("/api/dir/meals")
def dir_meals():
    return jsonify(_cached("meals", client.get_meal_types))


@app.route("/api/dir/hotels")
def dir_hotels():
    body = {k: request.args.get(k, type=int) for k in ("country_id", "city_id", "category_id", "meal_id")}
    return jsonify(client.get_hotel_list(**{k: v for k, v in body.items() if v}))


@app.route("/api/dir/packages")
def dir_packages():
    country_id = request.args.get("country_id", type=int)
    return jsonify(_cached(f"packages:{country_id or 'all'}",
                           lambda: client.get_package_list(country_id)))


@app.route("/api/dir/transport_dates")
def dir_transport_dates():
    cid = request.args.get("country_id", type=int) or 0
    return jsonify(client.get_transport_available_dates(cid))


@app.route("/api/dir/excursion_countries")
def dir_exc_countries():
    lang = request.args.get("lang", config.DEFAULT_LANG)
    return jsonify(_cached(f"exc_countries:{lang}", lambda: client.get_excursion_countries(lang)))


@app.route("/api/dir/excursion_departures")
def dir_exc_departures():
    lang = request.args.get("lang", config.DEFAULT_LANG)
    return jsonify(_cached(f"exc_departures:{lang}", lambda: client.get_excursion_departures(lang)))


@app.route("/api/dir/excursion_programs")
def dir_exc_programs():
    lang = request.args.get("lang", config.DEFAULT_LANG)
    return jsonify(_cached(f"exc_programs:{lang}", lambda: client.get_excursion_programs(lang)))


# ============================ API: search ============================

@app.route("/api/search/hotels", methods=["POST"])
def search_hotels():
    p = _body()
    try:
        data = client.search_hotels(
            adults=int(p.get("adults", 2)),
            children=_int_list(p.get("children")) or [],
            from_date=p["from_date"],
            to_date=p["to_date"],
            from_nights=int(p.get("from_nights", 7)),
            to_nights=int(p.get("to_nights", 7)),
            hotel_ids=_int_list(p.get("hotel_ids")),
            meal_ids=_int_list(p.get("meal_ids")),
            city_ids=_int_list(p.get("city_ids")),
            category_ids=_int_list(p.get("category_ids")),
            facility_ids=_int_list(p.get("facility_ids")),
            show_stops=bool(p.get("show_stops", True)),
            with_description=bool(p.get("with_description", True)),
        )
        db.audit(_actor(), "search.hotels", details=p)
        if isinstance(data, dict) and data.get("status") == "error":
            return _json_error(data.get("message", "SHS error"), 400, shs_response=data)
        return jsonify(_decorate_hotel_results(data, p))
    except SHSError as e:
        return _json_error(str(e), 502)
    except KeyError as e:
        return _json_error(f"missing field: {e}")


@app.route("/api/search/transport", methods=["POST"])
def search_transport():
    p = _body()
    try:
        data = client.search_transport(
            departure=p["departure"],
            destinations=p["destinations"],
            from_date=p["from_date"],
            to_date=p["to_date"],
            adults=int(p.get("adults", 2)),
            children=[int(c) for c in p.get("children", [])],
            period_type=p.get("period_type", "departure_range"),
            days_from=int(p.get("days_from", 7)),
            days_to=int(p.get("days_to", 7)),
            days_interval_type=p.get("days_interval_type", "tour_days"),
            outbound=bool(p.get("outbound", True)),
            inbound=bool(p.get("inbound", True)),
        )
        db.audit(_actor(), "search.transport", details=p)
        return jsonify({"items": _decorate_transport(data)})
    except SHSError as e:
        return _json_error(str(e), 502)
    except KeyError as e:
        return _json_error(f"missing field: {e}")


def _to_pkg_date(s: str) -> str:
    """Convert YYYY-MM-DD (HTML input) to DD.MM.YYYY (SHS packages format)."""
    if not s:
        return s
    if "." in s:  # already in DD.MM.YYYY
        return s
    try:
        y, m, d = s.split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return s


def _int_list(val) -> list[int] | None:
    """Convert array of int/str to clean list of ints. Empty/None -> None."""
    if val is None:
        return None
    if not isinstance(val, list):
        val = [val]
    out = []
    for x in val:
        try:
            out.append(int(x))
        except (ValueError, TypeError):
            pass
    return out or None


@app.route("/api/search/packages", methods=["POST"])
def search_packages():
    p = _body()
    try:
        country_id = int(p["country_id"])
        package_id = int(p["package_id"])
        # SHS requires city_ids — fall back to all allowed cities for this package
        city_ids = p.get("city_ids") or []
        if not city_ids:
            try:
                pkg_list = client.get_package_list(country_id)
                pkg = next((x for x in (pkg_list or []) if int(x.get("id", -1)) == package_id), None)
                if pkg and pkg.get("city_ids"):
                    city_ids = pkg["city_ids"]
            except Exception:
                pass

        data = client.search_packages(
            departure_terminal_id=int(p["departure_terminal_id"]),
            package_id=package_id,
            country_id=country_id,
            from_date=_to_pkg_date(p["from_date"]),
            to_date=_to_pkg_date(p["to_date"]),
            from_nights=int(p.get("from_nights", 7)),
            to_nights=int(p.get("to_nights", 7)),
            adults=int(p.get("adults", 2)),
            children=_int_list(p.get("children")) or [],
            meal_ids=_int_list(p.get("meal_ids")),
            star_ids=_int_list(p.get("star_ids")),
            facility_ids=_int_list(p.get("facility_ids")),
            city_ids=_int_list(city_ids),
            hotel_ids=_int_list(p.get("hotel_ids")),
            grouped=bool(p.get("grouped", True)),
        )
        db.audit(_actor(), "search.packages", details=p)
        if isinstance(data, dict) and data.get("status") == "error":
            return _json_error(data.get("message", "SHS error"), 400, shs_response=data)
        return jsonify(_decorate_package_results(data, p))
    except SHSError as e:
        return _json_error(str(e), 502)
    except KeyError as e:
        return _json_error(f"missing field: {e}")


@app.route("/api/search/packages/page")
def package_page():
    session = request.args.get("session")
    page = request.args.get("page", type=int, default=1)
    markup = request.args.get("markup_percent", type=float) or 0
    adults = request.args.get("adults", type=int) or 2
    if not session:
        return _json_error("missing session")
    data = client.get_pricing_page(session, page)
    return jsonify(_decorate_package_results(data, {"markup_percent": markup, "adults": adults}))


@app.route("/api/hotel/details", methods=["POST"])
def hotel_details():
    """Get hotel description + photos + map for a single hotel (uses /hotel/search)."""
    p = _body()
    try:
        hotel_id = int(p["hotel_id"])
        data = client.search_hotels(
            adults=int(p.get("adults", 2)),
            children=_int_list(p.get("children")) or [],
            from_date=p.get("from_date") or (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
            to_date=p.get("to_date") or (date.today() + timedelta(days=37)).strftime("%Y-%m-%d"),
            from_nights=int(p.get("from_nights", 7)),
            to_nights=int(p.get("to_nights", 7)),
            hotel_ids=[hotel_id],
            with_description=True,
            show_stops=True,
        )
        hotels = (data or {}).get("hotels") or []
        if not hotels:
            return _json_error("hotel not found", 404)
        h = hotels[0]
        photos = h.get("photos") or []
        photo_urls = [
            (ph if str(ph).startswith("http") else f"{config.SHS_FILES_BASE_URL}/{ph}")
            for ph in photos
        ]
        default_photo = h.get("default_photo") or (photos[0] if photos else "")
        if default_photo and not str(default_photo).startswith("http"):
            default_photo = f"{config.SHS_FILES_BASE_URL}/{default_photo}"
        return jsonify({
            "hotel_id": h.get("hotel_id"),
            "hotel_name": h.get("hotel_name"),
            "country": h.get("country"),
            "city": h.get("city"),
            "star": h.get("star"),
            "description": h.get("description") or "",
            "photos": photo_urls,
            "default_photo": default_photo,
            "map_frame": h.get("map_frame") or "",
            "latitude": h.get("latitude"),
            "longitude": h.get("longitude"),
            "facility_ids": h.get("facility_ids") or [],
        })
    except SHSError as e:
        return _json_error(str(e), 502)
    except KeyError as e:
        return _json_error(f"missing field: {e}")


@app.route("/api/search/packages/hotel_rooms", methods=["POST"])
def package_hotel_rooms():
    """Fetch all room variants for one specific hotel using the same search params, grouped=false."""
    p = _body()
    try:
        country_id = int(p["country_id"])
        package_id = int(p["package_id"])
        hotel_id = int(p["hotel_id"])
        city_ids = _int_list(p.get("city_ids")) or []
        if not city_ids:
            try:
                pkg_list = client.get_package_list(country_id)
                pkg = next((x for x in (pkg_list or []) if int(x.get("id", -1)) == package_id), None)
                if pkg and pkg.get("city_ids"):
                    city_ids = pkg["city_ids"]
            except Exception:
                pass

        data = client.search_packages(
            departure_terminal_id=int(p["departure_terminal_id"]),
            package_id=package_id,
            country_id=country_id,
            from_date=_to_pkg_date(p["from_date"]),
            to_date=_to_pkg_date(p["to_date"]),
            from_nights=int(p.get("from_nights", 7)),
            to_nights=int(p.get("to_nights", 7)),
            adults=int(p.get("adults", 2)),
            children=_int_list(p.get("children")) or [],
            hotel_ids=[hotel_id],
            city_ids=_int_list(city_ids),
            grouped=False,
        )
        if isinstance(data, dict) and data.get("status") == "error":
            return _json_error(data.get("message", "SHS error"), 400, shs_response=data)
        return jsonify(_decorate_package_results(data, p))
    except SHSError as e:
        return _json_error(str(e), 502)
    except KeyError as e:
        return _json_error(f"missing field: {e}")


@app.route("/api/search/excursions", methods=["POST"])
def search_excursions():
    p = _body()
    try:
        data = client.search_excursions(
            departure_id=p.get("departure_id"),
            excursion_ids=p.get("excursion_ids"),
            date_from=p["date_from"],
            date_to=p["date_to"],
            adults=int(p.get("adults", 2)),
            children_ages=p.get("children_ages"),
            trip_type=p.get("trip_type", "excursion"),
            lang=p.get("lang", config.DEFAULT_LANG),
        )
        db.audit(_actor(), "search.excursions", details=p)
        return jsonify(data)
    except SHSError as e:
        return _json_error(str(e), 502)
    except KeyError as e:
        return _json_error(f"missing field: {e}")


@app.route("/api/search/transfers", methods=["POST"])
def search_transfers():
    p = _body()
    try:
        data = client.search_transfers(
            departure_id=int(p["departure_id"]),
            arrival_id=int(p["arrival_id"]),
            date=p["date"],
            adults=int(p.get("adults", 2)),
            children=[int(c) for c in p.get("children", [])],
            transfer_type=p.get("transfer_type"),
        )
        db.audit(_actor(), "search.transfers", details=p)
        return jsonify({"items": data})
    except SHSError as e:
        return _json_error(str(e), 502)
    except KeyError as e:
        return _json_error(f"missing field: {e}")


@app.route("/api/excursions/dates")
def excursion_dates():
    raw_ids = request.args.get("ids", "")
    ids = [int(x) for x in raw_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return _json_error("missing ids")
    return jsonify(client.get_excursion_dates(ids))


@app.route("/api/excursions/list")
def excursion_list():
    def _ids(name):
        raw = request.args.get(name, "")
        return [int(x) for x in raw.split(",") if x.strip().isdigit()]
    return jsonify(client.list_excursions(
        country_ids=_ids("countries") or None,
        program_ids=_ids("programs") or None,
        departure_ids=_ids("departures") or None,
        lang=request.args.get("lang", config.DEFAULT_LANG),
    ))


# ============================ API: price check ============================

@app.route("/api/check/transport", methods=["POST"])
def check_transport():
    p = _body()
    try:
        return jsonify(client.check_transport_flights(
            session=p["session"], price_id=int(p["price_id"]),
            departure_places=p.get("departure_places"),
            retur_places=p.get("retur_places"),
        ))
    except SHSError as e:
        return _json_error(str(e), 502)


@app.route("/api/check/excursion", methods=["GET"])
def check_excursion():
    pid = request.args.get("price_id", type=int)
    session = request.args.get("session")
    if not pid:
        return _json_error("missing price_id")
    return jsonify(client.check_excursion_price(price_id=pid, session=session))


# ============================ API: booking ============================

def _normalize_customers(customers: list[dict]) -> list[dict]:
    """Ensure customer dicts match SHS schema fields exactly."""
    out = []
    for c in customers or []:
        out.append({
            "Infant": bool(c.get("Infant", c.get("infant", False))),
            "Category": c.get("Category") or c.get("category") or "Mr",
            "Name": (c.get("Name") or c.get("name") or "").upper(),
            "Surname": (c.get("Surname") or c.get("surname") or "").upper(),
            "BirthDate": c.get("BirthDate", c.get("birth_date", "")) or "",
            "Age": int(c.get("Age", c.get("age", 0)) or 0),
            "Nationality": (c.get("Nationality") or c.get("nationality") or config.DEFAULT_NATIONALITY).upper(),
            "Idn": c.get("Idn", c.get("idn", "")) or "",
            "Telephone": c.get("Telephone", c.get("telephone", "")) or "",
            "Email": c.get("Email", c.get("email", "")) or "",
            "Visa": bool(c.get("Visa", c.get("visa", False))),
            "PassportNr": c.get("PassportNr", c.get("passport_nr", "")) or "",
            "PassportDateExpiry": c.get("PassportDateExpiry", c.get("passport_expiry", "")) or "",
        })
    return out


@app.route("/api/book/package", methods=["POST"])
@b2b_required
def book_package():
    p = _body()
    customers = _normalize_customers(p.get("customers", []))
    if not customers:
        return _json_error("at least one customer required")
    try:
        result = client.save_package_booking(
            session=p["session"], price_id=int(p["price_id"]),
            customers=customers,
            departure_places=p.get("departure_places"),
            retur_places=p.get("retur_places"),
        )
        _persist_booking(result, "package", p, customers)
        db.audit(_actor(), "book.package", target=str(result.get("order", "")), details={
            "price_id": p.get("price_id"), "session": p.get("session"),
        })
        return jsonify(result)
    except SHSError as e:
        return _json_error(str(e), 502)


@app.route("/api/book/transport", methods=["POST"])
@b2b_required
def book_transport():
    p = _body()
    customers = _normalize_customers(p.get("customers", []))
    if not customers:
        return _json_error("at least one customer required")
    try:
        result = client.create_remote_order(
            price_id=int(p["price_id"]), session=p["session"],
            customers=customers,
            departure_places=p.get("departure_places"),
            retur_places=p.get("retur_places"),
        )
        _persist_booking(result, "transport", p, customers)
        db.audit(_actor(), "book.transport", target=str(result.get("order", "")), details={
            "price_id": p.get("price_id"),
        })
        return jsonify(result)
    except SHSError as e:
        return _json_error(str(e), 502)


def _persist_booking(result: dict, kind: str, p: dict, customers: list[dict]) -> None:
    order_id = str(result.get("order") or "")
    if not order_id or result.get("status") != "ok":
        return
    main = customers[0] if customers else {}
    snapshot = p.get("snapshot") or {}
    sale_amount = float(snapshot.get("gross_amount") or 0)
    markup = float(p.get("markup_percent") or config.DEFAULT_MARKUP_PERCENT)
    final_sale = sale_amount * (1 + markup / 100.0) if sale_amount else 0
    db.upsert_order({
        "shs_order_id": order_id,
        "type": kind,
        "status": "in_work",
        "status_id": 1,
        "customer_main": f"{main.get('Surname','')} {main.get('Name','')}".strip(),
        "customer_phone": main.get("Telephone", ""),
        "customer_email": main.get("Email", ""),
        "pax_count": len(customers),
        "departure_date": snapshot.get("departure_date") or snapshot.get("check_in"),
        "return_date": snapshot.get("retur_departure_date") or snapshot.get("check_out"),
        "destination": snapshot.get("country") or snapshot.get("city"),
        "hotel_name": snapshot.get("hotel_name"),
        "meal": snapshot.get("meal"),
        "room_type": snapshot.get("room_type"),
        "nights": snapshot.get("nights"),
        "net_amount": snapshot.get("net_amount"),
        "gross_amount": snapshot.get("gross_amount"),
        "sale_amount": final_sale,
        "currency": snapshot.get("currency") or config.AGENCY_CURRENCY,
        "markup_percent": markup,
        "agent": _actor(),
        "payload": json.dumps({"snapshot": snapshot, "raw_result": result}, ensure_ascii=False),
    })


# ============================ API: orders ============================

@app.route("/api/orders")
def list_orders():
    items = db.list_orders(
        status=request.args.get("status") or None,
        q=request.args.get("q") or None,
        date_from=request.args.get("from") or None,
        date_to=request.args.get("to") or None,
    )
    return jsonify({"items": items, "count": len(items)})


@app.route("/api/orders/<int:oid>")
def get_order(oid):
    item = db.get_order(oid)
    if not item:
        return _json_error("not found", 404)
    if item.get("payload"):
        try:
            item["payload"] = json.loads(item["payload"])
        except Exception:
            pass
    messages = db.list_messages(item.get("shs_order_id"))
    return jsonify({"order": item, "messages": messages})


@app.route("/api/orders/lookup", methods=["POST"])
def lookup_order():
    """Fetch a specific order from SHS by its ID and persist it locally."""
    p = _body()
    raw_ids = p.get("ids") or [p.get("id")]
    ids = [int(x) for x in raw_ids if x and str(x).strip().isdigit()]
    if not ids:
        return _json_error("provide one or more SHS order IDs")
    try:
        statuses = client.get_order_status(ids, show_message=True)
    except SHSError as e:
        return _json_error(str(e), 502)
    status_map = {
        "1": "in_work", "2": "confirmed", "3": "confirmed_print",
        "4": "not_confirmed", "5": "canceled", "6": "accepted_for_processing",
    }
    saved = []
    for s in statuses or []:
        sid = str(s.get("Order") or s.get("order") or "")
        if not sid:
            continue
        status_id = str(s.get("StatusId") or s.get("status_id") or "")
        status_name = status_map.get(status_id, (s.get("StatusName") or "in_work").lower())
        db.upsert_order({
            "shs_order_id": sid,
            "type": "lookup",
            "status": status_name,
            "status_id": int(status_id) if status_id.isdigit() else None,
            "agent": _actor(),
            "payload": json.dumps(s, ensure_ascii=False),
        })
        saved.append(sid)
    db.audit(_actor(), "orders.lookup", details={"ids": ids, "saved": saved})
    return jsonify({"saved": saved, "statuses": statuses})


@app.route("/api/orders/sync", methods=["POST"])
def sync_orders():
    """Refresh statuses of given (or all open) orders from SHS."""
    p = _body()
    shs_ids = p.get("ids")
    if not shs_ids:
        rows = db.fetch_all("SELECT shs_order_id FROM orders WHERE status NOT IN ('canceled','confirmed_print')")
        shs_ids = [r["shs_order_id"] for r in rows if r["shs_order_id"]]
    if not shs_ids:
        return jsonify({"updated": 0})
    try:
        statuses = client.get_order_status([int(i) for i in shs_ids if str(i).isdigit()])
    except SHSError as e:
        return _json_error(str(e), 502)
    status_map = {
        "1": "in_work", "2": "confirmed", "3": "confirmed_print",
        "4": "not_confirmed", "5": "canceled", "6": "accepted_for_processing",
    }
    updated = 0
    for s in statuses:
        sid = str(s.get("Order") or s.get("order"))
        existing = db.get_order_by_shs(sid)
        status_id = str(s.get("StatusId") or s.get("status_id") or "")
        status_name = status_map.get(status_id, s.get("StatusName") or "in_work")
        if existing:
            db.upsert_order({
                "shs_order_id": sid,
                "status": status_name,
                "status_id": int(status_id) if status_id.isdigit() else None,
            })
            updated += 1
        else:
            # Order was unknown locally — create stub row
            db.upsert_order({
                "shs_order_id": sid,
                "status": status_name,
                "status_id": int(status_id) if status_id.isdigit() else None,
                "type": "imported",
                "agent": _actor(),
            })
            updated += 1
    db.audit(_actor(), "orders.sync", details={"count": updated})
    return jsonify({"updated": updated, "statuses": statuses})


@app.route("/api/orders/<shs_id>/status", methods=["POST"])
def update_order_status(shs_id):
    p = _body()
    status = p.get("status")
    locked = p.get("locked")
    if not status:
        return _json_error("missing status")
    try:
        result = client.update_order(order_id=int(shs_id), status=status, locked=locked)
        existing = db.get_order_by_shs(shs_id)
        if existing:
            db.upsert_order({"shs_order_id": shs_id, "status": status})
        db.audit(_actor(), "orders.update_status", target=shs_id, details={"status": status})
        return jsonify(result)
    except SHSError as e:
        return _json_error(str(e), 502)


@app.route("/api/orders/<shs_id>/message", methods=["POST"])
def order_message(shs_id):
    p = _body()
    text = (p.get("text") or "").strip()
    if not text:
        return _json_error("empty message")
    try:
        result = client.create_order_message(order_id=int(shs_id), message=text)
    except SHSError as e:
        return _json_error(str(e), 502)
    db.log_message(shs_id, "out", text, shs_message_id=str(result.get("message_id") or ""))
    db.audit(_actor(), "orders.message", target=shs_id, details={"text": text[:200]})
    return jsonify(result)


@app.route("/api/orders/report.xml")
def report_xml():
    date_from = request.args.get("from") or (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    date_to = request.args.get("to") or date.today().strftime("%Y-%m-%d")
    status = request.args.get("status", "all")
    search_type = request.args.get("search_type", "creation")
    xml = client.fetch_report_xml(date_from=date_from, date_to=date_to,
                                  status=status, search_type=search_type)
    return Response(xml, mimetype="application/xml")


@app.route("/api/orders/report/import", methods=["POST"])
def report_import():
    """Fetch XML report and merge into local DB."""
    p = _body()
    date_from = p.get("from") or (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    date_to = p.get("to") or date.today().strftime("%Y-%m-%d")
    status = p.get("status", "all")
    xml = client.fetch_report_xml(date_from=date_from, date_to=date_to, status=status)
    if not xml or "<" not in xml:
        return _json_error("empty report")
    imported = 0
    try:
        root = ET.fromstring(xml)
        for order in root.iter():
            if order.tag.lower() not in ("order", "booking", "row"):
                continue
            data = {child.tag: (child.text or "").strip() for child in order}
            shs_id = data.get("id") or data.get("Id") or data.get("OrderId")
            if not shs_id:
                continue
            db.upsert_order({
                "shs_order_id": str(shs_id),
                "type": data.get("type") or "imported",
                "status": (data.get("status") or "in_work").lower(),
                "customer_main": data.get("customer") or data.get("client"),
                "customer_phone": data.get("phone") or data.get("telephone"),
                "departure_date": data.get("departure_date") or data.get("date_from"),
                "return_date": data.get("return_date") or data.get("date_to"),
                "destination": data.get("destination") or data.get("country"),
                "hotel_name": data.get("hotel"),
                "meal": data.get("meal"),
                "room_type": data.get("room_type"),
                "nights": int(data.get("nights")) if (data.get("nights") or "").isdigit() else None,
                "gross_amount": _safe_float(data.get("amount") or data.get("price")),
                "currency": data.get("currency") or config.AGENCY_CURRENCY,
                "agent": _actor(),
                "payload": json.dumps(data, ensure_ascii=False),
            })
            imported += 1
    except ET.ParseError as e:
        return _json_error(f"xml parse error: {e}", 502)
    db.audit(_actor(), "orders.report_import", details={"imported": imported})
    return jsonify({"imported": imported})


def _safe_float(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None


# ============================ API: customers ============================

@app.route("/api/customers", methods=["GET", "POST"])
def customers():
    if request.method == "POST":
        p = _body()
        if not p.get("name") or not p.get("surname"):
            return _json_error("name and surname required")
        cid = db.create_customer({
            "category": p.get("category", "Mr"),
            "name": p["name"].upper(),
            "surname": p["surname"].upper(),
            "birth_date": p.get("birth_date", ""),
            "nationality": (p.get("nationality") or config.DEFAULT_NATIONALITY).upper(),
            "idn": p.get("idn", ""),
            "telephone": p.get("telephone", ""),
            "email": p.get("email", ""),
            "passport_nr": p.get("passport_nr", ""),
            "passport_expiry": p.get("passport_expiry", ""),
            "notes": p.get("notes", ""),
        })
        db.audit(_actor(), "customers.create", target=str(cid))
        return jsonify(db.get_customer(cid))
    q = request.args.get("q")
    return jsonify({"items": db.list_customers(q)})


@app.route("/api/customers/<int:cid>", methods=["GET", "PUT", "DELETE"])
def customer(cid):
    if request.method == "GET":
        c = db.get_customer(cid)
        if not c: return _json_error("not found", 404)
        return jsonify(c)
    if request.method == "DELETE":
        db.delete_customer(cid)
        db.audit(_actor(), "customers.delete", target=str(cid))
        return jsonify({"ok": True})
    p = _body()
    db.update_customer(cid, {k: v for k, v in p.items() if k in {
        "category", "name", "surname", "birth_date", "nationality", "idn",
        "telephone", "email", "passport_nr", "passport_expiry", "notes",
    }})
    db.audit(_actor(), "customers.update", target=str(cid))
    return jsonify(db.get_customer(cid))


# ============================ API: quotes ============================

@app.route("/api/quotes", methods=["GET", "POST"])
def quotes():
    if request.method == "POST":
        p = _body()
        qid = db.create_quote({
            "customer_id": p.get("customer_id"),
            "customer_main": p.get("customer_main"),
            "customer_phone": p.get("customer_phone"),
            "title": p.get("title", "Ofertă turistică"),
            "summary": p.get("summary"),
            "options": p.get("options"),
            "status": p.get("status", "open"),
            "sale_amount": p.get("sale_amount"),
            "currency": p.get("currency", config.AGENCY_CURRENCY),
            "agent": _actor(),
        })
        db.audit(_actor(), "quotes.create", target=str(qid))
        return jsonify(db.get_quote(qid))
    return jsonify({"items": db.list_quotes(request.args.get("status"))})


@app.route("/api/quotes/<int:qid>", methods=["GET", "PUT", "DELETE"])
def quote(qid):
    if request.method == "GET":
        q = db.get_quote(qid)
        if not q: return _json_error("not found", 404)
        return jsonify(q)
    if request.method == "DELETE":
        db.delete("quotes", qid)
        db.audit(_actor(), "quotes.delete", target=str(qid))
        return jsonify({"ok": True})
    p = _body()
    db.update_quote(qid, {k: v for k, v in p.items() if k in {
        "title", "summary", "options", "status", "sale_amount", "currency",
        "customer_main", "customer_phone",
    }})
    db.audit(_actor(), "quotes.update", target=str(qid))
    return jsonify(db.get_quote(qid))


@app.route("/api/quotes/<int:qid>/html")
def quote_html(qid):
    q = db.get_quote(qid)
    if not q: return _json_error("not found", 404)
    return render_template("quote_print.html", quote=q, agency=config.AGENCY_NAME, today=date.today())


# ============================ API: saved searches ============================

@app.route("/api/saved-searches", methods=["GET", "POST"])
def saved_searches():
    if request.method == "POST":
        p = _body()
        sid = db.save_search(p["name"], p["kind"], p.get("params", {}))
        return jsonify({"id": sid})
    return jsonify({"items": db.list_saved_searches(request.args.get("kind"))})


@app.route("/api/saved-searches/<int:sid>", methods=["DELETE"])
def saved_search(sid):
    db.delete("saved_searches", sid)
    return jsonify({"ok": True})


# ============================ API: reports / analytics ============================

@app.route("/api/reports/summary")
def report_summary():
    rows = db.fetch_all("""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(sale_amount),0) AS revenue,
            COALESCE(SUM(CASE WHEN status='confirmed' OR status='confirmed_print' THEN sale_amount ELSE 0 END),0) AS confirmed_revenue,
            COALESCE(AVG(sale_amount),0) AS avg_ticket
        FROM orders
    """)
    by_status = db.fetch_all("SELECT status, COUNT(*) AS cnt, COALESCE(SUM(sale_amount),0) AS revenue FROM orders GROUP BY status")
    by_destination = db.fetch_all("""
        SELECT destination, COUNT(*) AS cnt, COALESCE(SUM(sale_amount),0) AS revenue
        FROM orders WHERE destination IS NOT NULL AND destination != ''
        GROUP BY destination ORDER BY cnt DESC LIMIT 20
    """)
    by_hotel = db.fetch_all("""
        SELECT hotel_name, COUNT(*) AS cnt, COALESCE(SUM(sale_amount),0) AS revenue
        FROM orders WHERE hotel_name IS NOT NULL AND hotel_name != ''
        GROUP BY hotel_name ORDER BY cnt DESC LIMIT 20
    """)
    by_month = db.fetch_all("""
        SELECT substr(date(created_at, 'unixepoch'), 1, 7) AS month,
               COUNT(*) AS cnt, COALESCE(SUM(sale_amount),0) AS revenue
        FROM orders GROUP BY month ORDER BY month DESC LIMIT 12
    """)
    return jsonify({
        "summary": rows[0] if rows else {},
        "by_status": by_status,
        "by_destination": by_destination,
        "by_hotel": by_hotel,
        "by_month": by_month,
    })


@app.route("/api/audit")
def audit():
    items = db.fetch_all("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 200")
    return jsonify({"items": items})


# ============================ API: settings ============================

@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        p = _body()
        for k, v in p.items():
            db.set_setting(k, str(v))
        return jsonify({"ok": True})
    keys = ["default_markup_percent", "default_nationality", "default_lang", "agent_name"]
    return jsonify({k: db.get_setting(k) for k in keys})


# ============================ enrichment helpers ============================

def _decorate_hotel_results(data: dict, params: dict) -> dict:
    if not isinstance(data, dict):
        return {"raw": data}
    markup = float(params.get("markup_percent") or config.DEFAULT_MARKUP_PERCENT)
    for hotel in data.get("hotels", []) or []:
        for room in hotel.get("rooms", []) or []:
            try:
                gross = float(room.get("price") or room.get("net_price") or 0)
                room["sale_price"] = round(gross * (1 + markup / 100.0), 2)
            except Exception:
                pass
    return data


def _decorate_package_results(data: dict, params: dict) -> dict:
    """Compute two display values per result:
       - net_shs:  what the agency pays SHS (cost)             = API net_amount
       - brut_zebra: what the client pays Zebra Tur (retail)   = API gross_amount + optional markup
    """
    if not isinstance(data, dict):
        return {"raw": data}
    markup = float(params.get("markup_percent") or 0)
    prices = data.get("prices", []) or []
    for price in prices:
        try:
            net = float(price.get("net_amount") or 0)
            gross = float(price.get("gross_amount") or 0)
            brut_zebra = round(gross * (1 + markup / 100.0), 2)
            price["net_shs"] = round(net, 2)
            price["brut_zebra"] = brut_zebra
            price["agent_profit"] = round(brut_zebra - net, 2)
            # backwards-compat (used in older UI parts)
            price["sale_amount"] = brut_zebra
            price["shs_commission"] = round(gross - net, 2)
        except Exception:
            pass
    # Enrich with hotel photos and city names via a single batched /hotel/search call
    hotel_ids = list({p.get("hotel_id") for p in prices if p.get("hotel_id")})
    if hotel_ids and prices:
        try:
            sample = prices[0]
            adults = int(params.get("adults", 2))
            check_in = sample.get("check_in") or ""
            check_out = sample.get("check_out") or ""
            nights = int(sample.get("nights") or params.get("from_nights", 7))
            hotel_data = client.search_hotels(
                adults=adults,
                children=[],
                from_date=check_in or (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                to_date=check_in or (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                from_nights=nights,
                to_nights=nights,
                hotel_ids=hotel_ids,
                with_description=True,
                show_stops=True,
            )
            meta = {}
            for h in (hotel_data or {}).get("hotels", []) or []:
                hid = h.get("hotel_id")
                if not hid:
                    continue
                photos = h.get("photos") or []
                default_photo = h.get("default_photo") or (photos[0] if photos else "")
                if default_photo and not str(default_photo).startswith("http"):
                    default_photo = f"{config.SHS_FILES_BASE_URL}/{default_photo}"
                meta[hid] = {
                    "default_photo": default_photo,
                    "city": h.get("city"),
                    "country": h.get("country"),
                    "star": h.get("star"),
                }
            for p in prices:
                m = meta.get(p.get("hotel_id"))
                if m:
                    if not p.get("default_photo"):
                        p["default_photo"] = m["default_photo"]
                    if not p.get("city"):
                        p["city"] = m["city"]
                    if not p.get("country"):
                        p["country"] = m["country"]
                    if not p.get("star"):
                        p["star"] = m["star"]
        except Exception as exc:
            log.warning("photo enrichment failed: %s", exc)
    return data


def _decorate_transport(items) -> list[dict]:
    if not isinstance(items, list):
        return items
    return items


# ============================ static / 404 ============================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return _json_error("not found", 404)
    return render_template("404.html", agency=config.AGENCY_NAME), 404


@app.errorhandler(500)
def server_error(e):
    log.exception("server error")
    if request.path.startswith("/api/"):
        return _json_error("internal server error", 500)
    return render_template("500.html", agency=config.AGENCY_NAME), 500


if __name__ == "__main__":
    log.info("ZebraTur-SHS starting on %s:%s", config.HOST, config.PORT)
    log.info("SHS base: %s", config.SHS_BASE_URL)
    log.info("DB: %s", config.DB_PATH)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
