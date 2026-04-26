from decimal import Decimal
from django.utils.translation import gettext_lazy as _

def is_integer_decimal(value):
    """
    Retourne True si le Decimal est un entier (ex: 20.0000).
    """
    if value is None:
        return True
    decimal_val = Decimal(str(value))
    return decimal_val == decimal_val.to_integral_value()

def validate_unit_quantity(unite, value, field_label=None):
    """
    Lève une erreur si la valeur n'est pas compatible avec l'unité.
    Utile pour les clean() de formulaires ou les save() de modèles.
    """
    if unite and not unite.autorise_decimales:
        if not is_integer_decimal(value):
            msg = _("L'unité %(unite)s n'autorise que des quantités entières.") % {'unite': unite.nom}
            if field_label:
                msg = _("%(field)s : ") % {'field': field_label} + msg
            return False, msg
    return True, ""
