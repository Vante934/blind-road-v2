export class DetectionRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = this.canvas.getContext('2d');
        this.showLabels = true;

        this.colors = {
            blind_road: '#00FF88',
            person: '#FF4757',
            car: '#FF6B6B',
            motorcycle: '#FFA502',
            bicycle: '#FF7F50',
            truck: '#FF6348',
            bus: '#EE5A24',
            pole: '#70A1FF',
            trash_bin: '#7BED9F',
            construction: '#ECCC68',
            step: '#A4B0BE',
            pothole: '#E056FD',
            default: '#00CCFF'
        };

        this.cnNames = {
            blind_road:'盲道', person:'行人', car:'汽车',
            motorcycle:'摩托', bicycle:'自行车', truck:'卡车',
            bus:'公交', pole:'电杆', trash_bin:'垃圾桶',
            construction:'施工', step:'台阶', pothole:'坑洞'
        };
    }

    resize(w, h) {
        this.canvas.width = w;
        this.canvas.height = h;
    }

    render(detections = [], fps = 0) {
        const w = this.canvas.width;
        const h = this.canvas.height;
        this.ctx.clearRect(0, 0, w, h);

        for (const det of detections) {
            const color = this.colors[det.class] || this.colors.default;
            const [nx1, ny1, nx2, ny2] = det.bbox;
            const x1 = nx1 * w;
            const y1 = ny1 * h;
            const bw = (nx2 - nx1) * w;
            const bh = (ny2 - ny1) * h;

            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = det.danger_level === 'high' ? 3 : 2;
            if (det.is_blind_road) {
                this.ctx.setLineDash([8, 4]);
            } else {
                this.ctx.setLineDash([]);
            }
            this.ctx.strokeRect(x1, y1, bw, bh);
            this.ctx.setLineDash([]);

            this._drawCorners(x1, y1, bw, bh, 12, color, 3);

            if (this.showLabels) {
                const name = det.class_cn || this.cnNames[det.class] || det.class;
                const conf = `${(det.confidence * 100).toFixed(0)}%`;
                const dist = det.distance ? ` ${det.distance}m` : '';
                const label = `${name} ${conf}${dist}`;

                this.ctx.font = 'bold 13px Inter,sans-serif';
                const tw = this.ctx.measureText(label).width;

                this.ctx.fillStyle = color;
                this.ctx.globalAlpha = 0.85;
                this._fillRoundRect(x1, y1 - 22, tw + 10, 20, 4);
                this.ctx.globalAlpha = 1;

                this.ctx.fillStyle = det.is_blind_road ? '#000' : '#fff';
                this.ctx.fillText(label, x1 + 5, y1 - 6);
            }
        }
    }

    drawDetections(detections) {
        this.render(detections);
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    _drawCorners(x, y, w, h, len, color, lw) {
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = lw;
        this.ctx.beginPath();
        [[x,y],[x+w,y],[x+w,y+h],[x,y+h]].forEach(([cx,cy], i) => {
            const sx = i % 2 === 0 ? 1 : -1;
            const sy = i < 2 ? 1 : -1;
            this.ctx.moveTo(cx, cy + sy * len);
            this.ctx.lineTo(cx, cy);
            this.ctx.lineTo(cx + sx * len, cy);
        });
        this.ctx.stroke();
    }

    _fillRoundRect(x, y, w, h, r) {
        this.ctx.beginPath();
        this.ctx.roundRect(x, y, w, h, r);
        this.ctx.fill();
    }
}