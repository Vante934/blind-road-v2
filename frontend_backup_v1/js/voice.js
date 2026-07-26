export class VoiceManager {
    constructor() {
        this.synth = null;
        this.voices = [];
        this.currentVoice = null;
        this.isSpeaking = false;
        this.rate = 1.0;
        this.recognition = null;
    }

    init() {
        this.synth = window.speechSynthesis;
        this.loadVoices();

        if ('onvoiceschanged' in this.synth) {
            this.synth.onvoiceschanged = () => this.loadVoices();
        }
    }

    loadVoices() {
        this.voices = this.synth.getVoices();
        this.currentVoice = this.voices.find(v =>
            v.lang.includes('zh') || v.lang.includes('CN')
        ) || this.voices[0];
    }

    speak(text, type = 'normal') {
        if (!text || !this.synth) return;

        this.synth.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.voice = this.currentVoice;
        utterance.rate = this.rate;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        utterance.onstart = () => { this.isSpeaking = true; };
        utterance.onend = () => { this.isSpeaking = false; };
        utterance.onerror = () => { this.isSpeaking = false; };

        this.synth.speak(utterance);
    }

    setRate(rate) {
        this.rate = rate;
    }

    stop() {
        if (this.synth) {
            this.synth.cancel();
            this.isSpeaking = false;
        }
    }

    handleWarning(warning) {
        if (!warning || !warning.tts_text) return;

        const type = warning.level === 1 ? 'urgent' : warning.level === 2 ? 'warning' : 'info';
        this.speak(warning.tts_text, type);
    }

    startListening() {
        console.log('[Voice] Speech recognition disabled');
    }

    stopListening() {
    }

    handleCommand(command) {
        console.log('Voice command:', command);
    }
}