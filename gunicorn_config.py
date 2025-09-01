# Configuration Gunicorn pour Render.com
import os

# Nombre de workers - basé sur le nombre de CPU disponibles
workers = int(os.environ.get('GUNICORN_WORKERS', 2))

# Type de worker - sync pour compatibilité Python 3.13
worker_class = 'sync'

# Timeout configuration - plus long pour éviter les Bad Gateway
timeout = 120  # 2 minutes au lieu de 30 secondes par défaut
keepalive = 5

# Memory management
max_requests = 1000
max_requests_jitter = 100

# Logging
loglevel = 'info'
accesslog = '-'
errorlog = '-'

# Bind configuration
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"

# Preload application pour améliorer les performances
preload_app = True

# Graceful timeout pour les requêtes longues
graceful_timeout = 60

# Configuration pour éviter les timeouts sur les requêtes admin lourdes
def when_ready(server):
    """Callback appelé quand le serveur est prêt"""
    server.log.info("🚀 Serveur Gunicorn prêt pour DOUKA KM")

def worker_init(worker):
    """Callback appelé à l'initialisation de chaque worker"""
    worker.log.info(f"⚡ Worker {worker.pid} initialisé")

# Configuration SSL si nécessaire (pour production)
forwarded_allow_ips = '*'
secure_headers = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block'
}
