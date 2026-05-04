// SAPCPOS — main.js

// ── Auto-dismiss alerts ───────────────────────────────────────────────────────
document.querySelectorAll('.alert[data-autohide]').forEach(el => {
  setTimeout(() => el.remove(), 4000);
});

// ── Confirm delete ────────────────────────────────────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(btn => {
  btn.addEventListener('click', e => {
    if (!confirm(btn.dataset.confirm)) e.preventDefault();
  });
});

// ── Sidebar mobile toggle with overlay ───────────────────────────────────────
const menuBtn = document.getElementById('menu-toggle');
const sidebar = document.querySelector('.sidebar');

// Create overlay element dynamically
let overlay = document.querySelector('.sidebar-overlay');
if (!overlay) {
  overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);
}

function openSidebar() {
  sidebar.classList.add('open');
  overlay.classList.add('show');
  document.body.style.overflow = 'hidden'; // prevent background scroll
}

function closeSidebar() {
  sidebar.classList.remove('open');
  overlay.classList.remove('show');
  document.body.style.overflow = '';
}

if (menuBtn && sidebar) {
  menuBtn.addEventListener('click', e => {
    e.stopPropagation();
    if (sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });
}

// Close when overlay is clicked
overlay.addEventListener('click', closeSidebar);

// Close sidebar when a nav link is tapped on mobile
sidebar.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    if (window.innerWidth <= 768) closeSidebar();
  });
});

// Close on resize to desktop
window.addEventListener('resize', () => {
  if (window.innerWidth > 768) closeSidebar();
});

// ── OTP input — digits only ───────────────────────────────────────────────────
const otpInput = document.querySelector('.otp-input');
if (otpInput) {
  otpInput.addEventListener('input', () => {
    otpInput.value = otpInput.value.replace(/\D/g, '').slice(0, 6);
  });
}

// ── GPA bar fill ──────────────────────────────────────────────────────────────
document.querySelectorAll('.gpa-bar[data-gpa]').forEach(bar => {
  const gpa = parseFloat(bar.dataset.gpa);
  // Philippine scale: 1.0 = 100%, 5.0 = 0%
  const pct = Math.max(0, Math.min(100, ((5 - gpa) / 4) * 100));
  bar.style.width = pct + '%';
});