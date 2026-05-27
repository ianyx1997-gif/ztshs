# 🦓 ZebraTur SHS Integration

Software intern complet pentru agenția **Zebra Tur**, care simplifică maximal interacțiunea cu tour operatorul **SHS** (API Proxymo / shsbooking.com).

Acoperă **toate funcțiile** oferite de integrarea SHS: căutare pachete, hoteluri, transport (charter), excursii și transferuri; rezervare; gestionarea comenzilor; mesaje; rapoarte XML; bază de clienți; oferte; analize și jurnal de acțiuni.

---

## 🚀 Pornire rapidă

```bash
cd "/Users/ianyx/Desktop/api shs/zebra-shs"
./start.sh
```

Apoi deschide în browser: **http://127.0.0.1:5050**

> Prima dată va instala automat dependențele (`flask`, `requests`).

---

## 📁 Structură

```
zebra-shs/
├── app.py            ← server Flask, toate route-urile
├── shs_client.py     ← client API SHS (wrapper complet)
├── database.py       ← SQLite (clienți, comenzi, oferte, jurnal)
├── config.py         ← configurare (credențiale, port, markup)
├── templates/        ← interfața (HTML + Alpine.js + Tailwind)
├── static/           ← CSS și JS comun
├── data/             ← bază de date SQLite (creată automat)
├── start.sh          ← launcher
├── .env.example      ← model de configurare
└── requirements.txt
```

---

## 🧩 Funcționalități

### 🔍 Căutare unificată
- **Pachete** (Hotel + Transport + Transfer) cu toți parametrii SHS: țară, tip pachet, terminal de plecare, nopți, mese, stele, facilități, hoteluri, orașe
- **Hoteluri only** — selectare directă, multiple, filtre meal, descrieri
- **Transport** (charter) — KIV/RMO către orice destinație, dus/întors separat, perioadă tour
- **Excursii** — descoperire prin țară/program/plecare, două moduri: doar excursie sau pachet complet cu transport
- **Transferuri** — punct-la-punct cu preferințe (grup/individual/VIP)

### 💼 Rezervare
- Formular complet pentru pasageri (Mr/Mrs/Ch + Infant)
- Câmpurile cerute de SHS: Categorie, Nume, Prenume, Data nașterii, Vârsta, Cetățenie, IDNP, Telefon, Email, Viză, Pașaport (nr. + expirare)
- **Reutilizare din baza de clienți** — caută și inserează cu un click
- Aplicare automată markup% configurat (calculează preț de vânzare)
- Salvare automată locală pentru audit + sincronizare ulterioară

### 📋 Comenzi
- Listă cu filtre (status, dată, text liber)
- Detalii complete + jurnal mesaje
- **Sincronizare status** (apel `/remote_order/get_status` în masă)
- **Import raport XML** (apel `/book/report/xml/{token}/{date_range}/{status}`)
- **Trimitere mesaje** către SHS (`/remote_order/create_message`)
- **Schimbare status** (apel `/book/bundle_request/remote_update_order`)
- Mapare status numeric SHS → label uman (in_work, confirmed, canceled etc.)

### 👥 Clienți
- CRUD complet cu căutare după nume/telefon/email
- Pașaport, IDNP, cetățenie
- Reutilizare instant în formularul de rezervare

