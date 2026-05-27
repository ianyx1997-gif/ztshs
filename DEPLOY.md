# 🚀 Deploy pe Railway · Ghid pas cu pas

## Pregătire (5 min)

### 1. Cont pe Railway
- Mergi la **https://railway.app** și creează cont (poți folosi GitHub login)
- Vei primi **5$ credit gratuit/lună** — suficient pentru un proiect mic

### 2. Pregătește proiectul local pentru git
```bash
cd "/Users/ianyx/Desktop/api shs/zebra-shs"
git init
git add .
git commit -m "Initial commit"
```

### 3. Creează repo pe GitHub (opțional, dar recomandat)
- Mergi la https://github.com/new
- Numele: `zebra-tur-shs` (sau ce vrei)
- **Private** (pentru că include cod proprietate)
- Apoi:
```bash
git remote add origin git@github.com:USERNAME/zebra-tur-shs.git
git push -u origin main
```

---

## Deploy pe Railway (10 min)

### Opțiunea A: Din GitHub (cel mai simplu, recomandat)

1. Pe Railway → **New Project** → **Deploy from GitHub repo**
2. Selectează repo-ul `zebra-tur-shs`
3. Railway detectează automat Flask și începe build
4. **Setări → Variables** — adaugă manual:
   ```
   SHS_USERNAME=ianyx1997@gmail.com
   SHS_PASSWORD=aRxHghmAQH5Fdolr7kdMwNPMtpOFdM
   SHS_REPORT_TOKEN=aRxHghmAQH5Fdolr7kdMwNPMtpOFdM
   RESEND_API_KEY=re_NmbHN67g_CroQSKJPk94e6wqpT77NT6sJ
   NOTIFY_EMAIL=ianyx1997@gmail.com
   B2B_USERNAME=admin
   B2B_PASSWORD=schimbă-mă-cu-ceva-greu-de-ghicit
   SECRET_KEY=schimbă-cu-string-random-lung
   PUBLIC_BASE_URL=https://NUME-PROIECT.up.railway.app
   CORS_ALLOWED_ORIGINS=https://zebratur.md,https://www.zebratur.md
   ```
5. **Setări → Networking → Generate Domain** — primești ceva gen `zebra-tur-shs-production.up.railway.app`
6. Re-deploy (Railway re-build cu noile env vars)

### Opțiunea B: Direct cu Railway CLI

```bash
npm install -g @railway/cli
railway login
cd "/Users/ianyx/Desktop/api shs/zebra-shs"
railway init
railway up
```

---

## După deploy

### Test rapid
- Vizitează `https://NUME.up.railway.app/turist` → trebuie să fie public
- Vizitează `https://NUME.up.railway.app/` → te redirectează la `/login`
- Login cu `admin` / parola pusă în `B2B_PASSWORD`

### Domeniu propriu (opțional)
Dacă vrei `tour.zebratur.md` în loc de `*.railway.app`:
1. Railway → **Setări → Networking → Custom Domain** → adaugă `tour.zebratur.md`
2. La registrarul DNS al `zebratur.md` adaugă un record:
   ```
   CNAME  tour  →  NUME.up.railway.app
   ```
3. Așteaptă 5-30 min pentru propagare DNS
4. Update `PUBLIC_BASE_URL=https://tour.zebratur.md` în env vars

---

## 🧩 Embed pe zebratur.md/bulgaria

Pune codul de mai jos oriunde în pagina ta HTML / WordPress / CMS:

```html
<!-- Începe widget Zebra Tur -->
<div id="zebra-tur-widget"></div>
<script src="https://NUME.up.railway.app/widget.js" async></script>
<!-- Sfârșit widget -->
```

Widget-ul:
- creează automat un `<iframe>` în div-ul `#zebra-tur-widget`
- ascunde headerul și footerul nostru (mode `?embed=1`)
- se auto-ajustează ca înălțime în funcție de conținut (prin `postMessage`)
- folosește fontul Inter din Google Fonts, fără conflict cu stilurile site-ului tău

**În WordPress:** folosește un block HTML (Gutenberg → „HTML personalizat") sau plugin tip „Insert Headers and Footers".

**Pe Tilda:** block T123 (HTML cod).

**Pe Wix/Squarespace:** widget Embed → HTML.

---

## 📊 Limitări tier gratuit Railway

- **5$ credit/lună** — la trafic mic (sub 100 vizite/zi) e suficient
- **Sleep după inactivitate** — proiectul se „adoarme" după ~5 min fără cereri și se trezește la prima cerere (adaugă ~3 sec la prima vizită). Pentru a evita, upgradează la $5/lună plan Hobby.
- **Date efemeră** — baza SQLite se resetează la fiecare redeploy. Pentru date persistente:
  - **Plan Hobby ($5/lună)** → mount un Volume la `/app/data`
  - SAU migrează la PostgreSQL (Railway oferă gratis în plan dedicat)

Pentru MVP / lansare: tier gratuit e perfect. Dacă vrei date persistente garantat, plan Hobby.

---

## 🐛 Troubleshooting

**Build eșuează** → verifică logs în Railway, probabil lipsește o dependență din `requirements.txt`

**„Application failed to respond"** → verifică că `Procfile` are linia corectă cu `--bind 0.0.0.0:$PORT`

**SHS OFFLINE după deploy** → verifică env vars `SHS_USERNAME` și `SHS_PASSWORD` în Railway

**Widget nu se afișează** → verifică în Network tab al browser-ului dacă `widget.js` se încarcă; verifică `CORS_ALLOWED_ORIGINS` include domeniul tău

**Email nu ajunge** → verifică folder spam; pentru a folosi domeniu propriu (`rezervari@zebratur.md`), verifică domeniul pe https://resend.com/domains

---

🦓 **Zebra Tur** — Made with ♥️
