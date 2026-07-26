// ============================================================ 
 // proTabs.js — 专业工具介绍区块的 Tab 切换逻辑 
 // 轻量独立模块，由 annotateView 在 init() 时调用 
 // ============================================================ 
 
 export function initProTabs() { 
   const btns   = document.querySelectorAll('.pro-tab-btn'); 
   const panels = document.querySelectorAll('.pro-tab-panel'); 
 
   if (!btns.length) return; 
 
   btns.forEach(btn => { 
     btn.addEventListener('click', () => { 
       const target = btn.dataset.tab; 
 
       btns.forEach(b => b.classList.remove('active')); 
       panels.forEach(p => p.classList.remove('active')); 
 
       btn.classList.add('active'); 
       const panel = document.getElementById(target); 
       if (panel) panel.classList.add('active'); 
     }); 
   }); 
 
   _tryLoadScreenshots(); 
 } 
 
 function _tryLoadScreenshots() { 
   const shots = [ 
     { img: 'screenshot-train-img', placeholder: 'screenshot-train' }, 
     { img: 'screenshot-eval-img',  placeholder: 'screenshot-eval'  }, 
   ]; 
   shots.forEach(({ img, placeholder }) => { 
     const imgEl = document.getElementById(img); 
     if (!imgEl) return; 
     imgEl.addEventListener('load', () => { 
       imgEl.classList.remove('hidden'); 
       const ph = document.getElementById(placeholder); 
       if (ph) ph.classList.add('hidden'); 
     }); 
   }); 
 }