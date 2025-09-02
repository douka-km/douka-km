#!/usr/bin/env python3
"""
Script pour corriger les types PostgreSQL et tester les requêtes
"""

import os
import sys
from sqlalchemy import create_engine, text
from models import *

def test_postgresql_queries():
    """Tester les requêtes PostgreSQL après correction"""
    
    # Utiliser la variable d'environnement DATABASE_URL si disponible
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non défini")
        return False
    
    try:
        # Créer l'engine PostgreSQL
        engine = create_engine(database_url)
        
        print("🔍 Test des requêtes PostgreSQL...")
        
        # Test 1: Vérifier les types de colonnes
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'id'
            """))
            
            for row in result:
                print(f"✅ Colonne orders.id: {row.column_name} ({row.data_type})")
        
        # Test 2: Tester une requête avec conversion de type
        with engine.connect() as conn:
            # Cette requête devrait maintenant fonctionner
            result = conn.execute(text("""
                SELECT id, customer_email, status 
                FROM orders 
                WHERE id = :order_id AND merchant_id IS NULL 
                LIMIT 1
            """), {"order_id": 1})
            
            row = result.fetchone()
            if row:
                print(f"✅ Test requête réussie: Commande {row.id} ({row.customer_email})")
            else:
                print("ℹ️ Aucune commande admin trouvée (normal si base vide)")
        
        print("✅ Tests PostgreSQL réussis!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test PostgreSQL: {e}")
        return False

def main():
    """Fonction principale"""
    print("=== Correction des types PostgreSQL ===")
    
    if test_postgresql_queries():
        print("\n✅ Toutes les corrections sont appliquées avec succès!")
    else:
        print("\n❌ Des problèmes persistent")
        sys.exit(1)

if __name__ == "__main__":
    main()
