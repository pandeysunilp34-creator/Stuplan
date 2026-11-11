const CACHE_NAME='stuplan-v1';
self.addEventListener('install',e=>{self.skipWaiting();});
self.addEventListener('activate',e=>{self.clients.claim();});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});
self.addEventListener('push',e=>{let d={title:'StuPlan',body:'通知'};try{d=e.data.json();}catch(err){}e.waitUntil(self.registration.showNotification(d.title,{body:d.body,icon:'/static/icon-192.png'}));});
self.addEventListener('notificationclick',e=>{e.notification.close();e.waitUntil(clients.openWindow('/home'));});