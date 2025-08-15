#!/usr/bin/env python3
"""
Script pour ajouter le paramètre logo_url dans la base de données
pour corriger le problème de logo manquant sur render.com
"""

import os
import sys
from flask import Flask
from models import db, SiteSettings
from sqlalchemy.exc import IntegrityError

def create_app():
    """Créer l'application Flask pour la configuration de la base de données"""
    app = Flask(__name__)
    
    # Configuration de la base de données
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Production (PostgreSQL sur Render)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://')
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Local (SQLite)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/douka_km.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-for-logo-fix')
    
    db.init_app(app)
    return app

def add_default_logo_setting():
    """Ajouter le paramètre logo_url par défaut"""
    app = create_app()
    
    with app.app_context():
        try:
            # Vérifier si le paramètre logo_url existe déjà
            existing_logo = SiteSettings.query.filter_by(key='logo_url').first()
            
            if existing_logo:
                print(f"✅ Le paramètre logo_url existe déjà: {existing_logo.value}")
                return True
            
            # Créer le paramètre logo_url par défaut
            logo_setting = SiteSettings(
                key='logo_url',
                value='/static/img/logo.png',
                description='URL du logo principal du site'
            )
            
            db.session.add(logo_setting)
            db.session.commit()
            
            print("✅ Paramètre logo_url ajouté avec succès: /static/img/logo.png")
            return True
            
        except IntegrityError as e:
            db.session.rollback()
            print(f"⚠️ Le paramètre logo_url existe probablement déjà: {e}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de l'ajout du paramètre logo_url: {e}")
            return False

def check_all_site_settings():
    """Afficher tous les paramètres du site pour diagnostic"""
    app = create_app()
    
    with app.app_context():
        try:
            settings = SiteSettings.query.all()
            print(f"📋 Nombre de paramètres dans la base: {len(settings)}")
            
            if settings:
                print("\n🔧 Paramètres existants:")
                for setting in settings:
                    print(f"  - {setting.key}: {setting.value}")
            else:
                print("⚠️ Aucun paramètre trouvé dans la base de données")
                
            # Vérifier spécifiquement le logo
            logo_setting = SiteSettings.query.filter_by(key='logo_url').first()
            if logo_setting:
                print(f"\n🖼️ Logo URL trouvé: {logo_setting.value}")
            else:
                print("\n❌ Aucun paramètre logo_url trouvé")
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des paramètres: {e}")

if __name__ == '__main__':
    print("🔧 Script de correction du logo DOUKA KM")
    print("=" * 50)
    
    # Vérifier l'état actuel
    print("\n1️⃣ Vérification de l'état actuel...")
    check_all_site_settings()
    
    # Ajouter le paramètre logo si nécessaire
    print("\n2️⃣ Ajout du paramètre logo_url...")
    success = add_default_logo_setting()
    
    # Vérifier le résultat
    print("\n3️⃣ Vérification après modification...")
    check_all_site_settings()
    
    if success:
        print("\n✅ Script terminé avec succès!")
        print("💡 Le logo devrait maintenant apparaître sur render.com")
        print("🔄 Redémarrez l'application sur Render si nécessaire")
    else:
        print("\n❌ Problème lors de l'exécution du script")
        sys.exit(1)
