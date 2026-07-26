export class GestureManager {
    constructor() {
        this.lastTapTime = 0;
        this.lastTapX = 0;
        this.lastTapY = 0;
        this.longPressTimer = null;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.isLongPress = false;

        this.onSingleTap = null;
        this.onDoubleTap = null;
        this.onLongPress = null;
        this.onSwipeUp = null;
    }

    init() {
        document.addEventListener('touchend', (e) => this.handleTap(e));
        document.addEventListener('touchstart', (e) => this.handleTouchStart(e));
        document.addEventListener('touchmove', (e) => this.handleTouchMove(e));
    }

    handleTap(e) {
        const now = Date.now();
        const tapLength = now - this.lastTapTime;

        if (this.isLongPress) {
            this.isLongPress = false;
            this.lastTapTime = now;
            return;
        }

        if (tapLength < 300 && tapLength > 0) {
            e.preventDefault();
            if (this.onDoubleTap) {
                this.onDoubleTap();
            }
        } else {
            if (this.onSingleTap) {
                this.onSingleTap();
            }
        }

        this.lastTapTime = now;
    }

    handleTouchStart(e) {
        const touch = e.touches[0];
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;

        this.longPressTimer = setTimeout(() => {
            this.isLongPress = true;
            if (this.onLongPress) {
                this.onLongPress();
            }
            this.longPressTimer = null;
        }, 3000);
    }

    handleTouchMove(e) {
        const touch = e.touches[0];
        const deltaX = touch.clientX - this.touchStartX;
        const deltaY = touch.clientY - this.touchStartY;

        if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }
        }

        if (deltaY < -50 && Math.abs(deltaX) < 30) {
            if (this.onSwipeUp) {
                this.onSwipeUp();
            }
        }
    }
}