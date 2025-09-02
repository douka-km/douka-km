#!/usr/bin/env python3
"""
Script pour créer un utilisateur de test et tester la vérification d'email.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_final_with_db import app, users_db
from models import db, User
from datetime import datetime

def create_test_user():
    """Créer un utilisateur de test non vérifié"""
    
    with app.app_context():
        print("👤 Création d'un utilisateur de test")
        print("=" * 35)
        
        test_email = "test.user@doukakm.com"
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = User.query.filter_by(email=test_email).first()
        
        if existing_user:
            print(f"⚠️  L'utilisateur {test_email} existe déjà")
            print(f"   email_verified: {existing_user.email_verified}")
            
            # Marquer comme non vérifié pour le test
            if existing_user.email_verified:
                existing_user.email_verified = False
                db.session.commit()
                print(f"✅ Marqué comme non vérifié pour le test")
            
            return existing_user.id
        
        # Créer un nouvel utilisateur
        from werkzeug.security import generate_password_hash
        
        new_user = User(
            email=test_email,
            password_hash=generate_password_hash("testpassword123"),  # Mot de passe requis
            first_name="Test",
            last_name="User",
            phone="123456789",
            address="Adresse de test",
            city="Antananarivo",
            region="Analamanga",
            email_verified=False,  # Non vérifié par défaut
            is_active=True,
            created_at=datetime.now()
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            print(f"✅ Utilisateur créé: {test_email}")
            print(f"   ID: {new_user.id}")
            print(f"   email_verified: {new_user.email_verified}")
            
            return new_user.id
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la création: {e}")
            return None

def test_verification_process(user_id):
    """Tester le processus de vérification"""
    
    with app.app_context():
        print(f"\n🔧 Test de vérification pour l'utilisateur ID {user_id}")
        print("=" * 50)
        
        user = User.query.get(user_id)
        if not user:
            print("❌ Utilisateur non trouvé")
            return
        
        print(f"👤 {user.first_name} {user.last_name} ({user.email})")
        print(f"   État avant: email_verified = {user.email_verified}")
        
        # Simuler la vérification
        if not user.email_verified:
            user.email_verified = True
            db.session.commit()
            print(f"✅ Email vérifié avec succès")
        
        # Vérifier l'état après
        user_after = User.query.get(user_id)
        print(f"   État après: email_verified = {user_after.email_verified}")
        
        # Tester l'affichage dans l'interface admin
        print(f"\n🖥️  Test de l'affichage admin:")
        
        if user_after.email_verified:
            print(f"   ✅ L'interface admin devrait afficher:")
            print(f"      - Badge vert 'Vérifié'")
            print(f"      - Pas de bouton 'Vérifier maintenant'")
        else:
            print(f"   ⚠️  L'interface admin devrait afficher:")
            print(f"      - Badge orange 'Non vérifié'")
            print(f"      - Bouton 'Vérifier maintenant'")

def list_all_users_status():
    """Lister tous les utilisateurs et leur statut"""
    
    with app.app_context():
        print(f"\n📋 Liste de tous les utilisateurs")
        print("=" * 35)
        
        users = User.query.all()
        
        for user in users:
            status = "✅ Vérifié" if user.email_verified else "❌ Non vérifié"
            print(f"ID {user.id}: {user.first_name} {user.last_name} ({user.email}) - {status}")

if __name__ == "__main__":
    print("🧪 Test complet de vérification d'email")
    print("=" * 40)
    
    # 1. Lister les utilisateurs existants
    list_all_users_status()
    
    # 2. Créer un utilisateur de test
    user_id = create_test_user()
    
    if user_id:
        # 3. Tester le processus de vérification
        test_verification_process(user_id)
        
        # 4. État final
        print(f"\n📋 État final:")
        list_all_users_status()
        
        print(f"\n💡 Pour tester dans l'interface web:")
        print(f"   1. Aller sur /admin/users/{user_id}")
        print(f"   2. Vérifier l'affichage du statut d'email")
        print(f"   3. Utiliser F5 ou Ctrl+F5 pour forcer le rechargement sans cache")
    else:
        print("❌ Impossible de créer l'utilisateur de test")
