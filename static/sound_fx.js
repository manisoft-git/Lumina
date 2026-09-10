/**
 * Lumina World-Class Web Audio Synthesis & Celebration Engine
 * 100% Zero-Cloud, Pure Web Audio API Synthesizer (0 external assets, 0 latency, 0 bandwidth cost)
 */
(function() {
    let audioCtx = null;
    let soundEnabled = localStorage.getItem('lumina_sound_enabled') !== 'false';

    function getAudioContext() {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                audioCtx = new AudioContext();
            }
        }
        if (audioCtx && audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        return audioCtx;
    }

    window.LuminaAudio = {
        isEnabled: function() {
            return soundEnabled;
        },
        toggle: function() {
            soundEnabled = !soundEnabled;
            localStorage.setItem('lumina_sound_enabled', soundEnabled ? 'true' : 'false');
            this.updateToggleUI();
            if (soundEnabled) {
                this.playClick();
            }
            return soundEnabled;
        },
        updateToggleUI: function() {
            const btns = document.querySelectorAll('.sound-toggle-btn');
            btns.forEach(b => {
                b.textContent = soundEnabled ? '🔊' : '🔇';
                b.title = soundEnabled ? 'Mute Sound Effects' : 'Enable Sound Effects';
                b.setAttribute('aria-label', soundEnabled ? 'Mute Audio' : 'Unmute Audio');
            });
        },
        playClick: function() {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(600, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.03);
                gain.gain.setValueAtTime(0.08, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.03);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.03);
            } catch (e) {}
        },
        playKey: function() {
            this.keyCorrect();
        },
        keyCorrect: function() {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.04);
                gain.gain.setValueAtTime(0.06, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.04);
            } catch (e) {}
        },
        playError: function() {
            this.keyWrong();
        },
        keyWrong: function() {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(220, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(140, ctx.currentTime + 0.12);
                gain.gain.setValueAtTime(0.09, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.12);
            } catch (e) {}
        },
        comboChime: function(streak) {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                const baseFreq = 523.25;
                const scale = [1.0, 1.125, 1.25, 1.5, 1.667, 2.0];
                const step = Math.min(scale.length - 1, Math.floor((streak || 10) / 10));
                const freq = baseFreq * scale[step];
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(freq, ctx.currentTime);
                gain.gain.setValueAtTime(0.12, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.18);
            } catch (e) {}
        },
        gameStart: function() {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                [392, 523.25, 659.25].forEach((freq, idx) => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.08);
                    gain.gain.setValueAtTime(0.1, ctx.currentTime + idx * 0.08);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.08 + 0.15);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(ctx.currentTime + idx * 0.08);
                    osc.stop(ctx.currentTime + idx * 0.08 + 0.15);
                });
            } catch (e) {}
        },
        gameWin: function() {
            this.playFanfare();
        },
        notification: function() {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                [800, 1200].forEach((freq, idx) => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.08);
                    gain.gain.setValueAtTime(0.1, ctx.currentTime + idx * 0.08);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.08 + 0.2);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(ctx.currentTime + idx * 0.08);
                    osc.stop(ctx.currentTime + idx * 0.08 + 0.2);
                });
            } catch (e) {}
        },
        startFocusSoundscape: function() {
            // Safe 432Hz ambient focus
            if (this._soundscapeOsc) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                this._soundscapeOsc = ctx.createOscillator();
                this._soundscapeGain = ctx.createGain();
                this._soundscapeOsc.type = 'sine';
                this._soundscapeOsc.frequency.setValueAtTime(432, ctx.currentTime);
                this._soundscapeGain.gain.setValueAtTime(0.015, ctx.currentTime);
                this._soundscapeOsc.connect(this._soundscapeGain);
                this._soundscapeGain.connect(ctx.destination);
                this._soundscapeOsc.start();
            } catch (e) {}
        },
        stopFocusSoundscape: function() {
            if (this._soundscapeOsc) {
                try {
                    this._soundscapeOsc.stop();
                    this._soundscapeOsc.disconnect();
                } catch (e) {}
                this._soundscapeOsc = null;
                this._soundscapeGain = null;
            }
        },
        playSuccess: function() {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6 (Bright major chord)
                notes.forEach((freq, idx) => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'triangle';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.07);
                    gain.gain.setValueAtTime(0.12, ctx.currentTime + idx * 0.07);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.07 + 0.35);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(ctx.currentTime + idx * 0.07);
                    osc.stop(ctx.currentTime + idx * 0.07 + 0.35);
                });
            } catch (e) {}
        },
        playFanfare: function() {
            if (!soundEnabled) return;
            const ctx = getAudioContext();
            if (!ctx) return;
            try {
                const melody = [
                    { f: 523.25, t: 0.0, d: 0.12 },
                    { f: 523.25, t: 0.12, d: 0.12 },
                    { f: 523.25, t: 0.24, d: 0.12 },
                    { f: 659.25, t: 0.36, d: 0.25 },
                    { f: 783.99, t: 0.60, d: 0.40 }
                ];
                melody.forEach(item => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(item.f, ctx.currentTime + item.t);
                    gain.gain.setValueAtTime(0.15, ctx.currentTime + item.t);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + item.t + item.d);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(ctx.currentTime + item.t);
                    osc.stop(ctx.currentTime + item.t + item.d);
                });
            } catch (e) {}
        }
    };

    // Confetti Engine (Zero Dependency)
    window.LuminaConfetti = function() {
        const canvas = document.createElement('canvas');
        canvas.id = 'lumina-confetti-canvas';
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100vw';
        canvas.style.height = '100vh';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '99999';
        document.body.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        const count = 75;
        const particles = [];
        const colors = ['#6366f1', '#a855f7', '#ec4899', '#3b82f6', '#10b981', '#f59e0b', '#38bdf8'];

        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        for (let i = 0; i < count; i++) {
            particles.push({
                x: canvas.width / 2 + (Math.random() - 0.5) * 200,
                y: canvas.height / 2,
                vx: (Math.random() - 0.5) * 14,
                vy: (Math.random() - 0.9) * 16 - 2,
                size: Math.random() * 8 + 5,
                color: colors[Math.floor(Math.random() * colors.length)],
                rotation: Math.random() * 360,
                rSpeed: (Math.random() - 0.5) * 12,
                alpha: 1
            });
        }

        let animationFrame;
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let alive = 0;
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.35; // gravity
                p.vx *= 0.98; // drag
                p.rotation += p.rSpeed;
                p.alpha -= 0.012;

                if (p.alpha > 0) {
                    alive++;
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate((p.rotation * Math.PI) / 180);
                    ctx.fillStyle = p.color;
                    ctx.globalAlpha = Math.max(0, p.alpha);
                    ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
                    ctx.restore();
                }
            });

            if (alive > 0) {
                animationFrame = requestAnimationFrame(animate);
            } else {
                cancelAnimationFrame(animationFrame);
                canvas.remove();
            }
        }
        animate();
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.LuminaAudio.updateToggleUI();
    });
})();
