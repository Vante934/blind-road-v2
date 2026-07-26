const CACHE = 'shijie-v2.0';
const PRECACHE = [
    '/',
    '/index.html',
    '/css/style.css',
    '/js/app.js',
    '/js/camera.js',
    '/js/ws.js',
    '/js/renderer.js',
    '/js/voice.js',
    '/js/gesture.js',
    '/js/auth.js',
    '/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE)
            .then((cache) => Promise.allSettled(
                PRECACHE.map(url => cache.add(url).catch(e => console.warn('skip:', url)))
            ))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    const currentCaches = [CACHE];
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return cacheNames.filter((cacheName) => !currentCaches.includes(cacheName));
        }).then((cachesToDelete) => {
            return Promise.all(cachesToDelete.map((cacheToDelete) => {
                return caches.delete(cacheToDelete);
            }));
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.url.includes('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    if (event.request.url.includes('/ws/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            return cachedResponse || fetch(event.request);
        })
    );
});