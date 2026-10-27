/**
 * Assignment Tracker - Main JavaScript
 */

// ─────────────────────── Toast Notifications ─────────────────────────

function showToast(message, type = 'success') {
  const container = document.getElementById('messages-container');
  if (!container) return;

  const icons = {
    success: '✓',
    error: '✕',
    danger: '✕',
    info: 'ℹ',
    warning: '⚠',
  };

  const toast = document.createElement('div');
  toast.className = `alert alert-${type}`;
  toast.innerHTML = `
    <span class="alert-icon">${icons[type] || icons.success}</span>
    <div class="alert-content">
      <span class="alert-text">${escapeHtml(message)}</span>
    </div>
    <button class="alert-close" onclick="this.parentElement.remove()">×</button>
  `;
  container.appendChild(toast);

  // Auto-remove after 4 seconds
  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(text));
  return d.innerHTML;
}

// Auto-dismiss existing Django messages
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.alert[data-auto-dismiss]').forEach(function (el) {
    setTimeout(function () {
      el.style.animation = 'fadeOut 0.3s ease forwards';
      setTimeout(() => el.remove(), 300);
    }, 4000);
  });
});

// ─────────────────────── Mobile Sidebar ──────────────────────────────

(function () {
  const hamburger = document.getElementById('hamburger-btn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  function openSidebar() {
    sidebar && sidebar.classList.add('open');
    overlay && overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar && sidebar.classList.remove('open');
    overlay && overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  hamburger && hamburger.addEventListener('click', openSidebar);
  overlay && overlay.addEventListener('click', closeSidebar);

  // Close on nav item click (mobile)
  document.querySelectorAll('.nav-item').forEach(function (item) {
    item.addEventListener('click', function () {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
})();

// ─────────────────────── Confirm Dialog ──────────────────────────────

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

// Close modal on overlay click
document.addEventListener('click', function (e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});

// Escape key closes modals
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.active').forEach(function (m) {
      m.classList.remove('active');
    });
  }
});

// Delete confirmation setup
function setupDeleteConfirm(buttonSelector, modalId, formId, titleEl) {
  document.querySelectorAll(buttonSelector).forEach(function (btn) {
    btn.addEventListener('click', function () {
      const title = btn.dataset.title || '';
      if (titleEl) {
        const el = document.getElementById(titleEl);
        if (el) el.textContent = title;
      }
      const form = document.getElementById(formId);
      if (form) form.action = btn.dataset.action;
      openModal(modalId);
    });
  });
}

// ─────────────────────── Form Enhancements ───────────────────────────

// Due date: set min to today for new assignments
(function () {
  const dueDateInput = document.querySelector('input[name="due_date"]');
  const isEditPage = document.body.dataset.page === 'edit';

  if (dueDateInput && !isEditPage) {
    const today = new Date().toISOString().split('T')[0];
    dueDateInput.min = today;
  }
})();

// Status → submitted_at auto notice
(function () {
  const statusSelect = document.querySelector('select[name="status"]');
  if (!statusSelect) return;

  statusSelect.addEventListener('change', function () {
    const notice = document.getElementById('submitted-notice');
    if (notice) {
      notice.style.display = this.value === 'submitted' ? 'block' : 'none';
    }
  });
})();

// ─────────────────────── Search with debounce ────────────────────────

(function () {
  const searchInput = document.getElementById('search-input');
  if (!searchInput) return;

  let timer;
  searchInput.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      const form = document.getElementById('filter-form');
      if (form) form.submit();
    }, 500);
  });
})();

// ─────────────────────── Filter form auto-submit ─────────────────────

(function () {
  const selects = document.querySelectorAll('.filter-select-auto');
  selects.forEach(function (sel) {
    sel.addEventListener('change', function () {
      const form = document.getElementById('filter-form');
      if (form) form.submit();
    });
  });
})();

// ─────────────────────── Chart.js helper ─────────────────────────────

function renderStatusChart(canvasId, chartData) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: chartData.labels,
      datasets: [{
        data: chartData.data,
        backgroundColor: chartData.colors,
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            padding: 16,
            font: { size: 13, family: 'Inter, sans-serif' },
            usePointStyle: true,
          }
        },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total ? Math.round(ctx.parsed / total * 100) : 0;
              return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

// Initialize chart if data is embedded in page
document.addEventListener('DOMContentLoaded', function () {
  const el = document.getElementById('chart-data');
  if (el) {
    try {
      const data = JSON.parse(el.textContent);
      renderStatusChart('status-chart', data);
    } catch (e) {
      console.warn('Could not parse chart data', e);
    }
  }
});
