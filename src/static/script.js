const $ = id => document.getElementById(id);
const chatMessages = $('chatMessages');
const flightsContent = $('flightsContent');
const flightCount = $('flightCount');
const userInput = $('userInput');
const sendBtn = $('sendBtn');
const chatPanel = $('chatPanel');
const chatResize = $('chatResize');
let history = [];

userInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !sendBtn.disabled) sendMessage();
});

/* ─── Resize chat panel ─── */
let isResizing = false;
chatResize.addEventListener('mousedown', (e) => {
  isResizing = true;
  chatResize.classList.add('active');
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
  e.preventDefault();
});

document.addEventListener('mousemove', (e) => {
  if (!isResizing) return;
  const w = Math.min(600, Math.max(280, e.clientX));
  chatPanel.style.width = w + 'px';
});

document.addEventListener('mouseup', () => {
  if (!isResizing) return;
  isResizing = false;
  chatResize.classList.remove('active');
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
});

function md(text) {
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(text);
  }
  return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
}

function addMsg(role, content) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  if (role === 'assistant') div.innerHTML = md(content);
  else div.textContent = content;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addToolCall(call) {
  const div = document.createElement('div');
  div.className = 'msg tool-call';
  const params = Object.entries(call)
    .filter(([_, v]) => v != null)
    .map(([k, v]) => `<span class="tool-param-key">${k}</span><span class="tool-param-val">${v}</span>`)
    .join('');
  div.innerHTML = `<div class="tool-call-header">&#128295; search_flights</div><div class="tool-call-params">${params}</div>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showLoading() {
  const d = document.createElement('div');
  d.className = 'typing-indicator'; d.id = 'typing';
  d.innerHTML = '<span></span><span></span><span></span>';
  chatMessages.appendChild(d);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideLoading() { const e = $('typing'); if (e) e.remove(); }

function showSearching() {
  flightsContent.innerHTML = `
    <div class="searching-overlay">
      <div class="search-spinner"></div>
      <div class="searching-text">Searching flights...</div>
    </div>
    <div class="skeleton-card"><div class="skeleton-line h20 w60"></div><div class="skeleton-line w80"></div><div class="skeleton-line w40"></div></div>
    <div class="skeleton-card"><div class="skeleton-line h20 w60"></div><div class="skeleton-line w80"></div><div class="skeleton-line w40"></div></div>
    <div class="skeleton-card"><div class="skeleton-line h20 w60"></div><div class="skeleton-line w80"></div><div class="skeleton-line w40"></div></div>
  `;
  flightCount.style.display = 'none';
}

function hideSearching() {
  const overlay = flightsContent.querySelector('.searching-overlay');
  if (overlay) flightsContent.innerHTML = '';
}

function fmtDur(m) {
  const h = Math.floor(m / 60), mm = m % 60;
  if (h === 0) return `${mm}m`;
  if (mm === 0) return `${h}h`;
  return `${h}h ${mm}m`;
}

function fmtPrice(p, c) {
  c = c || 'VND';
  if (c === 'VND') return new Intl.NumberFormat('vi-VN').format(p) + ' VND';
  if (c === 'EUR') return new Intl.NumberFormat('de-DE', {style:'currency',currency:'EUR'}).format(p);
  return new Intl.NumberFormat('en-US', {style:'currency',currency:c}).format(p);
}

function getTime(dt) { return dt ? dt.split(' ')[1] || dt : ''; }
function getDate(dt) { return dt ? dt.split(' ')[0] || '' : ''; }

function uniqueLogos(segs) {
  const m = new Map();
  segs.forEach(s => { if (!m.has(s.airline)) m.set(s.airline, s.airline_logo); });
  return [...m.entries()];
}

function renderFlights(flights, currency) {
  if (!flights?.length) return;
  flightsContent.innerHTML = '';
  flightCount.textContent = flights.length;
  flightCount.style.display = 'inline';
  const cur = currency || 'VND';

  flights.forEach((fl, idx) => {
    const segs = fl.segments || [];
    const lays = fl.layovers || [];
    const nStops = segs.length - 1;
    const first = segs[0] || {};
    const last = segs[segs.length - 1] || {};
    const airlines = uniqueLogos(segs);
    const cls = first.travel_class || 'Economy';

    const logosHtml = airlines.map(([n, l]) =>
      l ? `<img class="airline-logo" src="${l}" alt="${n}" title="${n}">` : ''
    ).join('');

    // Stop dots for route track
    let stopDots = '';
    for (let i = 0; i < nStops; i++) stopDots += '<div class="route-stop-dot"></div>';

    // Segments
    let segsHtml = '';
    segs.forEach((s, si) => {
      const logo = s.airline_logo ? `<img src="${s.airline_logo}" alt="">` : '';

      segsHtml += `
        <div class="seg-item">
          <div class="seg-timeline">
            <div class="seg-dot-dep"></div>
            <div class="seg-line"></div>
            <div class="seg-dot-arr"></div>
          </div>
          <div class="seg-body">
            <div class="seg-dep-row">
              <span class="seg-time">${getTime(s.departure_time)}</span>
              <span class="seg-date">${getDate(s.departure_time)}</span>
              <span class="seg-sep">&middot;</span>
              <span class="seg-airport-code">${s.departure_airport}</span>
              <span class="seg-airport-name">${s.departure_airport_name || ''}</span>
            </div>
            <div class="seg-flight-info">
              <div class="seg-flight-top">
                ${logo}
                <span class="seg-flight-id">${s.airline} ${s.flight_number}</span>
                <span class="seg-flight-dur">${fmtDur(s.duration)}</span>
              </div>
              <div class="seg-flight-details">
                <div class="seg-detail-item"><span class="label">Aircraft:</span><span class="value">${s.airplane || 'N/A'}</span></div>
                <div class="seg-detail-item"><span class="label">Class:</span><span class="value">${s.travel_class || 'Economy'}</span></div>
                ${s.legroom ? `<div class="seg-detail-item"><span class="label">Legroom:</span><span class="value">${s.legroom}</span></div>` : ''}
                ${s.often_delayed ? '<div class="seg-detail-item"><span class="value" style="color:#fca5a5">&#9888; Often delayed &gt;30min</span></div>' : ''}
                ${s.overnight ? '<div class="seg-detail-item"><span class="value" style="color:#c4b5fd">&#127769; Overnight flight</span></div>' : ''}
              </div>
            </div>
            <div class="seg-arr-row">
              <span class="seg-time">${getTime(s.arrival_time)}</span>
              <span class="seg-date">${getDate(s.arrival_time)}</span>
              <span class="seg-sep">&middot;</span>
              <span class="seg-airport-code">${s.arrival_airport}</span>
              <span class="seg-airport-name">${s.arrival_airport_name || ''}</span>
            </div>
          </div>
        </div>
      `;

      if (si < lays.length) {
        const l = lays[si];
        segsHtml += `
          <div class="seg-layover">
            <div class="layover-text">Transfer at <span>${l.airport_name || l.airport}</span></div>
            <div class="layover-dur">${fmtDur(l.duration)}</div>
          </div>
        `;
      }
    });

    const card = document.createElement('div');
    card.className = 'flight-card';
    card.style.animationDelay = `${idx * 0.08}s`;
    card.innerHTML = `
      <div class="card-header">
        <div class="card-airlines-row">
          ${logosHtml}
          <span class="card-airline-names">${airlines.map(a=>a[0]).join(' / ')}</span>
        </div>
        <div class="card-price-box">
          <div class="card-price">${fmtPrice(fl.price, cur)}</div>
          <div class="card-type">${cls}</div>
        </div>
      </div>
      <div class="card-route">
        <div class="route-endpoint">
          <div class="route-time">${getTime(first.departure_time)}</div>
          <div class="route-date">${getDate(first.departure_time)}</div>
          <div class="route-airport-name">${first.departure_airport_name || first.departure_airport}</div>
          <div class="route-iata">${first.departure_airport}</div>
        </div>
        <div class="route-connector">
          <div class="route-total-dur">${fmtDur(fl.total_duration)}</div>
          <div class="route-track"><div class="route-stop-dots">${stopDots}</div></div>
          <div class="route-stops-txt">${nStops === 0 ? 'Nonstop' : nStops + ' stop' + (nStops > 1 ? 's' : '')}</div>
        </div>
        <div class="route-endpoint">
          <div class="route-time">${getTime(last.arrival_time)}</div>
          <div class="route-date">${getDate(last.arrival_time)}</div>
          <div class="route-airport-name">${last.arrival_airport_name || last.arrival_airport}</div>
          <div class="route-iata">${last.arrival_airport}</div>
        </div>
      </div>
      <div class="card-segments">${segsHtml}</div>
    `;
    flightsContent.appendChild(card);
  });
}

/* ─── Send ─── */
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;
  addMsg('user', text);
  userInput.value = '';
  sendBtn.disabled = true;
  showLoading();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history }),
    });
    const data = await res.json();
    hideLoading();

    addMsg('assistant', data.response);
    history.push({ role: 'user', content: text });
    history.push({ role: 'assistant', content: data.response });

    // Only update right panel if a search was actually performed
    if (data.searched && data.flights?.length) {
      // Brief searching animation then reveal results
      showSearching();
      const cur = data.tool_calls?.[0]?.currency || 'VND';
      setTimeout(() => {
        hideSearching();
        renderFlights(data.flights, cur);
      }, 600);
    }
  } catch (err) {
    hideLoading();
    addMsg('assistant', 'Cannot connect to server. Please try again.');
    console.error(err);
  }
  sendBtn.disabled = false;
  userInput.focus();
}