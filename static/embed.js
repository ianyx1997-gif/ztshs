/**
 * Zebra Tur — Inline embed widget (no iframe)
 * Injects search UI directly into the host page, keeps the parent URL.
 * Usage:
 *   <div id="zebra-tur-widget"></div>
 *   <script src="https://YOUR.up.railway.app/embed-config.js"></script>
 *   <script src="https://YOUR.up.railway.app/embed.js" async></script>
 */
(function() {
  'use strict';

  // ============ CONFIG ============
  var API = (typeof window !== 'undefined' && window.ZEBRA_TUR_API)
    ? window.ZEBRA_TUR_API
    : (function() {
        // Derive from current script src
        var scripts = document.getElementsByTagName('script');
        for (var i = scripts.length - 1; i >= 0; i--) {
          var s = scripts[i].src;
          if (s && s.indexOf('/embed.js') >= 0) {
            return s.replace(/\/embed\.js.*$/, '');
          }
        }
        return '';
      })();

  var CONTAINER_ID = 'zebra-tur-widget';

  // ============ I18N ============
  var I18N = {
    ro: {
      heroTitle: 'Vacanța ta în Bulgaria începe aici',
      heroSubtitle: 'Plajă, soare și hoteluri de top — la cele mai bune prețuri',
      tripBus: 'Pachet cu autocar', tripBusDesc: 'Transport Chișinău ⇄ Bulgaria + cazare + asigurare + transfer',
      tripSelf: 'Doar cazare', tripSelfDesc: 'Doar hotelul — transportul îl asiguri tu',
      labelDates: '📅 Plecare în perioada', labelNights: '🌙 Nopți', labelTourists: '👥 Turiști',
      labelMeal: '🍽️ Tip masă', labelStars: '⭐ Categorie hotel', labelResort: '📍 Stațiune', labelFacilities: '✨ Facilități',
      adults: 'Adulți', adultsHint: '12+ ani', children: 'Copii', childrenHint: '0-12 ani',
      childAge: 'Vârsta copilului', years: 'ani', done: 'Gata',
      allResorts: 'Toate stațiunile din Bulgaria',
      searching: 'Se caută cele mai bune oferte...', search: '🔍 Caută vacanța mea',
      offersFound: 'oferte găsite', offerFound: 'ofertă găsită', noOffers: '🔍 Nu am găsit oferte. Modifică filtrele și încearcă din nou.',
      sortAsc: '💰 Preț crescător', sortDesc: '💎 Preț descrescător', sortStars: '⭐ Stele',
      forPax: 'pentru',
      mealBreakfast: '☕ Mic dejun', mealHB: '🥐 Demi-pensiune', mealFB: '🍴 Full Board', mealAI: '🍽️ All Inclusive', mealUltra: '🍾 Ultra All',
      facFirstLine: '🏖️ Prima linie', facPool: '🏊 Piscină', facAqua: '💦 Aquapark', facBeach: '⛱️ Plajă', facAdult: '🔞 Adult Only', facWifi: '📶 Wi-Fi', facParking: '🅿️ Parcare',
      details: 'Vezi →',
      backToSearch: '← Înapoi la căutare',
      save: '🤍 Salvează', saved: '❤️ Salvat', copyLink: '🔗 Copiază link', reserveTemp: '⚡ Rezervare temporară',
      roomsTitle: '🛏️ Camere și prețuri disponibile',
      roomCol: 'Cameră / Masă',
      tapPrice: 'Apasă pe preț pentru rezervare temporară. Prețurile sunt pentru',
      reserve: 'Rezervă temporar',
      loading: '⏳ Se încarcă...',
      aboutHotel: '📝 Despre hotel', mapLocation: '📍 Pe hartă',
      reserveTitle: '🎉 Rezervare temporară',
      reserveDesc: 'Un agent te va contacta în maxim 2 ore.',
      yourName: 'Numele tău complet', phone: 'Telefon', phonePh: '+373 69 ...',
      msgAgent: 'Mesaj pentru agent (opțional)', msgPh: 'ex: cameră cu vedere la mare',
      cancel: 'Anulează', sendReserve: '✅ Trimite rezervarea temporară', sending: 'Se trimite...',
      missingFields: 'Completează numele și telefonul',
      reserveSent: '🎉 Rezervare trimisă! #',
      favTitle: '❤️ Favoritele mele', favNone: 'Nicio favorită încă', favNoneSub: 'Apasă pe inima 🤍 de la orice tur ca să-l salvezi aici.',
      favCopyAll: '📋 Copiază toate', favWhatsApp: '💬 WhatsApp', favClearAll: '🗑️',
      favConfirmClear: 'Ștergi toate favoritele?',
      favSaved: '❤️ Salvat la favorite!', favRemoved: '💔 Eliminat din favorite',
      copied: '✅ Copiat!', linkCopied: '🔗 Link copiat!',
      noRoomsAvailable: 'Nu sunt camere disponibile pentru rezervare',
      ztOffers: 'oferte', contact: 'Contact',
      // Months for date formatting
      // (we use ISO dates, native input handles display)
    },
    ru: {
      heroTitle: 'Ваш отдых в Болгарии начинается здесь',
      heroSubtitle: 'Пляж, солнце и лучшие отели — по лучшим ценам',
      tripBus: 'Пакет с автобусом', tripBusDesc: 'Транспорт Кишинев ⇄ Болгария + проживание + страховка + трансфер',
      tripSelf: 'Только проживание', tripSelfDesc: 'Только отель — транспорт ваш',
      labelDates: '📅 Период вылета', labelNights: '🌙 Ночи', labelTourists: '👥 Туристы',
      labelMeal: '🍽️ Тип питания', labelStars: '⭐ Категория отеля', labelResort: '📍 Курорт', labelFacilities: '✨ Удобства',
      adults: 'Взрослые', adultsHint: '12+ лет', children: 'Дети', childrenHint: '0-12 лет',
      childAge: 'Возраст ребёнка', years: 'лет', done: 'Готово',
      allResorts: 'Все курорты Болгарии',
      searching: 'Ищем лучшие предложения...', search: '🔍 Найти отдых',
      offersFound: 'предложений найдено', offerFound: 'предложение найдено', noOffers: '🔍 Предложений не найдено. Измените фильтры и попробуйте снова.',
      sortAsc: '💰 Цена по возрастанию', sortDesc: '💎 Цена по убыванию', sortStars: '⭐ Звёзды',
      forPax: 'для',
      mealBreakfast: '☕ Завтрак', mealHB: '🥐 Полупансион', mealFB: '🍴 Полный пансион', mealAI: '🍽️ Всё включено', mealUltra: '🍾 Ультра всё включено',
      facFirstLine: '🏖️ Первая линия', facPool: '🏊 Бассейн', facAqua: '💦 Аквапарк', facBeach: '⛱️ Пляж', facAdult: '🔞 Adult Only', facWifi: '📶 Wi-Fi', facParking: '🅿️ Парковка',
      details: 'Подробнее →',
      backToSearch: '← Назад к поиску',
      save: '🤍 Сохранить', saved: '❤️ Сохранено', copyLink: '🔗 Копировать ссылку', reserveTemp: '⚡ Предварительное бронирование',
      roomsTitle: '🛏️ Доступные номера и цены',
      roomCol: 'Номер / Питание',
      tapPrice: 'Нажмите на цену для предварительного бронирования. Цены указаны для',
      reserve: 'Забронировать',
      loading: '⏳ Загрузка...',
      aboutHotel: '📝 Об отеле', mapLocation: '📍 На карте',
      reserveTitle: '🎉 Предварительное бронирование',
      reserveDesc: 'Агент свяжется с вами в течение 2 часов.',
      yourName: 'Ваше полное имя', phone: 'Телефон', phonePh: '+373 69 ...',
      msgAgent: 'Сообщение агенту (необязательно)', msgPh: 'например: номер с видом на море',
      cancel: 'Отмена', sendReserve: '✅ Отправить заявку', sending: 'Отправка...',
      missingFields: 'Заполните имя и телефон',
      reserveSent: '🎉 Заявка отправлена! №',
      favTitle: '❤️ Избранное', favNone: 'Пока нет избранных', favNoneSub: 'Нажмите на сердечко 🤍 у любого тура, чтобы сохранить здесь.',
      favCopyAll: '📋 Скопировать все', favWhatsApp: '💬 WhatsApp', favClearAll: '🗑️',
      favConfirmClear: 'Удалить все избранные?',
      favSaved: '❤️ Добавлено в избранное!', favRemoved: '💔 Удалено из избранного',
      copied: '✅ Скопировано!', linkCopied: '🔗 Ссылка скопирована!',
      noRoomsAvailable: 'Нет доступных номеров для бронирования',
      ztOffers: 'предложений', contact: 'Контакт',
    }
  };

  // Detect language: query param, data attribute, URL path, or default
  function detectLang() {
    try {
      // 1. ?lang=ru in current URL
      var sp = new URLSearchParams(location.search);
      if (sp.get('lang') && I18N[sp.get('lang')]) return sp.get('lang');
      // 2. data-lang on container
      var c = document.getElementById(CONTAINER_ID);
      if (c && c.dataset && c.dataset.lang && I18N[c.dataset.lang]) return c.dataset.lang;
      // 3. window.ZEBRA_TUR_LANG global
      if (window.ZEBRA_TUR_LANG && I18N[window.ZEBRA_TUR_LANG]) return window.ZEBRA_TUR_LANG;
      // 4. URL path contains /ru/ or /ru$
      if (/\/ru(\/|$)/.test(location.pathname)) return 'ru';
      // 5. <html lang="ru">
      var hl = (document.documentElement.lang || '').toLowerCase();
      if (hl.indexOf('ru') === 0) return 'ru';
    } catch (e) {}
    return 'ro';
  }
  var LANG = detectLang();
  function t(key) {
    var dict = I18N[LANG] || I18N.ro;
    return dict[key] || I18N.ro[key] || key;
  }

  // ============ STATE ============
  var S = {
    cities: [], packages: [], facilities: [],
    selectedPackage: null,
    filters: {
      tripType: 'bus', cityId: '',
      dateFrom: defaultDate(3), dateTo: defaultDate(10),
      nights: 7, adults: 2, children: [],
      mealIds: [6, 20], starIds: [5, 6], facilityIds: [],
    },
    results: null, loading: false, sortBy: 'price_asc',
    view: 'search',  // search | hotel
    hotel: null, hotelRooms: [], hotelPhotoIdx: 0,
    favorites: loadFavs(),
    reserveOpen: false, reserveOffer: null,
    favOpen: false,
    paxOpen: false,
  };

  // ============ HELPERS ============
  function defaultDate(d) { var x = new Date(); x.setDate(x.getDate() + d); return x.toISOString().slice(0,10); }
  function formatMoney(n) { if (n==null) return '—'; return Math.round(n).toLocaleString('ro-RO') + ' €'; }
  function formatMoneyShort(n) { if (n==null) return '—'; return Math.round(n) + '€'; }
  function formatDate(s) { if (!s) return '—'; try { var p = s.split('-'); return p[2]+'.'+p[1]+'.'+p[0]; } catch(e) { return s; } }
  function formatDateShort(s) { if (!s) return '—'; try { var p = s.split('-'); return p[2]+'.'+p[1]; } catch(e) { return s; } }
  function dayShort(s) { return dayShortLang(s); }
  function mealHuman(m) {
    if (!m) return '—';
    if (LANG === 'ru') {
      var ruMap = {'ALL INCLUSIVE':'🍽️ Всё включено','AI':'🍽️ Всё включено','ULTRA ALL':'🍾 Ультра всё включено',
        'PREMIUM ALL':'💎 Премиум всё включено','AI LIGHT':'🍽️ All Light','ALL LIGHT':'🍽️ All Light',
        'BB':'☕ Завтрак','BED AND BREAKFAST':'☕ Завтрак',
        'HB':'🥐 Полупансион','HALF BOARD':'🥐 Полупансион',
        'FB':'🍴 Полный пансион','FULL BOARD':'🍴 Полный пансион',
        'RO':'🛏️ Только проживание','ROOM ONLY':'🛏️ Только проживание'};
      return ruMap[m] || m;
    }
    var map = {'ALL INCLUSIVE':'🍽️ All Inclusive','AI':'🍽️ All Inclusive','ULTRA ALL':'🍾 Ultra All Inclusive',
      'PREMIUM ALL':'💎 Premium All','AI LIGHT':'🍽️ All Light','ALL LIGHT':'🍽️ All Light',
      'BB':'☕ Mic dejun','HB':'🥐 HB','FB':'🍴 FB','RO':'🛏️ Doar cazare'};
    return map[m] || m;
  }
  function roomHuman(r) {
    if (!r) return '—';
    if (LANG === 'ru') return r.replace(/DBL\b/gi,'Двухместный').replace(/SGL\b/gi,'Одноместный').replace(/TPL\b/gi,'Трёхместный').replace(/STUDIO/gi,'Студия');
    return r.replace(/DBL\b/gi,'Dublă').replace(/SGL\b/gi,'Single').replace(/TPL\b/gi,'Triplă');
  }
  function cityHuman(s) { if(!s) return ''; return s.split(' ').map(function(w){return w.charAt(0)+w.slice(1).toLowerCase();}).join(' '); }
  function esc(s) { if(s==null) return ''; return String(s).replace(/[&<>"']/g, function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
  function loadFavs() { try { return JSON.parse(localStorage.getItem('zt-favorites') || '[]'); } catch(e) { return []; } }
  function saveFavs() { try { localStorage.setItem('zt-favorites', JSON.stringify(S.favorites)); } catch(e) {} }
  function isFav(o) { return S.favorites.some(function(f){ return f.price_id === o.price_id; }); }

  function api(path, body) {
    var opts = { method: body ? 'POST' : 'GET', headers: { 'Accept':'application/json' } };
    if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    return fetch(API + path, opts).then(function(r){ return r.json(); });
  }

  function toast(text, kind) {
    var el = document.createElement('div');
    el.className = 'zt-toast' + (kind ? ' zt-toast-' + kind : '');
    el.textContent = text;
    document.body.appendChild(el);
    setTimeout(function(){ el.classList.add('zt-fade'); setTimeout(function(){ el.remove(); }, 300); }, 3000);
  }

  // ============ HASH ROUTING ============
  // URL format on parent: #zt:hotel=12345&in=2026-06-03&out=2026-06-10&n=7&a=2&t=self&p=87
  function readHash() {
    var h = location.hash;
    if (!h.indexOf('#zt:') === 0) return null;
    var raw = h.slice(4);
    var params = {};
    raw.split('&').forEach(function(p){
      var kv = p.split('=');
      if (kv.length === 2) params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1]);
    });
    return params;
  }
  function writeHash(params) {
    if (!params) { history.replaceState(null, '', location.pathname + location.search); return; }
    var pairs = [];
    Object.keys(params).forEach(function(k){ pairs.push(encodeURIComponent(k)+'='+encodeURIComponent(params[k])); });
    history.replaceState(null, '', location.pathname + location.search + '#zt:' + pairs.join('&'));
  }

  // ============ STYLES ============
  var STYLES = `
    /* Override host theme CSS that might hide the widget */
    #zebra-tur-widget {
      display: block !important;
      visibility: visible !important;
      opacity: 1 !important;
      height: auto !important;
      min-height: 600px !important;
      max-height: none !important;
      width: 100% !important;
      overflow: visible !important;
      position: relative !important;
      z-index: 1 !important;
      clip: auto !important;
      clip-path: none !important;
    }
    #zebra-tur-widget > .zt-app {
      display: block !important;
      visibility: visible !important;
      opacity: 1 !important;
      width: 100% !important;
      max-width: 1280px !important;
      margin: 0 auto !important;
      padding: 16px !important;
    }
    #zebra-tur-widget .zt-app * {
      visibility: visible !important;
    }
    .zt-app { font-family: Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif; color: #0b1020; }
    .zt-app *, .zt-app *::before, .zt-app *::after { box-sizing: border-box; }
    .zt-card { background: #fff; border-radius: 18px; box-shadow: 0 4px 24px rgba(13,16,42,0.08); padding: 20px; }
    .zt-grid { display: grid; gap: 12px; }
    .zt-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .zt-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 8px 16px; border-radius: 8px; border: 2px solid transparent; font-weight: 600; font-size: 14px; cursor: pointer; transition: all 0.15s; font-family: inherit; }
    .zt-btn-primary { background: linear-gradient(90deg, #f97316, #ea580c); color: white; }
    .zt-btn-primary:hover { background: linear-gradient(90deg, #ea580c, #c2410c); }
    .zt-btn-secondary { background: #f1f5f9; color: #475569; border-color: #e2e8f0; }
    .zt-btn-secondary:hover { background: #e2e8f0; }
    .zt-btn-brand { background: #3a48d0; color: white; }
    .zt-btn-brand:hover { background: #2f38aa; }
    .zt-input, .zt-select { width: 100%; padding: 10px 12px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 14px; font-weight: 500; background: white; color: #0b1020; font-family: inherit; }
    .zt-input:focus, .zt-select:focus { outline: none; border-color: #3a48d0; }
    .zt-label { display: block; font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .zt-chip { display: inline-flex; align-items: center; padding: 6px 12px; border-radius: 999px; border: 2px solid #e2e8f0; background: white; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s; user-select: none; font-family: inherit; }
    .zt-chip:hover { border-color: #cbd5e1; }
    .zt-chip-active { background: #3a48d0; color: white; border-color: #3a48d0; }
    .zt-chip-meal-active { background: #3a48d0; color: white; border-color: #3a48d0; }
    .zt-chip-star-active { background: #f59e0b; color: white; border-color: #f59e0b; }
    .zt-chip-fac-active { background: #059669; color: white; border-color: #059669; }
    .zt-chip-warn { background: #fff1f2; color: #be123c; border-color: #fda4af; }
    .zt-chip-warn-active { background: #f43f5e; color: white; border-color: #f43f5e; }
    .zt-radio-card { flex: 1; padding: 14px; border: 2px solid #e2e8f0; border-radius: 14px; cursor: pointer; transition: all 0.15s; display: flex; gap: 10px; align-items: center; min-width: 200px; }
    .zt-radio-card:hover { border-color: #c7d2fe; }
    .zt-radio-card-active { background: #eef2ff; border-color: #3a48d0; }
    .zt-trip-icon { font-size: 28px; }
    .zt-trip-title { font-weight: 700; font-size: 15px; }
    .zt-trip-desc { font-size: 11px; color: #64748b; margin-top: 2px; }
    .zt-hero { background: linear-gradient(135deg, rgba(13,16,42,0.55), rgba(13,16,42,0.7)), url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=2000&q=80') center/cover; color: white; padding: 32px 24px; border-radius: 18px; margin-bottom: 16px; }
    .zt-hero h1 { font-size: 28px; font-weight: 800; margin: 0 0 6px; line-height: 1.2; }
    .zt-hero p { font-size: 15px; opacity: 0.85; margin: 0; }
    .zt-results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
    .zt-hotel-card { background: white; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); transition: box-shadow 0.2s, transform 0.2s; cursor: pointer; }
    .zt-hotel-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.12); }
    .zt-hotel-photo { position: relative; aspect-ratio: 4/3; background: #e2e8f0; overflow: hidden; }
    .zt-hotel-photo img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s; }
    .zt-hotel-card:hover .zt-hotel-photo img { transform: scale(1.05); }
    .zt-badge-star { position: absolute; top: 10px; left: 10px; background: rgba(255,255,255,0.95); color: #d97706; font-weight: 700; padding: 3px 8px; border-radius: 999px; font-size: 13px; backdrop-filter: blur(4px); }
    .zt-fav-btn { position: absolute; top: 10px; right: 10px; width: 38px; height: 38px; background: rgba(255,255,255,0.95); border: 0; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: transform 0.15s; }
    .zt-fav-btn:hover { transform: scale(1.1); }
    .zt-hotel-body { padding: 12px 14px; }
    .zt-hotel-name { font-weight: 700; font-size: 15px; line-height: 1.3; margin-bottom: 4px; color: #0b1020; }
    .zt-hotel-name:hover { color: #3a48d0; }
    .zt-hotel-meta { font-size: 12px; color: #64748b; }
    .zt-hotel-meta-row { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
    .zt-hotel-footer { display: flex; align-items: flex-end; justify-content: space-between; margin-top: 10px; padding-top: 10px; border-top: 1px solid #f1f5f9; }
    .zt-price-pax { font-size: 11px; color: #64748b; }
    .zt-price { font-size: 24px; font-weight: 800; color: #3a48d0; line-height: 1; }
    .zt-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 999999; display: flex; align-items: center; justify-content: center; padding: 20px; overflow-y: auto; }
    .zt-modal-body { background: white; border-radius: 18px; max-width: 1000px; width: 100%; margin: auto; max-height: calc(100vh - 40px); overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
    .zt-modal-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 20px; border-bottom: 1px solid #f1f5f9; position: sticky; top: 0; background: white; z-index: 2; border-radius: 18px 18px 0 0; }
    .zt-modal-close { background: none; border: 0; cursor: pointer; font-size: 28px; color: #94a3b8; line-height: 1; padding: 0 4px; font-family: inherit; }
    .zt-modal-close:hover { color: #475569; }
    .zt-modal-footer { padding: 18px 20px; border-top: 1px solid #f1f5f9; background: #f8fafc; border-radius: 0 0 18px 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
    .zt-photo-stage { position: relative; background: #0b1020; border-radius: 14px; overflow: hidden; aspect-ratio: 16/9; }
    .zt-photo-stage img { width: 100%; height: 100%; object-fit: contain; }
    .zt-photo-nav { position: absolute; top: 50%; transform: translateY(-50%); background: rgba(255,255,255,0.85); border: 0; border-radius: 50%; width: 44px; height: 44px; cursor: pointer; font-size: 22px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
    .zt-photo-nav-l { left: 12px; }
    .zt-photo-nav-r { right: 12px; }
    .zt-photo-counter { position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); color: white; padding: 4px 12px; border-radius: 999px; font-size: 13px; }
    .zt-photo-thumbs { display: flex; gap: 6px; overflow-x: auto; padding: 10px 0; margin: 0 -2px; }
    .zt-photo-thumb { width: 80px; height: 60px; flex-shrink: 0; border-radius: 6px; overflow: hidden; cursor: pointer; opacity: 0.7; transition: all 0.15s; }
    .zt-photo-thumb:hover { opacity: 1; }
    .zt-photo-thumb-active { opacity: 1; outline: 3px solid #3a48d0; outline-offset: -3px; }
    .zt-photo-thumb img { width: 100%; height: 100%; object-fit: cover; }
    .zt-matrix { width: 100%; border-collapse: collapse; font-size: 13px; }
    .zt-matrix th { text-align: left; padding: 8px; border-bottom: 2px solid #e2e8f0; font-weight: 700; color: #334155; }
    .zt-matrix th.zt-matrix-date { text-align: center; min-width: 90px; }
    .zt-matrix-date-day { font-size: 11px; color: #94a3b8; font-weight: 500; }
    .zt-matrix td { padding: 4px 4px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    .zt-matrix td.zt-matrix-room { padding: 10px 8px; }
    .zt-matrix-row:hover { background: #f8fafc; }
    .zt-matrix-meal { display: inline-block; padding: 2px 6px; background: #d1fae5; color: #065f46; font-size: 10px; font-weight: 700; border-radius: 4px; margin-bottom: 4px; }
    .zt-matrix-roomname { font-weight: 600; font-size: 13px; line-height: 1.2; }
    .zt-matrix-placement { font-size: 11px; color: #94a3b8; }
    .zt-matrix-price { width: 100%; background: #eef2ff; color: #3a48d0; font-weight: 800; padding: 8px 4px; border: 0; border-radius: 8px; cursor: pointer; font-size: 13px; transition: all 0.15s; font-family: inherit; }
    .zt-matrix-price:hover { background: #f97316; color: white; }
    .zt-matrix-price-rezerva { display: block; font-size: 10px; font-weight: 500; opacity: 0.7; margin-top: 2px; }
    .zt-empty-cell { color: #cbd5e1; text-align: center; font-size: 16px; }
    .zt-spinner { display: inline-block; animation: zt-spin 0.8s linear infinite; }
    @keyframes zt-spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
    .zt-toast { position: fixed; bottom: 24px; right: 24px; background: #0b1020; color: white; padding: 12px 18px; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); z-index: 9999999; transition: opacity 0.3s; font-size: 14px; font-family: inherit; }
    .zt-toast.zt-fade { opacity: 0; }
    .zt-toast-success { background: #16a34a; }
    .zt-toast-error { background: #dc2626; }
    .zt-fav-fab { position: fixed; left: 20px; bottom: 20px; width: 60px; height: 60px; background: linear-gradient(135deg, #ec4899, #e11d48); color: white; border: 0; border-radius: 50%; cursor: pointer; font-size: 28px; box-shadow: 0 8px 24px rgba(225,29,72,0.4); z-index: 9998; display: flex; align-items: center; justify-content: center; transition: transform 0.15s; }
    .zt-fav-fab:hover { transform: scale(1.1); }
    .zt-fav-fab-badge { position: absolute; top: -4px; right: -4px; background: white; color: #e11d48; border: 2px solid #e11d48; border-radius: 50%; width: 26px; height: 26px; font-size: 12px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
    .zt-fav-panel { position: fixed; left: 0; top: 0; bottom: 0; width: 100%; max-width: 480px; background: white; box-shadow: 8px 0 32px rgba(0,0,0,0.2); z-index: 9999; overflow-y: auto; transform: translateX(-100%); transition: transform 0.3s; }
    .zt-fav-panel.zt-open { transform: translateX(0); }
    .zt-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9998; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
    .zt-overlay.zt-open { opacity: 1; pointer-events: auto; }
    .zt-fav-row { display: flex; gap: 12px; padding: 12px; border: 2px solid #f1f5f9; border-radius: 14px; margin-bottom: 8px; }
    .zt-fav-row:hover { border-color: #fecdd3; background: #fff1f2; }
    .zt-fav-img { width: 88px; height: 88px; flex-shrink: 0; background: #e2e8f0; border-radius: 10px; overflow: hidden; }
    .zt-fav-img img { width: 100%; height: 100%; object-fit: cover; }
    .zt-search-form { display: block; }
    .zt-cell-dates { margin-bottom: 10px; }
    .zt-date-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
    .zt-date-grid > .zt-input { min-width: 0; width: 100%; }
    .zt-dual-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .zt-radio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
    @media (min-width: 720px) {
      .zt-search-form { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 12px; align-items: end; }
      .zt-cell-dates { margin-bottom: 0; }
      .zt-dual-grid { display: contents; }
    }
    .zt-photo-stage { touch-action: pan-y; user-select: none; -webkit-user-select: none; }
    @media (max-width: 720px) {
      #zebra-tur-widget > .zt-app { padding: 8px !important; }
      .zt-hero h1 { font-size: 20px; }
      .zt-hero { padding: 16px 12px; border-radius: 12px; }
      .zt-hero p { font-size: 13px; }
      .zt-card { padding: 12px; border-radius: 12px; }
      .zt-results-grid { grid-template-columns: 1fr; gap: 10px; }
      .zt-modal { padding: 8px; }
      .zt-modal-body { border-radius: 12px; }
      .zt-modal-header { padding: 14px; }
      .zt-modal-footer { padding: 12px 14px; }

      /* Trip type cards stack vertically */
      .zt-radio-grid { grid-template-columns: 1fr; gap: 8px; }
      .zt-radio-card { min-width: 0; padding: 12px; }
      .zt-trip-icon { font-size: 24px; }
      .zt-trip-title { font-size: 14px; }
      .zt-trip-desc { font-size: 11px; }

      .zt-input, .zt-select { padding: 9px 8px; font-size: 13px; }
      .zt-label { font-size: 10px; margin-bottom: 4px; }

      /* Chips: compact but tappable */
      .zt-chip { padding: 6px 10px; font-size: 12px; }
      .zt-btn { padding: 8px 14px; font-size: 14px; }

      /* Hotel cards */
      .zt-hotel-name { font-size: 14px; }
      .zt-price { font-size: 20px; }

      /* Matrix: smaller cells */
      .zt-matrix th, .zt-matrix td { padding: 4px 2px; font-size: 11px; }
      .zt-matrix th.zt-matrix-date { min-width: 60px; }
      .zt-matrix-roomname { font-size: 12px; }
      .zt-matrix-price { padding: 6px 2px; font-size: 12px; }

      /* FAB smaller on mobile, doesn't cover content */
      .zt-fav-fab { width: 52px; height: 52px; font-size: 22px; left: 14px; bottom: 14px; }
      .zt-fav-fab-badge { width: 22px; height: 22px; font-size: 11px; }

      /* Pax dropdown panel — narrower */
      .zt-pax-panel { width: calc(100vw - 32px) !important; max-width: 280px; }
    }
    @media (max-width: 380px) {
      .zt-hero h1 { font-size: 18px; }
      .zt-input, .zt-select { font-size: 12px; padding: 8px 6px; }
    }
  `;

  // ============ TEMPLATES ============
  function tplSearchPage() {
    var nightsWord = LANG === 'ru' ? ' ночей' : ' nopți';
    return `
      <div class="zt-hero">
        <h1>${t('heroTitle')}</h1>
        <p>${t('heroSubtitle')}</p>
      </div>
      <div class="zt-card" style="margin-bottom:16px;">
        <div class="zt-radio-grid">
          <button class="zt-radio-card ${S.filters.tripType==='bus'?'zt-radio-card-active':''}" data-action="trip" data-value="bus">
            <div class="zt-trip-icon">🚌</div>
            <div><div class="zt-trip-title">${t('tripBus')} ${S.filters.tripType==='bus'?'<span style="color:#3a48d0">✓</span>':''}</div><div class="zt-trip-desc">${t('tripBusDesc')}</div></div>
          </button>
          <button class="zt-radio-card ${S.filters.tripType==='self'?'zt-radio-card-active':''}" data-action="trip" data-value="self">
            <div class="zt-trip-icon">🚗</div>
            <div><div class="zt-trip-title">${t('tripSelf')} ${S.filters.tripType==='self'?'<span style="color:#3a48d0">✓</span>':''}</div><div class="zt-trip-desc">${t('tripSelfDesc')}</div></div>
          </button>
        </div>

        <div class="zt-search-form">
          <div class="zt-cell-dates">
            <label class="zt-label">${t('labelDates')}</label>
            <div class="zt-date-grid">
              <input type="date" class="zt-input" data-action="filter" data-key="dateFrom" value="${esc(S.filters.dateFrom)}">
              <input type="date" class="zt-input" data-action="filter" data-key="dateTo" value="${esc(S.filters.dateTo)}">
            </div>
          </div>
          <div class="zt-dual-grid">
            <div>
              <label class="zt-label">${t('labelNights')}</label>
              <select class="zt-select" data-action="filter" data-key="nights">
                ${[1,2,3,4,5,6,7,8,9,10,11,12,13,14].map(function(n){
                  return '<option value="'+n+'"'+(S.filters.nights===n?' selected':'')+'>'+n+nightsWord+'</option>';
                }).join('')}
              </select>
            </div>
            <div style="position:relative;">
              <label class="zt-label">${t('labelTourists')}</label>
              <button class="zt-select" style="text-align:left;cursor:pointer;" data-action="paxToggle">
                ${paxLabel()} <span style="float:right;color:#94a3b8;">▾</span>
              </button>
              ${S.paxOpen ? tplPaxPanel() : ''}
            </div>
          </div>
        </div>

        <div style="border-top:1px solid #f1f5f9;padding-top:14px;">
          <div style="margin-bottom:12px;">
            <div class="zt-label">${t('labelMeal')}</div>
            <div class="zt-row" style="gap:6px;">
              ${[{id:7,l:t('mealBreakfast')},{id:8,l:t('mealHB')},{id:13,l:t('mealFB')},{id:6,l:t('mealAI')},{id:20,l:t('mealUltra')}].map(function(m){
                var on = S.filters.mealIds.indexOf(m.id) >= 0;
                return '<button class="zt-chip '+(on?'zt-chip-meal-active':'')+'" data-action="meal" data-value="'+m.id+'">'+m.l+'</button>';
              }).join('')}
            </div>
          </div>
          <div style="margin-bottom:12px;">
            <div class="zt-label">${t('labelStars')}</div>
            <div class="zt-row" style="gap:6px;">
              ${[{id:7,l:'⭐⭐⭐',w:true},{id:5,l:'⭐⭐⭐⭐'},{id:6,l:'⭐⭐⭐⭐⭐'}].map(function(s){
                var on = S.filters.starIds.indexOf(s.id) >= 0;
                var cls = s.w ? (on?'zt-chip-warn-active':'zt-chip-warn') : (on?'zt-chip-star-active':'');
                return '<button class="zt-chip '+cls+'" data-action="star" data-value="'+s.id+'">'+s.l+'</button>';
              }).join('')}
            </div>
          </div>
          <div style="margin-bottom:12px;">
            <div class="zt-label">${t('labelResort')}</div>
            <select class="zt-select" style="max-width:400px;" data-action="filter" data-key="cityId">
              <option value="">${t('allResorts')}</option>
              ${S.cities.map(function(c){ return '<option value="'+c.id+'"'+(String(S.filters.cityId)===String(c.id)?' selected':'')+'>'+esc(c.name)+'</option>'; }).join('')}
            </select>
          </div>
          <div style="margin-bottom:14px;">
            <div class="zt-label">${t('labelFacilities')}</div>
            <div class="zt-row" style="gap:6px;">
              ${[{id:39,l:t('facFirstLine')},{id:21,l:t('facPool')},{id:33,l:t('facAqua')},{id:8,l:t('facBeach')},{id:41,l:t('facAdult')},{id:24,l:t('facWifi')},{id:27,l:t('facParking')}].map(function(f){
                var on = S.filters.facilityIds.indexOf(f.id) >= 0;
                return '<button class="zt-chip '+(on?'zt-chip-fac-active':'')+'" data-action="fac" data-value="'+f.id+'">'+f.l+'</button>';
              }).join('')}
            </div>
          </div>
        </div>

        <button class="zt-btn zt-btn-primary" style="width:100%;padding:14px;font-size:16px;" data-action="search">
          ${S.loading ? '<span class="zt-spinner">⏳</span> ' + t('searching') : t('search')}
        </button>
      </div>

      ${tplResults()}
    `;
  }

  function tplPaxPanel() {
    return `
      <div class="zt-pax-panel" style="position:absolute;right:0;top:100%;margin-top:6px;background:white;border:2px solid #e2e8f0;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.12);padding:14px;z-index:10;width:280px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div><div style="font-weight:600;">${t('adults')}</div><div style="font-size:11px;color:#64748b;">${t('adultsHint')}</div></div>
          <div class="zt-row" style="gap:6px;">
            <button class="zt-chip" data-action="adults" data-value="-1" style="width:32px;height:32px;padding:0;border-radius:50%;border-color:#3a48d0;color:#3a48d0;">−</button>
            <span style="width:24px;text-align:center;font-weight:700;">${S.filters.adults}</span>
            <button class="zt-chip" data-action="adults" data-value="1" style="width:32px;height:32px;padding:0;border-radius:50%;border-color:#3a48d0;color:#3a48d0;">+</button>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div><div style="font-weight:600;">${t('children')}</div><div style="font-size:11px;color:#64748b;">${t('childrenHint')}</div></div>
          <div class="zt-row" style="gap:6px;">
            <button class="zt-chip" data-action="child" data-value="-1" style="width:32px;height:32px;padding:0;border-radius:50%;border-color:#3a48d0;color:#3a48d0;">−</button>
            <span style="width:24px;text-align:center;font-weight:700;">${S.filters.children.length}</span>
            <button class="zt-chip" data-action="child" data-value="1" style="width:32px;height:32px;padding:0;border-radius:50%;border-color:#3a48d0;color:#3a48d0;">+</button>
          </div>
        </div>
        ${S.filters.children.map(function(age, i){
          return '<div style="display:flex;justify-content:space-between;margin-bottom:6px;align-items:center;"><span style="font-size:13px;">'+t('childAge')+' '+(i+1)+'</span><select class="zt-select" style="width:90px;" data-action="childage" data-idx="'+i+'">'+[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17].map(function(a){return '<option value="'+a+'"'+(age===a?' selected':'')+'>'+a+' '+t('years')+'</option>';}).join('')+'</select></div>';
        }).join('')}
        <button class="zt-btn zt-btn-brand" style="width:100%;margin-top:6px;" data-action="paxClose">${t('done')}</button>
      </div>
    `;
  }

  function tplResults() {
    if (!S.results) return '';
    var prices = (S.results.prices || []).slice();
    var stars = function(s){ return parseInt(((s||'').match(/\d+/)||[0])[0]); };
    prices.sort(function(a,b){
      if (S.sortBy === 'price_asc') return (a.brut_zebra||a.gross_amount||0) - (b.brut_zebra||b.gross_amount||0);
      if (S.sortBy === 'price_desc') return (b.brut_zebra||b.gross_amount||0) - (a.brut_zebra||a.gross_amount||0);
      if (S.sortBy === 'star_desc') return stars(b.star) - stars(a.star);
      return 0;
    });
    if (!prices.length) {
      return '<div class="zt-card" style="text-align:center;padding:40px;color:#64748b;">' + t('noOffers') + '</div>';
    }
    var label = prices.length === 1 ? t('offerFound') : t('offersFound');
    return `
      <div class="zt-row" style="justify-content:space-between;margin-bottom:12px;">
        <h2 style="margin:0;font-size:20px;font-weight:700;">${prices.length} ${label}</h2>
        <select class="zt-select" style="width:auto;" data-action="sort">
          <option value="price_asc"${S.sortBy==='price_asc'?' selected':''}>${t('sortAsc')}</option>
          <option value="price_desc"${S.sortBy==='price_desc'?' selected':''}>${t('sortDesc')}</option>
          <option value="star_desc"${S.sortBy==='star_desc'?' selected':''}>${t('sortStars')}</option>
        </select>
      </div>
      <div class="zt-results-grid">
        ${prices.map(tplHotelCard).join('')}
      </div>
    `;
  }

  function tplHotelCard(o) {
    var photoSrc = o.default_photo || '';
    return `
      <div class="zt-hotel-card" data-action="openHotel" data-hotel="${esc(o.hotel_id)}" data-priceid="${esc(o.price_id)}">
        <div class="zt-hotel-photo">
          ${photoSrc ? '<img src="'+esc(photoSrc)+'" loading="lazy" onerror="this.style.display=&quot;none&quot;">' : '<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:48px;">🏨</div>'}
          <div class="zt-badge-star">${esc(o.star || '')}</div>
          <button class="zt-fav-btn" data-action="toggleFav" data-priceid="${esc(o.price_id)}" data-stop="1" aria-label="Favorite">
            ${isFav(o) ? '❤️' : '🤍'}
          </button>
        </div>
        <div class="zt-hotel-body">
          <div class="zt-hotel-name">${esc(o.hotel_name)}</div>
          <div class="zt-hotel-meta">📍 ${esc(o.city || 'Bulgaria')}</div>
          <div class="zt-hotel-meta">
            <div class="zt-hotel-meta-row">📅 ${formatDate(o.check_in)} → ${formatDate(o.check_out)}</div>
            <div class="zt-hotel-meta-row">🌙 ${o.nights} ${LANG==='ru'?'ночей':'nopți'} · 🍽️ ${esc(mealHuman(o.meal))}</div>
          </div>
          <div class="zt-hotel-footer">
            <div>
              <div class="zt-price-pax">${paxLabel(true)}</div>
              <div class="zt-price">${formatMoney(o.brut_zebra || o.gross_amount)}</div>
            </div>
            <button class="zt-btn zt-btn-primary" data-action="openHotel" data-hotel="${esc(o.hotel_id)}" data-priceid="${esc(o.price_id)}" data-stop="1" style="padding:6px 12px;font-size:13px;">${t('details')}</button>
          </div>
        </div>
      </div>
    `;
  }

  function tplHotelPage() {
    var h = S.hotel;
    return `
      <button class="zt-btn zt-btn-secondary" style="margin-bottom:14px;" data-action="backToSearch">${t('backToSearch')}</button>
      ${h ? tplHotelHeader(h) : '<div class="zt-card" style="text-align:center;padding:40px;">'+t('loading')+'</div>'}
      ${h ? tplHotelGallery(h) : ''}
      ${h ? tplHotelRooms() : ''}
      ${h && h.description ? '<div class="zt-card" style="margin-top:16px;"><h2 style="margin:0 0 12px;font-size:18px;">'+t('aboutHotel')+'</h2><div style="font-size:14px;line-height:1.6;">' + h.description + '</div></div>' : ''}
      ${h && h.map_frame ? '<div class="zt-card" style="margin-top:16px;"><h2 style="margin:0 0 12px;font-size:18px;">'+t('mapLocation')+'</h2><div style="border-radius:10px;overflow:hidden;">' + h.map_frame + '</div></div>' : ''}
    `;
  }

  function tplHotelHeader(h) {
    return `
      <div class="zt-card" style="margin-bottom:14px;">
        <div class="zt-row" style="justify-content:space-between;align-items:flex-start;">
          <div style="flex:1;min-width:200px;">
            <h1 style="margin:0;font-size:26px;font-weight:800;">${esc(h.hotel_name)} <span style="color:#d97706;">${esc(h.star || '')}</span></h1>
            <div style="color:#64748b;font-size:14px;margin-top:4px;">📍 ${esc(h.city || '')}, ${esc(h.country || 'Bulgaria')}</div>
          </div>
          <div class="zt-row" style="gap:6px;flex-wrap:wrap;">
            <button class="zt-btn zt-btn-secondary" data-action="toggleFavHotel">${isFavHotel() ? t('saved') : t('save')}</button>
            <button class="zt-btn zt-btn-secondary" data-action="shareLink">${t('copyLink')}</button>
            <button class="zt-btn zt-btn-primary" data-action="reserveCheapest">${t('reserveTemp')}</button>
          </div>
        </div>
      </div>
    `;
  }
  function isFavHotel() {
    if (!S.hotel) return false;
    return S.favorites.some(function(f){ return f.hotel_id === S.hotel.hotel_id; });
  }

  function tplHotelGallery(h) {
    var photos = h.photos || [];
    if (!photos.length) return '';
    var idx = S.hotelPhotoIdx;
    return `
      <div class="zt-card" style="margin-bottom:14px;">
        <div class="zt-photo-stage">
          <img src="${esc(photos[idx])}" alt="Foto hotel">
          ${photos.length > 1 ? '<button class="zt-photo-nav zt-photo-nav-l" data-action="photoPrev">‹</button><button class="zt-photo-nav zt-photo-nav-r" data-action="photoNext">›</button><div class="zt-photo-counter">'+(idx+1)+' / '+photos.length+'</div>' : ''}
        </div>
        ${photos.length > 1 ? '<div class="zt-photo-thumbs">'+photos.map(function(p, i){
          return '<div class="zt-photo-thumb '+(i===idx?'zt-photo-thumb-active':'')+'" data-action="photoGoto" data-idx="'+i+'"><img src="'+esc(p)+'" loading="lazy" onerror="this.style.display=&quot;none&quot;"></div>';
        }).join('')+'</div>' : ''}
      </div>
    `;
  }

  function tplHotelRooms() {
    if (!S.hotelRooms.length) {
      return '<div class="zt-card" style="text-align:center;padding:30px;color:#64748b;">'+t('loading')+'</div>';
    }
    // Pivot: rooms × dates
    var datesSet = {};
    var groups = {};
    S.hotelRooms.forEach(function(r){
      datesSet[r.check_in] = true;
      var k = r.meal + '__' + r.room_type + '__' + r.placement;
      if (!groups[k]) groups[k] = { key:k, meal:r.meal, room_type:r.room_type, placement:r.placement, prices:{} };
      var p = r.brut_zebra || r.gross_amount || 0;
      var ex = groups[k].prices[r.check_in];
      if (!ex || (ex.brut_zebra||ex.gross_amount||Infinity) > p) groups[k].prices[r.check_in] = r;
    });
    var dates = Object.keys(datesSet).sort();
    var groupList = Object.keys(groups).map(function(k){ return groups[k]; }).sort(function(a,b){
      var minA = Math.min.apply(null, Object.keys(a.prices).map(function(d){ return a.prices[d].brut_zebra||a.prices[d].gross_amount||Infinity; }));
      var minB = Math.min.apply(null, Object.keys(b.prices).map(function(d){ return b.prices[d].brut_zebra||b.prices[d].gross_amount||Infinity; }));
      return minA - minB;
    });
    return `
      <div class="zt-card" style="margin-bottom:14px;">
        <h2 style="margin:0 0 12px;font-size:18px;">${t('roomsTitle')}</h2>
        <div style="overflow-x:auto;">
          <table class="zt-matrix">
            <thead><tr>
              <th>${t('roomCol')}</th>
              ${dates.map(function(d){ return '<th class="zt-matrix-date"><div class="zt-matrix-date-day">'+dayShort(d)+'</div>'+formatDateShort(d)+'</th>'; }).join('')}
            </tr></thead>
            <tbody>
              ${groupList.map(function(g){
                return '<tr class="zt-matrix-row"><td class="zt-matrix-room"><span class="zt-matrix-meal">'+esc(mealHuman(g.meal))+'</span><div class="zt-matrix-roomname">'+esc(roomHuman(g.room_type))+'</div><div class="zt-matrix-placement">'+esc(g.placement)+'</div></td>'+
                  dates.map(function(d){
                    var p = g.prices[d];
                    if (!p) return '<td><div class="zt-empty-cell">—</div></td>';
                    return '<td><button class="zt-matrix-price" data-action="reserve" data-priceid="'+esc(p.price_id)+'">'+formatMoneyShort(p.brut_zebra||p.gross_amount)+'<span class="zt-matrix-price-rezerva">'+t('reserve')+'</span></button></td>';
                  }).join('') +
                  '</tr>';
              }).join('')}
            </tbody>
          </table>
        </div>
        <div style="font-size:11px;color:#94a3b8;margin-top:8px;">${t('tapPrice')} ${paxLabel(true)}.</div>
      </div>
    `;
  }

  function tplReserveModal(offer) {
    var nightsW = LANG==='ru' ? 'ночей' : 'nopți';
    return `
      <div class="zt-modal" data-action="closeReserve">
        <div class="zt-modal-body" style="max-width:560px;" onclick="event.stopPropagation()">
          <div class="zt-modal-header">
            <div><h3 style="margin:0;font-size:22px;font-weight:800;">${t('reserveTitle')}</h3><div style="font-size:13px;color:#64748b;margin-top:4px;">${t('reserveDesc')}</div></div>
            <button class="zt-modal-close" data-action="closeReserve">×</button>
          </div>
          <div style="padding:20px;">
            <div style="background:#eef2ff;padding:12px 14px;border-radius:10px;margin-bottom:16px;font-size:14px;">
              <div style="font-weight:700;color:#3a48d0;">${esc(offer.hotel_name || (S.hotel && S.hotel.hotel_name) || '')} <span style="color:#d97706;">${esc(offer.star || (S.hotel && S.hotel.star) || '')}</span></div>
              <div>📍 ${esc(offer.city || (S.hotel && S.hotel.city) || 'Bulgaria')} · ${esc(mealHuman(offer.meal))}</div>
              <div>📅 ${formatDate(offer.check_in)} → ${formatDate(offer.check_out)} (${offer.nights} ${nightsW})</div>
              <div style="font-size:20px;font-weight:800;color:#3a48d0;margin-top:6px;">${formatMoney(offer.brut_zebra||offer.gross_amount)}</div>
            </div>
            <div style="margin-bottom:12px;">
              <label class="zt-label">${t('yourName')} *</label>
              <input id="zt-resv-name" type="text" class="zt-input" placeholder="${LANG==='ru'?'например: Иван Иванов':'ex: Ion Popescu'}">
            </div>
            <div style="margin-bottom:12px;">
              <label class="zt-label">${t('phone')} *</label>
              <input id="zt-resv-phone" type="tel" class="zt-input" placeholder="${t('phonePh')}">
            </div>
            <div style="margin-bottom:12px;">
              <label class="zt-label">${t('msgAgent')}</label>
              <textarea id="zt-resv-notes" class="zt-input" rows="3" placeholder="${t('msgPh')}"></textarea>
            </div>
          </div>
          <div class="zt-modal-footer">
            <button class="zt-btn zt-btn-secondary" data-action="closeReserve">${t('cancel')}</button>
            <button class="zt-btn zt-btn-primary" data-action="submitReserve">${t('sendReserve')}</button>
          </div>
        </div>
      </div>
    `;
  }

  function tplFavoritesPanel() {
    if (!S.favorites.length) {
      return '<div style="padding:50px 20px;text-align:center;"><div style="font-size:60px;">🤍</div><h3 style="margin:10px 0 4px;">Nicio favorită încă</h3><div style="color:#64748b;font-size:13px;">Apasă pe inima 🤍 de la orice tur ca să-l salvezi aici.</div></div>';
    }
    return `
      <div style="padding:12px;background:#f8fafc;border-bottom:1px solid #e2e8f0;display:flex;flex-wrap:wrap;gap:6px;">
        <button class="zt-btn zt-btn-brand" data-action="copyAllFavs">📋 Copiază toate</button>
        <button class="zt-btn" style="background:#16a34a;color:white;" data-action="shareWhatsApp">💬 WhatsApp</button>
        <button class="zt-btn zt-btn-secondary" style="margin-left:auto;color:#dc2626;" data-action="clearFavs">🗑️</button>
      </div>
      <div style="padding:12px;">
        ${S.favorites.map(function(f){
          return '<div class="zt-fav-row"><div class="zt-fav-img">'+
            (f.default_photo ? '<img src="'+esc(f.default_photo)+'" loading="lazy" onerror="this.style.display=&quot;none&quot;">' : '')+
            '</div><div style="flex:1;min-width:0;"><div style="font-weight:700;">'+esc(f.hotel_name)+' '+esc(f.star||'')+'</div>'+
            '<div style="font-size:12px;color:#64748b;">📍 '+esc(f.city||'')+'</div>'+
            '<div style="font-size:12px;margin-top:4px;">📅 '+formatDate(f.check_in)+' → '+formatDate(f.check_out)+' ('+(f.nights||'?')+'n)</div>'+
            '<div style="font-size:12px;color:#64748b;">🍽️ '+esc(mealHuman(f.meal))+' · '+esc(roomHuman(f.room_type))+'</div>'+
            '<div class="zt-row" style="justify-content:space-between;margin-top:6px;"><div style="font-size:18px;font-weight:800;color:#3a48d0;">'+formatMoney(f.brut_zebra||f.gross_amount)+'</div>'+
            '<div class="zt-row" style="gap:4px;"><button class="zt-btn zt-btn-secondary" style="padding:4px 8px;font-size:11px;" data-action="copyFav" data-priceid="'+esc(f.price_id)+'">📋 Copiază</button>'+
            '<button class="zt-btn zt-btn-primary" style="padding:4px 10px;font-size:11px;" data-action="openHotel" data-hotel="'+esc(f.hotel_id)+'">Vezi →</button>'+
            '<button class="zt-btn" style="padding:4px 8px;font-size:11px;color:#dc2626;background:#fef2f2;" data-action="removeFav" data-priceid="'+esc(f.price_id)+'">×</button></div></div></div></div>';
        }).join('')}
      </div>
    `;
  }

  function paxLabel(short) {
    var a = S.filters.adults, c = S.filters.children.length;
    if (LANG === 'ru') {
      var adultsW = a === 1 ? 'взрослый' : 'взрослых';
      var childW = c === 1 ? 'ребёнок' : 'детей';
      return a + ' ' + adultsW + (c ? (short ? ', ' : ' + ') + c + ' ' + childW : '');
    }
    return a + ' adult' + (a===1?'':'i') + (c ? (short?', ':' + ') + c + ' copil' + (c===1?'':'i') : '');
  }
  function dayShortLang(s) {
    if (!s) return '';
    try {
      var d = new Date(s);
      if (LANG === 'ru') return ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'][d.getDay()];
      return ['Du','Lu','Ma','Mi','Jo','Vi','Sâ'][d.getDay()];
    } catch(e) { return ''; }
  }

  // ============ ACTIONS ============
  function setFilter(key, value) {
    if (key === 'cityId') S.filters.cityId = value;
    else if (key === 'dateFrom' || key === 'dateTo') S.filters[key] = value;
    else if (key === 'nights') S.filters.nights = parseInt(value) || 7;
    render();
  }
  function toggleCascade(arr, id, order) {
    var idx = order.indexOf(id);
    var i = arr.indexOf(id);
    if (i >= 0) { arr.splice(i, 1); }
    else {
      for (var j = idx; j < order.length; j++) {
        if (arr.indexOf(order[j]) < 0) arr.push(order[j]);
      }
    }
  }
  function toggleMeal(id) { toggleCascade(S.filters.mealIds, id, [7,8,13,6,20]); render(); }
  function toggleStar(id) { toggleCascade(S.filters.starIds, id, [7,5,6]); render(); }
  function toggleFacility(id) {
    var i = S.filters.facilityIds.indexOf(id);
    if (i>=0) S.filters.facilityIds.splice(i,1); else S.filters.facilityIds.push(id);
    render();
  }
  function adjustAdults(d) { S.filters.adults = Math.max(1, Math.min(9, S.filters.adults + d)); render(); }
  function adjustChild(d) {
    if (d > 0 && S.filters.children.length < 4) S.filters.children.push(5);
    if (d < 0) S.filters.children.pop();
    render();
  }
  function setChildAge(idx, age) { S.filters.children[idx] = parseInt(age); }
  function setTrip(t) { S.filters.tripType = t; render(); }

  function pickPackage() {
    if (!S.packages.length) return null;
    var has = function(p) { var args = Array.prototype.slice.call(arguments, 1); return Array.isArray(p.content) && args.every(function(c){ return p.content.indexOf(c) >= 0; }); };
    if (S.filters.tripType === 'bus') {
      return S.packages.filter(function(p){ return has(p, 'transport', 'hotel'); })[0] ||
             S.packages.filter(function(p){ return has(p, 'transport'); })[0] || S.packages[0];
    } else {
      return S.packages.filter(function(p){ return Array.isArray(p.content) && p.content.length === 1 && p.content[0] === 'hotel'; })[0] ||
             S.packages.filter(function(p){ return has(p, 'hotel') && p.content.indexOf('transport') < 0; })[0] || S.packages[0];
    }
  }

  async function doSearch() {
    var pkg = pickPackage();
    if (!pkg) { toast('Pachetele nu s-au încărcat. Reîncarcă.', 'error'); return; }
    S.loading = true; S.results = null; render();
    var terminalId = (S.filters.tripType === 'bus' && pkg.departure_terminals && pkg.departure_terminals.length) ? pkg.departure_terminals[0].id : 0;
    try {
      var r = await api('/api/search/packages', {
        country_id: 1, package_id: pkg.id, departure_terminal_id: terminalId,
        from_date: S.filters.dateFrom, to_date: S.filters.dateTo,
        from_nights: S.filters.nights, to_nights: S.filters.nights,
        adults: S.filters.adults, children: S.filters.children,
        meal_ids: S.filters.mealIds, star_ids: S.filters.starIds, facility_ids: S.filters.facilityIds,
        city_ids: S.filters.cityId ? [parseInt(S.filters.cityId)] : null,
        markup_percent: 0,
      });
      if (r && r.error) throw new Error(r.error);
      S.results = r;
    } catch (e) {
      toast('Eroare: ' + (e.message || e), 'error');
    } finally {
      S.loading = false;
      render();
      // Scroll to the results section so user sees what was found
      setTimeout(function() {
        var resultsHeader = rootEl && rootEl.querySelector('.zt-results-grid');
        if (resultsHeader) {
          resultsHeader.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
          // Fallback: scroll to the results area (h2 with count)
          var resultsAnchor = rootEl && rootEl.querySelector('h2');
          if (resultsAnchor) resultsAnchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }

  function scrollToWidgetTop() {
    if (!rootEl) return;
    rootEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function openHotel(hotelId, priceId) {
    S.view = 'hotel'; S.hotel = null; S.hotelRooms = []; S.hotelPhotoIdx = 0;
    writeHash({ h: hotelId, in: S.filters.dateFrom, out: S.filters.dateTo, n: S.filters.nights, a: S.filters.adults, t: S.filters.tripType });
    render();
    // Scroll to top of widget so user sees the hotel name and photos first
    setTimeout(scrollToWidgetTop, 50);
    var pkg = pickPackage();
    var terminalId = (S.filters.tripType === 'bus' && pkg && pkg.departure_terminals && pkg.departure_terminals.length) ? pkg.departure_terminals[0].id : 0;
    try {
      var hd = await api('/api/hotel/details', {
        hotel_id: parseInt(hotelId),
        from_date: S.filters.dateFrom, to_date: S.filters.dateFrom,
        from_nights: S.filters.nights, to_nights: S.filters.nights,
        adults: S.filters.adults, children: S.filters.children,
      });
      if (hd && hd.error) throw new Error(hd.error);
      S.hotel = hd;
      render();
      // Load rooms in parallel
      var rooms = await api('/api/search/packages/hotel_rooms', {
        country_id: 1, package_id: pkg ? pkg.id : 87, departure_terminal_id: terminalId,
        hotel_id: parseInt(hotelId),
        from_date: S.filters.dateFrom, to_date: S.filters.dateTo,
        from_nights: S.filters.nights, to_nights: S.filters.nights,
        adults: S.filters.adults, children: S.filters.children,
      });
      if (rooms && rooms.prices) {
        S.hotelRooms = rooms.prices.sort(function(a,b){ return (a.brut_zebra||a.gross_amount) - (b.brut_zebra||b.gross_amount); });
      }
      render();
    } catch (e) {
      toast('Eroare: ' + e.message, 'error');
    }
  }

  function backToSearch() {
    S.view = 'search'; S.hotel = null; S.hotelRooms = []; writeHash(null); render();
  }

  function toggleFav(offer) {
    var i = S.favorites.findIndex(function(f){ return f.price_id === offer.price_id; });
    if (i >= 0) {
      S.favorites.splice(i, 1);
      toast(t('favRemoved'));
    } else {
      S.favorites.unshift({
        price_id: offer.price_id, hotel_id: offer.hotel_id, hotel_name: offer.hotel_name,
        star: offer.star, city: offer.city, meal: offer.meal, room_type: offer.room_type,
        nights: offer.nights, check_in: offer.check_in, check_out: offer.check_out,
        gross_amount: offer.gross_amount, brut_zebra: offer.brut_zebra, currency: offer.currency || 'EUR',
        default_photo: offer.default_photo,
        url: location.origin + location.pathname + '#zt:h=' + offer.hotel_id + '&in=' + S.filters.dateFrom + '&out=' + S.filters.dateTo + '&n=' + S.filters.nights + '&a=' + S.filters.adults + '&t=' + S.filters.tripType,
        saved_at: new Date().toISOString(),
      });
      toast(t('favSaved'));
    }
    saveFavs(); render();
  }

  function findOffer(priceId) {
    var p = parseInt(priceId);
    var r = S.results && S.results.prices ? S.results.prices.find(function(o){ return o.price_id === p; }) : null;
    if (r) return r;
    r = S.hotelRooms.find(function(o){ return o.price_id === p; });
    if (r) return r;
    return S.favorites.find(function(o){ return o.price_id === p; });
  }

  function openReserve(offer) {
    S.reserveOffer = offer; S.reserveOpen = true; render();
  }
  function closeReserve() { S.reserveOpen = false; render(); }

  async function submitReserve() {
    var name = (document.getElementById('zt-resv-name')||{}).value;
    var phone = (document.getElementById('zt-resv-phone')||{}).value;
    var notes = (document.getElementById('zt-resv-notes')||{}).value;
    if (!name || !phone) { toast(t('missingFields'), 'error'); return; }
    try {
      var r = await api('/api/turist/reserve', {
        customer_name: name, customer_phone: phone, notes: notes,
        adults: S.filters.adults, children_ages: S.filters.children.join(', '),
        offer: S.reserveOffer,
      });
      if (r && r.error) throw new Error(r.error);
      S.reserveOpen = false; render();
      toast(t('reserveSent') + r.quote_id, 'success');
    } catch (e) {
      toast('Eroare: ' + e.message, 'error');
    }
  }

  function copyFavText(f) {
    var lines = ['🏨 ' + (f.hotel_name||'') + ' ' + (f.star||''),
      '📍 ' + (f.city||'Bulgaria'),
      '📅 ' + formatDate(f.check_in) + ' → ' + formatDate(f.check_out) + ' (' + f.nights + ' nopți)',
      '🍽️ ' + mealHuman(f.meal),
      '🛏️ ' + roomHuman(f.room_type),
      '💶 ' + formatMoney(f.brut_zebra||f.gross_amount) + ' pentru ' + paxLabel(true)
    ];
    if (f.url) lines.push('🔗 ' + f.url);
    return lines.join('\n');
  }
  function copyToClipboard(text) {
    try {
      navigator.clipboard.writeText(text).then(function(){ toast(t('copied'), 'success'); });
    } catch (e) {
      var ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
      toast(t('copied'), 'success');
    }
  }

  // ============ EVENT HANDLER ============
  function onClick(ev) {
    var t = ev.target.closest('[data-action]');
    if (!t) return;
    var a = t.getAttribute('data-action');
    var stop = t.getAttribute('data-stop');
    if (stop) ev.stopPropagation();

    if (a === 'trip') setTrip(t.getAttribute('data-value'));
    else if (a === 'meal') toggleMeal(parseInt(t.getAttribute('data-value')));
    else if (a === 'star') toggleStar(parseInt(t.getAttribute('data-value')));
    else if (a === 'fac') toggleFacility(parseInt(t.getAttribute('data-value')));
    else if (a === 'adults') adjustAdults(parseInt(t.getAttribute('data-value')));
    else if (a === 'child') adjustChild(parseInt(t.getAttribute('data-value')));
    else if (a === 'paxToggle') { S.paxOpen = !S.paxOpen; render(); }
    else if (a === 'paxClose') { S.paxOpen = false; render(); }
    else if (a === 'search') doSearch();
    else if (a === 'openHotel') openHotel(t.getAttribute('data-hotel'), t.getAttribute('data-priceid'));
    else if (a === 'backToSearch') backToSearch();
    else if (a === 'toggleFav') {
      var o = findOffer(t.getAttribute('data-priceid'));
      if (o) toggleFav(o);
    }
    else if (a === 'toggleFavHotel') {
      if (!S.hotel) return;
      // Find cheapest offer for this hotel
      var cheap = S.hotelRooms[0];
      if (cheap) toggleFav(Object.assign({}, cheap, { hotel_id: S.hotel.hotel_id, hotel_name: S.hotel.hotel_name, star: S.hotel.star, city: S.hotel.city, default_photo: S.hotel.default_photo }));
    }
    else if (a === 'shareLink') { copyToClipboard(location.href); toast(t('linkCopied'), 'success'); }
    else if (a === 'reserveCheapest') {
      if (S.hotelRooms && S.hotelRooms.length) {
        var cheapest = S.hotelRooms[0];  // already sorted by price asc
        var enriched = Object.assign({}, cheapest, {
          hotel_name: S.hotel ? S.hotel.hotel_name : cheapest.hotel_name,
          star: S.hotel ? S.hotel.star : cheapest.star,
          city: S.hotel ? S.hotel.city : cheapest.city,
          default_photo: S.hotel ? S.hotel.default_photo : cheapest.default_photo,
        });
        openReserve(enriched);
      } else {
        toast(t('noRoomsAvailable'), 'error');
      }
    }
    else if (a === 'reserve') {
      var off = findOffer(t.getAttribute('data-priceid'));
      if (off) openReserve(off);
    }
    else if (a === 'closeReserve') closeReserve();
    else if (a === 'submitReserve') submitReserve();
    else if (a === 'photoNext') { if (S.hotel && S.hotel.photos) { S.hotelPhotoIdx = (S.hotelPhotoIdx+1) % S.hotel.photos.length; render(); } }
    else if (a === 'photoPrev') { if (S.hotel && S.hotel.photos) { S.hotelPhotoIdx = (S.hotelPhotoIdx-1+S.hotel.photos.length) % S.hotel.photos.length; render(); } }
    else if (a === 'photoGoto') { S.hotelPhotoIdx = parseInt(t.getAttribute('data-idx')); render(); }
    else if (a === 'favToggle') { S.favOpen = !S.favOpen; render(); }
    else if (a === 'sort') { S.sortBy = t.value; render(); }
    else if (a === 'copyFav') { var f = findOffer(t.getAttribute('data-priceid')); if (f) copyToClipboard(copyFavText(f)); }
    else if (a === 'copyAllFavs') {
      var txt = '🦓 Zebra Tur — ' + S.favorites.length + ' ' + t('ztOffers') + '\n' + '─'.repeat(40) + '\n\n' +
        S.favorites.map(function(f, i){ return (i+1) + '. ' + copyFavText(f); }).join('\n\n') +
        '\n\n' + '─'.repeat(40) + '\n📞 ' + t('contact') + ': +37378326222';
      copyToClipboard(txt);
    }
    else if (a === 'shareWhatsApp') {
      var txt = '🦓 Zebra Tur — ' + S.favorites.length + ' ' + t('ztOffers') + '\n\n' + S.favorites.map(function(f, i){ return (i+1) + '. ' + copyFavText(f); }).join('\n\n');
      window.open('https://wa.me/?text=' + encodeURIComponent(txt), '_blank');
    }
    else if (a === 'clearFavs') {
      if (confirm(t('favConfirmClear'))) { S.favorites = []; saveFavs(); render(); }
    }
    else if (a === 'removeFav') {
      var pid = parseInt(t.getAttribute('data-priceid'));
      var i = S.favorites.findIndex(function(f){ return f.price_id === pid; });
      if (i >= 0) { S.favorites.splice(i,1); saveFavs(); render(); }
    }
  }
  function onChange(ev) {
    var t = ev.target;
    var a = t.getAttribute('data-action');
    if (a === 'filter') setFilter(t.getAttribute('data-key'), t.value);
    else if (a === 'childage') setChildAge(parseInt(t.getAttribute('data-idx')), t.value);
    else if (a === 'sort') { S.sortBy = t.value; render(); }
  }
  function onInput(ev) {
    var t = ev.target;
    var a = t.getAttribute('data-action');
    if (a === 'filter') {
      var k = t.getAttribute('data-key');
      if (k === 'dateFrom' || k === 'dateTo') S.filters[k] = t.value;
      else if (k === 'cityId') S.filters.cityId = t.value;
    }
  }

  // ============ RENDER ============
  var rootEl;
  function render() {
    if (!rootEl) return;
    var html = '<div class="zt-app">';
    if (S.view === 'search') html += tplSearchPage();
    else if (S.view === 'hotel') html += tplHotelPage();
    html += '</div>';

    // FAB + favorites panel
    html += '<button class="zt-fav-fab" data-action="favToggle" aria-label="Favorite">❤️' + (S.favorites.length ? '<span class="zt-fav-fab-badge">'+S.favorites.length+'</span>' : '') + '</button>';
    html += '<div class="zt-overlay '+(S.favOpen?'zt-open':'')+'" data-action="favToggle"></div>';
    html += '<div class="zt-fav-panel '+(S.favOpen?'zt-open':'')+'"><div style="padding:14px;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;"><h3 style="margin:0;font-size:20px;">'+t('favTitle')+'</h3><button class="zt-modal-close" data-action="favToggle">×</button></div>' + tplFavoritesPanel() + '</div>';

    // Reserve modal
    if (S.reserveOpen && S.reserveOffer) html += tplReserveModal(S.reserveOffer);

    rootEl.innerHTML = html;
  }

  // ============ INIT ============
  async function init() {
    // Find or create container
    rootEl = document.getElementById(CONTAINER_ID);
    if (!rootEl) {
      var scripts = document.getElementsByTagName('script');
      var current = scripts[scripts.length - 1];
      rootEl = document.createElement('div');
      rootEl.id = CONTAINER_ID;
      if (current && current.parentNode) current.parentNode.insertBefore(rootEl, current.nextSibling);
      else document.body.appendChild(rootEl);
    }

    // Force visibility via inline styles (highest priority — beats host theme CSS)
    rootEl.style.cssText = 'display:block !important; visibility:visible !important; opacity:1 !important; ' +
      'height:auto !important; min-height:600px !important; max-height:none !important; ' +
      'width:100% !important; overflow:visible !important; position:relative !important; ' +
      'z-index:1 !important; clip:auto !important; clip-path:none !important; margin:0 auto !important;';

    // Also walk up the DOM and remove any obvious hiding rules on ancestor containers (Creatium often wraps widgets)
    var node = rootEl.parentNode;
    var depth = 0;
    while (node && node !== document.body && depth < 6) {
      var cs = window.getComputedStyle(node);
      if (cs.display === 'none' || cs.visibility === 'hidden' ||
          parseInt(cs.height) === 0 || parseInt(cs.maxHeight) === 0) {
        node.style.cssText += 'display:block !important; visibility:visible !important; height:auto !important; max-height:none !important; overflow:visible !important;';
      }
      node = node.parentNode;
      depth++;
    }

    // Inject styles once
    if (!document.getElementById('zt-styles')) {
      var st = document.createElement('style');
      st.id = 'zt-styles';
      st.textContent = STYLES;
      document.head.appendChild(st);
    }

    // Set up listeners
    document.addEventListener('click', onClick);
    document.addEventListener('change', onChange);
    document.addEventListener('input', onInput);

    // Touch swipe for photo gallery
    var tStartX = 0, tStartY = 0, tStarted = false;
    document.addEventListener('touchstart', function(ev) {
      var stage = ev.target.closest('.zt-photo-stage, .zt-photo-thumbs');
      if (!stage || stage.classList.contains('zt-photo-thumbs')) { tStarted = false; return; }
      tStartX = ev.touches[0].clientX;
      tStartY = ev.touches[0].clientY;
      tStarted = true;
    }, { passive: true });
    document.addEventListener('touchend', function(ev) {
      if (!tStarted) return;
      tStarted = false;
      var t = ev.changedTouches[0];
      var dx = t.clientX - tStartX;
      var dy = t.clientY - tStartY;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) {
        if (!S.hotel || !S.hotel.photos || !S.hotel.photos.length) return;
        if (dx < 0) S.hotelPhotoIdx = (S.hotelPhotoIdx + 1) % S.hotel.photos.length;
        else S.hotelPhotoIdx = (S.hotelPhotoIdx - 1 + S.hotel.photos.length) % S.hotel.photos.length;
        render();
      }
    }, { passive: true });

    // Load directories
    try {
      var cities = await fetch(API + '/api/dir/cities?country_id=1').then(function(r){ return r.json(); });
      var packages = await fetch(API + '/api/dir/packages?country_id=1').then(function(r){ return r.json(); });
      if (Array.isArray(cities)) {
        var popular = ['SUNNY BEACH','GOLDEN SANDS','NESSEBAR','POMORIE','ELENITE','ST. VLAS','ALBENA','BALCHIK','OBZOR','BANSKO','BURGAS','VARNA'];
        S.cities = cities.filter(function(c){ return popular.indexOf((c.city_name||'').toUpperCase()) >= 0; })
          .sort(function(a,b){ return popular.indexOf((a.city_name||'').toUpperCase()) - popular.indexOf((b.city_name||'').toUpperCase()); })
          .map(function(c){ return { id: c.city_id, name: cityHuman(c.city_name) }; });
      }
      if (Array.isArray(packages)) S.packages = packages;
    } catch (e) { console.warn('ZebraTur: load directories failed', e); }

    // Read hash for deep links
    var hash = readHash();
    if (hash && hash.h) {
      S.filters.dateFrom = hash.in || S.filters.dateFrom;
      S.filters.dateTo = hash.out || S.filters.dateTo;
      S.filters.nights = parseInt(hash.n) || S.filters.nights;
      S.filters.adults = parseInt(hash.a) || S.filters.adults;
      S.filters.tripType = hash.t || S.filters.tripType;
      render();
      openHotel(hash.h);
    } else {
      render();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
