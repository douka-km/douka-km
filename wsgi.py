#!/usr/bin/env python3
"""
Point d'entrée WSGI pour Render.com
"""
import os

# S'assurer que nous sommes en mode production
os.environ['RENDER'] = '1'
# S'assurer que l'URL de base est définie
if not os.environ.get('VERIFICATION_URL_BASE'):
    os.environ['VERIFICATION_URL_BASE'] = 'https://douka-km.onrender.com'

try:
    from app_final_with_db import app
    
    # Configuration spécifique pour WSGI
    if __name__ == "__main__":
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    
    # Export pour Gunicorn
    application = app
    
except Exception as e:
    print(f"❌ Erreur lors de l'import de l'application: {e}")
    import traceback
    traceback.print_exc()
    raise
