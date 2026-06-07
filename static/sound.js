/* Lumina v5.1 — Sound Effects Engine */
const LuminaAudio = {
    ctx: null,
    init() {
        if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    },
    playTone(freq, duration, type='sine', volume=0.1) {
        if (!this.ctx) this.init();
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
    },
    keyCorrect() { this.playTone(880, 0.05, 'sine', 0.05); },
    keyWrong() { this.playTone(220, 0.1, 'square', 0.08); },
    gameStart() { this.playTone(523, 0.15); setTimeout(() => this.playTone(659, 0.15), 150); setTimeout(() => this.playTone(784, 0.2), 300); },
    gameWin() { this.playTone(784, 0.15); setTimeout(() => this.playTone(988, 0.15), 150); setTimeout(() => this.playTone(1175, 0.3), 300); },
    gameLose() { this.playTone(300, 0.3, 'sawtooth', 0.08); },
    moveMade() { this.playTone(600, 0.08, 'sine', 0.06); },
    capture() { this.playTone(440, 0.1, 'square', 0.08); setTimeout(() => this.playTone(880, 0.15), 100); },
    notification() { this.playTone(800, 0.1); setTimeout(() => this.playTone(1000, 0.1), 120); },
};
// Initialize on first user interaction to satisfy browser autoplay policies
document.addEventListener('click', () => LuminaAudio.init(), {once:true});
document.addEventListener('keydown', () => LuminaAudio.init(), {once:true});
