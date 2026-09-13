const CACHE="tracepulse-shell-v2";
const STATIC=["./","./index.html","./manifest.webmanifest","./icons/icon-192.svg","./icons/icon-512.svg","./icons/maskable-512.svg"];
const scoped=(p)=>new URL(p,self.registration.scope).toString();
const same=(u)=>u.origin===self.location.origin;
const api=(u)=>u.pathname.includes("/api/")||u.pathname.includes("/socket.io/");
const sensitive=(r)=>r.method!=="GET"||r.headers.has("authorization")||r.headers.has("cookie")||r.cache==="no-store";
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(STATIC))));
self.addEventListener("activate",e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith("tracepulse-shell-")&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",e=>{const r=e.request,u=new URL(r.url);if(!same(u)||api(u)||sensitive(r))return;if(r.mode==="navigate")e.respondWith(fetch(r).catch(()=>caches.match(scoped("./index.html"))));else if(["script","style","image","font","manifest"].includes(r.destination))e.respondWith(caches.match(r).then(hit=>hit||fetch(r).then(async response=>{if(response.ok){const c=await caches.open(CACHE);await c.put(r,response.clone());}return response;})));});