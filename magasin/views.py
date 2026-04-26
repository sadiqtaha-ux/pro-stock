"""
App Magasin - Vues
Vue 2D interactive du magasin, gestion des emplacements
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from core.mixins import KanbanListMixin, ExportMixin

from .models import ZoneStockage, Rayon, Emplacement, PlanMagasin, NiveauRayon, AffectationStock, DelimitationPlan
from .forms import ZoneStockageForm, RayonForm, EmplacementForm


# ============================================================
# UTILS & HELPERS
# ============================================================

from django.urls import reverse, NoReverseMatch
from urllib.parse import urlencode

def safe_reverse_url(view_name, query=None):
    """
    Tente de générer une URL sans faire planter l'application si elle n'existe pas.
    """
    try:
        url = reverse(view_name)
        if query:
            url += "?" + urlencode(query)
        return url
    except NoReverseMatch:
        return None

def calculer_statut_stock(article):
    """
    Calcule le statut de stock selon les règles métier.
    Gère les valeurs nulles ou manquantes.
    """
    try:
        stock = float(getattr(article, 'stock_actuel', 0) or 0)
        s_min = float(getattr(article, 'stock_minimum', 0) or 0)
        s_max = float(getattr(article, 'stock_maximum', 0) or 0)
        # point_commande n'existe que sur MP, on prend s_min pour PF
        pc = float(getattr(article, 'point_commande', s_min) or s_min)

        if stock <= 0:
            return "RUPTURE"
        if stock <= s_min:
            return "CRITIQUE"
        if stock <= pc or (s_max > 0 and stock < (s_max * 0.5)):
            return "ALERTE"
        return "NORMAL"
    except (TypeError, ValueError):
        return "NORMAL"


# ============================================================
# VUE 2D DU MAGASIN
# ============================================================

class PlanMagasinView(LoginRequiredMixin, TemplateView):
    """
    Vue 2D interactive du magasin.
    Affiche les zones, rayons et emplacements sur un plan graphique.
    """
    template_name = 'magasin/plan/vue_2d.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plan'] = PlanMagasin.objects.filter(est_actif=True).first()
        return context

@login_required
def api_plan_data(request):
    """
    GET /magasin/api/plan/
    Retourne les données du plan 2D. 
    """
    from produits.models import MatierePremiere, ProduitFini
    
    try:
        # 1. Config du Plan
        plan_obj = PlanMagasin.objects.filter(est_actif=True).first()
        base_w = plan_obj.largeur_totale if plan_obj else 2000
        base_h = plan_obj.hauteur_totale if plan_obj else 1200
        
        # Trouver la taille maximale nécessaire
        max_w, max_h = base_w, base_h
        for z in ZoneStockage.objects.filter(actif=True):
            if z.position_x + z.largeur + 100 > max_w:
                max_w = z.position_x + z.largeur + 100
            if z.position_y + z.hauteur + 100 > max_h:
                max_h = z.position_y + z.hauteur + 100

        plan_config = {
            "width": max_w,
            "height": max_h
        }

        # 2. Zones et Rayons (imbriqués)
        data_zones = []
        zones_qs = ZoneStockage.objects.filter(actif=True).order_by('ordre').prefetch_related(
            'rayons', 
            'rayons__niveaux', 
            'rayons__niveaux__affectations'
        )
        
        for z in zones_qs:
            z_stats = {"articles": 0, "ruptures": 0, "critiques": 0, "alertes": 0}
            data_rayons = []
            
            for r in z.rayons.filter(actif=True):
                r_stats = {"occupe": 0, "ruptures": 0, "critiques": 0, "alertes": 0}
                data_niveaux = []
                worst_statut = "NORMAL"
                
                for n in r.niveaux.all():
                    data_affs = []
                    affs = n.affectations.filter(actif=True)
                    if affs.exists(): r_stats["occupe"] += 1
                    
                    for aff in affs:
                        art = aff.matiere_premiere or aff.produit_fini
                        if not art: continue
                        
                        statut = calculer_statut_stock(art)
                        z_stats["articles"] += 1
                        if statut == "RUPTURE": 
                            z_stats["ruptures"] += 1
                            r_stats["ruptures"] += 1
                            worst_statut = "RUPTURE"
                        elif statut == "CRITIQUE": 
                            z_stats["critiques"] += 1
                            r_stats["critiques"] += 1
                            if worst_statut != "RUPTURE": worst_statut = "CRITIQUE"
                        elif statut == "ALERTE": 
                            z_stats["alertes"] += 1
                            r_stats["alertes"] += 1
                            if worst_statut not in ["RUPTURE", "CRITIQUE"]: worst_statut = "ALERTE"
                        
                        # Génération sécurisée du lien d'approvisionnement
                        appro_url = safe_reverse_url(
                            'approvisionnement:proposition-creer', 
                            {"article_id": art.id, "type": "MP" if aff.matiere_premiere else "PF"}
                        )
                        
                        # Fallbacks si proposition-creer n'existe pas
                        if not appro_url:
                            appro_url = safe_reverse_url('approvisionnement:commandes-a-valider')
                        if not appro_url:
                            appro_url = safe_reverse_url('approvisionnement:dashboard')
                        
                        data_affs.append({
                            "id": aff.pk,
                            "reference": art.reference,
                            "nom": art.nom,
                            "stock_actuel": float(art.stock_actuel),
                            "unite": art.unite.symbole if art.unite else "U",
                            "statut_stock": statut,
                            "appro_url": appro_url or "#"
                        })
                        
                    data_niveaux.append({
                        "id": n.pk,
                        "numero": n.numero,
                        "affectations": data_affs
                    })
                    
                data_rayons.append({
                    "id": r.pk,
                    "code": r.code,
                    "nom": r.nom or r.libelle,
                    "x": r.position_x,
                    "y": r.position_y,
                    "w": r.largeur,
                    "h": r.hauteur,
                    "couleur": r.couleur,
                    "niveaux": data_niveaux,
                    "stats": {
                        "total_niveaux": r.nombre_niveaux,
                        "occupe": r_stats["occupe"],
                        "ruptures": r_stats["ruptures"],
                        "alertes": r_stats["alertes"],
                        "worst_statut": worst_statut
                    }
                })

            data_zones.append({
                "id": z.pk,
                "code": z.code,
                "nom": z.nom or z.libelle,
                "type_zone": z.type_zone,
                "x": z.position_x,
                "y": z.position_y,
                "w": z.largeur,
                "h": z.hauteur,
                "couleur": z.couleur,
                "stats": z_stats,
                "rayons": data_rayons
            })

        # 3. Articles Disponibles
        data_dispo = []
        mps = MatierePremiere.objects.filter(actif=True).select_related('unite')[:100]
        pfs = ProduitFini.objects.filter(actif=True).select_related('unite')[:100]
        for m in mps:
            data_dispo.append({"type_article": "MATIERE_PREMIERE", "id": m.pk, "reference": m.reference, "stock_actuel": float(m.stock_actuel)})
        for p in pfs:
            data_dispo.append({"type_article": "PRODUIT_FINI", "id": p.pk, "reference": p.reference, "stock_actuel": float(p.stock_actuel)})

        # 4. Délimitations
        data_delims = []
        delims_qs = DelimitationPlan.objects.filter(actif=True)
        for d in delims_qs:
            data_delims.append({
                "id": d.pk,
                "nom": d.nom,
                "type": d.type_delimitation,
                "x": d.position_x,
                "y": d.position_y,
                "w": d.largeur,
                "h": d.hauteur,
                "couleur": d.couleur,
                "epaisseur": d.epaisseur,
                "style": d.style_trait
            })

        return JsonResponse({
            "success": True,
            "plan": plan_config,
            "zones": data_zones,
            "delimitations": data_delims,
            "articles_disponibles": data_dispo,
            "warnings": warnings if 'warnings' in locals() else []
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ============================================================
# API CRUD ZONES
# ============================================================

@login_required
def api_zone_create(request):
    if request.method != 'POST': 
        return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=405)
    
    import json
    try:
        payload = json.loads(request.body)
        
        # Validation minimale
        if not payload.get('nom'):
            return JsonResponse({"success": False, "error": "Le nom est obligatoire."}, status=400)
        
        zone = ZoneStockage.objects.create(
            code=payload.get('code', f"Z{ZoneStockage.objects.count() + 1}"),
            nom=payload.get('nom'),
            libelle=payload.get('nom'),
            type_zone=payload.get('type_zone', 'MIXTE'),
            position_x=payload.get('x', 0),
            position_y=payload.get('y', 0),
            largeur=payload.get('w', 200),
            hauteur=payload.get('h', 150),
            couleur=payload.get('couleur', '#f1f5f9'),
            cree_par=request.user
        )
        return JsonResponse({
            "success": True,
            "id": zone.id, 
            "nom": zone.nom,
            "message": "Zone créée avec succès."
        })
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "error": f"Impossible de créer la zone : {str(e)}"
        }, status=400)


@login_required
def api_zone_patch(request, pk):
    if request.method != 'PATCH': 
        return JsonResponse({"success": False, "error": "PATCH required"}, status=405)
    import json
    try:
        data = json.loads(request.body)
        zone = get_object_or_404(ZoneStockage, pk=pk)
        
        # Identification
        if 'nom' in data: 
            zone.nom = data['nom']
            zone.libelle = data['nom']
        if 'code' in data: zone.code = data['code']
        if 'type_zone' in data: zone.type_zone = data['type_zone']
        
        # Dimensions & Position
        if 'x' in data: zone.position_x = data['x']
        if 'y' in data: zone.position_y = data['y']
        if 'w' in data: zone.largeur = data['w']
        if 'h' in data: zone.hauteur = data['h']
        
        # Esthétique
        if 'couleur' in data: zone.couleur = data['couleur']
        
        # Environnement
        if 'temperature_min' in data: zone.temperature_min = data['temperature_min']
        if 'temperature_max' in data: zone.temperature_max = data['temperature_max']
        if 'humidite_min' in data: zone.humidite_min = data['humidite_min']
        if 'humidite_max' in data: zone.humidite_max = data['humidite_max']
        
        zone.save()
        return JsonResponse({"success": True, "message": "Zone mise à jour"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
def api_zone_delete(request, pk):
    if request.method != 'DELETE': 
        return JsonResponse({"success": False, "error": "Méthode non autorisée (DELETE requis)"}, status=405)
    
    try:
        zone = get_object_or_404(ZoneStockage, pk=pk)
        
        # Check for rayons
        rayons_count = zone.rayons.count()
        if rayons_count > 0:
            rayons_data = []
            for r in zone.rayons.all():
                rayons_data.append({
                    "id": r.id,
                    "code": r.code,
                    "nom": r.nom or r.libelle,
                    "has_stock": AffectationStock.objects.filter(niveau__rayon=r, actif=True).exists()
                })
            
            return JsonResponse({
                "success": False, 
                "reason": "HAS_RAYONS",
                "error": f"Cette zone contient {rayons_count} rayon(s). Supprimez ou déplacez les rayons avant de supprimer la zone.",
                "rayons": rayons_data
            }, status=400)
            
        zone.delete()
        return JsonResponse({"success": True, "message": "Zone supprimée avec succès."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
def api_rayon_create(request):
    if request.method != 'POST': 
        return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=405)
    
    import json
    try:
        payload = json.loads(request.body)
        zone_id = payload.get('zone_id')
        if not zone_id:
            return JsonResponse({"success": False, "error": "Zone parente manquante."}, status=400)
            
        zone = get_object_or_404(ZoneStockage, pk=zone_id)
        
        rayon = Rayon.objects.create(
            zone=zone,
            code=payload.get('code', f"R{Rayon.objects.count() + 1}"),
            nom=payload.get('nom'),
            libelle=payload.get('nom'),
            nombre_niveaux=payload.get('nombre_niveaux', 5),
            type_stock=payload.get('type_stock', 'MIXTE'),
            position_x=payload.get('x', 0),
            position_y=payload.get('y', 0),
            largeur=payload.get('w', 100),
            hauteur=payload.get('h', 40),
            couleur=payload.get('couleur', '#ffffff'),
            cree_par=request.user
        )
        
        # Création automatique des niveaux
        for i in range(1, int(rayon.nombre_niveaux) + 1):
            NiveauRayon.objects.create(rayon=rayon, numero=i, libelle=f"Niveau {i}")
            
        return JsonResponse({
            "success": True,
            "id": rayon.id, 
            "nom": rayon.nom,
            "message": "Rayon créé avec succès."
        })
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "error": f"Impossible de créer le rayon : {str(e)}"
        }, status=400)


@login_required
def api_rayon_patch(request, pk):
    if request.method != 'PATCH': return JsonResponse({"success": False, "error": "PATCH required"}, status=405)
    import json
    try:
        data = json.loads(request.body)
        rayon = get_object_or_404(Rayon, pk=pk)
        
        # Identification
        if 'nom' in data: 
            rayon.nom = data['nom']
            rayon.libelle = data['nom']
        if 'code' in data: rayon.code = data['code']
        
        # Configuration
        if 'type_stock' in data: rayon.type_stock = data['type_stock']
        if 'statut' in data: rayon.statut = data['statut']
        if 'nombre_niveaux' in data:
            new_n = int(data['nombre_niveaux'])
            if new_n != rayon.nombre_niveaux:
                if new_n > rayon.nombre_niveaux:
                    for i in range(rayon.nombre_niveaux + 1, new_n + 1):
                        NiveauRayon.objects.get_or_create(rayon=rayon, numero=i, defaults={'libelle': f'Niveau {i}'})
                rayon.nombre_niveaux = new_n

        # Dimensions & Position
        if 'x' in data: rayon.position_x = data['x']
        if 'y' in data: rayon.position_y = data['y']
        if 'w' in data: rayon.largeur = data['w']
        if 'h' in data: rayon.hauteur = data['h']
        
        # Esthétique
        if 'couleur' in data: rayon.couleur = data['couleur']
        
        rayon.save()
        return JsonResponse({"success": True, "message": "Rayon mis à jour"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
def api_rayon_delete(request, pk):
    if request.method != 'DELETE': 
        return JsonResponse({"success": False, "error": "Méthode non autorisée (DELETE requis)"}, status=405)
    
    force = request.GET.get('force') == 'true' or request.POST.get('force') == 'true'
    
    try:
        rayon = get_object_or_404(Rayon, pk=pk)
        
        # Check for affectations
        affectations = AffectationStock.objects.filter(niveau__rayon=rayon, actif=True).select_related('matiere_premiere', 'produit_fini', 'niveau')
        
        if affectations.exists():
            if force and (request.user.is_staff or request.user.is_superuser):
                # Forced delete: remove all affectations first
                count = affectations.count()
                affectations.delete()
                rayon.delete()
                return JsonResponse({
                    "success": True, 
                    "message": f"Rayon supprimé avec succès ainsi que {count} affectation(s) retirée(s)."
                })
            else:
                # Return list of affectations for guided UI
                aff_list = []
                for a in affectations:
                    art = a.matiere_premiere or a.produit_fini
                    aff_list.append({
                        "id": a.id,
                        "reference": art.reference if art else "N/A",
                        "nom": art.nom if art else "N/A",
                        "niveau": a.niveau.numero,
                        "quantite": float(a.quantite_affectee),
                        "unite": art.unite.symbole if art and art.unite else "U"
                    })
                
                return JsonResponse({
                    "success": False, 
                    "reason": "HAS_AFFECTATIONS",
                    "error": "Ce rayon contient du stock affecté. Retirez les articles avant de supprimer le rayon.",
                    "affectations": aff_list
                }, status=400)
                
        rayon.delete()
        return JsonResponse({"success": True, "message": "Rayon supprimé avec succès."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# ============================================================
# API AFFECTATIONS
# ============================================================

@login_required
def api_affectation_create(request):
    if request.method != 'POST': 
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    import json
    from produits.models import MatierePremiere, ProduitFini
    try:
        data = json.loads(request.body)
        niveau_id = data.get('niveau_id')
        if not niveau_id:
            return JsonResponse({"success": False, "error": "ID Niveau manquant"}, status=400)
            
        niveau = get_object_or_404(NiveauRayon, pk=niveau_id)
        
        aff_params = {
            "niveau": niveau,
            "cree_par": request.user,
            "quantite_affectee": data.get('quantite_affectee', 0),
            "capacite_reservee": data.get('capacite_reservee', 0)
        }
        
        type_art = data.get('type_article')
        art_id = data.get('article_id')
        
        if type_art == "MATIERE_PREMIERE":
            aff_params["matiere_premiere"] = get_object_or_404(MatierePremiere, pk=art_id)
        elif type_art == "PRODUIT_FINI":
            aff_params["produit_fini"] = get_object_or_404(ProduitFini, pk=art_id)
        else:
            return JsonResponse({"success": False, "error": "Type d'article invalide"}, status=400)
            
        aff = AffectationStock.objects.create(**aff_params)
        return JsonResponse({"success": True, "id": aff.id, "message": "Stock affecté avec succès"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
def api_affectation_delete(request, pk):
    if request.method != 'DELETE': 
        return JsonResponse({"success": False, "error": "Méthode non autorisée (DELETE requis)"}, status=405)
    try:
        aff = get_object_or_404(AffectationStock, pk=pk)
        aff.delete()
        return JsonResponse({"success": True, "message": "Affectation retirée avec succès."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# ============================================================
# API BULK POSITIONS & PROPERTIES
# ============================================================

@login_required
def api_bulk_positions(request):
    if request.method != 'PATCH': return JsonResponse({"success": False, "error": "PATCH required"}, status=405)
    import json
    try:
        data = json.loads(request.body)
        
        # Mise à jour des zones
        for z_data in data.get('zones', []):
            update_fields = {
                'position_x': z_data['x'],
                'position_y': z_data['y'],
                'largeur': z_data.get('w', 200),
                'hauteur': z_data.get('h', 150)
            }
            if 'nom' in z_data: 
                update_fields['nom'] = z_data['nom']
                update_fields['libelle'] = z_data['nom']
            if 'code' in z_data: update_fields['code'] = z_data['code']
            if 'couleur' in z_data: update_fields['couleur'] = z_data['couleur']
            if 'type_zone' in z_data: update_fields['type_zone'] = z_data['type_zone']
            
            # Facultatifs environnement
            for f in ['temperature_min', 'temperature_max', 'humidite_min', 'humidite_max']:
                if f in z_data: update_fields[f] = z_data[f]

            ZoneStockage.objects.filter(pk=z_data['id']).update(**update_fields)
            
        # Mise à jour des rayons
        for r_data in data.get('rayons', []):
            update_fields = {
                'position_x': r_data['x'],
                'position_y': r_data['y'],
                'largeur': r_data.get('w', 120),
                'hauteur': r_data.get('h', 40)
            }
            if 'nom' in r_data: 
                update_fields['nom'] = r_data['nom']
                update_fields['libelle'] = r_data['nom']
            if 'code' in r_data: update_fields['code'] = r_data['code']
            if 'couleur' in r_data: update_fields['couleur'] = r_data['couleur']
            if 'type_stock' in r_data: update_fields['type_stock'] = r_data['type_stock']
            if 'statut' in r_data: update_fields['statut'] = r_data['statut']
            if 'nombre_niveaux' in r_data: update_fields['nombre_niveaux'] = r_data['nombre_niveaux']

            Rayon.objects.filter(pk=r_data['id']).update(**update_fields)

        # Mise à jour des délimitations
        for d_data in data.get('delimitations', []):
            update_fields = {
                'position_x': d_data['x'],
                'position_y': d_data['y'],
                'largeur': d_data.get('w', 100),
                'hauteur': d_data.get('h', 100)
            }
            if 'nom' in d_data: update_fields['nom'] = d_data['nom']
            if 'couleur' in d_data: update_fields['couleur'] = d_data['couleur']
            if 'type' in d_data: update_fields['type_delimitation'] = d_data['type']
            if 'epaisseur' in d_data: update_fields['epaisseur'] = d_data['epaisseur']
            if 'style' in d_data: update_fields['style_trait'] = d_data['style']

            DelimitationPlan.objects.filter(pk=d_data['id']).update(**update_fields)
            
        return JsonResponse({"success": True, "message": "Toutes les modifications ont été enregistrées."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# ============================================================
# API CRUD DÉLIMITATIONS
# ============================================================

@login_required
def api_delimitation_create(request):
    if request.method != 'POST': return JsonResponse({"success": False, "error": "POST required"}, status=405)
    import json
    try:
        data = json.loads(request.body)
        delim = DelimitationPlan.objects.create(
            nom=data.get('nom', 'Nouvelle délimitation'),
            type_delimitation=data.get('type', 'AUTRE'),
            position_x=data.get('x', 0),
            position_y=data.get('y', 0),
            largeur=data.get('w', 100),
            hauteur=data.get('h', 100),
            couleur=data.get('couleur', '#000000'),
            epaisseur=data.get('epaisseur', 2),
            style_trait=data.get('style', 'PLEIN'),
            cree_par=request.user
        )
        return JsonResponse({"success": True, "id": delim.id, "message": "Délimitation créée"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@login_required
def api_delimitation_patch(request, pk):
    if request.method != 'PATCH': return JsonResponse({"success": False, "error": "PATCH required"}, status=405)
    import json
    try:
        data = json.loads(request.body)
        delim = get_object_or_404(DelimitationPlan, pk=pk)
        if 'nom' in data: delim.nom = data['nom']
        if 'type' in data: delim.type_delimitation = data['type']
        if 'x' in data: delim.position_x = data['x']
        if 'y' in data: delim.position_y = data['y']
        if 'w' in data: delim.largeur = data['w']
        if 'h' in data: delim.hauteur = data['h']
        if 'couleur' in data: delim.couleur = data['couleur']
        if 'epaisseur' in data: delim.epaisseur = data['epaisseur']
        if 'style' in data: delim.style_trait = data['style']
        delim.save()
        return JsonResponse({"success": True, "message": "Délimitation mise à jour"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@login_required
def api_delimitation_delete(request, pk):
    if request.method != 'DELETE': return JsonResponse({"success": False, "error": "DELETE required"}, status=405)
    delim = get_object_or_404(DelimitationPlan, pk=pk)
    delim.delete()
    return JsonResponse({"success": True, "message": "Délimitation supprimée"})


@login_required
def api_emplacement_detail(request, ref):
    """
    API JSON — Détail complet d'un article par référence.
    Gère indifféremment MatierePremiere et ProduitFini.
    """
    from produits.models import MatierePremiere, ProduitFini
    from mouvements.models import MouvementStock
    from approvisionnement.models import BonCommande
    
    # 1. Identifier si c'est une MP ou un PF
    item = MatierePremiere.objects.filter(reference=ref, actif=True).first()
    item_type = "MP"
    if not item:
        item = ProduitFini.objects.filter(reference=ref, actif=True).first()
        item_type = "PF"
        
    if not item:
        return JsonResponse({"error": "Article non trouvé"}, status=404)

    stock = float(item.stock_actuel)
    s_min = float(item.stock_minimum)
    s_max = float(getattr(item, 'stock_maximum', 0))
    pc    = float(getattr(item, 'point_commande', s_min))
    pct   = round(stock / s_max * 100, 1) if s_max > 0 else 0

    def get_statut(s, mi, ma, p):
        if s <= 0: return "RUPTURE"
        if s <= mi: return "CRITIQUE"
        if s < p or (ma > 0 and s < (ma * 0.5)): return "ALERTE"
        return "NORMAL"

    statut = get_statut(stock, s_min, s_max, pc)

    # 5 derniers mouvements
    filter_mvt = {'matiere': item} if item_type == "MP" else {'produit_fini': item}
    derniers_mvts = MouvementStock.objects.filter(**filter_mvt).select_related('operateur').order_by('-date_mouvement')[:5]

    mouvements_data = [
        {
            "type":      mv.type_mouvement,
            "quantite":  float(mv.quantite),
            "date":      mv.date_mouvement.isoformat(),
            "lot":       mv.numero_lot,
            "operateur": (mv.operateur.get_full_name() or mv.operateur.username) if mv.operateur else "—",
        }
        for mv in derniers_mvts
    ]

    # Bons de commande en cours (uniquement pour MP)
    bons_data = []
    if item_type == "MP":
        bons_en_cours = BonCommande.objects.filter(
            matiere=item,
            statut__in=['BROUILLON', 'ENVOYE']
        ).select_related('fournisseur').order_by('-date_creation')[:5]

        bons_data = [
            {
                "reference":          bc.reference,
                "statut":             bc.statut,
                "quantite_commandee": float(bc.quantite_commandee),
                "fournisseur":        bc.fournisseur.nom,
                "date_creation":      bc.date_creation.isoformat(),
                "date_prevue":        bc.date_reception_prevue.isoformat() if bc.date_reception_prevue else None,
            }
            for bc in bons_en_cours
        ]

    return JsonResponse({
        "id":              item.pk,
        "type":            item_type,
        "ref":             item.reference,
        "nom":             item.nom,
        "cat":             getattr(item, 'categorie', '—'),
        "emplacement":     item.emplacement,
        "qty":             stock,
        "max":             s_max,
        "min":             s_min,
        "pc":              pc,
        "unit":            item.unite.symbole if item.unite else "U",
        "prix":            float(getattr(item, 'prix_unitaire', 0)),
        "statut":          statut,
        "valeur_stock":    round(stock * float(getattr(item, 'prix_unitaire', 0)), 2),
        "mouvements":      mouvements_data,
        "bons_en_cours":   bons_data,
    })




# ============================================================
# ZONES
# ============================================================

class ZoneListeView(LoginRequiredMixin, ExportMixin, ListView):
    model = ZoneStockage
    template_name = 'magasin/zone/liste.html'
    context_object_name = 'zones'
    export_fields = ['code', 'libelle', 'type_zone', 'couleur']
    export_headers = ['Code', 'Libellé', 'Type', 'Couleur']

    def get_queryset(self):
        return ZoneStockage.objects.filter(est_actif=True).annotate(
            nb_rayons=Count('rayons'),
        ).prefetch_related('rayons')

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="zones")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Liste des Zones de Stockage", filename_prefix="zones")
        return super().get(request, *args, **kwargs)


class ZoneDetailView(LoginRequiredMixin, DetailView):
    model = ZoneStockage
    template_name = 'magasin/zone/detail.html'
    context_object_name = 'zone'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rayons'] = self.object.rayons.filter(est_actif=True).annotate(
            nb_emplacements=Count('emplacements'),
            nb_libres=Count('emplacements', filter=Q(emplacements__statut='LIBRE')),
        )
        return context


class ZoneCreerView(LoginRequiredMixin, CreateView):
    model = ZoneStockage
    form_class = ZoneStockageForm
    template_name = 'magasin/zone/form.html'
    success_url = reverse_lazy('magasin:zone-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Zone créée avec succès."))
        return super().form_valid(form)


# ============================================================
# RAYONS
# ============================================================

class RayonListeView(LoginRequiredMixin, ExportMixin, ListView):
    model = Rayon
    template_name = 'magasin/rayon/liste.html'
    context_object_name = 'rayons'
    export_fields = ['code', 'libelle', 'zone__code', 'nombre_niveaux', 'nombre_colonnes']
    export_headers = ['Code', 'Libellé', 'Zone', 'Niveaux', 'Colonnes']

    def get_queryset(self):
        qs = Rayon.objects.select_related('zone').filter(est_actif=True).annotate(
            nb_emplacements=Count('emplacements'),
        )
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(libelle__icontains=q) | Q(code__icontains=q) | Q(zone__code__icontains=q))
        return qs.order_by('zone', 'code')

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="rayons")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Registre des Rayons", filename_prefix="rayons")
        return super().get(request, *args, **kwargs)


class RayonCreerView(LoginRequiredMixin, CreateView):
    model = Rayon
    form_class = RayonForm
    template_name = 'magasin/rayon/form.html'
    success_url = reverse_lazy('magasin:rayon-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Rayon créé avec succès."))
        return super().form_valid(form)


# ============================================================
# EMPLACEMENTS
# ============================================================

class EmplacementListeView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    model               = Emplacement
    template_name       = 'magasin/emplacement/liste.html'
    kanban_template_name = 'magasin/emplacement/kanban.html'
    context_object_name = 'emplacements'
    paginate_by         = 50
    export_fields       = ['code', 'rayon__zone__code', 'rayon__code', 'niveau', 'colonne', 'statut']
    export_headers      = ['Code', 'Zone', 'Rayon', 'Niveau', 'Colonne', 'Statut']

    def get_queryset(self):
        qs = Emplacement.objects.select_related('rayon', 'rayon__zone').filter(est_actif=True)
        
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(rayon__code__icontains=q) | Q(rayon__zone__code__icontains=q))
            
        statut = self.request.GET.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
            
        zone = self.request.GET.get('zone')
        if zone:
            qs = qs.filter(rayon__zone_id=zone)
            
        return qs.order_by('rayon__zone', 'rayon', 'niveau', 'colonne')

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="emplacements")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Registre des Emplacements", filename_prefix="emplacements")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts_choices'] = Emplacement.StatutEmplacement.choices
        context['zones'] = ZoneStockage.objects.filter(est_actif=True)
        return context


class EmplacementCreerView(LoginRequiredMixin, CreateView):
    model = Emplacement
    form_class = EmplacementForm
    template_name = 'magasin/emplacement/form.html'
    success_url = reverse_lazy('magasin:emplacement-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Emplacement créé avec succès."))
        return super().form_valid(form)
