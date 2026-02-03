/**
 * Service Worker - CIANET Atendente PWA
 * Versão: 3.0
 * 
 * Funcionalidades:
 * - Cache de assets estáticos
 * - Cache de API com strategy network-first
 * - Suporte offline básico
 * - Push notifications
 * - Background sync
 */

const CACHE_NAME = 'cianet-atendente-v3';
const API_CACHE = 'cianet-api-v3';

// Assets para cache imediato
const STATIC_ASSETS = [
    '/',
    '/mobile',
    '/mobile/chat',
    '/static/manifest.json',
    '/static/css/mobile.css',
    '/static/js/mobile-app.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Instalar Service Worker
self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker v3...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS.filter(url => !url.includes('undefined')));
            })
            .then(() => {
                console.log('[SW] Static assets cached');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Cache error:', error);
            })
    );
});

// Ativar Service Worker
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME && cacheName !== API_CACHE) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[SW] Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Interceptar requisições
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Ignorar requisições de extensões
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    // Estratégia diferente para API vs Static
    if (url.pathname.startsWith('/api/')) {
        // Network-first para API
        event.respondWith(networkFirstStrategy(request));
    } else {
        // Cache-first para static
        event.respondWith(cacheFirstStrategy(request));
    }
});

/**
 * Network First Strategy
 * Tenta rede primeiro, fallback para cache
 */
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        
        // Cache resposta se sucesso
        if (networkResponse.ok) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed, trying cache:', request.url);
        
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Retornar resposta offline
        return new Response(
            JSON.stringify({
                error: 'offline',
                message: 'Você está offline. Conecte-se à internet para continuar.'
            }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

/**
 * Cache First Strategy
 * Usa cache se disponível, fallback para rede
 */
async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        // Cache resposta
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Fetch failed:', request.url);
        
        // Página offline para navegação
        if (request.mode === 'navigate') {
            return caches.match('/offline.html');
        }
        
        return new Response('Offline', { status: 503 });
    }
}

// Push Notifications
self.addEventListener('push', (event) => {
    console.log('[SW] Push received');
    
    let data = {
        title: 'CIANET Atendente',
        body: 'Nova mensagem recebida',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge.png',
        tag: 'cianet-notification'
    };
    
    if (event.data) {
        try {
            data = { ...data, ...event.data.json() };
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        tag: data.tag,
        data: data,
        vibrate: [100, 50, 100],
        actions: [
            { action: 'open', title: 'Abrir' },
            { action: 'close', title: 'Fechar' }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Clique na notificação
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked');
    
    event.notification.close();
    
    if (event.action === 'close') {
        return;
    }
    
    // Abrir ou focar na janela
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Se já tem uma janela aberta, focar
                for (const client of clientList) {
                    if (client.url.includes('/mobile') && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // Senão, abrir nova
                if (clients.openWindow) {
                    const url = event.notification.data?.url || '/mobile/chat';
                    return clients.openWindow(url);
                }
            })
    );
});

// Background Sync
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'sync-messages') {
        event.waitUntil(syncMessages());
    }
});

/**
 * Sincronizar mensagens pendentes
 */
async function syncMessages() {
    console.log('[SW] Syncing pending messages...');
    
    try {
        // Abrir IndexedDB para mensagens pendentes
        const db = await openDB('cianet-offline', 1);
        const tx = db.transaction('pending-messages', 'readonly');
        const store = tx.objectStore('pending-messages');
        const messages = await store.getAll();
        
        for (const msg of messages) {
            try {
                await fetch('/api/messages/v2/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${msg.token}`
                    },
                    body: JSON.stringify(msg.data)
                });
                
                // Remover do pending se sucesso
                const deleteTx = db.transaction('pending-messages', 'readwrite');
                deleteTx.objectStore('pending-messages').delete(msg.id);
                
                console.log('[SW] Message synced:', msg.id);
            } catch (error) {
                console.error('[SW] Failed to sync message:', msg.id, error);
            }
        }
    } catch (error) {
        console.error('[SW] Sync failed:', error);
    }
}

/**
 * Abrir IndexedDB
 */
function openDB(name, version) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(name, version);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            if (!db.objectStoreNames.contains('pending-messages')) {
                db.createObjectStore('pending-messages', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

console.log('[SW] Service Worker loaded');
