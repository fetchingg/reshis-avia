import os
import sys


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

activate = os.path.join(BASE, "venv", "bin", "activate_this.py")
with open(activate) as f:
    exec(f.read(), {"__file__": activate})

sys.path.insert(0, os.path.join(BASE, "app"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
