/**
 * frontend/src/main.js
 * ====================
 * Entry point cho Vite build.
 * Xử lý: Dark Mode toggle, SocketIO real-time notifications, Lucide Icons.
 */
import './style.css';

// ─── Dark Mode ───────────────────────────────────────────────────────────────
function initDarkMode() {
    // Khôi phục preference từ localStorage hoặc OS setting
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (saved === 'dark' || (!saved && prefersDark)) {
        document.documentElement.classList.add('dark');
    }

    // Tạo nút toggle Dark Mode
    const btn = document.createElement('button');
    btn.id = 'dark-mode-toggle';
    btn.className = 'dark-toggle';
    btn.setAttribute('title', 'Chuyển chế độ sáng/tối');
    btn.innerHTML = `
        <svg class="sun-icon w-5 h-5 hidden dark:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z"/>
        </svg>
        <svg class="moon-icon w-5 h-5 block dark:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
        </svg>
    `;
    btn.addEventListener('click', () => {
        document.documentElement.classList.toggle('dark');
        const isDark = document.documentElement.classList.contains('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
    document.body.appendChild(btn);
}

// ─── SocketIO Real-time Notifications ────────────────────────────────────────
function initSocketNotifications() {
    // Kiểm tra Socket.IO client có được load chưa (từ CDN hoặc bundled)
    if (typeof io === 'undefined') {
        console.warn('[Socket] Socket.IO client chưa được load.');
        return;
    }

    const socket = io();
    const userId = document.body.dataset.userId;

    socket.on('connect', () => {
        console.log('[Socket] Đã kết nối:', socket.id);
        if (userId) {
            socket.emit('join', { user_id: parseInt(userId) });
        }
    });

    // Nhận cảnh báo 90% ngân sách
    socket.on('budget_warning', (data) => {
        showToastNotification(`⚠️ Chiến dịch "${data.campaign}" đã dùng ${(data.ratio * 100).toFixed(1)}% ngân sách!`, 'warning');
        updateNotificationBadge();
    });

    // Nhận cảnh báo ngân sách vượt 100%
    socket.on('budget_exceeded', (data) => {
        showToastNotification(`🚨 Chiến dịch "${data.campaign}" đã hết ngân sách và kết thúc!`, 'error');
        updateNotificationBadge();
    });

    socket.on('disconnect', () => {
        console.warn('[Socket] Mất kết nối với server.');
    });
}

// ─── Toast Notification ───────────────────────────────────────────────────────
function showToastNotification(message, type = 'info') {
    const colors = {
        info:    'bg-indigo-600',
        warning: 'bg-amber-500',
        error:   'bg-red-600',
        success: 'bg-emerald-600',
    };

    const toast = document.createElement('div');
    toast.className = `fixed top-6 right-6 z-[9999] max-w-sm px-5 py-4 rounded-2xl shadow-2xl
                       text-white text-sm font-semibold flex items-center gap-3
                       transform translate-x-full opacity-0 transition-all duration-300
                       ${colors[type] || colors.info}`;
    toast.innerHTML = `<span>${message}</span>`;
    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full', 'opacity-0');
    });

    // Auto remove sau 5 giây
    setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// ─── Cập nhật badge thông báo trên sidebar ────────────────────────────────────
function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (!badge) return;
    const current = parseInt(badge.textContent || '0');
    badge.textContent = current + 1;
    badge.classList.remove('hidden');
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    initSocketNotifications();
    console.log('[Vite] ADS Manager frontend khởi tạo thành công.');
});

// Export để sử dụng trong các module khác nếu cần
export { showToastNotification };
