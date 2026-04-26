/**
 * Magasin Plan Editor 5.0
 * Refonte complète - Architecture Orientée État (Figma-style)
 */

class PlanEditor {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.wrapper = this.canvas.parentElement;
        this.root = document.getElementById('mpe-root');

        // --- État Central ---
        this.state = {
            mode: 'select',
            prevMode: 'select',
            selected: { type: null, id: null },
            interaction: {
                isDragging: false,
                isResizing: false,
                isDrawing: false,
                isPanning: false,
                dragStart: { x: 0, y: 0 },
                startRect: null,
                lastMousePos: { x: 0, y: 0 }
            },
            viewport: {
                zoom: 1,
                scrollLeft: 0,
                scrollTop: 0,
                showGrid: true,
                snapToGrid: true,
                gridSize: 32
            },
            data: {
                plan: { width: 2000, height: 1200 },
                zones: [],
                delimitations: [],
                articlesDisponibles: []
            },
            dirty: false,
            loading: false,
            needsRender: true
        };

        // --- Configuration ---
        this.config = {
            colors: {
                selection: '#3b82f6',
                gridMajor: '#e2e8f0',
                gridMinor: '#f1f5f9',
                handle: '#ffffff'
            },
            palettes: {
                zones: ['#dbeafe', '#dcfce7', '#fef9c3', '#fde68a', '#bfdbfe', '#ccfbf1', '#f1f5f9'],
                rayons: ['#ffffff', '#f8fafc', '#f1f5f9', '#dbeafe', '#dcfce7', '#fef9c3', '#fee2e2'],
                delims: ['#000000', '#4b5563', '#dc2626', '#2563eb', '#16a34a', '#d97706']
            }
        };

