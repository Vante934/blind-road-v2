/**
 * 视界项目 - 语音播报管理器
 * 解决"完全没声音"问题的关键实现
 */
export class VoiceManager {
  constructor() {
    this.enabled = false;
    this.voices = [];
    this.zhVoice = null;
    this.currentUtterance = null;
    this.queue = [];
    this.isSpeaking = false;
    this.lastText = '';
    this.lastSpeakTime = 0;
    this.minInterval = 2000;
    this._loadVoices();
  }

  _loadVoices() {
    const load = () => {
      this.voices = speechSynthesis.getVoices();
      this.zhVoice = this.voices.find(v =>
        v.lang.startsWith('zh') || v.name.includes('Chinese')
      ) || this.voices[0];
      console.log('[Voice] 加载语音', this.voices.length, '中文:', this.zhVoice?.name);
    };
    load();
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = load;
    }
  }

  activate() {
    if (this.enabled) return;
    try {
      const u = new SpeechSynthesisUtterance(' ');
      u.volume = 0;
      speechSynthesis.speak(u);
      this.enabled = true;
      console.log('[Voice] 已激活');
    } catch (e) {
      console.error('[Voice] 激活失败', e);
    }
  }

  speak(text, opts = {}) {
    if (!text) return;
    if (!this.enabled) {
      console.warn('[Voice] 未激活，跳过播报:', text);
      return;
    }
    const now = Date.now();
    if (text === this.lastText && now - this.lastSpeakTime < this.minInterval) {
      return;
    }
    this.lastText = text;
    this.lastSpeakTime = now;

    if (opts.priority === 'high') {
      speechSynthesis.cancel();
      this.queue = [];
    }

    const utterance = new SpeechSynthesisUtterance(text);
    if (this.zhVoice) utterance.voice = this.zhVoice;
    utterance.lang = 'zh-CN';
    utterance.rate = opts.rate || 1.1;
    utterance.pitch = opts.pitch || 1.0;
    utterance.volume = opts.volume || 1.0;

    utterance.onend = () => {
      this.currentUtterance = null;
      this.isSpeaking = false;
    };
    utterance.onerror = (e) => {
      console.error('[Voice] 播报错误', e);
      this.currentUtterance = null;
      this.isSpeaking = false;
    };

    this.currentUtterance = utterance;
    this.isSpeaking = true;
    speechSynthesis.speak(utterance);
    console.log('[Voice] 播报:', text);
  }

  stop() {
    speechSynthesis.cancel();
    this.queue = [];
    this.currentUtterance = null;
    this.isSpeaking = false;
  }
}