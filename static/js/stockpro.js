/**
 * StockPro — JavaScript Principal
 * MediCare Industries — Meknès, Maroc
 */

'use strict';

// ============================================================
// SIDEBAR TOGGLE
// ============================================================
document.addEventListener('DOMContentLoaded', function () {

    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const toggleBtn = document.getElementById('sidebarToggle');
    const SIDEBAR_KEY = 'stockpro_sidebar_collapsed';

    // Restaurer l'état de la sidebar
    const isMobile = window.innerWidth < 768;
    const isCollapsed = !isMobile && localStorage.getItem(SIDEBAR_KEY) === '1';
    if (isCollapsed && sidebar) sidebar.classList.add('collapsed');

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function () {
            if (window.innerWidth < 768) {
                sidebar.classList.toggle('mobile-open');
            } else {
                sidebar.classList.toggle('collapsed');
                localStorage.setItem(SIDEBAR_KEY, sidebar.classList.contains('collapsed') ? '1' : '0');
                // Fermer tous les sous-menus ouverts lors du collapse
                if (sidebar.classList.contains('collapsed')) {
                    sidebar.querySelectorAll('.collapse.show').forEach(el => {
                        bootstrap.Collapse.getOrCreateInstance(el).hide();
                    });
                }
            }
        });
    }

    // ============================================================
    // AUTO-DISMISS DES MESSAGES
    // ============================================================
    document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // ============================================================
    // TOOLTIPS BOOTSTRAP
    // ============================================================
    const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipEls.forEach(el => new bootstrap.Tooltip(el, { trigger: 'hover' }));

    // ============================================================
    // CONFIRMATION AVANT SUPPRESSION
    // ============================================================
    document.querySelectorAll('[data-confirm]').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const msg = this.dataset.confirm || 'Êtes-vous sûr de vouloir effectuer cette action ?';
            if (!confirm(msg)) e.preventDefault();
        });
    });

    // ============================================================
    // RAFRAÎCHISSEMENT DES KPIs (toutes les 60s)
    // ============================================================
    if (document.getElementById('kpi-refresh-zone')) {
        setInterval(rafraichirKPIs, 60000);
    }

    // ============================================================
    // FORMAT DES NOMBRES
    // ============================================================
    document.querySelectorAll('[data-format-number]').forEach(el => {
        const val = parseFloat(el.textContent.replace(/\s/g, '').replace(',', '.'));
        if (!isNaN(val)) {
            el.textContent = new Intl.NumberFormat('fr-MA', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2
            }).format(val);
        }
    });

});

// ============================================================
// RAFRAÎCHISSEMENT KPIs AJAX
// ============================================================
function rafraichirKPIs() {
    fetch('/dashboard/api/kpis/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json())
    .then(data => {
        ['nb_ruptures', 'nb_alertes', 'nb_suggestions', 'nb_commandes_attente'].forEach(key => {
            const el = document.getElementById(`kpi-${key}`);
            if (el) el.textContent = data[key];
        });
        const valeur = document.getElementById('kpi-valeur_stock');
        if (valeur) {
            valeur.textContent = new Intl.NumberFormat('fr-MA', {
                minimumFractionDigits: 2, maximumFractionDigits: 2
            }).format(data.valeur_stock) + ' DH';
        }
    })
    .catch(err => console.warn('Refresh KPI failed:', err));
}

// ============================================================
// CHART.JS — UTILITAIRES
// ============================================================
const StockProCharts = {

    colors: {
        primary: '#0d6efd',
        success: '#198754',
        warning: '#ffc107',
        danger: '#dc3545',
        info: '#0dcaf0',
        purple: '#6610f2',
        grid: 'rgba(0,0,0,0.06)',
    },

    defaultFont: {
        family: 'Inter, system-ui, sans-serif',
        size: 12,
    },

    /**
     * Créer un graphique de ligne (évolution mouvements)
     */
    creerGraphiqueLigne(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { font: this.defaultFont } },
                    tooltip: { mode: 'index', intersect: false },
                },
                scales: {
                    x: { grid: { color: this.colors.grid } },
                    y: { beginAtZero: true, grid: { color: this.colors.grid } },
                },
                ...options,
            }
        });
    },

    /**
     * Créer un camembert (valorisation par catégorie)
     */
    creerCamembert(canvasId, labels, valeurs, couleurs = []) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        const defaultColors = [
            '#0d6efd', '#198754', '#ffc107', '#dc3545',
            '#0dcaf0', '#6610f2', '#fd7e14', '#20c997',
            '#d63384', '#6c757d',
        ];
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: valeurs,
                    backgroundColor: couleurs.length ? couleurs : defaultColors.slice(0, valeurs.length),
                    borderWidth: 2,
                    borderColor: '#fff',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { font: this.defaultFont } },
                },
                cutout: '65%',
            }
        });
    },

    /**
     * Créer un graphique barres (ABC)
     */
    creerBarres(canvasId, labels, datasets) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        return new Chart(ctx, {
            type: 'bar',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, grid: { color: this.colors.grid } },
                },
            }
        });
    },
};

// ============================================================
// FILTRES PRODUITS — SOUMISSION AUTO
// ============================================================
document.querySelectorAll('select[data-autosubmit]').forEach(select => {
    select.addEventListener('change', function () {
        this.closest('form').submit();
    });
});

// ============================================================
// MARQUER NOTIFICATION LUE
// ============================================================
function marquerNotifLue(pk) {
    fetch(`/notifications/${pk}/lue/`, {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json())
    .then(data => {
        const badge = document.querySelector('.badge[data-notif-badge]');
        if (badge) {
            data.non_lues > 0 ? (badge.textContent = data.non_lues) : badge.remove();
        }
    });
}

// ============================================================
// EXPORT GLOBAL
// ============================================================
window.StockProCharts = StockProCharts;
window.rafraichirKPIs = rafraichirKPIs;