### 💼 Oferte (Quotes)
- Creare ofertă din rezultate de căutare (buton „+ Ofertă")
- Status: deschisă / trimisă / câștigată / pierdută
- **Tipărire / Export PDF** — pagină dedicată cu brand Zebra Tur

### 📊 Rapoarte
- KPI: total comenzi, venit estimat, venit confirmat, ticket mediu
- Evoluție lunară
- Distribuție statusuri (bars)
- Top destinații și top hoteluri (după volum și revenue)
- Jurnal acțiuni (audit log) — cine ce a făcut

### ⚙️ Setări
- Markup implicit %
- Cetățenie implicită (default: MOLDOVA)
- Limbă (RO/RU/EN)
- Verificare conexiune SHS

### 🔄 Căutări salvate
- Salvează combinații de filtre des folosite (ex: „Bulgaria Burgas iulie ALL ≥3*")
- Restaurare cu un click

---

## 🔌 Endpoint-urile SHS folosite

Toate endpoint-urile documentate de SHS sunt acoperite în [shs_client.py](shs_client.py):

| Categorie | Endpoint SHS | Folosit pentru |
|-----------|--------------|----------------|
| Auth | `POST /auth/get_jwt_token` | Auto-refresh token (TTL 55 min) |
| Geo | `GET /country/country_list`, `GET /city/city_list`, `GET /transport/get_terminals` | Dropdown-uri |
| Hoteluri | `GET /hotel/facilities`, `/hotel/category_list`, `/hotel/meal_list`, `POST /hotel/hotel_list`, `POST /hotel/search` | Cataloage + căutare |
| Transport | `POST /transport/search`, `POST /transport/check_flights`, `POST /v2/transport/available_dates` | Charter dus/întors |
| Pachete | `GET /packages/package_list`, `POST /packages/search`, `GET /packages/pricing_page` | Pachete + paginare |
| Excursii | `/excursions/countries`, `/excursions/departures`, `/excursions/programs`, `/excursions/list`, `/excursions/dates`, `/excursions/search`, `/excursions/check_price` | Toate cele 7 endpoint-uri |
| Transfer | `POST /transfer/search` | Transferuri |
| Booking | `POST /booking/save_booking`, `POST /remote_order/create` | Rezervare pachet & transport |
| Comenzi | `POST /remote_order/get_status`, `POST /remote_order/create_message`, `POST /book/bundle_request/remote_update_order`, `GET /book/report/xml/{...}` | Status, mesaje, update, raport |

---

## 🔐 Configurare credențiale

Editează fișierul `.env` (creează-l din `.env.example`):

```
SHS_USERNAME=ianyx1997@gmail.com
SHS_PASSWORD=aRxHghmAQH5Fdolr7kdMwNPMtpOFdM
SHS_REPORT_TOKEN=aRxHghmAQH5Fdolr7kdMwNPMtpOFdM
```

> **Notă:** dacă autentificarea eșuează cu credențialele furnizate, contactează managerul tău SHS pentru parola corectă. Indicatorul de status SHS din colțul dreapta-sus al interfeței arată stadiul conexiunii în timp real.

---

## 🛠️ Tehnologii

- **Backend:** Python 3.9+ · Flask · SQLite
- **Frontend:** Tailwind CSS (CDN) · Alpine.js (CDN) · Vanilla JS
- **Stocare:** SQLite local (`data/zebra.db`) cu schemă WAL pentru performanță
- **HTTP:** `requests` cu pooling (Session) + retry automat la expirarea JWT

Zero build step. Zero dependențe complicate. Funcționează offline (mai puțin apelurile către SHS).

---

## 📚 Note operaționale

- **JWT** este obținut la prima cerere și păstrat 55 min (sub TTL-ul de 60 min al SHS). Refresh automat la 401.
- **SQLite WAL** permite citiri paralele cu scrieri — sigur pentru mai mulți agenți care folosesc simultan.
- **Audit log** înregistrează fiecare căutare, rezervare, schimbare status — vezi pagina Rapoarte.
- **Cache directorii** (țări, terminale, mese) — 30 min, reduce apelurile inutile către SHS.
- **Markup** se aplică pe `gross_amount` și se afișează automat în rezultate; configurabil per căutare sau global.

---

## 🆘 Probleme frecvente

**„SHS OFFLINE" în bara de sus**
- Verifică credențialele din `.env`
- Click pe badge pentru re-testare
- Verifică `Settings → Conexiune SHS`

**Nu apar rezultate la căutare**
- API-ul SHS poate returna 0 rezultate pentru filtre stricte — relaxează (mai multe nopți, mai multe mese acceptate)
- Verifică data de plecare (trebuie să fie în viitor)

**Rezervarea returnează eroare**
- Cei mai mulți pasageri trebuie Nume + Prenume; cetățenie obligatorie
- Pașaportul e necesar pentru destinații cu viză

---

🦓 **Zebra Tur** · Construit pentru agenții care vor să rezerve repede, fără click-uri inutile.
