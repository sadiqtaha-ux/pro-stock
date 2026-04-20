import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')
django.setup()
from django.urls import get_resolver
resolver = get_resolver()

def get_urls(patterns, prefix=''):
    urls=[]
    for p in patterns:
        if hasattr(p, 'url_patterns'):
            urls += get_urls(p.url_patterns, prefix + p.namespace + ':' if getattr(p, 'namespace', None) else prefix)
        elif hasattr(p, 'name') and p.name:
            urls.append(prefix + p.name)
    return set(urls)

all_urls = get_urls(resolver.url_patterns)
print('\n'.join(sorted(all_urls)))
