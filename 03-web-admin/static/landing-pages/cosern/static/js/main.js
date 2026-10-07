// ============================================================
// Hearto H5 promo — data + rendering + interactions
// All girl data lives here so you can add/remove cards freely.
// ============================================================

const IMG_BASE = 'images/girls/';

// ---- Hero slider (3 big cards) ----
const HERO_GIRLS = [
  {
    img: '31.png',
    name: 'Priya',
    age: 23,
    distance: '1.2 km',
    city: 'Mumbai',
    tags: [{text:'🔥 Doggy Ready', hot:true}, {text:'Blowjob Queen'}, {text:'Creampie Slut'}],
  },
  {
    img: '30.png',
    name: 'Ananya',
    age: 21,
    distance: '0.8 km',
    city: 'Delhi',
    tags: [{text:'💦 Wants to Suck', hot:true}, {text:'Anal Addict'}, {text:'Deepthroat'}],
  },
  {
    img: '15.jpg',
    name: 'Riya',
    age: 24,
    distance: '2.5 km',
    city: 'Bangalore',
    tags: [{text:'⭐ Top Fuck', hot:true}, {text:'Creampie Only'}, {text:'Throat Goat'}],
  },
];

// ---- Grid (8 small cards) ----
const GRID_GIRLS = [
  {img: '6.jpg',  name: 'Aisha',  age: 22, badge: '⭐ VIP',    badgeType:'gold', tags:['Doggy','Creampie']},
  {img: '17.jpg', name: 'Neha',   age: 25, badge: '🔥 Hot',    badgeType:'',     tags:['Blowjob','Swallow']},
  {img: '22.jpg', name: 'Diya',   age: 20, badge: '✨ New',    badgeType:'new',  tags:['Anal','Rough']},
  {img: '38.png', name: 'Sana',   age: 24, badge: '💬 Active', badgeType:'',     tags:['Deepthroat','Slut']},
  {img: '45.png', name: 'Kavya',  age: 23, badge: '👑 Top',    badgeType:'gold', tags:['Cowgirl','Riding']},
  {img: '51.png', name: 'Tara',   age: 21, badge: '📍 Nearby', badgeType:'',     tags:['Missionary','Moaner']},
  {img: '8.jpg',  name: 'Maya',   age: 26, badge: '🔥 Hot',    badgeType:'',     tags:['Wild','Bareback']},
  {img: '36.png', name: 'Zoya',   age: 22, badge: '✨ New',    badgeType:'new',  tags:['Tease','Cumslut']},
];

// ---- Urgency strip ----
const URGENCY_GIRL = {img: '12.jpg', name: 'Aanya'};

// ============================================================
// Renderers
// ============================================================

function renderHero() {
  const swiper = document.getElementById('swiper');
  const dots = document.getElementById('dots');

  swiper.innerHTML = HERO_GIRLS.map(g => `
    <div class="slide" data-download>
      <div class="slide-img" style="background-image:url('${IMG_BASE}${g.img}')"></div>
      <div class="slide-verified">✓ Verified</div>
      <div class="slide-online"><span class="dot"></span> Online</div>
      <div class="slide-info">
        <div class="name">${g.name}</div>
        <div class="loc">📍 ${g.distance} · ${g.city}</div>
        <div class="tag-row">
          ${g.tags.map(t => `<span class="tag${t.hot ? ' hot' : ''}">${t.text}</span>`).join('')}
        </div>
      </div>
    </div>
  `).join('');

  dots.innerHTML = HERO_GIRLS.map((_, i) => `<i class="${i===0 ? 'on' : ''}"></i>`).join('');
}

function renderGrid() {
  const grid = document.getElementById('grid');
  grid.innerHTML = GRID_GIRLS.map(g => `
    <div class="card" data-download>
      <div class="card-img" style="background-image:url('${IMG_BASE}${g.img}')"></div>
      <span class="card-badge ${g.badgeType}">${g.badge}</span>
      <span class="card-heart">♥</span>
      <span class="card-online"></span>
      <div class="card-info">
        <div class="nm">${g.name}</div>
        <div class="tg">${g.tags.map(t => `<span>${t}</span>`).join('')}</div>
      </div>
    </div>
  `).join('');
}

function renderUrgency() {
  const av = document.querySelector('.urgency .av');
  const nameEl = document.querySelector('.urgency .txt b');
  av.style.backgroundImage = `url('${IMG_BASE}${URGENCY_GIRL.img}')`;
  nameEl.textContent = URGENCY_GIRL.name;
}

// ============================================================
// Swiper auto-play + dots
// ============================================================

function initSwiper() {
  const swiper = document.getElementById('swiper');
  const dots = document.getElementById('dots').children;
  const slides = swiper.children;
  let current = 0;
  let userInteracted = false;
  let lastTouch = 0;

  function setActive(i) {
    for (let k = 0; k < dots.length; k++) dots[k].classList.toggle('on', k === i);
    current = i;
  }

  swiper.addEventListener('scroll', () => {
    const idx = Math.round(swiper.scrollLeft / (slides[0].offsetWidth + 14));
    const clamped = Math.max(0, Math.min(slides.length - 1, idx));
    setActive(clamped);
  }, {passive: true});

  swiper.addEventListener('touchstart', () => { userInteracted = true; lastTouch = Date.now(); }, {passive: true});
  swiper.addEventListener('touchend',   () => { lastTouch = Date.now(); }, {passive: true});

  setInterval(() => {
    if (Date.now() - lastTouch < 4000 && userInteracted) return;
    const next = (current + 1) % slides.length;
    const left = slides[next].offsetLeft - (swiper.clientWidth - slides[next].offsetWidth) / 2;
    swiper.scrollTo({left, behavior: 'smooth'});
  }, 3200);
}

// ============================================================
// Live online counter (fake)
// ============================================================

function initOnlineCounter() {
  const el = document.getElementById('onlineNum');
  let n = 12847;
  setInterval(() => {
    const delta = Math.floor(Math.random() * 7) - 2;
    n = Math.max(12500, Math.min(13500, n + delta));
    el.textContent = n.toLocaleString('en-IN');
  }, 1400);
}

// ============================================================
// Download action — unified entry for CTA button + any card/image.
// ============================================================

function triggerDownload() {
  window.location.href = 'download.php?v=' + Date.now();
}

function initCta() {
  // primary sticky button
  const btn = document.getElementById('ctaBtn');
  btn.addEventListener('click', function() {
    this.style.transform = 'scale(0.95)';
    setTimeout(() => this.style.transform = '', 120);
    triggerDownload();
  });

  // delegated: any element with [data-download] (slides, grid cards, urgency)
  document.body.addEventListener('click', (e) => {
    const target = e.target.closest('[data-download]');
    if (!target || target === btn) return;
    target.style.transform = 'scale(0.97)';
    setTimeout(() => target.style.transform = '', 160);
    triggerDownload();
  });
}

// ============================================================
// Boot
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  renderHero();
  renderGrid();
  renderUrgency();
  initSwiper();
  initOnlineCounter();
  initCta();
});
