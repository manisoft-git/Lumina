/* Lumina v5.0 — Shared Utilities */
function loadGhost(passageText, keystrokes, wpm) {
    const ghost = document.getElementById('ghost-cursor');
    if (!ghost || !keystrokes || !keystrokes.length) return;
    ghost.style.display = 'block';
    const duration = (passageText.length / 5) / (wpm / 60) * 1000;
    const step = duration / keystrokes.length;
    let i = 0;
    const interval = setInterval(() => {
        if (i >= keystrokes.length) { clearInterval(interval); ghost.style.display = 'none'; return; }
        const spans = document.querySelectorAll('#passage-display .char');
        if (spans[i]) {
            const rect = spans[i].getBoundingClientRect();
            const parent = document.getElementById('passage-display').getBoundingClientRect();
            ghost.style.left = (rect.left - parent.left) + 'px';
            ghost.style.top = (rect.top - parent.top) + 'px';
        }
        i++;
    }, Math.max(step, 50));
}
function announce(msg, priority='polite') {
    let el = document.getElementById('aria-announcer');
    if (!el) {
        el = document.createElement('div');
        el.id = 'aria-announcer';
        el.setAttribute('aria-live', priority);
        el.setAttribute('aria-atomic', 'true');
        el.style.position = 'absolute'; el.style.left = '-9999px';
        document.body.appendChild(el);
    }
    el.textContent = '';
    setTimeout(() => el.textContent = msg, 100);
}
function toggleNav() {
    document.querySelector('.nav-links').classList.toggle('open');
}
function validateForm(form) {
    let ok = true;
    form.querySelectorAll('input[required], select[required], textarea[required]').forEach(inp => {
        if (!inp.value.trim()) { ok = false; inp.style.borderColor = 'var(--danger)'; }
        else { inp.style.borderColor = ''; }
    });
    return ok;
}
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach(f => {
        f.addEventListener('submit', (e) => { if (!validateForm(f)) e.preventDefault(); });
    });
});
window.addEventListener('load', () => {
    const loader = document.getElementById('page-loader');
    if (loader) loader.classList.add('hidden');
});
document.addEventListener('DOMContentLoaded', () => {
    const firstInput = document.querySelector('.auth-form input, .game-container input:not([disabled])');
    if (firstInput && !firstInput.disabled) firstInput.focus();
});

