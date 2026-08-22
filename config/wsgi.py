"""
WSGI config for config project.
"""
import os
import sys

# Ensure the project root is on the path
project_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load .env file before Django initializes
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_home, '.env'))
except ImportError:
    try:
        from decouple import config as _dc
        # python-decouple handles .env automatically
    except ImportError:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
