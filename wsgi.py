#!/usr/bin/env python3
"""
WSGI Principal pour DOUKA KM - Render.com
Optimisé pour Python 3.13 + SQLAlchemy 2.0
Point d'entrée principal de l'application
"""

import os
import sys
import warnings

# Configuration pour Python 3.13
print(f"🐍 Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

# Variables d'environnement
os.environ['RENDER'] = '1'
os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '1'

def check_python313_compatibility():
    """Vérifie que nous sommes bien en Python 3.13"""
    if sys.version_info.major == 3 and sys.version_info.minor >= 13:
        print("✅ Python 3.13+ détecté - Configuration native")
        return True
    else:
        print(f"⚠️ Python {sys.version_info.major}.{sys.version_info.minor} - Version non optimale")
        return False

def import_with_python313():
    """Import optimisé pour Python 3.13 avec SQLAlchemy 2.0"""
    
    try:
        # Vérifier les versions installées
        import sqlalchemy
        print(f"✅ SQLAlchemy {sqlalchemy.__version__}")
        
        import flask
        print(f"✅ Flask {flask.__version__}")
        
        import flask_sqlalchemy
        print(f"✅ Flask-SQLAlchemy {flask_sqlalchemy.__version__}")
        
        # Test PostgreSQL adapter
        print("🔍 Test des adapters PostgreSQL...")
        psycopg_available = False
        psycopg2_available = False
        
        try:
            import psycopg2
            psycopg2_available = True
            print(f"✅ psycopg2 {psycopg2.__version__} disponible")
        except ImportError as e:
            print(f"⚠️ psycopg2 non disponible: {e}")
        except Exception as e:
            print(f"❌ psycopg2 erreur: {e}")
        
        try:
            import psycopg
            psycopg_available = True
            print(f"✅ psycopg v3 {psycopg.__version__} disponible")
        except ImportError as e:
            print(f"⚠️ psycopg v3 non disponible: {e}")
        except Exception as e:
            print(f"❌ psycopg v3 erreur: {e}")
        
        if not psycopg2_available and not psycopg_available:
            print("❌ Aucun adapter PostgreSQL trouvé!")
            return None
        
        # Import des models (devrait fonctionner avec SQLAlchemy 2.0)
        print("📦 Import des models...")
        from models import db, User, Product, Category
        print("✅ Models importés avec succès")
        
        # Import de l'application
        print("📦 Import de l'application...")
        from app_final_with_db import app, initialize_production_db
        print("✅ Application importée")
        
        # Initialisation de la base de données
        print("🔄 Initialisation base de données...")
        with app.app_context():
            try:
                initialize_production_db()
                print("✅ Base de données initialisée")
            except Exception as db_error:
                print(f"⚠️ Erreur init DB: {db_error}")
                # Continuer sans la DB si nécessaire
        
        print("🎉 Application DOUKA KM démarrée avec Python 3.13!")
        return app
        
    except ImportError as e:
        print(f"❌ Erreur d'importation: {e}")
        print("📋 Diagnostic PostgreSQL:")
        
        # Diagnostic PostgreSQL
        try:
            import pkg_resources
            postgres_packages = ['psycopg2', 'psycopg2-binary', 'psycopg']
            for package in postgres_packages:
                try:
                    version = pkg_resources.get_distribution(package).version
                    print(f"  ✅ {package}: {version}")
                except:
                    print(f"  ❌ {package}: Non installé")
        except:
            pass
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_fallback_app():
    """Crée une app de fallback en cas d'erreur"""
    from flask import Flask
    
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/')
    def status():
        return {
            "status": "error",
            "message": "Erreur de configuration SQLAlchemy",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "timestamp": "2025-09-01"
        }, 500
    
    @fallback_app.route('/health')
    def health():
        return {"status": "fallback", "python": f"{sys.version_info.major}.{sys.version_info.minor}"}
    
    return fallback_app

# Configuration principale
print("🚀 Démarrage DOUKA KM avec Python 3.13")

# Vérifier la compatibilité Python 3.13
is_python313_compatible = check_python313_compatibility()

# Importer l'application
app = import_with_python313()

if app is None:
    print("⚠️ Échec import - Création app de fallback")
    app = create_fallback_app()

# Interface WSGI pour Gunicorn
def application(environ, start_response):
    """Interface WSGI standard"""
    return app(environ, start_response)

# Mode développement local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
