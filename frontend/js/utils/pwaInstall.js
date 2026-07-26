// ============================================================
// pwaInstall.js - PWA 安装引导
// ============================================================

let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  console.log('[PWA] beforeinstallprompt 已捕获');
});

window.addEventListener('appinstalled', () => {
  console.log('[PWA] 已安装到主屏幕');
  deferredPrompt = null;
});

export function triggerInstall() {
  const ua = navigator.userAgent.toLowerCase();
  const isIOS = /iphone|ipad|ipod/.test(ua);
  const isAndroid = /android/.test(ua);
  const isMobile = isIOS || isAndroid;

  if (!isMobile) {
    _showQRCodeModal();
    return;
  }

  if (deferredPrompt) {
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then((choice) => {
      console.log('[PWA] 用户选择:', choice.outcome);
      deferredPrompt = null;
    });
    return;
  }

  if (isIOS) {
    _showIOSGuide();
    return;
  }

  _showAndroidFallback();
}

function _showQRCodeModal() {
  const url = window.location.origin + window.location.pathname;
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=280x280&data=${encodeURIComponent(url)}`;

  _showModal('扫码到手机使用', `
    <div style="text-align:center;padding:8px;">
      <img src="${qrUrl}" alt="二维码" style="width:220px;height:220px;border:1px solid #eee;border-radius:8px;" />
      <p style="margin:16px 0 8px;color:#333;font-size:14px;">用手机浏览器扫码打开</p>
      <p style="margin:0;color:#888;font-size:12px;word-break:break-all;">${url}</p>
      <button id="pwa-copy-btn" style="margin-top:16px;padding:8px 20px;background:#4A9BF5;color:white;border:none;border-radius:6px;cursor:pointer;font-size:14px;">
        复制链接
      </button>
    </div>
  `);

  setTimeout(() => {
    const btn = document.getElementById('pwa-copy-btn');
    if (btn) btn.onclick = () => {
      navigator.clipboard?.writeText(url).then(() => {
        btn.textContent = '已复制';
        setTimeout(() => btn.textContent = '复制链接', 1500);
      });
    };
  }, 100);
}

function _showIOSGuide() {
  _showModal('添加到主屏幕（iOS）', `
    <div style="padding:8px;color:#333;font-size:14px;line-height:1.8;">
      <p><b>1.</b> 点击底部 <span style="color:#4A9BF5;">分享</span> 按钮 <span style="font-size:20px;">⬆️</span></p>
      <p><b>2.</b> 下拉找到 <b>「添加到主屏幕」</b></p>
      <p><b>3.</b> 点击 <b>「添加」</b> 完成</p>
      <div style="margin-top:16px;padding:12px;background:#F0F6FC;border-radius:6px;color:#666;font-size:13px;">
        安装后即可像原生 App 一样从桌面启动，支持离线打开
      </div>
    </div>
  `);
}

function _showAndroidFallback() {
  _showModal('已安装或需手动添加', `
    <div style="padding:8px;color:#333;font-size:14px;line-height:1.8;">
      <p>浏览器已不支持自动安装引导。请手动添加：</p>
      <p><b>1.</b> 点击浏览器右上角 <b>菜单</b></p>
      <p><b>2.</b> 选择 <b>「添加到主屏幕」</b> 或 <b>「安装应用」</b></p>
    </div>
  `);
}

function _showModal(title, htmlContent) {
  const old = document.getElementById('pwa-modal-mask');
  if (old) old.remove();

  const mask = document.createElement('div');
  mask.id = 'pwa-modal-mask';
  Object.assign(mask.style, {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.5)', zIndex: 9999,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  });

  const box = document.createElement('div');
  Object.assign(box.style, {
    background: 'white', borderRadius: '12px', padding: '24px',
    maxWidth: '360px', width: '90%', boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
  });
  box.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h3 style="margin:0;font-size:16px;color:#333;">${title}</h3>
      <span id="pwa-modal-close" style="cursor:pointer;font-size:22px;color:#999;line-height:1;">×</span>
    </div>
    ${htmlContent}
  `;
  mask.appendChild(box);
  document.body.appendChild(mask);

  const close = () => mask.remove();
  document.getElementById('pwa-modal-close').onclick = close;
  mask.onclick = (e) => { if (e.target === mask) close(); };
}