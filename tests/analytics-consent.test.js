const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const consentScript = fs.readFileSync(
  path.join(__dirname, '..', 'static', 'analytics-consent.js'),
  'utf8'
);

function createPage(savedChoice = null, initialCookies = '', options = {}) {
  const elements = new Map();
  const scripts = [];
  const storage = new Map(savedChoice ? [['career-platform-analytics-consent', savedChoice]] : []);
  const sessionStorage = options.sessionStorage || new Map();
  const cookieWrites = [];

  function element(id) {
    if (!elements.has(id)) {
      elements.set(id, {
        hidden: id === 'analytics-consent',
        textContent: '',
        focused: false,
        listeners: {},
        addEventListener(type, callback) { this.listeners[type] = callback; },
        focus() { this.focused = true; },
        setAttribute(name, value) { this[name] = value; },
      });
    }
    return elements.get(id);
  }

  const documentListeners = {};

const document = {
  getElementById: element,
  addEventListener(type, callback) {
    documentListeners[type] = callback;
  },
  createElement(tag) {
    return { tagName: tag.toUpperCase() };
  },
  querySelectorAll() {
    return [];
  },
  head: {
    appendChild(script) {
      scripts.push(script);
    },
  },
  get cookie() {
    return initialCookies;
  },
  set cookie(value) {
    cookieWrites.push(value);
  },
};
  const localStorage = {
    getItem(key) { return storage.has(key) ? storage.get(key) : null; },
    setItem(key, value) {
      if (options.failLocalStorageWrites) throw new Error('storage unavailable');
      storage.set(key, value);
    },
  };
    const sessionStorageApi = {
    getItem(key) { return sessionStorage.has(key) ? sessionStorage.get(key) : null; },
    removeItem(key) { sessionStorage.delete(key); },
    setItem(key, value) {
      if (options.failSessionStorageWrites) throw new Error('session storage unavailable');
      sessionStorage.set(key, value);
    },
  };

  const window = {
  location: {
    hostname: 'localhost',
    reloadCount: 0,
    reload() {
      this.reloadCount++;
    },
  },
};

  window.localStorage = localStorage;
  window.sessionStorage = sessionStorageApi;
  const context = { window, document, localStorage, URL, Date, console };
  vm.runInNewContext(consentScript, context, { filename: 'analytics-consent.js' });

  return {
    elements,
    scripts,
    storage,
    sessionStorage,
    cookieWrites,
    window,
    click(id) { element(id).listeners.click(); },
  };
}

test('first visit waits for a choice, then loads exactly one configured GA tag on acceptance', () => {
  const page = createPage(null, '_ga=old; _ga_OLD=session; unrelated=keep');
  assert.equal(page.elements.get('analytics-consent').hidden, false);
  assert.equal(page.scripts.length, 0);
  assert.ok(page.cookieWrites.some(value => value.startsWith('_ga=;')));
  assert.ok(page.cookieWrites.some(value => value.startsWith('_ga_OLD=;')));

  page.click('analytics-accept');
  page.click('analytics-accept');
  assert.equal(page.storage.get('career-platform-analytics-consent'), 'accepted');
  assert.equal(page.scripts.length, 1);
  assert.equal(page.scripts[0].src, 'https://www.googletagmanager.com/gtag/js?id=G-D1DVSB3CWV');
  assert.equal(page.window.dataLayer.filter(args => Array.from(args)[0] === 'config').length, 1);
  assert.deepEqual(Array.from(page.window.dataLayer.find(args => Array.from(args)[0] === 'config')), ['config', 'G-D1DVSB3CWV']);
});

test('rejecting analytics on a first visit never loads the Google Analytics script', () => {
  const page = createPage();
  assert.equal(page.elements.get('analytics-consent').hidden, false);
  page.click('analytics-reject');
  assert.equal(page.storage.get('career-platform-analytics-consent'), 'rejected');
  assert.equal(page.scripts.length, 0);
});

test('a saved rejection keeps GA unloaded and settings can reopen the choice', () => {
  const page = createPage('rejected');
  assert.equal(page.elements.get('analytics-consent').hidden, true);
  assert.equal(page.scripts.length, 0);

  page.click('analytics-settings');
  assert.equal(page.elements.get('analytics-consent').hidden, false);
  assert.equal(page.elements.get('analytics-accept').focused, true);
  page.click('analytics-accept');
  assert.equal(page.scripts.length, 1);
});

test('withdrawing saved acceptance removes GA cookies and reloads without loading GA again', () => {
  const page = createPage('accepted', '_ga=client; _ga_OLD=session; _gid=visit; preference=keep');
  assert.equal(page.scripts.length, 1);

  page.click('analytics-settings');
  page.click('analytics-reject');
  assert.equal(page.storage.get('career-platform-analytics-consent'), 'rejected');
  assert.equal(page.window.location.reloadCount, 1);
  assert.ok(page.cookieWrites.some(value => value.startsWith('_ga=;')));
  assert.ok(page.cookieWrites.some(value => value.startsWith('_ga_OLD=;')));
  assert.ok(page.cookieWrites.some(value => value.startsWith('_gid=;')));
  assert.ok(!page.cookieWrites.some(value => value.startsWith('preference=;')));
  assert.equal(page.scripts.length, 1);
  assert.ok(page.window.dataLayer.some(args => {
    const command = Array.from(args);
    return command[0] === 'consent' && command[1] === 'update' && command[2].analytics_storage === 'denied';
  }));

  const reloadedPage = createPage('rejected');
  assert.equal(reloadedPage.scripts.length, 0);
});

test('failed preference save stops analytics and uses session rejection across reload', () => {
  const page = createPage('accepted', '', { failLocalStorageWrites: true });
  assert.equal(page.scripts.length, 1);

  page.click('analytics-settings');
  page.click('analytics-reject');
  assert.equal(page.window.location.reloadCount, 1);
  assert.equal(page.scripts.length, 1);
  assert.match(page.elements.get('analytics-consent-status').textContent, /could not be saved/);

  const reloadedPage = createPage('accepted', '', { sessionStorage: page.sessionStorage });
  assert.equal(reloadedPage.scripts.length, 0);
  assert.equal(reloadedPage.elements.get('analytics-consent').hidden, true);
  reloadedPage.click('analytics-settings');
  reloadedPage.click('analytics-accept');
  assert.equal(reloadedPage.scripts.length, 1);
  const nextPage = createPage('accepted', '', { sessionStorage: page.sessionStorage });
  assert.equal(nextPage.scripts.length, 1);
});

test('if both storage APIs fail, withdrawal stops analytics without reloading or claiming persistence', () => {
  const page = createPage('accepted', '', {
    failLocalStorageWrites: true,
    failSessionStorageWrites: true,
  });
  page.click('analytics-settings');
  page.click('analytics-reject');
  assert.equal(page.window.location.reloadCount, 0);
  assert.equal(page.scripts.length, 1);
  assert.match(page.elements.get('analytics-consent-status').textContent, /may load again if you reload/);
});
