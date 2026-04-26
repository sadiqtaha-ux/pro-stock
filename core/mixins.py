from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
import csv
from datetime import datetime
from xhtml2pdf import pisa
import io
from core.models import JournalActivite
from core.utils import log_action

class KanbanListMixin:
    """
    Mixin pour gérer le basculement entre vue Liste et vue Kanban.
    """
    kanban_template_name = None
    
    def get_template_names(self):
        view_type = self.request.GET.get('view', 'table')
        if view_type == 'kanban' and self.kanban_template_name:
            return [self.kanban_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_view'] = self.request.GET.get('view', 'table')
        # Calculer le nombre de filtres actifs pour l'UI
        context['active_filters_count'] = sum(
            1 for k, v in self.request.GET.items() 
            if k not in ['view', 'page', 'q'] and v
        )
        context['search_query'] = self.request.GET.get('q', '')
        return context

class ExportMixin:
    """
    Mixin pour l'export CSV et PDF des QuerySets.
    Peut être utilisé avec ListView.
    """
    export_fields = [] # Liste des champs à exporter (ex: 'reference', 'matiere__nom')
    export_headers = [] # En-têtes humanisés (ex: 'Référence', 'Matière')
    export_filename = "export"
    export_title = "Rapport de données"
    
    def _get_export_data(self, queryset):
        """Prépare les données formatées pour l'export."""
        rows = []
        for obj in queryset:
            row = []
            for field in self.export_fields:
                # Gestion des clés étrangères (ex: matiere__nom)
                val = obj
                for part in field.split('__'):
                    if val is None: break
                    val = getattr(val, part, None)
                
                if callable(val):
                    val = val()
                
                # Formatage spécial pour certains types
                if isinstance(val, datetime):
                    val = val.strftime('%d/%m/%Y %H:%M')
                elif isinstance(val, bool):
                    val = "Oui" if val else "Non"
                elif val is None:
                    val = "—"
                
                row.append(val)
            rows.append(row)
        return rows

    def render_to_csv(self, queryset, filename_prefix=None):
        prefix = filename_prefix or self.export_filename
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # BOM pour Excel (UTF-8 avec BOM)
        response.write(u'\ufeff'.encode('utf8'))
        
        writer = csv.writer(response, delimiter=';')
        # Header
        writer.writerow(self.export_headers or self.export_fields)
        
        rows = self._get_export_data(queryset)
        for row in rows:
            writer.writerow(row)
        
        # Log export
        log_action(
            self.request if hasattr(self, 'request') else None,
            JournalActivite.TypeAction.EXPORT,
            self.model.__name__ if hasattr(self, 'model') else 'Unknown',
            None,
            f"Export CSV de {len(rows)} lignes ({prefix})"
        )
        
        return response

    def render_to_pdf(self, queryset, title=None, filename_prefix=None):
        prefix = filename_prefix or self.export_filename
        report_title = title or self.export_title
        template_path = 'core/export/pdf_base.html'
        
        # Filtres appliqués pour le PDF
        filters_list = []
        for k, v in self.request.GET.items():
            if k not in ['export', 'view', 'page'] and v:
                filters_list.append(f"{k}: {v}")
        
        context = {
            'title': report_title,
            'today': datetime.now(),
            'headers': self.export_headers or self.export_fields,
            'rows': self._get_export_data(queryset),
            'filters': ", ".join(filters_list) if filters_list else "Aucun"
        }
        
        html = render_to_string(template_path, context)
        
        # Création du PDF
        result = io.BytesIO()
        try:
            pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
            
            if not pdf.err:
                # Log export
                log_action(
                    self.request if hasattr(self, 'request') else None,
                    JournalActivite.TypeAction.EXPORT,
                    self.model.__name__ if hasattr(self, 'model') else 'Unknown',
                    None,
                    f"Export PDF de {len(context['rows'])} lignes ({prefix})"
                )
                
                response = HttpResponse(result.getvalue(), content_type='application/pdf')
                filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                return HttpResponse(f"Erreur lors de la génération du PDF : {pdf.err}", status=500)
        except Exception as e:
            log_action(
                self.request if hasattr(self, 'request') else None,
                JournalActivite.TypeAction.EXPORT,
                self.model.__name__ if hasattr(self, 'model') else 'Unknown',
                None,
                f"ÉCHEC Export PDF ({prefix}) : {str(e)}",
                niveau=JournalActivite.Niveau.ERROR
            )
            return HttpResponse(f"Erreur système lors de la génération du PDF : {str(e)}", status=500)

    def get(self, request, *args, **kwargs):
        """
        Intercepte la requête GET pour vérifier si un export est demandé.
        """
        export_type = request.GET.get('export')
        if export_type in ['csv', 'pdf']:
            queryset = self.get_queryset()
            if export_type == 'csv':
                return self.render_to_csv(queryset)
            elif export_type == 'pdf':
                return self.render_to_pdf(queryset)
        
        # Continue le flux normal (ListView.get)
        return super().get(request, *args, **kwargs)
