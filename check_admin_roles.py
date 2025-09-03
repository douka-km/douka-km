#!/usr/bin/env python3
"""
Script pour vérifier et corriger les rôles des administrateurs
"""

import os
import sys
from sqlalchemy import create_engine, text

def check_and_fix_admin_roles():
    """Vérifier et corriger les rôles des administrateurs"""
    
    # Utiliser la variable d'environnement DATABASE_URL si disponible
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non défini")
        return False
    
    try:
        # Créer l'engine PostgreSQL
        engine = create_engine(database_url)
        
        print("🔍 Vérification des administrateurs...")
        
        # Vérifier les administrateurs existants
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, email, first_name, last_name, role, status, created_at
                FROM admins 
                ORDER BY created_at
            """))
            
            admins = result.fetchall()
            
            print(f"\n=== ADMINISTRATEURS TROUVÉS ({len(admins)}) ===")
            for admin in admins:
                print(f"ID: {admin.id}")
                print(f"Email: {admin.email}")
                print(f"Nom: {admin.first_name} {admin.last_name}")
                print(f"Rôle: {admin.role}")
                print(f"Status: {admin.status}")
                print(f"Créé: {admin.created_at}")
                print("-" * 50)
            
            # Corriger les rôles si nécessaire
            print("\n🔧 Correction des rôles...")
            
            # Mettre à jour tous les admins avec role 'manager' vers 'admin'
            result = conn.execute(text("""
                UPDATE admins 
                SET role = 'admin' 
                WHERE role = 'manager' AND email LIKE '%douka%'
                RETURNING id, email, role
            """))
            
            updated_admins = result.fetchall()
            
            if updated_admins:
                print(f"✅ {len(updated_admins)} administrateurs mis à jour:")
                for admin in updated_admins:
                    print(f"  - {admin.email}: rôle changé vers '{admin.role}'")
                
                # Confirmer les changements
                conn.commit()
            else:
                print("ℹ️ Aucun administrateur à mettre à jour")
        
        print("\n✅ Vérification terminée!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def main():
    """Fonction principale"""
    print("=== Vérification des rôles administrateurs ===")
    
    if check_and_fix_admin_roles():
        print("\n✅ Script terminé avec succès!")
    else:
        print("\n❌ Erreurs détectées")
        sys.exit(1)

if __name__ == "__main__":
    main()
