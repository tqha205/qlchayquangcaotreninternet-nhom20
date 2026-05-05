/**
 * static/js/landing.js
 * =====================
 * Toàn bộ logic JavaScript cho Landing Page (index.html).
 */

/* ── 1. Lucide Icons ─────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    if (typeof lucide !== 'undefined') lucide.createIcons();
    initScrollReveal();
    initCountUp();
    initFAB();
    initNavActive();
    initDashboardMockup();
});

/* ── 2. Scroll Reveal ────────────────────────────────────────────── */
function initScrollReveal() {
    const io = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); }
        });
    }, { threshold: 0.1 });
    document.querySelectorAll('.fade-up').forEach(el => io.observe(el));
}

/* ── 3. Count-Up Animation ───────────────────────────────────────── */
function initCountUp() {
    const io = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (!e.isIntersecting) return;
            const el = e.target;
            const end = parseInt(el.dataset.target || 0);
            const suffix = el.dataset.suffix || '';
            const prefix = el.dataset.prefix || '';
            const dur = 1800;
            const fps = 60;
            const step = end / fps;
            let cur = 0;
            const t = setInterval(() => {
                cur += step;
                if (cur >= end) { cur = end; clearInterval(t); }
                el.textContent = prefix + Math.floor(cur).toLocaleString('vi-VN') + suffix;
            }, dur / fps);
            io.unobserve(el);
        });
    }, { threshold: 0.6 });
    document.querySelectorAll('[data-target]').forEach(el => io.observe(el));
}

/* ── 4. FAB Hover ────────────────────────────────────────────────── */
function initFAB() {
    const fab = document.getElementById('fab-contact');
    if (!fab) return;
    fab.addEventListener('mouseenter', () => fab.querySelector('.fab-label').classList.remove('w-0','opacity-0'));
    fab.addEventListener('mouseleave', () => fab.querySelector('.fab-label').classList.add('w-0','opacity-0'));
}

/* ── 5. Active Nav Link ──────────────────────────────────────────── */
function initNavActive() {
    const path = window.location.pathname;
    document.querySelectorAll('[data-nav]').forEach(a => {
        if (a.getAttribute('href') === path) a.classList.add('!text-brandred', 'font-black');
    });
}

/* ── 6. Animated Dashboard Bar Chart ────────────────────────────── */
function initDashboardMockup() {
    const bars = document.querySelectorAll('.mock-bar');
    bars.forEach((bar, i) => {
        setTimeout(() => {
            bar.style.transition = 'height .6s ease';
            bar.style.height = bar.dataset.h + '%';
        }, i * 80);
    });
}
