function startDownload(btn) {
    if (btn && btn.classList.contains('is-loading')) return;

    const downloadUrl = window.APP_CONFIG ? window.APP_CONFIG.downloadUrl : "";

    if (downloadUrl) {
        handleLeadConversion();

        window.location.href = downloadUrl;
    } else {
        console.error("Download URL not found!");
        return;
    }

    updateButtonLoadingState();

    setTimeout(() => {
        resetButtonState();
    }, 5000);
}

/**
 * 处理 Lead 回传逻辑
 */
function handleLeadConversion() {
    const STORAGE_KEY = 'fb_lead_sent';
    const hasSent = localStorage.getItem(STORAGE_KEY);

    if (!hasSent) {
        if (typeof fbq === 'function') {
            fbq('track', 'Lead', {
                content_name: 'App Download',
                source: window.location.hostname
            });
            console.log("FB Lead event tracked.");
        } else {
            console.warn("Facebook Pixel (fbq) not found.");
        }

        localStorage.setItem(STORAGE_KEY, 'true');
    } else {
        console.log("Lead already recorded locally, skipping FB track.");
    }
}

/**
 * 视觉控制：进入加载状态
 */
function updateButtonLoadingState() {
    document.querySelectorAll('button').forEach(b => {
        const text = b.querySelector('.btn-text');
        const spinner = b.querySelector('.loading-spinner');
        const icon = b.querySelector('i:not(.loading-spinner)');

        if (text) text.innerText = 'Downloading & Securing...';
        if (spinner) spinner.style.display = 'inline-block';
        if (icon) icon.style.display = 'none';

        b.classList.add('is-loading');
        b.style.opacity = '0.8';
        b.style.pointerEvents = 'none';
    });
}

/**
 * 视觉控制：恢复/完成状态
 */
function resetButtonState() {
    document.querySelectorAll('button').forEach(b => {
        const text = b.querySelector('.btn-text');
        const spinner = b.querySelector('.loading-spinner');
        const icon = b.querySelector('i:not(.loading-spinner)');

        if (text) text.innerText = 'Check Notification Bar';
        if (spinner) spinner.style.display = 'none';
        if (icon) {
            icon.className = 'fas fa-check-circle';
            icon.style.display = 'inline-block';
        }
        b.classList.remove('is-loading');
        b.style.opacity = '1';
        b.style.pointerEvents = 'auto';
    });
}

// 保持卡片进入动画
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.shrink-0');
    cards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateX(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateX(0)';
        }, 100 * i);
    });
});