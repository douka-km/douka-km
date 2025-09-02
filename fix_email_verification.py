#!/usr/bin/env python3
"""
Script pour vérifier et corriger l'état de vérification des emails.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_final_with_db import app, users_db
from models import db, User

def check_email_verification_status():
    """Vérifier l'état de vérification des emails"""
    
    with app.app_context():
        print("📧 Vérification de l'état des emails")
        print("=" * 40)
        
        # Récupérer tous les utilisateurs de la base de données
        db_users = User.query.all()
        
        print(f"👥 Utilisateurs dans la base de données: {len(db_users)}")
        
        for user in db_users:
            print(f"\n🔍 {user.first_name} {user.last_name} ({user.email})")
            print(f"   DB email_verified: {user.email_verified}")
            
            # Vérifier dans le dictionnaire
            if user.email in users_db:
                dict_verified = users_db[user.email].get('email_verified', False)
                print(f"   Dict email_verified: {dict_verified}")
                
                # Vérifier la cohérence
                if user.email_verified != dict_verified:
                    print(f"   ⚠️  INCOHÉRENCE! DB: {user.email_verified}, Dict: {dict_verified}")
            else:
                print(f"   ⚠️  Utilisateur absent du dictionnaire users_db")

def sync_email_verification():
    """Synchroniser les statuts de vérification entre DB et dictionnaire"""
    
    with app.app_context():
        print("\n🔄 Synchronisation des statuts de vérification")
        print("=" * 45)
        
        db_users = User.query.all()
        updated_count = 0
        
        for user in db_users:
            if user.email in users_db:
                dict_verified = users_db[user.email].get('email_verified', False)
                
                # Si l'utilisateur semble vérifié dans le dictionnaire mais pas en DB
                if dict_verified and not user.email_verified:
                    print(f"✅ Mise à jour DB: {user.email} -> vérifié")
                    user.email_verified = True
                    updated_count += 1
                
                # Si l'utilisateur est vérifié en DB mais pas dans le dictionnaire
                elif user.email_verified and not dict_verified:
                    print(f"✅ Mise à jour Dict: {user.email} -> vérifié")
                    users_db[user.email]['email_verified'] = True
                    updated_count += 1
        
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"\n✅ {updated_count} statuts synchronisés avec succès")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Erreur lors de la sauvegarde: {e}")
        else:
            print("\n✅ Tous les statuts sont déjà synchronisés")

def manually_verify_all_test_emails():
    """Vérifier manuellement tous les emails de test"""
    
    with app.app_context():
        print("\n🚀 Vérification manuelle des emails de test")
        print("=" * 45)
        
        # Emails de test à vérifier automatiquement
        test_emails = [
            'mohamed@test.com',
            'test@test.com',
            'admin@test.com'
        ]
        
        updated_count = 0
        
        for email in test_emails:
            user = User.query.filter_by(email=email).first()
            
            if user:
                if not user.email_verified:
                    print(f"✅ Vérification: {email}")
                    user.email_verified = True
                    updated_count += 1
                else:
                    print(f"✓ Déjà vérifié: {email}")
                
                # Synchroniser avec le dictionnaire
                if email in users_db:
                    users_db[email]['email_verified'] = True
            else:
                print(f"❌ Utilisateur non trouvé: {email}")
        
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"\n✅ {updated_count} emails de test vérifiés")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Erreur: {e}")

if __name__ == "__main__":
    print("🔧 Script de vérification des emails")
    print("=" * 40)
    
    # 1. Vérifier l'état actuel
    check_email_verification_status()
    
    # 2. Demander les actions à effectuer
    print("\n❓ Actions disponibles:")
    print("1. Synchroniser les statuts entre DB et dictionnaire")
    print("2. Vérifier manuellement tous les emails de test")
    print("3. Les deux")
    
    choice = input("\nVotre choix (1/2/3): ")
    
    if choice in ['1', '3']:
        sync_email_verification()
    
    if choice in ['2', '3']:
        manually_verify_all_test_emails()
    
    # 3. Vérifier l'état final
    print("\n" + "="*40)
    check_email_verification_status()
