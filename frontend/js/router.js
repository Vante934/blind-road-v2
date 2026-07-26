/**
 * 视界项目 - 简单 Hash 路由
 * 负责根据 URL hash 切换 .view 容器的显示状态
 */

export class Router {
  constructor() {
    this.routes = new Map();  // hash -> { viewId, onEnter, onLeave }
    this.currentRoute = null;
    this._bindEvents();
  }

  /**
   * 注册路由
   * @param {string} hash - 如 '#/detect'
   * @param {string} viewId - 对应的视图元素 id
   * @param {object} handlers - { onEnter, onLeave } 回调
   */
  register(hash, viewId, handlers = {}) {
    this.routes.set(hash, { viewId, ...handlers });
  }

  /**
   * 手动导航
   */
  navigate(hash) {
    if (window.location.hash !== hash) {
      window.location.hash = hash;
    } else {
      this._handleRouteChange();
    }
  }

  /**
   * 启动路由（初始化时调用）
   */
  start(defaultHash = '#/') {
    if (!window.location.hash) {
      window.location.hash = defaultHash;
    } else {
      this._handleRouteChange();
    }
  }

  _bindEvents() {
    window.addEventListener('hashchange', () => this._handleRouteChange());
  }

  _handleRouteChange() {
    const hash = window.location.hash || '#/';
    const route = this.routes.get(hash);

    if (!route) {
      console.warn(`[Router] 未找到路由: ${hash}`);
      return;
    }

    // 触发离开回调
    if (this.currentRoute && this.currentRoute.onLeave) {
      try { this.currentRoute.onLeave(); } catch (e) { console.error(e); }
    }

    // 隐藏所有视图
    document.querySelectorAll('.view').forEach(el => {
      el.classList.remove('active');
    });

    // 显示新视图
    const viewEl = document.getElementById(route.viewId);
    if (viewEl) {
      viewEl.classList.add('active');
    } else {
      console.error(`[Router] 视图元素不存在: ${route.viewId}`);
    }

    // 触发进入回调
    if (route.onEnter) {
      try { route.onEnter(); } catch (e) { console.error(e); }
    }

    // 更新当前路由
    this.currentRoute = route;

    console.log(`[Router] 已切换到: ${hash}`);
  }
}