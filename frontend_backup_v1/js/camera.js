export class CameraManager {
    constructor() {
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        this.captureTimer = null;
        this.lastSendTime = 0;
        this.targetFPS = 10;
        this.onFrame = null;
        this.isRunning = false;
    }

    async start() {
        try {
            if (!this.video) {
                this.video = document.getElementById('camera-feed');
                if (!this.video) {
                    console.error('[Camera] 找不到 #camera-feed 元素');
                    throw new Error('找不到 #camera-feed 元素');
                }
            }

            if (!this.canvas) {
                this.canvas = document.createElement('canvas');
                this.ctx = this.canvas.getContext('2d');
            }

            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    frameRate: { ideal: 30 }
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;

            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    resolve();
                };
            });

            await this.video.play();

            this.isRunning = true;
            this._startCapture();

            console.log('[Camera] 启动完成, targetFPS:', this.targetFPS, 'videoWidth:', this.video.videoWidth);
        } catch (e) {
            console.error('[Camera] 启动失败:', e);
            throw e;
        }
    }

    stop() {
        this.isRunning = false;
        this._stopCapture();
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        console.log('[Camera] 已停止');
    }

    setFPS(fps) {
        this.targetFPS = fps;
        if (this.isRunning) {
            this._startCapture();
        }
    }

    _startCapture() {
        this._stopCapture();
        const interval = 1000 / this.targetFPS;

        console.log('[Camera] 启动定时器, 间隔:', interval, 'ms');

        this.captureTimer = setInterval(() => {
            if (!this.isRunning) {
                console.log('[Camera] isRunning=false, 跳过');
                return;
            }
            if (!this.onFrame) {
                console.log('[Camera] onFrame未设置, 跳过');
                return;
            }

            this.captureAndSend();
        }, interval);
    }

    _stopCapture() {
        if (this.captureTimer) {
            clearInterval(this.captureTimer);
            this.captureTimer = null;
        }
    }

    captureAndSend() {
        if (!this.video || !this.canvas || !this.ctx) {
            console.log('[Camera] video/canvas/ctx为空');
            return;
        }
        if (this.video.readyState < 2) {
            console.log('[Camera] video未就绪, readyState:', this.video.readyState);
            return;
        }
        if (this.canvas.width !== this.video.videoWidth) {
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
        }

        this.ctx.drawImage(this.video, 0, 0);
        const base64 = this.canvas.toDataURL('image/jpeg', 0.7).split(',')[1];

        console.log('[Camera] 帧捕获成功:', base64.length, 'bytes');

        if (this.onFrame) {
            this.onFrame(base64);
        }
    }
}