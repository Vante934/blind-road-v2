export class WSClient {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectTimer = null;
        this.shouldReconnect = false;
        this.onResult = null;
        this.onStatusChange = null;
        this.deviceId = null;
        this.token = '';
        this.lastSendTime = 0;
        this.minSendInterval = 100;
    }

    async connect(deviceId, token = '') {
        if (!deviceId) {
            console.error('[WS] Error: deviceId is undefined');
            throw new Error('deviceId is required');
        }

        if (this.socket) {
            console.log('[WS] Closing existing socket before reconnecting');
            const oldSocket = this.socket;
            this.socket = null;
            oldSocket.onclose = null;
            oldSocket.onerror = null;
            oldSocket.onmessage = null;
            oldSocket.onopen = null;
            try {
                oldSocket.close(1000, 'reconnect');
            } catch (e) {}
        }

        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        this.shouldReconnect = true;
        this.deviceId = deviceId;
        this.token = token;

        return new Promise((resolve, reject) => {
            const serverUrl = document.getElementById('input-server')?.value || '';

            let wsUrl;
            if (serverUrl) {
                const url = new URL(serverUrl);
                wsUrl = `ws${url.protocol === 'https:' ? 's' : ''}://${url.host}/ws/${deviceId}`;
            } else {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                wsUrl = `${protocol}//${window.location.host}/ws/${deviceId}`;
            }

            if (token) {
                wsUrl += `?token=${token}`;
            }

            console.log('[WS] Connecting to:', wsUrl);
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                console.log('[WS] Connected, readyState:', this.socket.readyState);
                this.reconnectAttempts = 0;

                console.log('[WS] 触发onStatusChange:', typeof this.onStatusChange);
                if (this.onStatusChange) {
                    this.onStatusChange('online');
                } else {
                    console.warn('[WS] onStatusChange未设置！');
                }

                resolve();
            };

            this.socket.onmessage = (event) => {
                console.log('[WS] Message received:', event.data.length, 'bytes');
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('[WS] Parse error:', e);
                }
            };

            this.socket.onclose = (event) => {
                console.log('[WS] Disconnected:', event.code, event.reason);
                if (this.onStatusChange) {
                    this.onStatusChange('offline');
                }
                this.scheduleReconnect();
            };

            this.socket.onerror = (event) => {
                console.error('[WS] Error connecting:', wsUrl, event);
                if (this.onStatusChange) {
                    this.onStatusChange('offline');
                }
                reject(new Error('WebSocket connection failed'));
            };
        });
    }

    scheduleReconnect() {
        if (!this.shouldReconnect) {
            console.log('[WS] Reconnect skipped (shouldReconnect=false)');
            return;
        }
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[WS] Reconnect max attempts reached');
            return;
        }
        this.reconnectAttempts++;
        const delay = Math.pow(2, this.reconnectAttempts) * 1000;
        console.log('[WS] Reconnect attempt', this.reconnectAttempts, 'in', delay, 'ms');
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect(this.deviceId, this.token).catch(err => {
                console.error('[WS] Reconnect failed:', err.message);
            });
        }, delay);
    }

    disconnect() {
        this.shouldReconnect = false;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        this.reconnectAttempts = 0;
        if (this.socket) {
            this.socket.onclose = null;
            this.socket.onerror = null;
            this.socket.onmessage = null;
            this.socket.onopen = null;
            try {
                this.socket.close(1000, 'client disconnect');
            } catch (e) {}
            this.socket = null;
        }
        console.log('[WS] Disconnected cleanly');
    }

    sendFrame(base64Image) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            return;
        }

        const now = Date.now();
        if (now - this.lastSendTime < this.minSendInterval) {
            return;
        }
        this.lastSendTime = now;

        const message = {
            type: 'frame',
            data: {
                image: base64Image
            }
        };

        this.socket.send(JSON.stringify(message));
    }

    sendSensorData(data) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.log('[WS] Cannot send sensor - socket not ready:', this.socket?.readyState);
            return;
        }

        const message = {
            type: 'sensor_data',
            data: data
        };

        this.socket.send(JSON.stringify(message));
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('[WS] Connected message:', data);
                if (this.onStatusChange) {
                    this.onStatusChange('connected');
                }
                break;

            case 'detection_result':
                console.log('[WS] Detection result:', data.fps, 'FPS,', data.detections?.length || 0, 'detections');
                if (this.onResult) {
                    this.onResult(data);
                }
                break;

            case 'sensor_result':
                console.log('[WS] Sensor result:', data);
                break;

            default:
                console.warn('[WS] Unknown message type:', data.type);
        }
    }
}