        this.init();
    }

    async init() {
        this.setLoading(true);
        try {
            await this.loadData();
            this.setupEventListeners();
            this.fitToScreen();
            this.startRenderLoop();
            this.setLoading(false);
            this.showMessage("Éditeur prêt", "info");
        } catch (e) {
            console.error("Init failed:", e);
            this.showMessage("Erreur critique d'initialisation", "danger");
        }
    }

    // --- Data Management ---

    async loadData() {
        const res = await fetch('/magasin/api/plan/');
        const json = await res.json();
        if (!json.success) throw new Error(json.error);
        
        this.state.data = {
            plan: json.plan || { width: 2000, height: 1200 },
            zones: json.zones || [],
            delimitations: json.delimitations || [],
            articlesDisponibles: json.articles_disponibles || []
        };
        
        this.canvas.width = this.state.data.plan.width;
        this.canvas.height = this.state.data.plan.height;
        this.state.dirty = false;
        this.updateUI();
    }

    async saveChanges() {
        this.setLoading(true);
        try {
            const payload = {
                zones: this.state.data.zones.map(z => ({
                    id: z.id, x: z.x, y: z.y, w: z.w, h: z.h,
                    nom: z.nom, code: z.code, couleur: z.couleur, type_zone: z.type_zone
                })),
                rayons: [],
                delimitations: this.state.data.delimitations.map(d => ({
                    id: d.id, x: d.x, y: d.y, w: d.w, h: d.h,
                    nom: d.nom, couleur: d.couleur, type: d.type, epaisseur: d.epaisseur, style: d.style
                }))
            };

            this.state.data.zones.forEach(z => {
                if (z.rayons) {
                    z.rayons.forEach(r => payload.rayons.push({
                        id: r.id, x: r.x, y: r.y, w: r.w, h: r.h,
                        nom: r.nom, code: r.code, couleur: r.couleur,
                        type_stock: r.type_stock, nombre_niveaux: r.nombre_niveaux
                    }));
                }
            });

            const res = await fetch('/magasin/api/plan/positions/', {
                method: 'PATCH',
                headers: this.getHeaders(),
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.success) {
                this.state.dirty = false;
                this.updateUI();
                this.showMessage("Plan enregistré avec succès", "success");
            } else throw new Error(result.error);
        } catch (e) {
            this.showMessage("Erreur : " + e.message, "danger");
        } finally {
            this.setLoading(false);
        }
    }

    // --- Event Listeners ---

    setupEventListeners() {
        // Canvas Events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));
        window.addEventListener('mouseup', (e) => this.onMouseUp(e));
        
        // Viewport Controls
        document.getElementById('btn-zoom-in').onclick = () => this.zoom(0.2);
        document.getElementById('btn-zoom-out').onclick = () => this.zoom(-0.2);
        document.getElementById('btn-zoom-reset').onclick = () => { this.state.viewport.zoom = 1; this.applyZoom(); };
        document.getElementById('btn-fit').onclick = () => this.fitToScreen();
        document.getElementById('btn-grid-toggle').onclick = (e) => {
            this.state.viewport.showGrid = !this.state.viewport.showGrid;
            e.currentTarget.classList.toggle('active', this.state.viewport.showGrid);
            this.requestRender();
        };

        // Modes
        document.querySelectorAll('.mpe-tool-btn[data-mode]').forEach(btn => {
            btn.onclick = () => this.setMode(btn.dataset.mode);
        });

        // Global Actions
        document.getElementById('btn-save').onclick = () => this.saveChanges();
        
        // Keyboard Shortcuts
        window.addEventListener('keydown', (e) => {
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
            if (e.code === 'Space') {
                if (this.state.mode !== 'pan') {
                    this.state.prevMode = this.state.mode;
                    this.setMode('pan');
                }
                e.preventDefault();
            }
            if (e.key === 'v') this.setMode('select');
            if (e.key === 'z') this.setMode('add_zone');
            if (e.key === 'r') this.setMode('add_rayon');
            if (e.key === 'd') this.setMode('add_delim');
            if (e.key === 'Delete' || e.key === 'Backspace') this.deleteSelected();
        });

        window.addEventListener('keyup', (e) => {
            if (e.code === 'Space' && this.state.mode === 'pan') {
                this.setMode(this.state.prevMode);
            }
        });

        // Zoom Molette
        this.wrapper.addEventListener('wheel', (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                this.zoom(e.deltaY > 0 ? -0.1 : 0.1);
            }
        }, { passive: false });
    }

    // --- Interaction Logic ---

    onMouseDown(e) {
        const pos = this.getMousePos(e);
        this.state.interaction.lastMousePos = pos;

        if (this.state.mode === 'pan') {
            this.state.interaction.isPanning = true;
            this.state.interaction.dragStart = { x: e.clientX, y: e.clientY };
            this.state.interaction.startRect = { left: this.wrapper.scrollLeft, top: this.wrapper.scrollTop };
            return;
        }

        if (['add_zone', 'add_rayon', 'add_delim'].includes(this.state.mode)) {
            this.state.interaction.isDrawing = true;
            this.state.interaction.dragStart = pos;
            this.state.tempRect = { x: pos.x, y: pos.y, w: 0, h: 0 };
            return;
        }

        if (this.state.mode === 'select') {
            const item = this.getSelectedObject();
            if (item && this.isOverHandle(pos, item)) {
                this.state.interaction.isResizing = true;
                this.state.interaction.dragStart = pos;
                this.state.interaction.startRect = { ...item };
                return;
            }

            // Hit test hiérarchique
            const rayon = this.hitTestRayon(pos.x, pos.y);
            if (rayon) {
                this.selectObject('rayon', rayon.id);
                this.state.interaction.isDragging = true;
                this.state.interaction.dragStart = { x: pos.x - rayon.x, y: pos.y - rayon.y };
                return;
            }

            const delim = this.hitTestDelim(pos.x, pos.y);
            if (delim) {
                this.selectObject('delim', delim.id);
                this.state.interaction.isDragging = true;
                this.state.interaction.dragStart = { x: pos.x - delim.x, y: pos.y - delim.y };
                return;
            }

            const zone = this.hitTestZone(pos.x, pos.y);
            if (zone) {
                this.selectObject('zone', zone.id);
                this.state.interaction.isDragging = true;
                this.state.interaction.dragStart = { x: pos.x - zone.x, y: pos.y - zone.y };
                return;
            }

            this.clearSelection();
        }
    }

    onMouseMove(e) {
        const pos = this.getMousePos(e);
        const inter = this.state.interaction;

        if (inter.isPanning) {
            this.wrapper.scrollLeft = inter.startRect.left - (e.clientX - inter.dragStart.x);
            this.wrapper.scrollTop = inter.startRect.top - (e.clientY - inter.dragStart.y);
            return;
        }

        if (inter.isDrawing) {
            this.state.tempRect = {
                x: Math.min(pos.x, inter.dragStart.x),
                y: Math.min(pos.y, inter.dragStart.y),
                w: Math.abs(pos.x - inter.dragStart.x),
                h: Math.abs(pos.y - inter.dragStart.y)
            };
            this.requestRender();
        }

        if (inter.isDragging || inter.isResizing) {
            const item = this.getSelectedObject();
            if (!item) return;

            this.state.dirty = true;
            this.updateUI();

            if (inter.isDragging) {
                const oldX = item.x;
                const oldY = item.y;

                item.x = this.clamp(pos.x - inter.dragStart.x, 0, this.canvas.width - item.w);
                item.y = this.clamp(pos.y - inter.dragStart.y, 0, this.canvas.height - item.h);

                const dx = item.x - oldX;
                const dy = item.y - oldY;

                // Liaison Parent-Enfant : déplacer les rayons avec la zone
                if (this.state.selected.type === 'zone' && item.rayons) {
                    item.rayons.forEach(r => {
                        r.x += dx;
                        r.y += dy;
                    });
                }
            } else if (inter.isResizing) {
                const min = 32;
                item.w = this.clamp(pos.x - item.x, min, this.canvas.width - item.x);
                item.h = this.clamp(pos.y - item.y, min, this.canvas.height - item.y);
            }
            this.requestRender();
            this.syncSidebarCoords(item);
        }

        // Mise à jour coordonnées status bar
        const coordEl = document.getElementById('status-coords');
        if (coordEl) coordEl.innerText = `X: ${Math.round(pos.x)}, Y: ${Math.round(pos.y)}`;
    }

    async onMouseUp() {
        const inter = this.state.interaction;
        if (inter.isDrawing) {
            const rect = this.state.tempRect;
            if (rect && rect.w > 20 && rect.h > 20) {
                if (this.state.mode === 'add_zone') await this.createZone(rect);
                else if (this.state.mode === 'add_rayon') {
                    const zone = this.hitTestZone(rect.x + rect.w/2, rect.y + rect.h/2);
                    if (zone) await this.createRayon(rect, zone.id);
                    else this.showMessage("Le rayon doit être placé dans une zone.", "warning");
                }
                else if (this.state.mode === 'add_delim') await this.createDelim(rect);
            }
        }
        
        inter.isDragging = false;
        inter.isResizing = false;
        inter.isDrawing = false;
        inter.isPanning = false;
        this.state.tempRect = null;
        this.requestRender();
    }

    // --- Actions ---

    async createZone(rect) {
        const nom = prompt("Nom de la nouvelle zone ?"); if (!nom) return;
        this.setLoading(true);
        try {
            const res = await fetch('/magasin/api/zones/', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ nom, x: rect.x, y: rect.y, w: rect.w, h: rect.h })
            });
            const data = await res.json();
            if (data.success) {
                await this.loadData();
                this.selectObject('zone', data.id);
                this.showMessage("Zone créée", "success");
            } else throw new Error(data.error);
        } catch (e) { this.showMessage(e.message, "danger"); }
        finally { this.setLoading(false); }
    }

    async createRayon(rect, zoneId) {
        const nom = prompt("Nom du rayon ?"); if (!nom) return;
        this.setLoading(true);
        try {
            const res = await fetch('/magasin/api/rayons/', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ zone_id: zoneId, nom, x: rect.x, y: rect.y, w: rect.w, h: rect.h })
            });
            const data = await res.json();
            if (data.success) {
                await this.loadData();
                this.selectObject('rayon', data.id);
                this.showMessage("Rayon créé", "success");
            } else throw new Error(data.error);
        } catch (e) { this.showMessage(e.message, "danger"); }
        finally { this.setLoading(false); }
    }

    async createDelim(rect) {
        const nom = prompt("Nom de la délimitation ?"); if (!nom) return;
        this.setLoading(true);
        try {
            const res = await fetch('/magasin/api/delimitations/', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ nom, x: rect.x, y: rect.y, w: rect.w, h: rect.h })
            });
            const data = await res.json();
            if (data.success) {
                await this.loadData();
                this.selectObject('delim', data.id);
                this.showMessage("Délimitation créée", "success");
            } else throw new Error(data.error);
        } catch (e) { this.showMessage(e.message, "danger"); }
        finally { this.setLoading(false); }
    }

    async deleteSelected(force = false) {
        const obj = this.getSelectedObject();
        if (!obj) return;
        
        const typeLabel = { 'zone': 'la zone', 'rayon': 'le rayon', 'delim': 'la délimitation' }[this.state.selected.type];
        const confirmMsg = force 
            ? `ATTENTION : Cette action retirera TOUTES les affectations et supprimera ${typeLabel} "${obj.nom || obj.code}". Confirmer ?`
            : `Supprimer définitivement ${typeLabel} "${obj.nom || obj.code}" ?`;
            
        if (!confirm(confirmMsg)) return;

        let url = "";
        if (this.state.selected.type === 'zone') url = `/magasin/api/zones/${obj.id}/delete/`;
        else if (this.state.selected.type === 'rayon') url = `/magasin/api/rayons/${obj.id}/delete/`;
        else if (this.state.selected.type === 'delim') url = `/magasin/api/delimitations/${obj.id}/delete/`;

        if (force) url += "?force=true";

        this.setLoading(true);
        try {
            const res = await fetch(url, { method: 'DELETE', headers: this.getHeaders() });
            const data = await res.json();
            
            if (data.success) {
                this.state.selected.blocker = null;
                this.clearSelection();
                await this.loadData();
                this.showMessage(data.message, "success");
            } else {
                if (data.reason === 'HAS_AFFECTATIONS' || data.reason === 'HAS_RAYONS') {
                    this.state.selected.blocker = data;
                    this.renderProperties();
                    this.showMessage(data.error, "warning");
                } else {
                    throw new Error(data.error || "Erreur lors de la suppression");
                }
            }
        } catch (e) { 
            this.showMessage(e.message, "danger"); 
        } finally { 
            this.setLoading(false); 
        }
    }

    async updateItemProperty(key, value) {
        const obj = this.getSelectedObject();
        if (!obj) return;
        obj[key] = value;
        this.state.dirty = true;
        this.updateUI();
        this.requestRender();
        if (['nom', 'code', 'couleur', 'type_zone', 'type_stock', 'type', 'style'].includes(key)) {
            this.renderProperties();
        }
    }

    async affecterArticle() {
        const artVal = document.getElementById('sel-art').value;
        const nivId = document.getElementById('sel-niv').value;
        if (!artVal || !nivId) return;
        const [type, id] = artVal.split(':');
        
        this.setLoading(true);
        try {
            const res = await fetch('/magasin/api/affectations/', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ niveau_id: nivId, type_article: type, article_id: id })
            });
            const data = await res.json();
            if (data.success) {
                await this.loadData();
                this.renderProperties();
                this.showMessage("Article affecté", "success");
            } else throw new Error(data.error);
        } catch (e) { this.showMessage(e.message, "danger"); }
        finally { this.setLoading(false); }
    }

    async retirerAffectation(affId) {
        if (!confirm("Retirer cet article ?")) return;
        this.setLoading(true);
        try {
            const res = await fetch(`/magasin/api/affectations/${affId}/delete/`, { method: 'DELETE', headers: this.getHeaders() });
            const data = await res.json();
            if (data.success) {
                if (this.state.selected) this.state.selected.blocker = null;
                await this.loadData();
                this.renderProperties();
                this.showMessage("Article retiré", "info");
            } else throw new Error(data.error);
        } catch (e) { this.showMessage(e.message, "danger"); }
        finally { this.setLoading(false); }
    }

    // --- Hit Testing ---

    hitTestRayon(x, y) {
        for (let z of this.state.data.zones) {
            const r = (z.rayons || []).slice().reverse().find(r => this.isInside({x, y}, r));
            if (r) return r;
        }
        return null;
    }
    hitTestDelim(x, y) { return this.state.data.delimitations.slice().reverse().find(d => this.isInside({x, y}, d)); }
    hitTestZone(x, y) { return this.state.data.zones.slice().reverse().find(z => this.isInside({x, y}, z)); }
    isInside(pos, rect) { return pos.x >= rect.x && pos.x <= rect.x + rect.w && pos.y >= rect.y && pos.y <= rect.y + rect.h; }
    isOverHandle(pos, item) { return Math.sqrt(Math.pow(pos.x - (item.x + item.w), 2) + Math.pow(pos.y - (item.y + item.h), 2)) < 10 / this.state.viewport.zoom; }

    // --- Rendering ---

    startRenderLoop() {
        const loop = () => {
            if (this.state.needsRender) {
                this.render();
                this.state.needsRender = false;
            }
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }

    requestRender() { this.state.needsRender = true; }

    render() {
        const { ctx, canvas, viewport, data } = this.state;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        if (viewport.showGrid) this.drawGrid();

        // Layer 1: Zones
        data.zones.forEach(z => this.drawZone(z));
        // Layer 2: Delims
        data.delimitations.forEach(d => this.drawDelim(d));
        // Layer 3: Temp Drawing
        if (this.state.tempRect) this.drawTempRect(this.state.tempRect);
        // Layer 4: Selection
        this.drawSelectionOverlay();
    }

    drawGrid() {
        const { ctx } = this;
        const { gridSize } = this.state.viewport;
        ctx.save();
        ctx.beginPath();
        for (let x = 0; x <= this.canvas.width; x += gridSize) {
            ctx.lineWidth = (x % (gridSize * 5) === 0) ? 1 : 0.5;
            ctx.strokeStyle = (x % (gridSize * 5) === 0) ? '#e2e8f0' : '#f1f5f9';
            ctx.moveTo(x, 0); ctx.lineTo(x, this.canvas.height);
        }
        for (let y = 0; y <= this.canvas.height; y += gridSize) {
            ctx.lineWidth = (y % (gridSize * 5) === 0) ? 1 : 0.5;
            ctx.strokeStyle = (y % (gridSize * 5) === 0) ? '#e2e8f0' : '#f1f5f9';
            ctx.moveTo(0, y); ctx.lineTo(this.canvas.width, y);
        }
        ctx.stroke();
        ctx.restore();
    }

    drawZone(z) {
        const { ctx } = this;
        ctx.fillStyle = z.couleur || '#f8fafc';
        ctx.globalAlpha = 0.4; ctx.fillRect(z.x, z.y, z.w, z.h); ctx.globalAlpha = 1;
        ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 1; ctx.strokeRect(z.x, z.y, z.w, z.h);
        
        ctx.fillStyle = '#64748b'; ctx.font = 'bold 12px Inter';
        ctx.fillText(`${z.code} - ${z.nom}`, z.x + 8, z.y + 18);

        if (z.rayons) z.rayons.forEach(r => this.drawRayon(r));
    }

    drawRayon(r) {
        const { ctx } = this;
        ctx.fillStyle = r.couleur || '#ffffff'; ctx.fillRect(r.x, r.y, r.w, r.h);
        
        let border = '#94a3b8';
        if (r.stats && r.stats.worst_statut !== 'NORMAL') {
            const colors = { 'RUPTURE': '#ef4444', 'CRITIQUE': '#f97316', 'ALERTE': '#f59e0b' };
            border = colors[r.stats.worst_statut] || border;
        }
        ctx.strokeStyle = border; ctx.lineWidth = 1.5; ctx.strokeRect(r.x, r.y, r.w, r.h);
        
        ctx.fillStyle = '#1e293b'; ctx.font = 'bold 10px Inter';
        ctx.fillText(r.code, r.x + 4, r.y + 12);

        if (r.stats && (r.stats.ruptures > 0 || r.stats.alertes > 0)) {
            ctx.fillStyle = '#ffc107'; ctx.fillRect(r.x, r.y - 12, r.w, 12);
            ctx.fillStyle = '#000'; ctx.font = 'bold 8px Inter';
            ctx.fillText("⚠️ RÉAPPRO", r.x + 4, r.y - 3);
        }
    }

    drawDelim(d) {
        const { ctx } = this;
        ctx.save();
        ctx.strokeStyle = d.couleur || '#000'; ctx.lineWidth = d.epaisseur || 2;
        if (d.style === 'POINTILLE') ctx.setLineDash([6, 4]);
        ctx.strokeRect(d.x, d.y, d.w, d.h);
        ctx.fillStyle = d.couleur || '#000'; ctx.globalAlpha = 0.08; ctx.fillRect(d.x, d.y, d.w, d.h); ctx.globalAlpha = 1;
        ctx.font = 'italic 10px Inter'; ctx.fillText(d.nom, d.x + 5, d.y + 14);
        ctx.restore();
    }

    drawTempRect(rect) {
        const { ctx } = this;
        ctx.strokeStyle = this.getModeColor(); ctx.lineWidth = 2; ctx.setLineDash([5, 5]);
        ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
        ctx.globalAlpha = 0.2; ctx.fillStyle = this.getModeColor(); ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
        ctx.setLineDash([]); ctx.globalAlpha = 1;
    }

    drawSelectionOverlay() {
        const item = this.getSelectedObject();
        if (!item) return;
        const { ctx } = this;
        ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2.5;
        ctx.strokeRect(item.x - 2, item.y - 2, item.w + 4, item.h + 4);
        
        // Handle de redimensionnement
        ctx.fillStyle = 'white'; ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(item.x + item.w, item.y + item.h, 6, 0, Math.PI*2); ctx.fill(); ctx.stroke();
    }

    // --- UI Update ---

    updateUI() {
        const statusText = document.getElementById('status-text');
        if (statusText) {
            const modes = { 'select': 'Sélection', 'pan': 'Navigation', 'add_zone': '+ Zone', 'add_rayon': '+ Rayon', 'add_delim': '+ Délimitation' };
            statusText.innerText = `Mode: ${modes[this.state.mode]} | ${this.state.dirty ? 'Modifications en cours...' : 'Prêt'}`;
        }
        document.getElementById('unsaved-badge').classList.toggle('d-none', !this.state.dirty);
        document.getElementById('btn-save').disabled = !this.state.dirty;
    }

    renderProperties() {
        const panel = document.getElementById('sp-body');
        const obj = this.getSelectedObject();
        if (!obj) {
            panel.innerHTML = `<div class="text-center py-5 text-muted"><i class="bi bi-info-circle mb-3 d-block fs-1 opacity-25"></i><p class="small">Sélectionnez un élément.</p></div>`;
            return;
        }

        let html = `<div class="mb-3 d-flex justify-content-between align-items-center">
            <span class="badge bg-primary-subtle text-primary border border-primary-subtle">${this.state.selected.type.toUpperCase()}</span>
            <span class="small text-muted font-monospace">ID: ${obj.id}</span>
        </div>`;

        if (this.state.selected.blocker) {
            html += this.getBlockerHtml(this.state.selected.blocker);
        } else {
            if (this.state.selected.type === 'zone') html += this.getZoneForm(obj);
            else if (this.state.selected.type === 'rayon') html += this.getRayonForm(obj);
            else if (this.state.selected.type === 'delim') html += this.getDelimForm(obj);
        }

        panel.innerHTML = html;
    }

    getBlockerHtml(blocker) {
        let listHtml = '';
        if (blocker.reason === 'HAS_AFFECTATIONS') {
            blocker.affectations.forEach(a => {
                listHtml += `
                    <div class="mpe-aff-item d-flex justify-content-between align-items-center bg-warning-subtle border-warning-subtle">
                        <div class="small">
                            <div class="fw-bold">${a.reference}</div>
                            <div class="x-small">Niv ${a.niveau} • ${a.quantite}${a.unite}</div>
                        </div>
                        <button type="button" class="btn btn-xs btn-danger" onclick="editor.retirerAffectation(${a.id})" title="Retirer l'affectation">
                            <i class="bi bi-trash-fill"></i>
                        </button>
                    </div>`;
            });
            
            return `
                <div class="alert alert-warning p-2 small mb-3">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>Suppression bloquée</strong><br>Ce rayon contient encore du stock.
                </div>
                <div class="mb-3">
                    <label class="small fw-bold mb-2">Articles à retirer :</label>
                    <div style="max-height: 200px; overflow-y: auto;">${listHtml}</div>
                </div>
                <div class="d-grid gap-2">
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="editor.state.selected.blocker=null; editor.renderProperties();">Annuler</button>
                    <button type="button" class="btn btn-sm btn-danger" onclick="editor.deleteSelected(true)"><i class="bi bi-shield-lock me-2"></i>Forcer la suppression (Admin)</button>
                </div>
            `;
        } else if (blocker.reason === 'HAS_RAYONS') {
            blocker.rayons.forEach(r => {
                listHtml += `
                    <div class="mpe-aff-item d-flex justify-content-between align-items-center">
                        <div class="small">
                            <div class="fw-bold">${r.code}</div>
                            <div class="x-small">${r.nom} ${r.has_stock ? '⚠️ Contient du stock' : ''}</div>
                        </div>
                    </div>`;
            });
            return `
                <div class="alert alert-warning p-2 small mb-3">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>Zone occupée</strong><br>Elle contient ${blocker.rayons.length} rayon(s).
                </div>
                <div class="mb-3">
                    <label class="small fw-bold mb-2">Rayons présents :</label>
                    <div style="max-height: 200px; overflow-y: auto;">${listHtml}</div>
                </div>
                <p class="x-small text-muted mb-3 text-center">Videz la zone ou déplacez les rayons avant de la supprimer.</p>
                <button type="button" class="btn btn-sm btn-outline-secondary w-100" onclick="editor.state.selected.blocker=null; editor.renderProperties();">Retour</button>
            `;
        }
        return '';
    }

    getZoneForm(z) {
        return `
            <div class="mb-3"><label class="small fw-bold mb-1">Code & Nom</label>
                <div class="row g-2">
                    <div class="col-4"><input type="text" class="form-control form-control-sm" value="${z.code}" onchange="editor.updateItemProperty('code', this.value)"></div>
                    <div class="col-8"><input type="text" class="form-control form-control-sm" value="${z.nom}" onchange="editor.updateItemProperty('nom', this.value)"></div>
                </div>
            </div>
            <div class="mb-3"><label class="small fw-bold mb-1">Type de zone</label>
                <select class="form-select form-select-sm" onchange="editor.updateItemProperty('type_zone', this.value)">
                    ${this.state.data.articlesDisponibles ? '' : '' /* mock skip */}
                    <option value="MIXTE" ${z.type_zone==='MIXTE'?'selected':''}>Mixte</option>
                    <option value="FROIDE" ${z.type_zone==='FROIDE'?'selected':''}>Froide</option>
                    <option value="SECHE" ${z.type_zone==='SECHE'?'selected':''}>Sèche</option>
                </select>
            </div>
            <div class="mb-3"><label class="small fw-bold mb-1">Couleur</label>
                <div class="d-flex gap-1 flex-wrap mb-2">
                    ${this.config.palettes.zones.map(c => `<button type="button" class="mpe-palette-btn" style="background:${c}" onclick="editor.updateItemProperty('couleur', '${c}')"></button>`).join('')}
                    <input type="color" class="form-control-color form-control-sm border-0 p-0" value="${z.couleur}" onchange="editor.updateItemProperty('couleur', this.value)">
                </div>
            </div>
            <div class="alert alert-info p-2 x-small mb-3">
                <i class="bi bi-info-circle me-1"></i>
                ${z.rayons && z.rayons.length > 0 ? `Contient ${z.rayons.length} rayon(s).` : "Zone vide."}
            </div>
            <hr class="my-3">
            <button type="button" class="btn btn-sm btn-outline-danger w-100" onclick="editor.deleteSelected()"><i class="bi bi-trash me-2"></i>Supprimer la zone</button>
        `;
    }

    getRayonForm(r) {
        let affList = '';
        (r.niveaux || []).forEach(n => {
            (n.affectations || []).forEach(aff => {
                const color = aff.statut_stock === 'RUPTURE' ? 'danger' : (aff.statut_stock === 'CRITIQUE' ? 'warning' : 'info');
                affList += `<div class="mpe-aff-item d-flex justify-content-between align-items-center">
                    <div><div class="fw-bold small">${aff.reference} <span class="badge bg-${color}" style="font-size:7px">${aff.statut_stock}</span></div>
                    <div class="x-small text-muted">Niv. ${n.numero} • ${aff.stock_actuel} ${aff.unite}</div></div>
                    <button type="button" class="btn btn-xs text-danger" onclick="editor.retirerAffectation(${aff.id})"><i class="bi bi-x-circle"></i></button>
                </div>`;
            });
        });

        return `
            <div class="mb-3"><label class="small fw-bold mb-1">Code & Nom</label>
                <div class="row g-2">
                    <div class="col-4"><input type="text" class="form-control form-control-sm" value="${r.code}" onchange="editor.updateItemProperty('code', this.value)"></div>
                    <div class="col-8"><input type="text" class="form-control form-control-sm" value="${r.nom}" onchange="editor.updateItemProperty('nom', this.value)"></div>
                </div>
            </div>
            <div class="bg-light p-2 rounded mb-3">
                <label class="small fw-bold d-block mb-2">Affectations</label>
                <div style="max-height:120px; overflow-y:auto;" class="mb-2">${affList || '<div class="text-center x-small text-muted py-2">Vide</div>'}</div>
                <select id="sel-art" class="form-select form-select-sm mb-1"><option value="">-- Article --</option>
                    ${this.state.data.articlesDisponibles.map(a => `<option value="${a.type_article}:${a.id}">${a.reference}</option>`).join('')}
                </select>
                <select id="sel-niv" class="form-select form-select-sm mb-2">
                    ${(r.niveaux || []).map(n => `<option value="${n.id}">Niveau ${n.numero}</option>`).join('')}
                </select>
                <button type="button" class="btn btn-primary btn-sm w-100" onclick="editor.affecterArticle()">Affecter</button>
            </div>
            <div class="mb-3"><label class="small fw-bold mb-1">Stock</label>
                <select class="form-select form-select-sm" onchange="editor.updateItemProperty('type_stock', this.value)">
                    <option value="MIXTE" ${r.type_stock==='MIXTE'?'selected':''}>Mixte</option>
                    <option value="MATIERE_PREMIERE" ${r.type_stock==='MATIERE_PREMIERE'?'selected':''}>MP</option>
                    <option value="PRODUIT_FINI" ${r.type_stock==='PRODUIT_FINI'?'selected':''}>PF</option>
                </select>
            </div>
            <div class="alert alert-info p-2 x-small mb-3">
                <i class="bi bi-info-circle me-1"></i>
                ${r.niveaux && r.niveaux.some(n => n.affectations && n.affectations.length > 0) 
                    ? "Ce rayon contient des articles affectés." 
                    : "Ce rayon est vide."}
            </div>
            <hr class="my-3">
            <button type="button" class="btn btn-sm btn-outline-danger w-100" onclick="editor.deleteSelected()"><i class="bi bi-trash me-2"></i>Supprimer le rayon</button>
        `;
    }

    getDelimForm(d) {
        return `
            <div class="mb-3"><label class="small fw-bold mb-1">Nom</label><input type="text" class="form-control form-control-sm" value="${d.nom}" onchange="editor.updateItemProperty('nom', this.value)"></div>
            <div class="mb-3"><label class="small fw-bold mb-1">Style</label>
                <select class="form-select form-select-sm" onchange="editor.updateItemProperty('style', this.value)">
                    <option value="PLEIN" ${d.style==='PLEIN'?'selected':''}>Plein</option>
                    <option value="POINTILLE" ${d.style==='POINTILLE'?'selected':''}>Pointillé</option>
                </select>
            </div>
            <div class="mb-3"><label class="small fw-bold mb-1">Couleur</label>
                <div class="d-flex gap-1 flex-wrap mb-2">
                    ${this.config.palettes.delims.map(c => `<button type="button" class="mpe-palette-btn" style="background:${c}" onclick="editor.updateItemProperty('couleur', '${c}')"></button>`).join('')}
                    <input type="color" class="form-control-color form-control-sm border-0 p-0" value="${d.couleur}" onchange="editor.updateItemProperty('couleur', this.value)">
                </div>
            </div>
            <hr class="my-3">
            <button type="button" class="btn btn-sm btn-outline-danger w-100" onclick="editor.deleteSelected()"><i class="bi bi-trash me-2"></i>Supprimer</button>
        `;
    }

    // --- Helpers ---

    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        let x = (e.clientX - rect.left) / this.state.viewport.zoom;
        let y = (e.clientY - rect.top) / this.state.viewport.zoom;
        if (this.state.viewport.snapToGrid && this.state.mode !== 'pan') {
            const gs = this.state.viewport.gridSize / 2;
            x = Math.round(x / gs) * gs; y = Math.round(y / gs) * gs;
        }
        return { x, y };
    }

    selectObject(type, id) {
        this.state.selected = { type, id };
        this.renderProperties();
        this.requestRender();
    }

    clearSelection() {
        if (this.state.selected) this.state.selected.blocker = null;
        this.state.selected = { type: null, id: null, blocker: null };
        this.renderProperties();
        this.requestRender();
    }

    getSelectedObject() {
        const { type, id } = this.state.selected;
        if (!type || !id) return null;
        if (type === 'zone') return this.state.data.zones.find(z => z.id === id);
        if (type === 'rayon') {
            for (let z of this.state.data.zones) {
                const r = (z.rayons || []).find(r => r.id === id);
                if (r) return r;
            }
        }
        if (type === 'delim') return this.state.data.delimitations.find(d => d.id === id);
        return null;
    }

    setMode(mode) {
        this.state.mode = mode;
        this.root.dataset.mode = mode;
        document.querySelectorAll('.mpe-tool-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
        this.wrapper.className = 'mpe-canvas-wrapper mode-' + mode;
        this.updateUI();
    }

    zoom(delta) {
        this.state.viewport.zoom = this.clamp(this.state.viewport.zoom + delta, 0.2, 3);
        this.applyZoom();
    }

    applyZoom() {
        this.canvas.style.transform = `scale(${this.state.viewport.zoom})`;
        this.canvas.style.transformOrigin = 'top left';
        this.requestRender();
    }

    fitToScreen() {
        const padding = 60;
        const scaleX = (this.wrapper.clientWidth - padding) / this.state.data.plan.width;
        const scaleY = (this.wrapper.clientHeight - padding) / this.state.data.plan.height;
        this.state.viewport.zoom = Math.min(scaleX, scaleY, 1);
        this.applyZoom();
        this.centerView();
    }

    centerView() {
        const cw = this.canvas.width * this.state.viewport.zoom;
        const ch = this.canvas.height * this.state.viewport.zoom;
        this.wrapper.scrollLeft = (cw - this.wrapper.clientWidth) / 2;
        this.wrapper.scrollTop = (ch - this.wrapper.clientHeight) / 2;
    }

    setLoading(loading) {
        this.state.loading = loading;
        document.getElementById('mpe-loader').classList.toggle('d-none', !loading);
    }

    showMessage(msg, type = "info") {
        const el = document.getElementById('status-text');
        if (el) {
            const original = el.innerText;
            el.innerHTML = `<span class="text-${type === 'danger' ? 'danger' : (type === 'success' ? 'success' : 'white')} fw-bold">${msg}</span>`;
            if (type !== 'info') setTimeout(() => el.innerText = original, 4000);
        }
    }

    getHeaders() { return { 'Content-Type': 'application/json', 'X-CSRFToken': this.getCsrf() }; }

    getCsrf() {
        const name = 'csrftoken'; let val = null;
        if (document.cookie && document.cookie !== '') {
            for (let c of document.cookie.split(';')) {
                c = c.trim();
                if (c.substring(0, name.length + 1) === (name + '=')) { val = decodeURIComponent(c.substring(name.length + 1)); break; }
            }
        }
        return val;
    }

    clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
    getModeColor() {
        const c = { 'add_zone': '#3b82f6', 'add_rayon': '#10b981', 'add_delim': '#ef4444' };
        return c[this.state.mode] || '#64748b';
    }

    syncSidebarCoords(item) {
        // Optionnel : mise à jour en temps réel des inputs X/Y si présents
    }
}

// Init
window.editor = new PlanEditor('mc');
