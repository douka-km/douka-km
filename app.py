#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DOUKA KM - Point d'entrée pour le déploiement
Application de commerce électronique des Comores
"""

import os
from app_final_with_db import app

if __name__ == '__main__':
    # Utiliser le port fourni par Render ou 5002 par défaut
    port = int(os.environ.get('PORT', 5002))
    
    # En production, ne pas utiliser le mode debug
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
