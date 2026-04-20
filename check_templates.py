import os
import re

base = 'templates'

# Collecter tous les template_name depuis les views
template_names = set()
apps = ['core', 'produits', 'mouvements', 'approvisionnement', 'dashboard', 'magasin']
for app in apps:
    vf = f'{app}/views.py'
    if os.path.exists(vf):
        content = open(vf, encoding='utf-8').read()
        names = re.findall(r'template_name\s*=\s*["\']([^"\']+)["\']', content)
        for n in names:
            template_names.add(n)

missing = []
existing = []
for t in sorted(template_names):
    path = os.path.join(base, t)
    if os.path.exists(path):
        existing.append(t)
    else:
        missing.append(t)

print('=== TEMPLATES MANQUANTS ===')
for m in missing:
    print(f'  MISSING: {m}')
print()
print('=== TEMPLATES EXISTANTS ===')
for e in existing:
    print(f'  OK:      {e}')
