#!/usr/bin/env python3
"""
Script simple pour exécuter sur render.com via la console shell
pour corriger le problème du logo manquant
"""

# Copier et coller ce code dans la console Python de Render.com
print("🔧 Démarrage de la correction du logo...")

try:
    from models import db, SiteSettings
    from sqlalchemy.exc import IntegrityError
    
    # Vérifier si le paramètre logo_url existe déjà
    existing_logo = SiteSettings.query.filter_by(key='logo_url').first()
    
    if existing_logo:
        print(f"✅ Logo URL existe déjà: {existing_logo.value}")
        print("Le logo devrait être visible. Vérifiez le cache du navigateur.")
    else:
        # Créer le paramètre logo_url par défaut
        logo_setting = SiteSettings(
            key='logo_url',
            value='/static/img/logo.png',
            description='URL du logo principal du site'
        )
        
        db.session.add(logo_setting)
        
        # Ajouter également le logo_alt_text s'il n'existe pas
        existing_alt = SiteSettings.query.filter_by(key='logo_alt_text').first()
        if not existing_alt:
            logo_alt_setting = SiteSettings(
                key='logo_alt_text',
                value='DOUKA KM Logo',
                description='Texte alternatif pour le logo'
            )
            db.session.add(logo_alt_setting)
        
        db.session.commit()
        
        print("✅ Paramètres logo ajoutés avec succès!")
        print("   - logo_url: /static/img/logo.png")
        print("   - logo_alt_text: DOUKA KM Logo")
        print("🔄 Le logo devrait maintenant apparaître sur le site.")
        
except Exception as e:
    if 'db' in locals():
        db.session.rollback()
    print(f"❌ Erreur: {e}")
    print("Contactez l'administrateur technique.")
    
print("🏁 Script terminé.")
