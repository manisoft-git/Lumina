/* Lumina v5.2 — Enhanced Synthesizer & Combo Sound Engine */
const LuminaAudio = {
    ctx: null,
    muted: localStorage.getItem('lumina_audio_muted') === 'true',

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
            }
        }
    },

    toggleMute() {
        this.muted = !this.muted;
        localStorage.setItem('lumina_audio_muted', this.muted);
        return this.muted;
    },

    playTone(freq, duration, type='sine', volume=0.1) {
        if (this.muted) return;
        if (!this.ctx) this.init();
        if (!this.ctx) return;
        try {
            if (this.ctx.state === 'suspended') {
                this.ctx.resume();
            }
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = type;
            osc.frequency.value = freq;
            gain.gain.value = volume;
            gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start();
            osc.stop(this.ctx.currentTime + duration);
        } catch (e) {
            // AudioContext autoplay fallback
        }
    },

    keyCorrect() {
        // Crisp, soft tactile switch feedback
        this.playTone(900, 0.04, 'sine', 0.04);
    },

    keyWrong() {
        // Soft error click
        this.playTone(220, 0.09, 'sawtooth', 0.06);
    },

    comboChime(streak) {
        if (streak < 10) return;
        // Rising pentatonic intervals based on combo streak
        const baseFreq = 523.25; // C5
        const scale = [1.0, 1.125, 1.25, 1.5, 1.667, 2.0];
        const step = Math.min(scale.length - 1, Math.floor((streak - 10) / 15));
        const freq = baseFreq * scale[step];
        this.playTone(freq, 0.12, 'sine', 0.08);
        setTimeout(() => this.playTone(freq * 1.25, 0.15, 'sine', 0.06), 80);
    },

    gameStart() {
        this.playTone(523, 0.12);
        setTimeout(() => this.playTone(659, 0.12), 120);
        setTimeout(() => this.playTone(784, 0.2), 240);
    },

    gameWin() {
        this.playTone(784, 0.15);
        setTimeout(() => this.playTone(988, 0.15), 140);
        setTimeout(() => this.playTone(1175, 0.3), 280);
    },

    gameLose() {
        this.playTone(320, 0.25, 'sawtooth', 0.08);
    },

    moveMade() {
        this.playTone(600, 0.06, 'sine', 0.05);
    },

    capture() {
        this.playTone(440, 0.08, 'square', 0.06);
        setTimeout(() => this.playTone(880, 0.12), 90);
    },

    notification() {
        this.playTone(800, 0.08);
        setTimeout(() => this.playTone(1000, 0.1), 100);
    },

    /* Sensory Ambient Focus Soundscape (432Hz Binaural Drone) */
    focusDrone: null,
    focusGain: null,
    isFocusPlaying: false,

    toggleFocusSoundscape() {
        if (this.isFocusPlaying) {
            this.stopFocusSoundscape();
            return false;
        } else {
            this.startFocusSoundscape();
            return true;
        }
    },

    startFocusSoundscape() {
        if (this.muted) return;
        if (!this.ctx) this.init();
        if (!this.ctx) return;
        try {
            if (this.ctx.state === 'suspended') this.ctx.resume();
            if (this.focusDrone) this.stopFocusSoundscape();

            const osc1 = this.ctx.createOscillator();
            const osc2 = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc1.type = 'sine';
            osc1.frequency.value = 216; // Harmonic foundation
            osc2.type = 'sine';
            osc2.frequency.value = 220; // 4Hz Theta binaural beat for deep focus

            gain.gain.setValueAtTime(0.001, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.04, this.ctx.currentTime + 2.0);

            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(this.ctx.destination);

            osc1.start();
            osc2.start();

            this.focusDrone = { osc1, osc2 };
            this.focusGain = gain;
            this.isFocusPlaying = true;
        } catch (e) {}
    },

    stopFocusSoundscape() {
        if (!this.focusDrone || !this.ctx) return;
        try {
            this.focusGain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + 1.0);
            setTimeout(() => {
                try {
                    this.focusDrone.osc1.stop();
                    this.focusDrone.osc2.stop();
                    this.focusDrone.osc1.disconnect();
                    this.focusDrone.osc2.disconnect();
                } catch (e) {}
                this.focusDrone = null;
                this.focusGain = null;
                this.isFocusPlaying = false;
            }, 1000);
        } catch (e) {
            this.focusDrone = null;
            this.isFocusPlaying = false;
        }
    }
};

// Initialize on first user interaction to satisfy browser autoplay policies
document.addEventListener('click', () => LuminaAudio.init(), { once: true });
document.addEventListener('keydown', () => LuminaAudio.init(), { once: true });
