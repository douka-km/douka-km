#!/usr/bin/env python3
"""
Script d'initialisation pour Render.com
Ce script s'exécute au démarrage pour configurer la base de données
"""
import os
import sys
import traceback

# Définir les variables d'environnement nécessaires
os.environ['RENDER'] = '1'

try:
    print("🚀 Initialisation de l'application pour Render.com...")
    
    # Import de l'application avec gestion d'erreur
    try:
        from app_final_with_db import app, initialize_production_db
        print("✅ Imports réussis")
    except ImportError as ie:
        print(f"❌ Erreur d'import: {ie}")
        print(f"📍 Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Initialiser la base de données
    print("🔄 Initialisation de la base de données...")
    initialize_production_db()
    
    print("✅ Application initialisée avec succès!")
    
except Exception as e:
    print(f"❌ Erreur d'initialisation: {e}")
    print(f"📍 Traceback complet: {traceback.format_exc()}")
    sys.exit(1)
