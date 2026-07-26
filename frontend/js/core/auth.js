export class AuthManager {
    constructor() {
        this.state = {
            isLoggedIn: false,
            user: null,
            token: '',
            deviceId: ''
        };
    }

    async init() {
        await this.loadSession();
    }

    async loadSession() {
        const token = localStorage.getItem('auth-token');
        const user = localStorage.getItem('auth-user');
        const deviceId = localStorage.getItem('device-id');

        if (token) {
            this.state.token = token;
        }

        if (user) {
            try {
                this.state.user = JSON.parse(user);
                this.state.isLoggedIn = true;
            } catch (e) {
                localStorage.removeItem('auth-user');
            }
        }

        if (deviceId) {
            this.state.deviceId = deviceId;
        }

        if (!this.state.isLoggedIn && !this.state.deviceId) {
            await this.guestLogin();
        }
    }

    getDeviceId() {
        return this.state.deviceId;
    }

    getToken() {
        return this.state.token;
    }

    async guestLogin() {
        try {
            const response = await fetch('/api/auth/guest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.state.deviceId = data.device_id;
                localStorage.setItem('device-id', data.device_id);
            }
        } catch (e) {
            console.error('Guest login failed:', e);
            const deviceId = 'guest_' + crypto.randomUUID();
            this.state.deviceId = deviceId;
            localStorage.setItem('device-id', deviceId);
        }
    }

    async register(email, password, nickname) {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, nickname })
            });

            if (response.ok) {
                const data = await response.json();
                this.saveSession(data.token, {
                    id: data.user_id,
                    nickname: data.nickname,
                    email: email
                });
                return { success: true };
            } else {
                const error = await response.json();
                return { success: false, message: error.detail || '注册失败' };
            }
        } catch (e) {
            return { success: false, message: '网络错误' };
        }
    }

    async login(email, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (response.ok) {
                const data = await response.json();
                this.saveSession(data.token, {
                    id: data.user_id,
                    nickname: data.nickname,
                    email: email
                });
                return { success: true };
            } else {
                const error = await response.json();
                return { success: false, message: error.detail || '登录失败' };
            }
        } catch (e) {
            return { success: false, message: '网络错误' };
        }
    }

    async getMe() {
        if (!this.state.token) return null;

        try {
            const response = await fetch('/api/user/me', {
                headers: { 'Authorization': `Bearer ${this.state.token}` }
            });

            if (response.ok) {
                return await response.json();
            }
            return null;
        } catch (e) {
            return null;
        }
    }

    async updateEmergency(name, phone) {
        if (!this.state.token) return { success: false };

        try {
            const response = await fetch('/api/user/emergency', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.state.token}`
                },
                body: JSON.stringify({ name, phone })
            });

            return response.ok ? { success: true } : { success: false };
        } catch (e) {
            return { success: false };
        }
    }

    saveSession(token, user) {
        this.state.token = token;
        this.state.user = user;
        this.state.isLoggedIn = true;

        localStorage.setItem('auth-token', token);
        localStorage.setItem('auth-user', JSON.stringify(user));
    }

    logout() {
        this.state.isLoggedIn = false;
        this.state.user = null;
        this.state.token = '';

        localStorage.removeItem('auth-token');
        localStorage.removeItem('auth-user');

        this.guestLogin();
    }

    isLoggedIn() {
        return this.state.isLoggedIn;
    }

    async triggerSOS() {
        if (!this.state.token) return;

        try {
            const response = await fetch('/api/auth/sos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.state.token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('SOS triggered:', data);
            }
        } catch (e) {
            console.error('SOS failed:', e);
        }
    }

    renderUserSection() {
        const section = document.getElementById('user-section');

        if (this.state.isLoggedIn && this.state.user) {
            section.innerHTML = `
                <div class="user-info">
                    <span>${this.state.user.nickname || this.state.user.email}</span>
                    <button onclick="window.Auth.openEmergencyModal()">紧急联系人</button>
                </div>
                <button onclick="window.Auth.logout()">退出登录</button>
            `;
        } else {
            section.innerHTML = `
                <div class="user-info">
                    <span>游客模式</span>
                </div>
                <button onclick="window.Auth.openAuthModal()">登录/注册</button>
            `;
        }
    }

    openAuthModal() {
        const panel = document.getElementById('auth-panel');
        panel.hidden = false;
        panel.setAttribute('aria-hidden', 'false');
        this.renderAuthForm('login');
    }

    closeAuthModal() {
        const panel = document.getElementById('auth-panel');
        panel.hidden = true;
        panel.setAttribute('aria-hidden', 'true');
    }

    renderAuthForm(mode) {
        const panel = document.getElementById('auth-panel');
        const title = mode === 'login' ? '登录' : '注册';
        const switchText = mode === 'login' ? '注册' : '登录';
        const switchMode = mode === 'login' ? 'register' : 'login';

        panel.innerHTML = `
            <div class="panel-header">
                <h2>${title}</h2>
                <button onclick="window.Auth.closeAuthModal()">✕</button>
            </div>
            <div class="panel-body">
                <form class="auth-form" id="auth-form">
                    ${mode === 'register' ? `
                    <input type="text" id="auth-nickname" placeholder="昵称" required>
                    ` : ''}
                    <input type="email" id="auth-email" placeholder="邮箱" required>
                    <input type="password" id="auth-password" placeholder="密码" required>
                    <button type="submit">${title}</button>
                    <div class="switch-link" onclick="window.Auth.renderAuthForm('${switchMode}')">
                        切换到${switchText}
                    </div>
                </form>
            </div>
        `;

        document.getElementById('auth-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('auth-email').value;
            const password = document.getElementById('auth-password').value;

            let result;
            if (mode === 'login') {
                result = await this.login(email, password);
            } else {
                const nickname = document.getElementById('auth-nickname').value;
                result = await this.register(email, password, nickname);
            }

            if (result.success) {
                this.closeAuthModal();
                this.renderUserSection();
            } else {
                alert(result.message);
            }
        });
    }

    openEmergencyModal() {
        const panel = document.getElementById('auth-panel');
        panel.hidden = false;
        panel.setAttribute('aria-hidden', 'false');

        panel.innerHTML = `
            <div class="panel-header">
                <h2>紧急联系人</h2>
                <button onclick="window.Auth.closeAuthModal()">✕</button>
            </div>
            <div class="panel-body">
                <form class="auth-form" id="emergency-form">
                    <input type="text" id="emergency-name" placeholder="姓名" required>
                    <input type="tel" id="emergency-phone" placeholder="电话号码" required>
                    <button type="submit">保存</button>
                </form>
            </div>
        `;

        document.getElementById('emergency-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('emergency-name').value;
            const phone = document.getElementById('emergency-phone').value;

            const result = await this.updateEmergency(name, phone);
            if (result.success) {
                this.closeAuthModal();
                alert('保存成功');
            } else {
                alert('保存失败');
            }
        });
    }
}