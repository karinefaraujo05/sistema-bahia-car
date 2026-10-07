{% load static %}// Service worker do Bahia Car. Deixa o sistema instalável como app e
// serve os arquivos estáticos do cache quando a internet oscila.
const CACHE = "bahiacar-v1";
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
  // Só mexe nos estáticos (cache primeiro). As páginas vão sempre pela rede,
  // pra nunca mostrar dado velho do negócio.
  if (url.origin === location.origin && url.pathname.includes("/static/")) {
    e.respondWith((async () => {
      const cacheado = await caches.match(req);
      if (cacheado) return cacheado;
      const resp = await fetch(req);
      const c = await caches.open(CACHE);
      c.put(req, resp.clone());
      return resp;
    })());
  }
});
