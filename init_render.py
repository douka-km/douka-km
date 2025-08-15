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
    
    # D'ABORD corriger la base de données (colonnes manquantes)
    print("🔧 Correction de la base de données...")
    try:
        from fix_render_db import fix_render_database, create_sample_categories
        if fix_render_database():
            print("✅ Schéma de base de données corrigé")
        else:
            print("⚠️ Échec de la correction du schéma")
    except Exception as fix_error:
        print(f"⚠️ Erreur lors de la correction DB: {fix_error}")
        print("🔄 L'application continuera malgré l'erreur")
    
    # ENSUITE initialiser la base de données avec les données
    print("🔄 Initialisation de la base de données...")
    try:
        initialize_production_db()
        print("✅ Données initialisées")
    except Exception as init_error:
        print(f"⚠️ Erreur lors de l'initialisation des données: {init_error}")
        print("🔄 L'application continuera avec un schéma vide")
    
    # Enfin créer les catégories d'exemple si nécessaire
    try:
        create_sample_categories()
        print("✅ Catégories d'exemple créées")
    except Exception as cat_error:
        print(f"⚠️ Erreur lors de la création des catégories: {cat_error}")
    
    print("✅ Application initialisée avec succès!")
    
except Exception as e:
    print(f"❌ Erreur d'initialisation: {e}")
    print(f"📍 Traceback complet: {traceback.format_exc()}")
    sys.exit(1)
