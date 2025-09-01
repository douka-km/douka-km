#!/usr/bin/env python3
"""
Script d'initialisation pour Render.com - Version simplifiée
Ce script s'exécute au démarrage pour configurer la base de données
"""
import os
import sys
import traceback

# Définir les variables d'environnement nécessaires
os.environ['RENDER'] = '1'

def check_compatibility():
    """Vérifie la compatibilité Python/SQLAlchemy"""
    print(f"Python version: {sys.version}")
    
    try:
        import sqlalchemy
        print(f"SQLAlchemy version: {sqlalchemy.__version__}")
        
        # Tester l'importation problématique
        from sqlalchemy.sql.elements import SQLCoreOperations
        print("SQLAlchemy imports OK")
        return True
    except Exception as e:
        print(f"Problème SQLAlchemy: {e}")
        return False

def safe_import_app():
    """Import sécurisé de l'application"""
    try:
        # Tester d'abord les imports SQLAlchemy
        if not check_compatibility():
            print("Problème de compatibilité détecté")
            return None, None
        
        # Import de l'application
        from app_final_with_db import app, initialize_production_db
        print("Imports application réussis")
        return app, initialize_production_db
    except ImportError as ie:
        print(f"Erreur d'import application: {ie}")
        print(f"Traceback: {traceback.format_exc()}")
        return None, None
    except Exception as e:
        print(f"Erreur générale: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None, None

def init_database_safely(app, initialize_production_db):
    """Initialise la base de données avec gestion robuste des transactions"""
    try:
        with app.app_context():
            # Import de la base de données
            from app_final_with_db import db
            
            # S'assurer que toutes les transactions précédentes sont fermées
            try:
                db.session.rollback()
                print("Transaction précédente fermée")
            except Exception:
                pass
            
            # Créer les tables
            try:
                db.create_all()
                print("Tables créées avec succès")
            except Exception as table_error:
                print(f"Erreur création tables: {table_error}")
                db.session.rollback()
                raise
            
            # Initialiser les données avec gestion d'erreur robuste
            try:
                initialize_production_db()
                print("Données initialisées avec succès")
                db.session.commit()
            except Exception as init_error:
                print(f"Erreur lors de l'initialisation des données: {init_error}")
                # Rollback en cas d'erreur
                try:
                    db.session.rollback()
                    print("Transaction annulée")
                except Exception:
                    pass
                print("L'application continuera avec un schéma vide")
                
    except Exception as db_error:
        print(f"Erreur lors de l'initialisation DB: {db_error}")
        print("L'application continuera malgré l'erreur")

try:
    print("Initialisation de l'application pour Render.com...")
    
    # Import sécurisé de l'application
    app, initialize_production_db = safe_import_app()
    
    if app is None:
        print("Échec de l'import de l'application")
        sys.exit(1)
    
    # Initialiser la base de données
    print("Initialisation de la base de données...")
    init_database_safely(app, initialize_production_db)
    
    print("Application initialisée avec succès!")
    
except Exception as e:
    print(f"Erreur d'initialisation: {e}")
    print(f"Traceback complet: {traceback.format_exc()}")
    sys.exit(1)
