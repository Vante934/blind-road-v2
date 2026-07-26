/**
 * 视界项目 - Toast 提示组件
 */

let container = null;


function ensureContainer() {
  if (container) return container;
  container = document.createElement('div');
  container.className = 'toast-container';
  container.setAttribute('role', 'status');
  container.setAttribute('aria-live', 'polite');
  document.body.appendChild(container);
  return container;
}


export function showToast(message, type = 'info', duration = 3000) {
  const c = ensureContainer();
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  c.appendChild(el);
  setTimeout(() => {
    el.classList.add('toast-hide');
    setTimeout(() => el.remove(), 300);
  }, duration);
}


export function showMobileOnlyToast(featureName) {
  showToast(`${featureName} 是移动端专属功能，请扫码在手机上体验`, 'warning', 4000);
}