// ZebraTur SHS — shared client-side helpers

const STATUS_LABELS = {
  in_work: 'În lucru',
  confirmed: 'Confirmat',
  confirmed_print: 'Confirmat (tipărit)',
  not_confirmed: 'Neconfirmat',
  canceled: 'Anulat',
  accepted_for_processing: 'Acceptat pt. procesare',
  not_confirmed_from_site: 'Neconfirmat (site)',
  imported: 'Importat',
};

const STATUS_CLASS = {
  in_work: 'bg-amber-100 text-amber-800',
  confirmed: 'bg-green-100 text-green-800',
  confirmed_print: 'bg-emerald-100 text-emerald-800',
  not_confirmed: 'bg-red-100 text-red-700',
  canceled: 'bg-slate-200 text-slate-600',
  accepted_for_processing: 'bg-blue-100 text-blue-700',
  not_confirmed_from_site: 'bg-orange-100 text-orange-700',
  imported: 'bg-slate-100 text-slate-700',
};

function statusLabel(s) { return STATUS_LABELS[s] || (s || '—'); }
function statusClassFn(s) { return STATUS_CLASS[s] || 'bg-slate-100 text-slate-700'; }

function formatMoney(val, currency) {
  if (val === null || val === undefined || val === '') return '—';
  const n = Number(val);
  if (Number.isNaN(n)) return '—';
  try {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency', currency: currency || 'EUR',
      minimumFractionDigits: 0, maximumFractionDigits: 2,
    }).format(n);
  } catch (e) {
    return n.toFixed(2) + ' ' + (currency || '');
  }
}

function formatDate(unixSec) {
  if (!unixSec) return '—';
  const d = new Date(Number(unixSec) * 1000);
  return d.toLocaleString('ro-RO', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
}

// ---------------- HTTP wrapper ----------------

const api = {
  async _request(method, url, body) {
    const opts = { method, headers: { 'Accept': 'application/json' } };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(url, opts);
    const text = await r.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { _raw: text }; }
    if (!r.ok) {
      const err = (data && data.error) || `HTTP ${r.status}`;
      throw new Error(err);
    }
    return data;
  },
  get(url) { return this._request('GET', url); },
  post(url, body) { return this._request('POST', url, body || {}); },
  put(url, body) { return this._request('PUT', url, body || {}); },
  del(url) { return this._request('DELETE', url); },
};

// ---------------- Toast ----------------

function toast(message, kind) {
  const el = document.createElement('div');
  el.className = 'toast ' + (kind || '');
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => { el.classList.add('fade'); setTimeout(() => el.remove(), 300); }, 3500);
}

// ---------------- SHS connection badge ----------------

async function refreshSHSBadge() {
  const btn = document.getElementById('shsStatus');
  if (!btn) return;
  try {
    const r = await api.get('/api/shs/ping');
    const ok = r.auth_ok;
    btn.innerHTML = `<span class="inline-block w-2 h-2 rounded-full ${ok ? 'bg-green-400' : 'bg-red-400'} mr-1"></span> SHS ${ok ? 'OK' : 'OFFLINE'}`;
    btn.title = ok ? 'Conectat la SHS' : ('Eroare auth · ' + r.base_url);
  } catch (e) {
    btn.innerHTML = '<span class="inline-block w-2 h-2 rounded-full bg-red-400 mr-1"></span> SHS error';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  refreshSHSBadge();
  document.getElementById('shsStatus')?.addEventListener('click', refreshSHSBadge);
});

window.addEventListener('shs-status', (e) => {
  const btn = document.getElementById('shsStatus');
  if (!btn) return;
  const ok = e.detail?.auth_ok;
  btn.innerHTML = `<span class="inline-block w-2 h-2 rounded-full ${ok ? 'bg-green-400' : 'bg-red-400'} mr-1"></span> SHS ${ok ? 'OK' : 'OFFLINE'}`;
});
