/* SentinelAI Service Worker — PWA offline support (v2)
 *
 * Why v2: the previous worker served "/" and "/index.html" cache-first under a
 * cache name that never changed, so after every deploy the cached HTML kept
 * pointing at chunk hashes that no longer existed. Vercel then answered those
 * missing chunks with index.html (text/html), and the browser refused to run a
 * module script with the wrong MIME type — a blank page.
 *
 * Rules now:
 *   - navigations  -> network-first (always pick up a new deploy), HTML cache fallback offline
 *   - /api/        -> network-first (never cached)
 *   - /assets/     -> cache-first (hashed/immutable), but never cache HTML responses
 *   - everything else -> stale-while-revalidate, HTML never cached
 */

const VERSION = 'v2';
const HTML_CACHE = `sentinelai-html-${VERSION}`;
const STATIC_CACHE = `sentinelai-static-${VERSION}`;

const isHtml = (res) => (res.headers.get('content-type') || '').includes('text/html');

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(HTML_CACHE)
      .then((cache) => cache.add(new Request('/index.html', { cache: 'reload' })))
      .catch(() => undefined)
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => !key.endsWith(VERSION)).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (!url.protocol.startsWith('http')) return;
  // Never intercept third-party requests.
  if (url.origin !== self.location.origin) return;

  // ── API: network-first, no caching ──────────────────────────────
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(
        () =>
          new Response(
            JSON.stringify({
              success: false,
              error: { code: 'offline', message: 'You appear to be offline.' },
            }),
            { status: 503, headers: { 'Content-Type': 'application/json' } },
          ),
      ),
    );
    return;
  }

  // ── Navigations: network-first so a new deploy is picked up ─────
  if (request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(request);
          if (fresh && fresh.ok && isHtml(fresh)) {
            const cache = await caches.open(HTML_CACHE);
            cache.put('/index.html', fresh.clone());
          }
          return fresh;
        } catch {
          const cached = await caches.match('/index.html');
          return (
            cached ||
            new Response('You are offline.', {
              status: 503,
              headers: { 'Content-Type': 'text/plain' },
            })
          );
        }
      })(),
    );
    return;
  }

  // ── Hashed build assets: cache-first, HTML never cached ─────────
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      (async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        const res = await fetch(request);
        if (res.ok && !isHtml(res)) {
          const cache = await caches.open(STATIC_CACHE);
          cache.put(request, res.clone());
        }
        return res;
      })(),
    );
    return;
  }

  // ── Other static files: stale-while-revalidate ──────────────────
  event.respondWith(
    (async () => {
      const cached = await caches.match(request);
      const network = fetch(request)
        .then((res) => {
          if (res.ok && !isHtml(res)) {
            caches.open(STATIC_CACHE).then((cache) => cache.put(request, res.clone()));
          }
          return res;
        })
        .catch(() => null);

      return cached || (await network) || new Response('Offline', { status: 503 });
    })(),
  );
});

// ── Push notifications ────────────────────────────────────────────
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {
    title: 'SentinelAI Alert',
    body: 'New security event detected',
    icon: '/icon-192.png',
  };

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || '/icon-192.png',
      badge: '/icon-192.png',
      data: data.url || '/dashboard',
      actions: [
        { action: 'view', title: 'View' },
        { action: 'dismiss', title: 'Dismiss' },
      ],
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  event.waitUntil(self.clients.openWindow(event.notification.data || '/dashboard'));
});
