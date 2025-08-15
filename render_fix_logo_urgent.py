#!/usr/bin/env python
"""
Script de correction urgente du logo sur Render.com
À exécuter directement en production pour corriger le problème du logo manquant.
"""

import os
from app_final_with_db import app, db
from models import SiteSettings

def fix_logo_settings():
    """Force l'ajout des paramètres de logo dans la base de données"""
    with app.app_context():
        try:
            # Vérifier si logo_url existe
            logo_url_setting = SiteSettings.query.filter_by(key='logo_url').first()
            if not logo_url_setting:
                print("📝 Ajout du paramètre logo_url...")
                logo_url_setting = SiteSettings(
                    key='logo_url',
                    value='/static/img/logo.png',
                    description='URL du logo du site'
                )
                db.session.add(logo_url_setting)
            else:
                print(f"✅ logo_url existe déjà: {logo_url_setting.value}")
                if not logo_url_setting.value or logo_url_setting.value.strip() == '':
                    print("🔧 Correction de logo_url vide...")
                    logo_url_setting.value = '/static/img/logo.png'
            
            # Vérifier si logo_alt_text existe
            logo_alt_setting = SiteSettings.query.filter_by(key='logo_alt_text').first()
            if not logo_alt_setting:
                print("📝 Ajout du paramètre logo_alt_text...")
                logo_alt_setting = SiteSettings(
                    key='logo_alt_text',
                    value='DOUKA KM - Marketplace des Comores',
                    description='Texte alternatif pour le logo'
                )
                db.session.add(logo_alt_setting)
            else:
                print(f"✅ logo_alt_text existe déjà: {logo_alt_setting.value}")
                if not logo_alt_setting.value or logo_alt_setting.value.strip() == '':
                    print("🔧 Correction de logo_alt_text vide...")
                    logo_alt_setting.value = 'DOUKA KM - Marketplace des Comores'
            
            # Sauvegarder les changements
            db.session.commit()
            print("✅ Paramètres du logo mis à jour avec succès!")
            
            # Vérifier le résultat
            print("\n📊 État actuel des paramètres:")
            all_settings = SiteSettings.query.all()
            for setting in all_settings:
                print(f"  {setting.key}: {setting.value}")
                
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la correction: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🚀 Correction urgente du logo DOUKA KM...")
    success = fix_logo_settings()
    if success:
        print("🎉 Logo corrigé! Le site devrait maintenant afficher le logo correctement.")
    else:
        print("😞 Échec de la correction. Vérifiez les logs pour plus de détails.")
