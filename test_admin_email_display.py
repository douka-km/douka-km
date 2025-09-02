#!/usr/bin/env python3
"""
Test pour vérifier l'affichage du statut de vérification d'email dans l'interface admin.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_final_with_db import app
from models import db, User

def test_admin_user_detail_display():
    """Tester l'affichage dans admin_user_detail"""
    
    with app.app_context():
        print("🔍 Test de l'affichage admin_user_detail")
        print("=" * 40)
        
        # Récupérer un utilisateur de la base de données
        users = User.query.all()
        
        if not users:
            print("❌ Aucun utilisateur trouvé dans la base de données")
            return
            
        for user in users:
            print(f"\n👤 Test pour: {user.first_name} {user.last_name} ({user.email})")
            print(f"   ID: {user.id}")
            print(f"   email_verified dans la DB: {user.email_verified}")
            
            # Simuler l'appel à admin_user_detail
            with app.test_request_context():
                from flask import session
                session['admin_email'] = 'admin@doukakm.com'
                session['user_role'] = 'super_admin'
                
                try:
                    # Simuler la logique de admin_user_detail
                    target_user_data = {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name or '',
                        'last_name': user.last_name or '',
                        'phone': user.phone or '',
                        'address': user.address or '',
                        'city': user.city or '',
                        'region': user.region or '',
                        'registration_date': user.created_at.strftime('%Y-%m-%d') if user.created_at else '',
                        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
                        'is_active': user.is_active,
                        'email_verified': user.email_verified,  # La propriété clé
                    }
                    
                    print(f"   ✅ Données pour le template:")
                    print(f"      user.email_verified = {target_user_data['email_verified']}")
                    
                    # Simuler la condition du template
                    if target_user_data['email_verified']:
                        print(f"      🟢 Template affichera: 'Vérifié' (badge vert)")
                    else:
                        print(f"      🟡 Template affichera: 'Non vérifié' + bouton 'Vérifier maintenant'")
                        
                except Exception as e:
                    print(f"   ❌ Erreur lors du test: {e}")

def update_email_verification_if_needed():
    """Mettre à jour la vérification d'email si nécessaire"""
    
    with app.app_context():
        print(f"\n🔧 Mise à jour des statuts de vérification")
        print("=" * 40)
        
        users = User.query.all()
        updated_count = 0
        
        for user in users:
            # Pour les tests, on peut marquer comme vérifié si c'est un admin
            if 'admin' in user.email.lower() and not user.email_verified:
                print(f"✅ Vérification automatique: {user.email}")
                user.email_verified = True
                updated_count += 1
                
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"✅ {updated_count} utilisateurs mis à jour")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erreur: {e}")
        else:
            print("✓ Aucune mise à jour nécessaire")

if __name__ == "__main__":
    print("🧪 Test d'affichage de vérification d'email")
    print("=" * 45)
    
    # 1. Tester l'affichage actuel
    test_admin_user_detail_display()
    
    # 2. Proposer une mise à jour si nécessaire
    choice = input("\n❓ Voulez-vous vérifier automatiquement les emails admin ? (y/N): ")
    if choice.lower() in ['y', 'yes', 'oui']:
        update_email_verification_if_needed()
        print("\n" + "="*40)
        test_admin_user_detail_display()
