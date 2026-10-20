(() => {
  const measurementId = 'G-D1DVSB3CWV';
  const preferenceKey = 'career-platform-analytics-consent';
  const sessionRejectionKey = 'career-platform-analytics-rejected-this-session';
  const banner = document.getElementById('analytics-consent');
  const acceptButton = document.getElementById('analytics-accept');
  const rejectButton = document.getElementById('analytics-reject');
  const settingsButton = document.getElementById('analytics-settings');
  const status = document.getElementById('analytics-consent-status');
  let analyticsLoaded = false;
  let analyticsWithdrawn = false;

  if (!banner || !acceptButton || !rejectButton || !settingsButton || !status) return;

  function getChoice() {
    try {
      const choice = window.localStorage.getItem(preferenceKey);
      return choice === 'accepted' || choice === 'rejected' ? choice : null;
    } catch {
      return null;
    }
  }

  function hasSessionRejection() {
    try {
      return window.sessionStorage.getItem(sessionRejectionKey) === 'rejected';
    } catch {
      return false;
    }
  }

  function saveSessionRejection() {
    try {
      window.sessionStorage.setItem(sessionRejectionKey, 'rejected');
      return true;
    } catch {
      return false;
    }
  }

  function clearSessionRejection() {
    try {
      window.sessionStorage.removeItem(sessionRejectionKey);
      return true;
    } catch {
      return false;
    }
  }

  function saveChoice(choice) {
    try {
      window.localStorage.setItem(preferenceKey, choice);
      return true;
    } catch {
      status.textContent = 'Your choice could not be saved, so analytics remains off. Please check your browser storage settings and try again.';
      return false;
    }
  }

  function clearAnalyticsCookies() {
    const names = document.cookie
      .split(';')
      .map(cookie => cookie.trim().split('=')[0])
      .filter(name => /^_(?:ga(?:_|$)|gid$|gat(?:_|$))/.test(name));
    const hostname = window.location.hostname;
    const parts = hostname.split('.');
    const domains = new Set(['', `; domain=${hostname}`]);
    if (parts.length > 2) domains.add(`; domain=.${parts.slice(-2).join('.')}`);

    for (const name of names) {
      for (const domain of domains) {
        document.cookie = `${name}=; Max-Age=0; path=/${domain}; SameSite=Lax`;
      }
    }
  }

  function loadAnalytics() {
    if (analyticsLoaded || analyticsWithdrawn) return;
    analyticsLoaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', measurementId);

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
    document.head.appendChild(script);
  }

  function stopAnalytics() {
    analyticsWithdrawn = true;
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', { analytics_storage: 'denied' });
    }
    // Keep the queued denial command available for gtag.js to process.
    window.gtag = function () {};
  }

  function showBanner(moveFocus = false) {
    banner.hidden = false;
    settingsButton.setAttribute('aria-expanded', 'true');
    status.textContent = '';
    if (moveFocus) acceptButton.focus();
  }

  function hideBanner() {
    banner.hidden = true;
    settingsButton.setAttribute('aria-expanded', 'false');
  }

  acceptButton.addEventListener('click', () => {
    if (!saveChoice('accepted')) return;
    if (!clearSessionRejection()) {
      status.textContent = 'Your earlier decline is still active for this browser session because the browser could not update session storage.';
      return;
    }
    hideBanner();
    loadAnalytics();
    status.textContent = 'Analytics accepted.';
  });

  rejectButton.addEventListener('click', () => {
    const saved = saveChoice('rejected');
    const sessionSaved = saveSessionRejection();
    clearAnalyticsCookies();
    stopAnalytics();
    hideBanner();
    if (saved) {
      status.textContent = 'Analytics declined. Your choice was saved.';
    } else if (sessionSaved) {
      status.textContent = 'Analytics stopped for this page and the rest of this browser session. Your choice could not be saved for future sessions.';
    } else {
      status.textContent = 'Analytics stopped for this page, but your choice could not be saved. It may load again if you reload or open another page.';
    }
    if (analyticsLoaded && (saved || sessionSaved)) window.location.reload();
  });

  settingsButton.addEventListener('click', () => showBanner(true));

  const choice = hasSessionRejection() ? 'rejected' : getChoice();
  if (choice === 'accepted') {
    hideBanner();
    loadAnalytics();
  } else {
    clearAnalyticsCookies();
    if (choice === 'rejected') hideBanner();
    else showBanner();
  }
})();
