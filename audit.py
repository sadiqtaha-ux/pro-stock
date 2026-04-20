import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockpro.settings")
django.setup()

from django.test import Client
from django.urls import get_resolver
from core.models import Utilisateur

def get_all_urls():
    urls = []
    resolver = get_resolver()
    for url_pattern in resolver.url_patterns:
        if hasattr(url_pattern, 'url_patterns'): # Include match
            namespace = url_pattern.namespace
            for sub_pattern in url_pattern.url_patterns:
                name = getattr(sub_pattern, 'name', None)
                if name:
                    urls.append(f"{namespace}:{name}" if namespace else name)
        else:
            name = getattr(url_pattern, 'name', None)
            if name:
                urls.append(name)
    return urls

def main():
    client = Client(HTTP_HOST='localhost')
    admin_user = Utilisateur.objects.get(username="admin")
    client.force_login(admin_user)

    from django.urls import reverse
    urls_to_test = get_all_urls()
    missing_or_error = []

    for url_name in urls_to_test:
        # Skip some patterns that require args (we can't blindly reverse them)
        try:
            url = reverse(url_name)
        except Exception:
            continue  # Requires args, difficult to test blindly without context

        try:
            response = client.get(url)
            if response.status_code not in (200, 301, 302):
                missing_or_error.append((url_name, url, response.status_code))
        except Exception as e:
            missing_or_error.append((url_name, url, str(e)))

    print("--- AUDIT RESULTS ---")
    if not missing_or_error:
        print("Toutes les vues sans paramètres ont fonctionné (200, 301, 302).")
    for item in missing_or_error:
        print(f"[{item[0]}] {item[1]} -> Erreur : {item[2]}")

if __name__ == "__main__":
    main()
