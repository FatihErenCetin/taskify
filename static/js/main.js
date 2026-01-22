/* ==========================================
   TASKIFY - MAIN JAVASCRIPT
   ========================================== */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initPageAnimations();
    initSmoothScrolling();
    initFormEffects();
    initTableRowEffects();
    initTooltips();
    initAlertDismiss();
    initCSRFProtection();
    // initParallaxEffect(); // Mouse hareket efekti devre disi
});

/* ==========================================
   CSRF PROTECTION FOR AJAX REQUESTS
   ========================================== */
function initCSRFProtection() {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    if (csrfToken) {
        // Add CSRF token to all AJAX requests
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            // Only add to same-origin requests
            if (!url.startsWith('http') || url.startsWith(window.location.origin)) {
                options.headers = {
                    ...options.headers,
                    'X-CSRFToken': csrfToken
                };
            }
            return originalFetch(url, options);
        };
        
        // Also set up for XMLHttpRequest
        const originalXHROpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url) {
            const result = originalXHROpen.apply(this, arguments);
            if (!url.startsWith('http') || url.startsWith(window.location.origin)) {
                this.setRequestHeader('X-CSRFToken', csrfToken);
            }
            return result;
        };
    }
}

/* ==========================================
   PAGE LOAD ANIMATIONS
   ========================================== */
function initPageAnimations() {
    // Fade in main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }

    // Stagger animations for cards
    const cards = document.querySelectorAll('.card, .feature-card, .glass-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';

        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 + (index * 100));
    });

    // Animate table rows
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';

        setTimeout(() => {
            row.style.transition = 'all 0.4s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateX(0)';
        }, 200 + (index * 50));
    });
}

/* ==========================================
   SMOOTH SCROLLING
   ========================================== */
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
}

/* ==========================================
   FORM EFFECTS
   ========================================== */
function initFormEffects() {
    // Add glass class to form controls
    const formControls = document.querySelectorAll('.form-control, textarea');
    formControls.forEach(control => {
        if (!control.classList.contains('form-control-glass')) {
            control.classList.add('form-control-glass');
        }
    });

    // Add glass class to selects
    const selects = document.querySelectorAll('.form-select');
    selects.forEach(select => {
        if (!select.classList.contains('form-select-glass')) {
            select.classList.add('form-select-glass');
        }
    });

    // Floating label effect
    const inputs = document.querySelectorAll('.form-control-glass');
    inputs.forEach(input => {
        // Add focus effects
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focused');
        });

        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('input-focused');
        });

        // Add ripple effect on focus
        input.addEventListener('focus', createRipple);
    });

    // Form submit animation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<span class="spinner"></span> Yükleniyor...';
                submitBtn.disabled = true;
            }
        });
    });
}

/* ==========================================
   TABLE ROW EFFECTS
   ========================================== */
function initTableRowEffects() {
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        if (!table.classList.contains('table-glass')) {
            table.classList.add('table-glass');
        }
    });

    // Add hover sound effect (optional - visual feedback)
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.01)';
        });

        row.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

/* ==========================================
   TOOLTIPS
   ========================================== */
function initTooltips() {
    // Initialize Bootstrap tooltips if available
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (typeof bootstrap !== 'undefined' && tooltipTriggerList.length > 0) {
        tooltipTriggerList.forEach(el => {
            new bootstrap.Tooltip(el);
        });
    }
}

/* ==========================================
   ALERT AUTO DISMISS
   ========================================== */
function initAlertDismiss() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // Add entrance animation
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-20px)';

        setTimeout(() => {
            alert.style.transition = 'all 0.4s ease';
            alert.style.opacity = '1';
            alert.style.transform = 'translateY(0)';
        }, 100);

        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                alert.remove();
            }, 400);
        }, 5000);
    });
}

/* ==========================================
   PARALLAX EFFECT
   ========================================== */
function initParallaxEffect() {
    // Subtle parallax on mouse move
    document.addEventListener('mousemove', function(e) {
        const cards = document.querySelectorAll('.feature-card, .glass-card');
        const mouseX = e.clientX / window.innerWidth - 0.5;
        const mouseY = e.clientY / window.innerHeight - 0.5;

        cards.forEach(card => {
            const rect = card.getBoundingClientRect();
            const cardCenterX = rect.left + rect.width / 2;
            const cardCenterY = rect.top + rect.height / 2;

            const distanceX = (e.clientX - cardCenterX) / 50;
            const distanceY = (e.clientY - cardCenterY) / 50;

            // Only apply if mouse is near the card
            if (Math.abs(distanceX) < 20 && Math.abs(distanceY) < 20) {
                card.style.transform = `perspective(1000px) rotateY(${distanceX * 0.5}deg) rotateX(${-distanceY * 0.5}deg)`;
            }
        });
    });

    // Reset on mouse leave
    document.addEventListener('mouseleave', function() {
        const cards = document.querySelectorAll('.feature-card, .glass-card');
        cards.forEach(card => {
            card.style.transform = 'perspective(1000px) rotateY(0) rotateX(0)';
        });
    });
}

/* ==========================================
   RIPPLE EFFECT
   ========================================== */
function createRipple(event) {
    const element = event.currentTarget;
    const ripple = document.createElement('span');

    ripple.classList.add('ripple-effect');
    ripple.style.cssText = `
        position: absolute;
        border-radius: 50%;
        background: rgba(249, 115, 22, 0.3);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    `;

    element.style.position = 'relative';
    element.style.overflow = 'hidden';
    element.appendChild(ripple);

    setTimeout(() => ripple.remove(), 600);
}

/* ==========================================
   UTILITY FUNCTIONS
   ========================================== */

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function for scroll events
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/* ==========================================
   CONFIRMATION DIALOGS
   ========================================== */

// Enhanced delete confirmation
window.confirmDelete = function(taskTitle) {
    return confirm(`"${taskTitle}" gorevini silmek istediginize emin misiniz?`);
};

/* ==========================================
   NAVBAR SCROLL EFFECT
   ========================================== */
window.addEventListener('scroll', throttle(function() {
    const navbar = document.querySelector('.navbar-glass');
    if (navbar) {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(249, 115, 22, 0.25)';
            navbar.style.boxShadow = '0 4px 30px rgba(0, 0, 0, 0.2)';
        } else {
            navbar.style.background = 'rgba(249, 115, 22, 0.15)';
            navbar.style.boxShadow = '0 4px 30px rgba(0, 0, 0, 0.1)';
        }
    }
}, 100));

/* ==========================================
   LOADING SPINNER STYLE
   ========================================== */
const style = document.createElement('style');
style.textContent = `
    .spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 0.8s linear infinite;
        margin-right: 8px;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }

    .input-focused {
        position: relative;
    }

    .input-focused::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        width: 0;
        height: 2px;
        background: var(--turuncu);
        transition: all 0.3s ease;
        transform: translateX(-50%);
    }

    .input-focused::after {
        width: 100%;
    }
`;
document.head.appendChild(style);

/* ==========================================
   COUNTER ANIMATION
   ========================================== */
function animateCounter(element, target, duration = 1000) {
    let start = 0;
    const increment = target / (duration / 16);

    const timer = setInterval(() => {
        start += increment;
        if (start >= target) {
            element.textContent = target;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(start);
        }
    }, 16);
}

// Initialize counters if present
document.querySelectorAll('[data-counter]').forEach(counter => {
    const target = parseInt(counter.dataset.counter);
    animateCounter(counter, target);
});
