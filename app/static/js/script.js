document.addEventListener("DOMContentLoaded", () => {
    // 1. Hide Global Loader after page loads
    const loader = document.getElementById('global-loader');
    if (loader) {
        setTimeout(() => {
            loader.style.opacity = '0';
            setTimeout(() => {
                loader.style.visibility = 'hidden';
                loader.style.display = 'none';
            }, 500);
        }, 300); // Small delay to let fonts/images kick in
    }

    // 2. Navbar Scroll Effect
    const navbar = document.querySelector('.custom-navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // 3. Intersection Observer for Fade-in elements
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target); // Only animate once
            }
        });
    }, observerOptions);

    const fadeElements = document.querySelectorAll('.fade-in-section');
    fadeElements.forEach(el => observer.observe(el));

    // 4. Auto-hide Toasts
    const toasts = document.querySelectorAll('.custom-toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.4s ease forwards';
            setTimeout(() => {
                toast.remove();
            }, 400);
        }, 5000); // 5 seconds display
    });

    // 5. Initialize Datepickers (Fallback to native if flatpickr is missing)
    const datePickers = document.querySelectorAll('.datepicker');
    datePickers.forEach(el => {
        if (typeof flatpickr !== 'undefined') {
            flatpickr(el, {
                minDate: "today",
                dateFormat: "Y-m-d",
                altInput: true,
                altFormat: "F j, Y"
            });
        } else {
            el.type = 'date';
        }
    });
});

// Toast notification helper
function showToast(message, type = 'success') {
    const container = document.getElementById('toastPlacement');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle' : (type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle');
    
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fa-solid ${icon} fs-4 me-3" style="color: var(--accent-gold);"></i>
            <div>
                <strong class="d-block text-dark">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <small class="text-muted">${message}</small>
            </div>
        </div>
        <button type="button" class="btn-close" style="font-size: 0.8rem;" onclick="this.parentElement.remove();"></button>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.5s forwards';
        setTimeout(() => toast.remove(), 500);
    }, 5000);
}

// 5. Wishlist Toggle (AJAX)
function toggleWishlist(btn) {
    const roomId = btn.getAttribute('data-room-id');
    const icon = btn.querySelector('i');
    const isAdding = icon.classList.contains('fa-regular');
    
    // Optimistic UI update
    if (isAdding) {
        icon.classList.replace('fa-regular', 'fa-solid');
        showToast('Adding to wishlist...', 'info');
    } else {
        icon.classList.replace('fa-solid', 'fa-regular');
        showToast('Removing from wishlist...', 'info');
    }

    fetch(`/wishlist/toggle/${roomId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'added') {
            showToast('Room added to wishlist!', 'success');
        } else if (data.status === 'removed') {
            showToast('Room removed from wishlist.', 'info');
        }
    })
    .catch(err => {
        console.error('Wishlist error:', err);
        // Revert on error
        if (isAdding) icon.classList.replace('fa-solid', 'fa-regular');
        else icon.classList.replace('fa-regular', 'fa-solid');
        showToast('Failed to update wishlist.', 'error');
    });
}

// 6. Notification System Updates
function markAllRead() {
    fetch('/notifications/mark_all_read', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const badge = document.getElementById('notificationBadge');
                if (badge) badge.classList.add('d-none');
                
                const items = document.querySelectorAll('.notification-item');
                items.forEach(item => item.classList.remove('unread'));
                
                showToast('All notifications marked as read', 'info');
            }
        })
        .catch(err => console.error('Notification error:', err));
}

function updateUnreadCount() {
    fetch('/notifications/unread_count')
        .then(res => res.json())
        .then(data => {
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                if (data.count > 0) {
                    badge.innerText = data.count;
                    badge.classList.remove('d-none');
                } else {
                    badge.classList.add('d-none');
                }
            }
        });
}

// Check unread count on load if user is logged in
if (document.getElementById('notificationBadge')) {
    updateUnreadCount();
    // Refresh every 30 seconds for "real-time" feel without WebSockets
    setInterval(updateUnreadCount, 30000);
}

// Utility function to trigger loader on form submissions
window.addEventListener('submit', (e) => {
    // Only if it's not a search/filter form (GET)
    if (e.target.method === 'post' || e.target.method === 'POST') {
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.style.display = 'flex';
            loader.style.visibility = 'visible';
            loader.style.opacity = '1';
        }
    }
});
