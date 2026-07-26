/**
 * 视界项目 - 应用主入口
 */
import { Router } from './router.js';
import { isMobileDevice } from './utils/device.js';
import { LandingView } from './views/landingView.js';
import { DetectView } from './views/detectView.js';
import { AnnotateView } from './views/annotateView.js';
import { showToast } from './utils/toast.js';
import { triggerInstall } from './utils/pwaInstall.js';

let detectView = null;
let annotateView = null;

class App {

  constructor() {
    this.router = new Router();
    this.isMobile = isMobileDevice();
  }


  init() {
    console.log('[App] 初始化', { isMobile: this.isMobile });
    document.body.classList.add(this.isMobile ? 'is-mobile' : 'is-desktop');

    document.querySelectorAll('[data-nav]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.navigate(el.dataset.nav);
      });
    });

    new LandingView(this.router).init();

    this.router.register('#/', 'view-landing');
    this.router.register('#/detect', 'view-detect', {
      onEnter: () => this._onEnterDetect(),
      onLeave: () => this._onLeaveDetect(),
    });
    this.router.register('#/annotate', 'view-annotate', {
      onEnter: () => this._onEnterAnnotate(),
      onLeave: () => this._onLeaveAnnotate(),
    });

    this.router.start('#/');

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').then(reg => {
        reg.update();
      }).catch(() => {});
    }

    const installBtn = document.querySelector('[data-action="install"]');
    if (installBtn) {
      installBtn.addEventListener('click', (e) => {
        e.preventDefault();
        triggerInstall();
      });
    }

    document.querySelectorAll('.nav-install, #btn-install').forEach(el => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        triggerInstall();
      });
    });
  }

  _onEnterDetect() {
    if (!detectView) {
      detectView = new DetectView();
    }
    detectView.init();
  }

  _onLeaveDetect() {
    if (detectView) {
      detectView.destroy && detectView.destroy();
    }
  }

  _onEnterAnnotate() {
    if (!annotateView) {
      annotateView = new AnnotateView();
    }
    annotateView.init();
  }

  _onLeaveAnnotate() {
    if (annotateView) {
      annotateView.destroy && annotateView.destroy();
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.__app = new App();
  window.__app.init();
});