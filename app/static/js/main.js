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

// ── Sidebar mobile toggle ─────────────────────────────────────────────────────
const menuBtn = document.getElementById('menu-toggle');
const sidebar = document.querySelector('.sidebar');
if (menuBtn && sidebar) {
  menuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.addEventListener('click', e => {
    if (!sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

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
  if (gpa <= 1.75)     bar.style.background = '#22c55e';
  else if (gpa <= 2.5) bar.style.background = '#f59e0b';
  else                 bar.style.background = '#ef4444';
});

// ── Analytics charts (Chart.js via CDN) ──────────────────────────────────────
function initCharts() {
  // Classification doughnut
  const ctxDist = document.getElementById('chart-dist');
  if (ctxDist && window.chartDistData) {
    const d = window.chartDistData;
    new Chart(ctxDist, {
      type: 'doughnut',
      data: {
        labels: ['Advanced', 'Average', 'At-Risk'],
        datasets: [{
          data: [d.Advanced, d.Average, d['At-Risk']],
          backgroundColor: ['#22c55e', '#f59e0b', '#ef4444'],
          borderWidth: 0,
        }]
      },
      options: {
        plugins: { legend: { labels: { color: '#94a3b8', font: { size: 12 } } } },
        cutout: '65%',
      }
    });
  }

  // Trend bar chart
  const ctxTrend = document.getElementById('chart-trend');
  if (ctxTrend && window.chartTrendData) {
    const t = window.chartTrendData;
    new Chart(ctxTrend, {
      type: 'bar',
      data: {
        labels: ['Improving', 'Stable', 'Declining'],
        datasets: [{
          label: 'Students',
          data: [t.improving, t.stable, t.declining],
          backgroundColor: ['#22c55e', '#6366f1', '#ef4444'],
          borderRadius: 6,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#2a2d3e' } },
          y: { ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#2a2d3e' } },
        }
      }
    });
  }

  // Scatter: attendance vs GPA
  const ctxScatter = document.getElementById('chart-scatter');
  if (ctxScatter && window.chartScatterData) {
    const colorMap = { Advanced: '#22c55e', Average: '#f59e0b', 'At-Risk': '#ef4444' };
    const points = window.chartScatterData.map(p => ({
      x: p.x, y: p.y,
      label: p.label,
      backgroundColor: colorMap[p.class] || '#6366f1',
    }));
    new Chart(ctxScatter, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Students',
          data: points,
          backgroundColor: points.map(p => p.backgroundColor),
          pointRadius: 6,
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => {
                const p = points[ctx.dataIndex];
                return `${p.label}  Att:${ctx.parsed.x}%  GPA:${ctx.parsed.y}`;
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Attendance (%)', color: '#94a3b8' },
            ticks: { color: '#94a3b8' }, grid: { color: '#2a2d3e' },
            min: 0, max: 100,
          },
          y: {
            title: { display: true, text: 'GPA (lower = better)', color: '#94a3b8' },
            ticks: { color: '#94a3b8' }, grid: { color: '#2a2d3e' },
            min: 1, max: 5, reverse: false,
          }
        }
      }
    });
  }

  // GPA histogram
  const ctxHisto = document.getElementById('chart-histo');
  if (ctxHisto && window.chartHistoData) {
    const h = window.chartHistoData;
    new Chart(ctxHisto, {
      type: 'bar',
      data: {
        labels: Object.keys(h),
        datasets: [{
          label: 'Students',
          data: Object.values(h),
          backgroundColor: ['#22c55e', '#6366f1', '#f59e0b', '#f97316', '#ef4444'],
          borderRadius: 6,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#2a2d3e' } },
          y: { ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#2a2d3e' } },
        }
      }
    });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCharts);
} else {
  initCharts();
}
