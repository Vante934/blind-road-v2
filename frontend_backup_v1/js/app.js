import { CameraManager } from './camera.js';
import { WSClient } from './ws.js';
import { DetectionRenderer } from './renderer.js';
import { VoiceManager } from './voice.js';
import { GestureManager } from './gesture.js';
import { AuthManager } from './auth.js';

class App {
    constructor() {
        this.camera = new CameraManager();
        this.ws = new WSClient();
        this.renderer = new DetectionRenderer();
        this.voice = new VoiceManager();
        this.gesture = new GestureManager();
        this.auth = new AuthManager();

        this.isDetecting = false;
        this.lastResult = null;
    }

    async init() {
        await this.auth.init();

        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js');
        }

        this._bindUI();
        this._bindGestures();
        this._bindVoiceCommands();

        setTimeout(() => {
            this.voice.speak('视界导航已启动，双击屏幕开始检测', 'info');
        }, 500);
    }

    _bindUI() {
        document.getElementById('btn-main').addEventListener('click', () => {
            if (this.isDetecting) this.stop();
            else this.start();
        });

        document.getElementById('btn-sos').addEventListener('click', () => {
            this._triggerSOS();
        });

        document.getElementById('btn-settings').addEventListener('click', () => {
            this._toggleSettings(true);
        });
        document.getElementById('btn-close-settings').addEventListener('click', () => {
            this._toggleSettings(false);
        });

        document.getElementById('input-fps').addEventListener('input', (e) => {
            const fps = parseInt(e.target.value);
            document.getElementById('fps-output').textContent = `${fps} FPS`;
            this.camera.setFPS(fps);
        });

        document.getElementById('input-voice-speed').addEventListener('input', (e) => {
            const speed = parseFloat(e.target.value);
            document.getElementById('speed-output').textContent = `${speed.toFixed(1)}x`;
            this.voice.setRate(speed);
        });

        this.ws.onResult = (data) => this._handleResult(data);
        this.ws.onStatusChange = (status) => this._updateConnStatus(status);
    }

    _bindGestures() {
        this.gesture.onSingleTap = () => {
            if (this.lastResult) {
                const level = this.lastResult.warning?.level || 0;
                const names = ['当前环境安全', '注意！附近有危险', '警告！请注意障碍', '危险！请立即停止'];
                this.voice.speak(names[level] || '正在检测', 'normal');
            } else {
                this.voice.speak('尚未开始检测', 'info');
            }
        };

        this.gesture.onDoubleTap = () => {
            if (this.isDetecting) this.stop();
            else this.start();
        };

        this.gesture.onLongPress = () => this._triggerSOS();

        this.gesture.onSwipeUp = () => this._toggleSettings(true);
    }

    _bindVoiceCommands() {
        window.addEventListener('voice-command', (e) => {
            switch (e.detail) {
                case 'start_detection': this.start(); break;
                case 'stop_detection': this.stop(); break;
                case 'query_ahead':
                    this._announceCurrentStatus();
                    break;
                case 'query_status':
                    this._announceCurrentStatus();
                    break;
                case 'sos': this._triggerSOS(); break;
                case 'help':
                    this.voice.speak(
                        '单击查询状态，双击开始停止，长按三秒求助，上滑打开设置',
                        'info'
                    );
                    break;
            }
        });
    }

    async start() {
        try {
            this.voice.speak('正在启动摄像头', 'info');

            const deviceId = this.auth.getDeviceId();
            const token = this.auth.getToken();
            await this.ws.connect(deviceId, token);

            const fps = parseInt(document.getElementById('input-fps').value);
            await this.camera.start();

            this.camera.onFrame = (base64) => {
                console.log('[App] 发送帧:', base64.length, 'bytes');
                this.ws.sendFrame(base64);
            };

            this.camera.setFPS(fps);

            if (document.getElementById('input-voice-cmd').checked) {
                this.voice.startListening();
            }

            this.isDetecting = true;
            const btn = document.getElementById('btn-main');
            btn.setAttribute('aria-pressed', 'true');
            btn.querySelector('.btn-text').textContent = '停止检测';
            btn.querySelector('.btn-icon').textContent = '⏹';

            this.voice.speak('检测已启动，双击停止', 'info');
        } catch (err) {
            this.voice.speak(`启动失败：${err.message}`, 'warning');
        }
    }

    stop() {
        this.camera.onFrame = null;
        this.camera.stop();
        this.ws.disconnect();
        this.voice.stopListening();
        this.isDetecting = false;
        this.lastResult = null;

        this.renderer.clear();

        const btn = document.getElementById('btn-main');
        btn.setAttribute('aria-pressed', 'false');
        btn.querySelector('.btn-text').textContent = '开始检测';
        btn.querySelector('.btn-icon').textContent = '▶';

        this._resetStatus();
        this.voice.speak('检测已停止', 'info');
    }

    _handleResult(data) {
        this.lastResult = data;

        this.renderer.drawDetections(data.detections);

        document.getElementById('fps-badge').textContent = `${data.fps} FPS`;

        this._updateBlindRoadStatus(data.blind_road_status);

        this._updateStats(data);

        this._updateDirections(data.detections);

        this._handleWarning(data.warning);

        this._updateSRStatus(data);
    }

    _updateConnStatus(status) {
        console.log('[UI] 更新连接状态:', status);
        const el = document.getElementById('conn-badge');
        
        if (!el) {
            console.error('conn-badge元素不存在！');
            return;
        }
        
        const isOnline = (status === 'online' || status === 'connected');
        el.textContent = isOnline ? '在线' : '离线';
        el.className = 'badge ' + (isOnline ? 'online' : 'offline');
        el.setAttribute('aria-label', `连接状态：${isOnline ? '在线' : '离线'}`);
    }

    _updateBlindRoadStatus(status) {
        const el = document.getElementById('blind-road-indicator');
        const map = {
            'detected': { text: '✓ 盲道', cls: 'detected' },
            'on_track': { text: '✓ 在盲道上', cls: 'detected' },
            'deviated_left': { text: '⚠ 偏右了', cls: 'blocked' },
            'deviated_right': { text: '⚠ 偏左了', cls: 'blocked' },
            'blocked': { text: '✗ 盲道被占', cls: 'blocked' },
            'not_found': { text: '× 未检测', cls: 'lost' },
        };
        const info = map[status] || map['not_found'];
        el.textContent = info.text;
        el.className = `indicator ${info.cls}`;
        el.setAttribute('aria-label', `盲道状态：${info.text}`);
    }

    _updateStats(data) {
        const dets = data.detections || [];
        const obstacles = dets.filter(d => !d.is_blind_road);
        const distances = obstacles.filter(d => d.distance).map(d => d.distance);
        const minDist = distances.length ? Math.min(...distances) : null;

        document.getElementById('stat-blind').textContent =
            data.blind_road_status === 'on_track' ? '✓' : '✗';
        document.getElementById('stat-obs').textContent = obstacles.length;
        document.getElementById('stat-dist').textContent =
            minDist ? `${minDist.toFixed(1)}m` : '--';

        const levelEl = document.getElementById('stat-level');
        const levelNames = ['安全', '危险', '警告', '提醒'];
        const level = data.warning?.level || 0;
        levelEl.textContent = levelNames[level] || '安全';
        levelEl.style.color = ['#00FF88','#FF0000','#FF8800','#00CCFF'][level];
    }

    _updateDirections(detections = []) {
        const dirs = { left: false, center: false, right: false };
        const dangers = { left: false, center: false, right: false };
        for (const det of detections) {
            if (det.is_blind_road) continue;
            dirs[det.direction] = true;
            if (det.danger_level === 'high') dangers[det.direction] = true;
        }
        for (const dir of ['left','center','right']) {
            const el = document.getElementById(`dir-${dir}`);
            el.className = `dir-zone${dirs[dir] ? (dangers[dir] ? ' danger' : ' active') : ''}`;
        }
    }

    _handleWarning(warning) {
        const level = warning?.level || 0;
        const text = warning?.tts_text || '';

        const overlay = document.getElementById('warning-overlay');
        overlay.className = `level-${level}`;
        const textEl = document.getElementById('warning-text');
        textEl.textContent = text;
        textEl.setAttribute('aria-label', text);

        this.voice.handleWarning(warning);
    }

    _updateSRStatus(data) {
        const obstacles = (data.detections||[]).filter(d=>!d.is_blind_road);
        const status = `检测到${obstacles.length}个障碍物，盲道${data.blind_road_status}`;
        document.getElementById('sr-status').textContent = status;
    }

    _resetStatus() {
        document.getElementById('blind-road-indicator').textContent = '未检测';
        document.getElementById('blind-road-indicator').className = 'indicator';
        document.getElementById('conn-badge').textContent = '离线';
        document.getElementById('conn-badge').className = 'offline';
        document.getElementById('fps-badge').textContent = '0 FPS';
        document.getElementById('stat-obs').textContent = '0';
        document.getElementById('stat-dist').textContent = '--';
        const overlay = document.getElementById('warning-overlay');
        overlay.className = 'level-0';
    }

    _announceCurrentStatus() {
        if (!this.lastResult) {
            this.voice.speak('尚未检测到数据', 'info');
            return;
        }
        const { detections, warning, blind_road_status } = this.lastResult;
        const obstacles = (detections||[]).filter(d=>!d.is_blind_road);

        let text = '';
        if (blind_road_status === 'on_track') text += '当前在盲道上。';
        if (obstacles.length === 0) text += '前方畅通。';
        else {
            const nearest = obstacles.sort((a,b)=>(a.distance||99)-(b.distance||99))[0];
            text += `前方有${obstacles.length}个障碍物，最近${nearest.class_cn}距离${nearest.distance?.toFixed(1)||'未知'}米。`;
        }
        this.voice.speak(text, 'normal');
    }

    _triggerSOS() {
        if (!this.auth.isLoggedIn()) {
            this.voice.speak('请登录后使用紧急求助功能', 'warning');
            return;
        }
        this.voice.speak('已触发紧急求助，正在联系紧急联系人', 'urgent');
        this.auth.triggerSOS();
    }

    _toggleSettings(show) {
        const panel = document.getElementById('settings-panel');
        if (show) {
            panel.removeAttribute('hidden');
            panel.setAttribute('aria-hidden', 'false');
            document.getElementById('btn-close-settings').focus();
        } else {
            panel.setAttribute('hidden', '');
            panel.setAttribute('aria-hidden', 'true');
            document.getElementById('btn-settings').focus();
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    window.app = new App();
    await window.app.init();
});