class WSClient {
  constructor() {
    this.socket = null;
    this.url = null;
    this.shouldReconnect = false;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 10000;
    this.reconnectTimer = null;
    this._lastSendTime = 0;
    this._minSendInterval = 200;
    this._pendingSend = false;
    this.onOpen = null;
    this.onClose = null;
    this.onMessage = null;
    this.onResult = null;
    this.onError = null;
  }

  connect(deviceId, token = null) {
    return new Promise((resolve, reject) => {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.url = `${proto}//${window.location.host}/ws/${deviceId}`;
      if (token) this.url += `?token=${token}`;
      this.shouldReconnect = true;
      try {
        this.socket = new WebSocket(this.url);
      } catch (e) { reject(e); return; }

      this.socket.addEventListener('open', () => {
        console.log('[WS] 已连接');
        this.reconnectDelay = 1000;
        if (this.onOpen) this.onOpen();
        resolve();
      });
      this.socket.addEventListener('close', () => {
        console.log('[WS] 已断开');
        this._pendingSend = false;
        if (this.onClose) this.onClose();
        if (this.shouldReconnect) this._scheduleReconnect(deviceId, token);
      });
      this.socket.addEventListener('error', (e) => {
        console.error('[WS] 错误', e);
        if (this.onError) this.onError(e);
        reject(e);
      });
      this.socket.addEventListener('message', (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.type === 'detection_result') {
            this._pendingSend = false;
            if (this.onResult) this.onResult(data);
          }
          if (this.onMessage) this.onMessage(data);
        } catch (e) { console.error('[WS] 解析失败', e); }
      });
    });
  }

  _scheduleReconnect(deviceId, token) {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this.connect(deviceId, token).catch(() => {});
    }, this.reconnectDelay);
  }

  sendFrame(base64) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false;
    if (this._pendingSend) return false;
    const now = Date.now();
    if (now - this._lastSendTime < this._minSendInterval) return false;
    this._lastSendTime = now;
    this._pendingSend = true;
    const pureBase64 = base64.replace(/^data:image\/\w+;base64,/, '');
    this.socket.send(JSON.stringify({
      type: 'frame',
      data: { image: pureBase64 }
    }));
    return true;
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this._pendingSend = false;
  }
}

export { WSClient };