/**
 * 视界项目 - 设备类型检测
 * 综合多种方式判断当前是否为移动设备
 */

export function isMobileDevice() {
  const hasTouch = navigator.maxTouchPoints > 0;
  const isNarrow = window.matchMedia('(max-width: 768px)').matches;
  const mobileUA = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
  
  return [hasTouch, isNarrow, mobileUA].filter(Boolean).length >= 2;
}

export function isIOS() {
  return /iPhone|iPad|iPod/i.test(navigator.userAgent);
}

export function isAndroid() {
  return /Android/i.test(navigator.userAgent);
}

export function watchDeviceChange(callback) {
  const mq = window.matchMedia('(max-width: 768px)');
  mq.addEventListener('change', () => callback(isMobileDevice()));
}