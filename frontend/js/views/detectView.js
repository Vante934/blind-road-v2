/**
 * 视界项目 - 检测页控制器
 */
import { CameraManager } from '../core/camera.js';
import { WSClient } from '../core/ws.js';
import { DetectionRenderer } from '../core/renderer.js';
import { VoiceManager } from '../core/voice.js';
import { showToast } from '../utils/toast.js';

export class DetectView {
  constructor() {
    this.camera = null;
    this.ws = null;
    this.renderer = null;
    this.voice = new VoiceManager();
    this.isDetecting = false;
    this.deviceId = 'web_' + Math.random().toString(36).substr(2, 9);
    this._frameCount = 0;
    this._lastFpsTime = Date.now();
    this._lastObjectSpeakTime = 0;
    this._lastSafeSpeakTime = 0;
    this._lastAnnouncedClass = '';
  }

  init() {
    this._bindEvents();
  }

  _bindEvents() {
    const startBtn = document.getElementById('btn-start-detect');
    const stopBtn = document.getElementById('btn-stop-detect');
    startBtn?.addEventListener('click', () => this.start());
    stopBtn?.addEventListener('click', () => this.stop());
  }

  async start() {
    if (this.isDetecting) return;
    const video = document.getElementById('detect-video');
    const canvas = document.getElementById('detect-canvas');
    const overlayCanvas = canvas;

    this.voice.activate();
    this.voice.speak('检测已启动', { priority: 'high' });

    try {
      this.ws = new WSClient();
      this.ws.onResult = (data) => this._handleResult(data);
      this.ws.onOpen = () => this._updateConnStatus(true);
      this.ws.onClose = () => this._updateConnStatus(false);
      await this.ws.connect(this.deviceId);

      this.camera = new CameraManager(video, canvas);
      this.camera.onFrame = (b64) => this.ws.sendFrame(b64);
      await this.camera.start();

      this.renderer = new DetectionRenderer(canvas);

      document.getElementById('detect-video-wrapper').style.display = 'block';
      document.getElementById('detect-placeholder').style.display = 'none';
      document.getElementById('btn-start-detect').style.display = 'none';
      document.getElementById('btn-stop-detect').style.display = 'inline-flex';

      this.isDetecting = true;
      showToast('检测已启动', 'success');
    } catch (e) {
      console.error('[Detect] 启动失败', e);
      showToast('启动失败：' + e.message, 'error');
      this.stop();
    }
  }

  stop() {
    this.isDetecting = false;
    this.voice.stop();
    if (this.camera) { this.camera.stop(); this.camera = null; }
    if (this.ws) { this.ws.disconnect(); this.ws = null; }
    document.getElementById('detect-video-wrapper').style.display = 'none';
    document.getElementById('detect-placeholder').style.display = 'block';
    document.getElementById('btn-start-detect').style.display = 'inline-flex';
    document.getElementById('btn-stop-detect').style.display = 'none';
    this._updateConnStatus(false);
  }

  _handleResult(data) {
    this._frameCount++;
    const now = Date.now();
    if (now - this._lastFpsTime >= 1000) {
      const fps = this._frameCount * 1000 / (now - this._lastFpsTime);
      document.getElementById('detect-fps').textContent = fps.toFixed(1) + ' FPS';
      this._frameCount = 0;
      this._lastFpsTime = now;
    }

    if (this.renderer && data.detections) {
      this.renderer.drawDetections(data.detections);
    }

    const brStatus = data.blind_road_status || 'not_found';
    const brEl = document.getElementById('blind-road-status');
    brEl.className = 'blind-road-badge ' + brStatus.replace('_', '-');
    brEl.textContent = {
      'on_track': '✅ 在盲道上',
      'off_track': '⚠️ 已偏离',
      'not_found': '未检测到盲道'
    }[brStatus] || '未知';

    const list = document.getElementById('detection-list');
    if (data.detections && data.detections.length > 0) {
      list.innerHTML = data.detections.slice(0, 5).map(d => `
        <li class="detection-item">
          <span class="detection-item-name">${d.class_cn || d.class}</span>
          <span class="detection-item-conf">${(d.confidence * 100).toFixed(0)}%</span>
        </li>
      `).join('');
    } else {
      list.innerHTML = '<li class="detection-item" style="color:var(--color-text-secondary);">暂无检测结果</li>';
    }

    const w = data.warning || { level: 0, tts_text: '' };
    const wEl = document.getElementById('warning-indicator');
    wEl.className = 'warning-indicator warning-level-' + w.level;
    wEl.textContent = ['安全', '注意', '警告', '危险'][w.level] || '安全';

    let ttsToSpeak = '';

    if (w.tts_text) {
      ttsToSpeak = w.tts_text;
    }
    else if (w.level >= 1) {
      const names = (data.detections || [])
        .slice(0, 2)
        .map(d => d.class_cn || d.class)
        .join('、');
      ttsToSpeak = names ? `前方注意${names}` : '请注意';
    }
    else if (data.detections && data.detections.length > 0) {
      const topClass = data.detections[0].class_cn || data.detections[0].class;
      if (topClass !== this._lastAnnouncedClass ||
          now - this._lastObjectSpeakTime > 5000) {
        ttsToSpeak = `检测到${topClass}`;
        this._lastObjectSpeakTime = now;
        this._lastAnnouncedClass = topClass;
      }
    }
    else {
      if (now - this._lastSafeSpeakTime > 10000) {
        ttsToSpeak = '前方安全';
        this._lastSafeSpeakTime = now;
      }
    }

    if (ttsToSpeak) {
      this.voice.speak(ttsToSpeak, {
        priority: w.level >= 2 ? 'high' : 'normal'
      });
      document.getElementById('tts-status').textContent = '🔊 ' + ttsToSpeak;
    }
  }

  _updateConnStatus(online) {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    if (online) {
      dot.className = 'status-dot online';
      text.textContent = '已连接';
    } else {
      dot.className = 'status-dot offline';
      text.textContent = '未连接';
    }
  }
}