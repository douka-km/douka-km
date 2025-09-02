#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'urgence pour la migration PostgreSQL sur Render.com
À exécuter manuellement via la console Render si la migration automatique échoue
"""

import os
import sys

# Forcer l'environnement Render
os.environ['RENDER'] = '1'

def emergency_migration():
    """Migration d'urgence pour corriger les colonnes manquantes"""
    try:
        # Import avec gestion d'erreur
        from app_final_with_db import app, db
        from sqlalchemy import text
        
        with app.app_context():
            print("🚨 MIGRATION D'URGENCE - PostgreSQL")
            print("=" * 50)
            
            # Vérifier la connexion
            try:
                db.session.execute(text("SELECT 1"))
                print("✅ Connexion PostgreSQL OK")
            except Exception as e:
                print(f"❌ Problème de connexion: {e}")
                return False
            
            # Commandes SQL directes pour ajouter les colonnes
            migration_commands = [
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_id INTEGER;",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_email VARCHAR(120);",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_name VARCHAR(200);",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_phone VARCHAR(20);",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP;"
            ]
            
            success_count = 0
            for i, command in enumerate(migration_commands, 1):
                try:
                    print(f"🔄 Exécution commande {i}/5...")
                    db.session.execute(text(command))
                    db.session.commit()
                    print(f"✅ Commande {i} réussie")
                    success_count += 1
                except Exception as e:
                    print(f"⚠️  Commande {i} ignorée: {e}")
                    try:
                        db.session.rollback()
                    except:
                        pass
            
            # Test final
            try:
                test_query = text("""
                    SELECT delivery_employee_id, delivery_employee_email 
                    FROM orders LIMIT 1
                """)
                db.session.execute(test_query)
                print("✅ TEST FINAL RÉUSSI - Les colonnes sont disponibles")
                return True
            except Exception as e:
                print(f"❌ TEST FINAL ÉCHOUÉ: {e}")
                return False
                
    except Exception as e:
        print(f"💥 ERREUR CRITIQUE: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def quick_fix():
    """Correction rapide avec SQL brut"""
    print("🔧 CORRECTION RAPIDE")
    print("=" * 30)
    
    sql_commands = """
    -- Ajouter les colonnes de livreur si elles n'existent pas
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_id INTEGER;
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_email VARCHAR(120);
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_name VARCHAR(200);
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_employee_phone VARCHAR(20);
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP;
    
    -- Optionnel: Ajouter l'index pour les performances
    CREATE INDEX IF NOT EXISTS idx_orders_delivery_employee ON orders(delivery_employee_id);
    CREATE INDEX IF NOT EXISTS idx_orders_assigned_at ON orders(assigned_at);
    """
    
    print("📋 Commandes SQL à exécuter:")
    print(sql_commands)
    print("\n💡 Copiez ces commandes et exécutez-les dans la console PostgreSQL de Render")

if __name__ == "__main__":
    print("🚨 SCRIPT DE MIGRATION D'URGENCE")
    print("=" * 40)
    
    # Essayer la migration automatique
    print("1️⃣ Tentative de migration automatique...")
    
    try:
        if emergency_migration():
            print("🎉 MIGRATION RÉUSSIE!")
            print("L'application devrait maintenant fonctionner correctement.")
            sys.exit(0)
        else:
            print("❌ Migration automatique échouée")
    except Exception as e:
        print(f"❌ Erreur lors de la migration automatique: {e}")
    
    # Afficher les commandes SQL manuelles
    print("\n2️⃣ Solution manuelle:")
    quick_fix()
    
    print("\n📖 INSTRUCTIONS:")
    print("1. Connectez-vous à la console Render.com")
    print("2. Allez dans votre service PostgreSQL")
    print("3. Ouvrez la console SQL")
    print("4. Exécutez les commandes SQL affichées ci-dessus")
    print("5. Redéployez votre application")
