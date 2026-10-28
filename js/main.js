document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  initMobileMenu();
  initPrefetch();
  initCardObservers();
});

function initDarkMode() {
  const isDark = localStorage.getItem('kalolsavam_dark') === 'true';
  if (isDark) {
    document.body.classList.add('dark');
  }

  const toggleBtn = document.getElementById('dark-mode-toggle');
  const toggleBtnMobile = document.getElementById('dark-mode-toggle-mobile');

  function handleToggle() {
    document.body.classList.toggle('dark');
    const active = document.body.classList.contains('dark');
    localStorage.setItem('kalolsavam_dark', active);
    updateToggleUI(toggleBtn, toggleBtnMobile, active);
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', handleToggle);
  }
  if (toggleBtnMobile) {
    toggleBtnMobile.addEventListener('click', handleToggle);
  }

  updateToggleUI(toggleBtn, toggleBtnMobile, document.body.classList.contains('dark'));
}

function updateToggleUI(desktopBtn, mobileBtn, isDark) {
  const sunSvg = `<svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"></circle><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>`;
  const moonSvg = `<svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>`;

  if (desktopBtn) {
    desktopBtn.innerHTML = isDark ? sunSvg : moonSvg;
    desktopBtn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
  }
  if (mobileBtn) {
    mobileBtn.innerHTML = isDark ? sunSvg : moonSvg;
    mobileBtn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
  }
}

function initMobileMenu() {
  const btn = document.getElementById('mobile-menu-btn');
  const menu = document.getElementById('mobile-menu');
  if (btn && menu) {
    btn.addEventListener('click', () => {
      menu.classList.toggle('open');
    });
    menu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        menu.classList.remove('open');
      });
    });
    window.addEventListener('resize', () => {
      if (window.innerWidth >= 768) {
        menu.classList.remove('open');
      }
    });
  }
}

function initPrefetch() {
  const preloadedPages = new Map();

  function prefetchPage(url) {
    if (!url || preloadedPages.has(url)) return;
    preloadedPages.set(url, true);
    const fetchUrl = url.startsWith('http') ? url : new URL(url, window.location.href).href;
    fetch(fetchUrl, { mode: 'no-cors' }).catch(() => {});
  }

  const links = document.querySelectorAll('nav a, #mobile-menu a, .hero-section a, .card-base');
  links.forEach(link => {
    const href = link.getAttribute('href') || (link.tagName === 'A' ? null : link.getAttribute('onclick') || link.querySelector('a')?.getAttribute('href'));
    if (href && !href.startsWith('http') && !href.startsWith('#') && !href.startsWith('tel:') && !href.startsWith('mailto:')) {
      prefetchPage(href);
      link.addEventListener('mouseenter', () => prefetchPage(href), { once: true });
      link.addEventListener('touchstart', () => prefetchPage(href), { once: true });
    }
  });

  // Also proactively prefetch all inner pages on load for zero-delay switching
  const internalPages = ['index.html', 'pages/venues.html', 'pages/competitions.html', 'pages/photos.html', 'pages/facilities.html', 'pages/help.html'];
  setTimeout(() => {
    internalPages.forEach(page => prefetchPage(page));
  }, 200);
}

function initCardObservers() {
  const observerOptions = {
    threshold: 0.05,
    rootMargin: '0px 0px -20px 0px'
  };

  const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  document.querySelectorAll('.card-base').forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(12px)';
    card.style.transition = `opacity 0.35s cubic-bezier(0.05, 0.7, 0.1, 1) ${index * 0.03}s, transform 0.35s cubic-bezier(0.05, 0.7, 0.1, 1) ${index * 0.03}s`;
    observer.observe(card);
  });
}
