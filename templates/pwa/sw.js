{% load static %}// Service worker do Bahia Car. Deixa o sistema instalável como app.
// Estáticos: REDE primeiro (sempre a versão nova), com cache só de reserva
// pra quando a internet cair. Assim uma atualização de visual aparece na hora.
const CACHE = "bahiacar-v3";
const ASSETS = [
  "{% static 'css/output.css' %}",
  "{% static 'js/htmx.min.js' %}",
  "{% static 'img/icon-192.png' %}"
];

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await Promise.allSettled(ASSETS.map((a) => c.add(a)));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const chaves = await caches.keys();
    await Promise.all(chaves.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin && url.pathname.includes("/static/")) {
    // Rede primeiro; se falhar (offline), usa o que estiver no cache.
    e.respondWith((async () => {
      try {
        const resp = await fetch(req);
        const c = await caches.open(CACHE);
        c.put(req, resp.clone());
        return resp;
      } catch (err) {
        const cacheado = await caches.match(req);
        if (cacheado) return cacheado;
        throw err;
      }
    })());
  }
});
