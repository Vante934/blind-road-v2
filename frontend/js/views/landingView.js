/**
 * 视界项目 - 落地页视图控制器
 */

import { showMobileOnlyToast } from '../utils/toast.js';


export class LandingView {

  constructor(router) {
    this.router = router;
  }


  init() {
    const view = document.getElementById('view-landing');
    if (!view) return;

    view.addEventListener('click', (e) => {
      const card = e.target.closest('[data-feature]');
      if (!card) return;
      const feature = card.dataset.feature;
      this._handleFeatureClick(feature);
    });
  }


  _handleFeatureClick(feature) {
    switch (feature) {
      case 'detect':
        this.router.navigate('#/detect');
        break;
      case 'annotate':
        this.router.navigate('#/annotate');
        break;
      case 'download':
        showMobileOnlyToast('手机端安装');
        break;
    }
  }
}