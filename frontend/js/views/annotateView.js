// ============================================================ 
 // annotateView.js — 标注工具页控制器 
 // 「视界」盲道智能导航系统 
 // ============================================================ 
 
 import { initProTabs } from '../utils/proTabs.js';

const CATEGORIES = [ 
   { id: 0, name: '盲道',  color: '#4A9BF5' }, 
   { id: 1, name: '障碍物', color: '#F5222D' }, 
   { id: 2, name: '行人',  color: '#52C41A' }, 
   { id: 3, name: '车辆',  color: '#FAAD14' }, 
   { id: 4, name: '坑洼',  color: '#722ED1' }, 
   { id: 5, name: '台阶',  color: '#13C2C2' }, 
 ]; 
 
 export class AnnotateView { 
   constructor() { 
     // DOM 元素 
     this.canvas      = document.getElementById('annotate-canvas'); 
     this.ctx         = this.canvas.getContext('2d'); 
     this.container   = document.getElementById('canvas-container'); 
     this.placeholder = document.getElementById('canvas-placeholder'); 
 
     // 状态 
     this.images       = [];      // { file, name, url, annotations:[] } 
     this.currentIndex = 0; 
     this.currentCat   = 0; 
     this.tool         = 'draw'; // 'draw' | 'select' 
     this.scale        = 1; 
     this.offset       = { x: 0, y: 0 }; 
 
     // 画框临时状态 
     this.isDrawing    = false; 
     this.drawStart    = null; 
     this.drawRect     = null; 
 
     // 选中状态 
     this.selectedIdx  = -1; 
 
     // 图片对象（已加载） 
     this.imgEl        = null; 
 
     this._bound = false; 
   } 
 
   /* ==================== 初始化 ==================== */ 
   init() { 
     if (this._bound) return; 
     this._bound = true; 
     this._bindEvents(); 
     this._resizeCanvas(); 
    initProTabs(); 
  } 
 
  destroy() { 
     // 路由离开时清理（预留） 
   } 
 
   /* ==================== 事件绑定 ==================== */ 
   _bindEvents() { 
     // 上传按钮 
     document.getElementById('btn-upload-images').addEventListener('click', () => this._openFilePicker()); 
 
     // 拖放 
     const dropZone = document.getElementById('drop-zone'); 
     dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); }); 
     dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over')); 
     dropZone.addEventListener('drop', e => { 
       e.preventDefault(); 
       dropZone.classList.remove('drag-over'); 
       const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')); 
       if (files.length) this._loadFiles(files); 
     }); 
 
     // 画布拖放 
     this.container.addEventListener('dragover', e => e.preventDefault()); 
     this.container.addEventListener('drop', e => { 
       e.preventDefault(); 
       const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')); 
       if (files.length) this._loadFiles(files); 
     }); 
 
     // 导航 
     document.getElementById('btn-prev-img').addEventListener('click', () => this._navigate(-1)); 
     document.getElementById('btn-next-img').addEventListener('click', () => this._navigate(1)); 
 
     // 类别 
     document.querySelectorAll('.category-btn').forEach(btn => { 
       btn.addEventListener('click', () => { 
         document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active')); 
         btn.classList.add('active'); 
         this.currentCat = parseInt(btn.dataset.category); 
         // 切换工具为画框 
         this._setTool('draw'); 
       }); 
     }); 
 
     // 工具 
     document.getElementById('tool-draw').addEventListener('click', () => this._setTool('draw')); 
     document.getElementById('tool-select').addEventListener('click', () => this._setTool('select')); 
     document.getElementById('tool-zoom-in').addEventListener('click', () => this._zoom(1.2)); 
     document.getElementById('tool-zoom-out').addEventListener('click', () => this._zoom(1 / 1.2)); 
     document.getElementById('tool-zoom-reset').addEventListener('click', () => this._resetView()); 
 
     // 操作 
     document.getElementById('btn-undo').addEventListener('click', () => this._undo()); 
     document.getElementById('btn-clear').addEventListener('click', () => this._clearAll()); 
     document.getElementById('btn-save-label').addEventListener('click', () => this._saveLabel()); 
 
     // 导出 
     document.getElementById('btn-export-zip').addEventListener('click', () => this._exportZip()); 
 
     // 画布鼠标事件 
     this.canvas.addEventListener('mousedown', e => this._onMouseDown(e)); 
     this.canvas.addEventListener('mousemove', e => this._onMouseMove(e)); 
     this.canvas.addEventListener('mouseup',   e => this._onMouseUp(e)); 
 
     // 键盘 
     document.addEventListener('keydown', e => { 
       if (!document.getElementById('view-annotate').classList.contains('active')) return; 
       if (e.key === 'z' || e.key === 'Z') this._undo(); 
       if (e.key === 'Delete' || e.key === 'Backspace') this._deleteSelected(); 
       if (e.key === 'ArrowLeft')  this._navigate(-1); 
       if (e.key === 'ArrowRight') this._navigate(1); 
       const num = parseInt(e.key); 
       if (num >= 1 && num <= 6) { 
         document.querySelectorAll('.category-btn')[num - 1]?.click(); 
       } 
     }); 
 
     // 窗口缩放 
     window.addEventListener('resize', () => this._resizeCanvas()); 
   } 
 
   /* ==================== 文件处理 ==================== */ 
   _openFilePicker() { 
     const input = document.createElement('input'); 
     input.type = 'file'; 
     input.accept = 'image/*'; 
     input.multiple = true; 
     input.addEventListener('change', () => { 
       const files = Array.from(input.files).filter(f => f.type.startsWith('image/')); 
       if (files.length) this._loadFiles(files); 
     }); 
     input.click(); 
   } 
 
   _loadFiles(files) { 
     const newItems = files.map(f => ({ 
       file: f, 
       name: f.name, 
       url: URL.createObjectURL(f), 
       annotations: [], 
       saved: false, 
     })); 
     this.images.push(...newItems); 
     this._updateCounter(); 
     this._updateThumbnails(); 
     this._goTo(this.images.length - newItems.length); 
   } 
 
   _updateCounter() { 
     const total    = this.images.length; 
     const labeled  = this.images.filter(im => im.annotations.length > 0).length; 
     document.getElementById('image-counter').textContent = `共 ${total} 张，已标注 ${labeled} 张`; 
     document.getElementById('export-info').textContent   = `已标注：${labeled} 张`; 
   } 
 
   /* ==================== 导航 ==================== */ 
   _navigate(dir) { 
     if (!this.images.length) return; 
     this._goTo(this.currentIndex + dir); 
   } 
 
   _goTo(idx) { 
     if (!this.images.length) return; 
     idx = Math.max(0, Math.min(idx, this.images.length - 1)); 
     this.currentIndex = idx; 
     this.selectedIdx  = -1; 
     this._loadCurrentImage(); 
     this._updateThumbnails(); 
     document.getElementById('img-index').textContent = `${idx + 1} / ${this.images.length}`; 
   } 
 
   _loadCurrentImage() { 
     const item = this.images[this.currentIndex]; 
     if (!item) return; 
 
     this.placeholder.classList.add('hidden'); 
     document.getElementById('toolbar-hint').textContent = item.name; 
 
     const img = new Image(); 
     img.onload = () => { 
       this.imgEl = img; 
       this._resetView(); 
       this._render(); 
     }; 
     img.src = item.url; 
   } 
 
   /* ==================== 缩略图 ==================== */ 
   _updateThumbnails() { 
     const strip = document.getElementById('thumbnail-strip'); 
     strip.innerHTML = ''; 
     this.images.forEach((im, i) => { 
       const el = document.createElement('div'); 
       el.className = 'thumbnail-item' + 
         (i === this.currentIndex ? ' active' : '') + 
         (im.annotations.length > 0 ? ' labeled' : ''); 
       el.innerHTML = `<span class="thumbnail-dot"></span><span>${im.name.substring(0,18)}</span>`; 
       el.addEventListener('click', () => this._goTo(i)); 
       strip.appendChild(el); 
     }); 
   } 
 
   /* ==================== 画布尺寸 ==================== */ 
   _resizeCanvas() { 
     const rect = this.container.getBoundingClientRect(); 
     this.canvas.width  = rect.width  || 800; 
     this.canvas.height = rect.height || 600; 
     this._render(); 
   } 
 
   _resetView() { 
     if (!this.imgEl) return; 
     const cw = this.canvas.width, ch = this.canvas.height; 
     const iw = this.imgEl.width,  ih = this.imgEl.height; 
     this.scale  = Math.min(cw / iw, ch / ih) * 0.95; 
     this.offset = { 
       x: (cw - iw * this.scale) / 2, 
       y: (ch - ih * this.scale) / 2, 
     }; 
     this._render(); 
   } 
 
   _zoom(factor) { 
     this.scale *= factor; 
     this._render(); 
   } 
 
   /* ==================== 坐标转换 ==================== */ 
   _canvasToImg(cx, cy) { 
     return { 
       x: (cx - this.offset.x) / this.scale, 
       y: (cy - this.offset.y) / this.scale, 
     }; 
   } 
 
   _getMousePos(e) { 
     const rect = this.canvas.getBoundingClientRect(); 
     return { 
       x: (e.clientX - rect.left) * (this.canvas.width  / rect.width), 
       y: (e.clientY - rect.top)  * (this.canvas.height / rect.height), 
     }; 
   } 
 
   /* ==================== 鼠标事件 ==================== */ 
   _onMouseDown(e) { 
     if (!this.imgEl) return; 
     const pos = this._getMousePos(e); 
 
     if (this.tool === 'draw') { 
       this.isDrawing = true; 
       this.drawStart = this._canvasToImg(pos.x, pos.y); 
       this.drawRect  = null; 
     } else if (this.tool === 'select') { 
       const anns = this.images[this.currentIndex]?.annotations || []; 
       let hit = -1; 
       for (let i = anns.length - 1; i >= 0; i--) { 
         const a = anns[i]; 
         const iw = this.imgEl.width, ih = this.imgEl.height; 
         const x1 = (a.cx - a.w / 2) * iw, y1 = (a.cy - a.h / 2) * ih; 
         const x2 = (a.cx + a.w / 2) * iw, y2 = (a.cy + a.h / 2) * ih; 
         const ip  = this._canvasToImg(pos.x, pos.y); 
         if (ip.x >= x1 && ip.x <= x2 && ip.y >= y1 && ip.y <= y2) { hit = i; break; } 
       } 
       this.selectedIdx = hit; 
       this._render(); 
       this._updateAnnotationList(); 
     } 
   } 
 
   _onMouseMove(e) { 
     if (!this.isDrawing) return; 
     const pos  = this._getMousePos(e); 
     const cur  = this._canvasToImg(pos.x, pos.y); 
     this.drawRect = { 
       x: Math.min(this.drawStart.x, cur.x), 
       y: Math.min(this.drawStart.y, cur.y), 
       w: Math.abs(cur.x - this.drawStart.x), 
       h: Math.abs(cur.y - this.drawStart.y), 
     }; 
     this._render(); 
   } 
 
   _onMouseUp(e) { 
     if (!this.isDrawing) return; 
     this.isDrawing = false; 
     if (!this.drawRect || this.drawRect.w < 5 || this.drawRect.h < 5) { 
       this.drawRect = null; 
       return; 
     } 
     const iw = this.imgEl.width, ih = this.imgEl.height; 
     const x1 = Math.max(0, this.drawRect.x); 
     const y1 = Math.max(0, this.drawRect.y); 
     const x2 = Math.min(iw, this.drawRect.x + this.drawRect.w); 
     const y2 = Math.min(ih, this.drawRect.y + this.drawRect.h); 
     const cx = (x1 + x2) / 2 / iw; 
     const cy = (y1 + y2) / 2 / ih; 
     const w  = (x2 - x1) / iw; 
     const h  = (y2 - y1) / ih; 
 
     this.images[this.currentIndex].annotations.push({ 
       cat: this.currentCat, 
       cx: cx, cy: cy, w: w, h: h, 
     }); 
     this.drawRect = null; 
     this._updateCounter(); 
     this._updateAnnotationList(); 
     this._render(); 
   } 
 
   /* ==================== 渲染 ==================== */ 
   _render() { 
     const ctx = this.ctx; 
     const cw  = this.canvas.width, ch = this.canvas.height; 
     ctx.clearRect(0, 0, cw, ch); 
 
     // 背景 
     ctx.fillStyle = '#1a1a2e'; 
     ctx.fillRect(0, 0, cw, ch); 
 
     if (!this.imgEl) return; 
 
     const iw = this.imgEl.width, ih = this.imgEl.height; 
     const dx = this.offset.x, dy = this.offset.y; 
     const dw = iw * this.scale,  dh = ih * this.scale; 
 
     // 绘图 
     ctx.drawImage(this.imgEl, dx, dy, dw, dh); 
 
     // 已有标注框 
     const anns = this.images[this.currentIndex]?.annotations || []; 
     anns.forEach((a, i) => { 
       const cat   = CATEGORIES[a.cat]; 
       const color = cat?.color || '#fff'; 
       const x1    = dx + (a.cx - a.w / 2) * iw * this.scale; 
       const y1    = dy + (a.cy - a.h / 2) * ih * this.scale; 
       const bw    = a.w * iw * this.scale; 
       const bh    = a.h * ih * this.scale; 
 
       ctx.strokeStyle = color; 
       ctx.lineWidth   = i === this.selectedIdx ? 3 : 2; 
       ctx.strokeRect(x1, y1, bw, bh); 
 
       // 填充（半透明） 
       ctx.fillStyle = color + '22'; 
       ctx.fillRect(x1, y1, bw, bh); 
 
       // 标签 
       ctx.fillStyle   = color; 
       ctx.font        = 'bold 13px sans-serif'; 
       const label     = cat?.name || `cls${a.cat}`; 
       const tw        = ctx.measureText(label).width + 8; 
       ctx.fillRect(x1, y1 - 20, tw, 20); 
       ctx.fillStyle   = '#fff'; 
       ctx.fillText(label, x1 + 4, y1 - 5); 
     }); 
 
     // 正在画的框 
     if (this.drawRect) { 
       const cat   = CATEGORIES[this.currentCat]; 
       const color = cat?.color || '#fff'; 
       const x1    = dx + this.drawRect.x * this.scale; 
       const y1    = dy + this.drawRect.y * this.scale; 
       const bw    = this.drawRect.w * this.scale; 
       const bh    = this.drawRect.h * this.scale; 
 
       ctx.strokeStyle = color; 
       ctx.lineWidth   = 2; 
       ctx.setLineDash([6, 3]); 
       ctx.strokeRect(x1, y1, bw, bh); 
       ctx.setLineDash([]); 
       ctx.fillStyle = color + '18'; 
       ctx.fillRect(x1, y1, bw, bh); 
     } 
   } 
 
   /* ==================== 标注操作 ==================== */ 
   _undo() { 
     const anns = this.images[this.currentIndex]?.annotations; 
     if (anns && anns.length > 0) { 
       anns.pop(); 
       this.selectedIdx = -1; 
       this._render(); 
       this._updateAnnotationList(); 
       this._updateCounter(); 
     } 
   } 
 
   _clearAll() { 
     if (!this.images[this.currentIndex]) return; 
     if (!confirm('确定清空当前图片的所有标注？')) return; 
     this.images[this.currentIndex].annotations = []; 
     this.selectedIdx = -1; 
     this._render(); 
     this._updateAnnotationList(); 
     this._updateCounter(); 
   } 
 
   _deleteSelected() { 
     const anns = this.images[this.currentIndex]?.annotations; 
     if (!anns || this.selectedIdx < 0) return; 
     anns.splice(this.selectedIdx, 1); 
     this.selectedIdx = -1; 
     this._render(); 
     this._updateAnnotationList(); 
     this._updateCounter(); 
   } 
 
   _saveLabel() { 
     const item = this.images[this.currentIndex]; 
     if (!item) return; 
     item.saved = true; 
     this._showToast(`已保存 ${item.name} 的标注（${item.annotations.length} 个框）`); 
     this._updateThumbnails(); 
   } 
 
   _showToast(msg, type = 'success') { 
    if (window.showToast) { window.showToast(msg, type); return; } 
    const colors = { success: '#52C41A', warning: '#FAAD14', error: '#F5222D', info: '#4A9BF5' }; 
    const t = document.createElement('div'); 
    t.textContent = msg; 
    Object.assign(t.style, { 
      position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)', 
      background: colors[type] || colors.success, color: '#fff', padding: '10px 20px', 
      borderRadius: '8px', fontSize: '14px', zIndex: 9999, 
    }); 
    document.body.appendChild(t); 
    setTimeout(() => t.remove(), 2500); 
  } 
 
   /* ==================== 标注列表 ==================== */ 
   _updateAnnotationList() { 
     const list = document.getElementById('annotation-list'); 
     const anns = this.images[this.currentIndex]?.annotations || []; 
     document.getElementById('annotation-count').textContent = `${anns.length} 个`; 
 
     if (!anns.length) { 
       list.innerHTML = '<div class="empty-list-hint">暂无标注</div>'; 
       return; 
     } 
 
     list.innerHTML = anns.map((a, i) => { 
       const cat   = CATEGORIES[a.cat]; 
       const color = cat?.color || '#999'; 
       return ` 
         <div class="annotation-item ${i === this.selectedIdx ? 'selected' : ''}" 
              data-idx="${i}"> 
           <span class="ann-color" style="background:${color}"></span> 
           <span class="ann-label">${cat?.name || 'unknown'}</span> 
           <span class="ann-delete" data-idx="${i}">✕</span> 
         </div>`; 
     }).join(''); 
 
     // 绑定点击 
     list.querySelectorAll('.annotation-item').forEach(el => { 
       el.addEventListener('click', () => { 
         this.selectedIdx = parseInt(el.dataset.idx); 
         this._render(); 
         this._updateAnnotationList(); 
       }); 
     }); 
     list.querySelectorAll('.ann-delete').forEach(el => { 
       el.addEventListener('click', e => { 
         e.stopPropagation(); 
         this.images[this.currentIndex].annotations.splice(parseInt(el.dataset.idx), 1); 
         if (this.selectedIdx >= this.images[this.currentIndex].annotations.length) this.selectedIdx = -1; 
         this._render(); 
         this._updateAnnotationList(); 
         this._updateCounter(); 
       }); 
     }); 
   } 
 
   /* ==================== 工具切换 ==================== */ 
  _setTool(tool) { 
    this.tool = tool; 
    document.getElementById('tool-draw').classList.toggle('active', tool === 'draw'); 
    document.getElementById('tool-select').classList.toggle('active', tool === 'select'); 
    this.canvas.style.cursor = tool === 'draw' ? 'crosshair' : 'default'; 
  } 
 
  /* ==================== 导出 ZIP ==================== */ 
  async _exportZip() { 
    const labeled = this.images.filter(im => im.annotations.length > 0); 
    if (!labeled.length) { 
      this._showToast('请先标注至少一张图片', 'warning'); return; 
    } 
 
    // 检查 JSZip 
    if (typeof JSZip === 'undefined') { 
      this._showToast('JSZip 未加载，请检查网络', 'error'); return; 
    } 
 
    this._showToast(`正在打包 ${labeled.length} 张图片...`); 
    const zip   = new JSZip(); 
    const imgF  = zip.folder('images'); 
    const lblF  = zip.folder('labels'); 
 
    // dataset.yaml 
    const yaml = [ 
      'path: .', 
      'train: images', 
      'val: images', 
      'nc: 6', 
      "names: ['blind_path','obstacle','person','vehicle','pothole','step']", 
    ].join('\n'); 
    zip.file('dataset.yaml', yaml); 
 
    // 逐张打包 
    for (const item of labeled) { 
      // 图片 blob 
      const resp = await fetch(item.url); 
      const blob = await resp.blob(); 
      imgF.file(item.name, blob); 
 
      // YOLO label 
      const txt = item.annotations 
        .map(a => `${a.cat} ${a.cx.toFixed(6)} ${a.cy.toFixed(6)} ${a.w.toFixed(6)} ${a.h.toFixed(6)}`) 
        .join('\n'); 
      const stem = item.name.replace(/\.[^.]+$/, ''); 
      lblF.file(`${stem}.txt`, txt); 
    } 
 
    // 下载 
    const blob = await zip.generateAsync({ type: 'blob' }); 
    const url  = URL.createObjectURL(blob); 
    const a    = document.createElement('a'); 
    a.href     = url; 
    a.download = 'blind_road_dataset.zip'; 
    a.click(); 
    URL.revokeObjectURL(url); 
    this._showToast(`导出成功！共 ${labeled.length} 张`); 
  } 
 }