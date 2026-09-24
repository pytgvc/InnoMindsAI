// InnoMinds AI - Modern Frontend Interactivity
// Pure Vanilla JS (Zero build step, high performance)

document.addEventListener("DOMContentLoaded", () => {
  initNotificationPolling();
  initTableFilter();
  initScoreSliders();
  initConfirmForms();
  initDemoCredentials();
  initKeyboardShortcuts();
});

// Poll unread notification count every 20s and update badge
function initNotificationPolling() {
  const badge = document.getElementById("notif-badge");
  if (!badge) return;

  const poll = () => {
    fetch("/api/notifications/count")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        if (data.count > 0) {
          badge.textContent = data.count;
          badge.style.display = "flex";
        } else {
          badge.style.display = "none";
        }
      })
      .catch(() => {});
  };
  poll();
  setInterval(poll, 20000);
}

// Live search / instant filter for idea tables
function initTableFilter() {
  const input = document.getElementById("table-search");
  const table = document.getElementById("filterable-table");
  if (!input || !table) return;

  input.addEventListener("input", () => {
    const term = input.value.trim().toLowerCase();
    const rows = table.querySelectorAll("tbody tr");
    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(term) ? "" : "none";
    });
  });
}

// Live numeric readout and dynamic gradient fill for evaluation score sliders
function initScoreSliders() {
  document.querySelectorAll(".score-slider").forEach((slider) => {
    const output = document.getElementById(slider.dataset.output);
    
    const updateSliderFill = () => {
      const min = parseFloat(slider.min) || 0;
      const max = parseFloat(slider.max) || 10;
      const val = parseFloat(slider.value) || 0;
      const percent = ((val - min) / (max - min)) * 100;
      slider.style.background = `linear-gradient(to right, #8b5cf6 0%, #ec4899 ${percent}%, rgba(255, 255, 255, 0.1) ${percent}%, rgba(255, 255, 255, 0.1) 100%)`;
      if (output) output.textContent = slider.value;
    };

    updateSliderFill();
    slider.addEventListener("input", updateSliderFill);
  });
}

// Confirmation before irreversible lifecycle actions
function initConfirmForms() {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg = form.getAttribute("data-confirm");
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-confirm-target]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const form = btn.closest("form");
      if (!form) return;
      const action = btn.value;
      const isReject = action === "reject";
      const promptText = isReject ? "Are you sure you want to reject this idea?" : "Confirm this action?";
      if (!confirm(promptText)) {
        e.preventDefault();
      }
    });
  });
}

// 1-Click Demo Account Autofill for quick and seamless evaluation
function initDemoCredentials() {
  document.querySelectorAll(".demo-chip-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const u = btn.dataset.username;
      const p = btn.dataset.password;
      const r = btn.dataset.role;

      const userField = document.querySelector('input[name="username"]');
      const passField = document.querySelector('input[name="password"]');
      const roleSelect = document.querySelector('select[name="role"]');

      if (userField && u) userField.value = u;
      if (passField && p) passField.value = p;
      if (roleSelect && r) {
        roleSelect.value = r;
        roleSelect.dispatchEvent(new Event("change"));
      }

      // Visual pulse on form
      const card = document.querySelector(".auth-card-modern");
      if (card) {
        card.style.transform = "scale(1.01)";
        setTimeout(() => { card.style.transform = ""; }, 200);
      }
    });
  });
}

// Global hotkeys (e.g., press '/' to focus search input)
function initKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
      const searchInput = document.getElementById("table-search");
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    }
  });
}
