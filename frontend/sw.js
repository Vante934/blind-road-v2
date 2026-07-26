// 视界项目 - Service Worker (重构版占位)
// 当前版本：主动清理旧缓存，暂不启用缓存策略（重构完成后再启用）
const CACHE_VERSION = 'shijie-v2-dev';


self.addEventListener('install', (e) => {
  self.skipWaiting();
});


self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});


// 开发期：所有请求直接走网络，不使用缓存
self.addEventListener('fetch', (e) => {
  // 不拦截，让浏览器默认处理
});