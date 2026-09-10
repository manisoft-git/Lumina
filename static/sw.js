// Lumina v5.2 Service Worker — Zero-Cloud Offline Resilience
const CACHE_NAME = 'lumina-v5.2-cache';
const OFFLINE_URLS = [
    '/',
    '/games',
    '/competitions',
    '/offline-hub',
    '/static/style.css',
    '/static/theme.css',
    '/static/audio.js',
    '/static/socket.io.min.js',
    '/static/chart.umd.min.js',
    '/static/qrcode.min.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(OFFLINE_URLS).catch(err => console.warn('PWA Cache pre-fill partial:', err));
        }).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    // Stale-while-revalidate for static assets, network-first for HTML
    if (event.request.method !== 'GET') return;
    
    if (event.request.url.includes('/static/')) {
        event.respondWith(
            caches.match(event.request).then((cached) => {
                return cached || fetch(event.request).then((response) => {
                    const cloned = response.clone();
                    caches.open(CACHE_NAME).then((c) => c.put(event.request, cloned));
                    return response;
                });
            })
        );
    } else {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
    }
});
