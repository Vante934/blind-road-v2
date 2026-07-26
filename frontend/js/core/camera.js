class CameraManager {
  constructor(videoEl, canvasEl) {
    this.video = videoEl;
    this.canvas = canvasEl;
    this.stream = null;
    this.isRunning = false;
    this.facingMode = 'environment';
    this.frameInterval = 200;
    this.onFrame = null;
    this._timer = null;
  }

  async start() {
    if (this.isRunning) return;
    const constraints = {
      video: {
        facingMode: this.facingMode,
        width: { ideal: 640 },
        height: { ideal: 480 }
      },
      audio: false
    };
    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      console.warn('[Camera] 后置失败，尝试前置', e);
      constraints.video.facingMode = 'user';
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.facingMode = 'user';
    }
    this.video.srcObject = this.stream;
    await this.video.play();
    this.canvas.width = 640;
    this.canvas.height = 480;
    this.isRunning = true;
    this._startCapture();
    console.log('[Camera] 启动成功', this.canvas.width, 'x', this.canvas.height);
  }

  _startCapture() {
    const ctx = this.canvas.getContext('2d');
    const capture = () => {
      if (!this.isRunning) return;
      ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
      if (this.onFrame) {
        const b64 = this.canvas.toDataURL('image/jpeg', 0.6);
        this.onFrame(b64);
      }
    };
    this._timer = setInterval(capture, this.frameInterval);
  }

  stop() {
    this.isRunning = false;
    if (this._timer) { clearInterval(this._timer); this._timer = null; }
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.video.srcObject = null;
    console.log('[Camera] 已停止');
  }

  async switchCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.facingMode = this.facingMode === 'user' ? 'environment' : 'user';
    const wasRunning = this.isRunning;
    this.isRunning = false;
    if (wasRunning) await this.start();
  }
}

export { CameraManager };