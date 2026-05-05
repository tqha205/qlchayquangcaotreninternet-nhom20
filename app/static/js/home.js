/**
 * static/js/home.js
 * =================
 * Logic JavaScript cho trang chủ (index.html).
 * Tách khỏi inline HTML để dễ bảo trì.
 */

// ─── Lucide Icons ─────────────────────────────────────────────────────────────
if (typeof lucide !== 'undefined') {
    lucide.createIcons();
}

// ─── Scroll Reveal Animation ──────────────────────────────────────────────────
(function initScrollReveal() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
})();

// ─── Stats Counter Animation ──────────────────────────────────────────────────
(function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    if (!counters.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const el     = entry.target;
            const target = parseInt(el.dataset.count);
            const prefix = el.dataset.prefix || '';
            const suffix = el.dataset.suffix || '';
            const duration = 1800;
            const steps    = 60;
            const step     = target / steps;
            let current    = 0;
            const timer = setInterval(() => {
                current += step;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                // Format số có dấu chấm phân cách hàng nghìn
                el.textContent = prefix + Math.floor(current).toLocaleString('vi-VN') + suffix;
            }, duration / steps);
            observer.unobserve(el);
        });
    }, { threshold: 0.5 });

    counters.forEach(el => observer.observe(el));
})();

// ─── FAB Tooltip ──────────────────────────────────────────────────────────────
(function initFAB() {
    const fab = document.getElementById('fab-contact');
    if (!fab) return;
    fab.addEventListener('mouseenter', () => fab.classList.add('fab-expanded'));
    fab.addEventListener('mouseleave', () => fab.classList.remove('fab-expanded'));
})();

// ─── Active Nav Link ──────────────────────────────────────────────────────────
(function markActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('[data-nav-link]').forEach(link => {
        if (link.getAttribute('href') === path) {
            link.classList.add('text-brandred', 'font-bold');
        }
    });
})();
