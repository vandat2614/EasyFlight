const $ = id => document.getElementById(id);
const chatMessages = $('chatMessages');
const flightsContent = $('flightsContent');
const userInput = $('userInput');
const sendBtn = $('sendBtn');
const chatPanel = $('chatPanel');
const chatResize = $('chatResize');
let history = [];
let lastSearchParams = null;

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
	return div;
}

function showLoading() {
	const d = document.createElement('div');
	d.className = 'typing-indicator'; d.id = 'typing';
	d.innerHTML = '<span></span><span></span><span></span>';
	chatMessages.appendChild(d);
	chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideLoading() { const e = $('typing'); if (e) e.remove(); }

function showChatSearching() {
	hideLoading();
	const d = document.createElement('div');
	d.className = 'msg assistant searching-msg'; d.id = 'chatSearching';
	d.innerHTML = '<div class="search-spinner-sm"></div><span>Searching flights...</span>';
	chatMessages.appendChild(d);
	chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideChatSearching() { const e = $('chatSearching'); if (e) e.remove(); }

function setInputEnabled(enabled) {
	sendBtn.disabled = !enabled;
	userInput.disabled = !enabled;
}

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
}

/* ─── Helpers ─── */
function fmtDur(m) {
	const h = Math.floor(m / 60), mm = m % 60;
	if (h === 0) return `${mm} min`;
	if (mm === 0) return `${h} hr`;
	return `${h} hr ${mm} min`;
}

function fmtPrice(p, c) {
	c = c || 'VND';
	if (c === 'VND') return new Intl.NumberFormat('vi-VN').format(p) + ' VND';
	if (c === 'EUR') return new Intl.NumberFormat('de-DE', {style:'currency',currency:'EUR'}).format(p);
	return new Intl.NumberFormat('en-US', {style:'currency',currency:c}).format(p);
}

function getTime(dt) { return dt ? dt.split(' ')[1] || dt : ''; }
function getDate(dt) {
	if (!dt) return '';
	const d = dt.split(' ')[0];
	try {
		const date = new Date(d + 'T00:00:00');
		const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
		const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
		return `${days[date.getDay()]}, ${months[date.getMonth()]} ${String(date.getDate()).padStart(2,'0')}`;
	} catch { return d; }
}

function uniqueLogos(segs) {
	const m = new Map();
	segs.forEach(s => { if (!m.has(s.airline)) m.set(s.airline, s.airline_logo); });
	return [...m.entries()];
}

/* ─── Render flights — Google Flights style ─── */
function renderFlights(flights, currency) {
	if (!flights?.length) return;
	flightsContent.innerHTML = '';
	const cur = currency || 'VND';

	flights.forEach((fl, idx) => {
		const segs = fl.segments || [];
		const lays = fl.layovers || [];
		if (!segs.length) return;

		const first = segs[0];
		const last = segs[segs.length - 1];
		const airlines = uniqueLogos(segs);
		const departDate = getDate(first.departure_time);

		// CO2
		const co2 = fl.carbon_emissions || {};
		let co2Html = '';
		if (co2.this_flight) {
			const kg = Math.round(co2.this_flight / 1000);
			const diff = co2.difference_percent || 0;
			const diffClass = diff < 0 ? 'lower' : diff > 0 ? 'higher' : '';
			const diffSign = diff > 0 ? '+' : '';
			co2Html = `
				<div class="card-co2">
					<div class="card-co2-amount">${kg} kg CO<sub>2</sub></div>
					${diff !== 0 ? `<div class="card-co2-diff ${diffClass}">${diffSign}${diff}% emissions</div>` : ''}
				</div>
			`;
		}

		// Logos
		const logoHtml = airlines.map(([n, l]) =>
			l ? `<img class="card-logo" src="${l}" alt="${n}" title="${n}">` : ''
		).join('');

		// Build segments HTML
		let segsHtml = '';
		segs.forEach((s, si) => {
			// Amenities
			const amenities = s.amenities || [];
			let amenityItems = '';
			amenities.forEach(a => { amenityItems += `<li>${a}</li>`; });
			if (co2.this_flight && si === 0) {
				amenityItems += `<li>Carbon emissions estimate: ${Math.round(co2.this_flight / 1000)} kg</li>`;
			}

			const amenityHtml = amenityItems
				? `<div class="seg-amenities-col"><ul class="seg-amenity-list">${amenityItems}</ul></div>`
				: '';

			segsHtml += `
				<div class="seg-row">
					<div class="seg-timeline-col">
						<div class="seg-point">
							<div class="seg-dot"></div>
							<span class="seg-point-time">${getTime(s.departure_time)}</span>
							<span class="seg-point-sep">&middot;</span>
							<span class="seg-point-airport">${s.departure_airport_name} (<span class="seg-point-code">${s.departure_airport}</span>)</span>
						</div>
						<div class="seg-travel">
							<span class="seg-travel-duration">Travel time: ${fmtDur(s.duration)}</span>
						</div>
						<div class="seg-point">
							<div class="seg-dot"></div>
							<span class="seg-point-time">${getTime(s.arrival_time)}</span>
							<span class="seg-point-sep">&middot;</span>
							<span class="seg-point-airport">${s.arrival_airport_name} (<span class="seg-point-code">${s.arrival_airport}</span>)</span>
						</div>
						<div class="seg-flight-line">
							<span>${s.airline}</span> &middot; ${s.travel_class || 'Economy'} &middot; ${s.airplane || ''} &middot; <span>${s.flight_number}</span>
						</div>
					</div>
					${amenityHtml}
				</div>
			`;

			// Layover
			if (si < lays.length) {
				const l = lays[si];
				segsHtml += `
					<div class="seg-layover">
						<span>${fmtDur(l.duration)} layover</span> &middot; ${l.airport_name || l.airport} (${l.airport})
					</div>
				`;
			}
		});

		const card = document.createElement('div');
		card.className = 'flight-card';
		card.style.animationDelay = `${idx * 0.06}s`;
		card.innerHTML = `
			<div class="card-header">
				${logoHtml}
				<div class="card-departure-label">Departure &middot; ${departDate}</div>
				${co2Html}
				<div class="card-price">${fmtPrice(fl.price, cur)}</div>
				${fl.booking_token ? `<button class="card-book-btn" data-idx="${idx}">Select flight</button>` : ''}
			</div>
			<div class="card-body">
				${segsHtml}
			</div>
		`;

		// Booking click handler — redirect to airline homepage
		const bookBtn = card.querySelector('.card-book-btn');
		if (bookBtn) {
			const airlineName = (segs[0] || {}).airline || '';
			bookBtn.addEventListener('click', () => {
				const url = getAirlineUrl(airlineName);
				window.open(url, '_blank');
			});
		}

		flightsContent.appendChild(card);
	});
}

const AIRLINE_URLS = {
	'AirAsia': 'https://www.airasia.com',
	'AirAsia X': 'https://www.airasia.com',
	'Vietnam Airlines': 'https://www.vietnamairlines.com',
	'VietJet Air': 'https://www.vietjetair.com',
	'Vietjet Air': 'https://www.vietjetair.com',
	'Bamboo Airways': 'https://www.bambooairways.com',
	'Singapore Airlines': 'https://www.singaporeair.com',
	'Thai Airways': 'https://www.thaiairways.com',
	'Malaysia Airlines': 'https://www.malaysiaairlines.com',
	'Cathay Pacific': 'https://www.cathaypacific.com',
	'Emirates': 'https://www.emirates.com',
	'Qatar Airways': 'https://www.qatarairways.com',
	'Korean Air': 'https://www.koreanair.com',
	'Japan Airlines': 'https://www.jal.co.jp',
	'ANA': 'https://www.ana.co.jp',
	'EVA Air': 'https://www.evaair.com',
	'China Airlines': 'https://www.china-airlines.com',
	'China Southern': 'https://www.csair.com',
	'China Eastern': 'https://www.ceair.com',
	'Jetstar': 'https://www.jetstar.com',
	'Scoot': 'https://www.flyscoot.com',
	'Cebu Pacific': 'https://www.cebupacificair.com',
	'Philippine Airlines': 'https://www.philippineairlines.com',
	'Garuda Indonesia': 'https://www.garuda-indonesia.com',
	'Lion Air': 'https://www.lionair.co.id',
	'Batik Air': 'https://www.batikair.com',
	'Turkish Airlines': 'https://www.turkishairlines.com',
	'Etihad Airways': 'https://www.etihad.com',
	'British Airways': 'https://www.britishairways.com',
	'Lufthansa': 'https://www.lufthansa.com',
	'Air France': 'https://www.airfrance.com',
	'KLM': 'https://www.klm.com',
	'Delta': 'https://www.delta.com',
	'United': 'https://www.united.com',
	'American Airlines': 'https://www.aa.com',
	'American': 'https://www.aa.com',
	'Qantas': 'https://www.qantas.com',
	'Thai Smile': 'https://www.thaismileair.com',
	'Starlux Airlines': 'https://www.starlux-airlines.com',
	'IndiGo': 'https://www.goindigo.in',
};

function getAirlineUrl(name) {
	if (AIRLINE_URLS[name]) return AIRLINE_URLS[name];
	const lower = name.toLowerCase();
	for (const [key, url] of Object.entries(AIRLINE_URLS)) {
		if (lower.includes(key.toLowerCase()) || key.toLowerCase().includes(lower)) return url;
	}
	return `https://www.google.com/search?q=${encodeURIComponent(name + ' book flight')}`;
}

/* ─── SSE Stream Send ─── */
async function sendMessage() {
	const text = userInput.value.trim();
	if (!text) return;
	addMsg('user', text);
	userInput.value = '';
	setInputEnabled(false);
	showLoading();

	let assistantText = '';
	let assistantDiv = null;

	try {
		const res = await fetch('/chat/stream', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ message: text, history }),
		});

		const reader = res.body.getReader();
		const decoder = new TextDecoder();
		let buffer = '';

		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split('\n');
			buffer = lines.pop();

			let eventType = '';
			for (const line of lines) {
				if (line.startsWith('event: ')) {
					eventType = line.slice(7).trim();
				} else if (line.startsWith('data: ')) {
					const data = line.slice(6);

					if (eventType === 'searching') {
						hideLoading();
						showChatSearching();

					} else if (eventType === 'searching_done') {
						hideChatSearching();
						showLoading();

					} else if (eventType === 'token') {
						hideChatSearching();
						if (!assistantDiv) {
							hideLoading();
							assistantDiv = addMsg('assistant', '');
						}
						const token = JSON.parse(data);
						assistantText += token;
						assistantDiv.innerHTML = md(assistantText);
						chatMessages.scrollTop = chatMessages.scrollHeight;

					} else if (eventType === 'flights') {
						const payload = JSON.parse(data);
						const flights = payload.flights || [];
						lastSearchParams = payload.search_params || null;
						const cur = lastSearchParams?.currency || 'VND';
						if (flights.length) {
							showSearching();
							setTimeout(() => renderFlights(flights, cur), 600);
						}

					} else if (eventType === 'done') {
						// stream finished
					}

					eventType = '';
				}
			}
		}

		if (!assistantDiv) {
			hideLoading();
			assistantText = 'No response received.';
			addMsg('assistant', assistantText);
		}

		history.push({ role: 'user', content: text });
		history.push({ role: 'assistant', content: assistantText });

	} catch (err) {
		hideLoading();
		addMsg('assistant', 'Cannot connect to server. Please try again.');
		console.error(err);
	}

	setInputEnabled(true);
	userInput.focus();
}
