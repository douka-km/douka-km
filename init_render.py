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
    """Vérifie la compatibilité Python/SQLAlchemy/psycopg"""
    print(f"Python version: {sys.version}")
    
    # Test psycopg v3 d'abord
    try:
        import psycopg
        print(f"✅ psycopg v3 version: {psycopg.__version__}")
    except ImportError:
        print("❌ psycopg v3 non disponible")
        try:
            import psycopg2
            print(f"⚠️  psycopg2 version: {psycopg2.__version__} (compatible mais non recommandé)")
        except ImportError:
            print("❌ Aucun adaptateur PostgreSQL disponible")
            return False
    
    try:
        import sqlalchemy
        print(f"SQLAlchemy version: {sqlalchemy.__version__}")
        
        # Tester l'importation problématique
        from sqlalchemy.sql.elements import SQLCoreOperations
        print("SQLAlchemy imports OK")
        
        # Test de la création d'engine avec psycopg
        try:
            database_url = os.environ.get('DATABASE_URL')
            if database_url:
                # S'assurer qu'on utilise psycopg v3
                if '+psycopg' not in database_url:
                    if database_url.startswith('postgres://'):
                        database_url = database_url.replace('postgres://', 'postgresql+psycopg://')
                    elif database_url.startswith('postgresql://'):
                        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
                
                from sqlalchemy import create_engine
                engine = create_engine(database_url, echo=False)
                print(f"✅ Engine PostgreSQL+psycopg créé avec succès")
                engine.dispose()
        except Exception as engine_error:
            print(f"⚠️  Problème création engine: {engine_error}")
        
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
            
            # MIGRATION: Ajouter les colonnes de livreur si elles n'existent pas
            try:
                print("🔄 Vérification et migration des colonnes de livreur...")
                run_delivery_migration()
                print("✅ Migration des colonnes terminée")
            except Exception as migration_error:
                print(f"⚠️  Erreur lors de la migration: {migration_error}")
                # Ne pas faire échouer le déploiement pour une erreur de migration
                try:
                    db.session.rollback()
                except Exception:
                    pass
            
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

def run_delivery_migration():
    """Exécute la migration des colonnes de livreur pour PostgreSQL"""
    from sqlalchemy import text
    from app_final_with_db import db
    
    def check_column_exists(table_name, column_name):
        """Vérifie si une colonne existe dans une table PostgreSQL"""
        query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name AND column_name = :column_name
        """)
        result = db.session.execute(query, {'table_name': table_name, 'column_name': column_name})
        return result.fetchone() is not None
    
    # Liste des colonnes à ajouter
    columns_to_add = [
        ('delivery_employee_id', 'INTEGER'),
        ('delivery_employee_email', 'VARCHAR(120)'),
        ('delivery_employee_name', 'VARCHAR(200)'),
        ('delivery_employee_phone', 'VARCHAR(20)'),
        ('assigned_at', 'TIMESTAMP')
    ]
    
    for column_name, column_type in columns_to_add:
        if not check_column_exists('orders', column_name):
            try:
                alter_query = text(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
                db.session.execute(alter_query)
                db.session.commit()
                print(f"✓ Colonne {column_name} ajoutée")
            except Exception as e:
                print(f"⚠️  Erreur lors de l'ajout de {column_name}: {e}")
                db.session.rollback()
        else:
            print(f"✓ Colonne {column_name} existe déjà")

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
