#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration pour PostgreSQL sur Render.com
Ajoute les champs de livreur aux tables orders
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_final_with_db import app, db
from sqlalchemy import text
import psycopg

def check_column_exists(table_name, column_name):
    """Vérifie si une colonne existe dans une table PostgreSQL"""
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name AND column_name = :column_name
    """)
    result = db.session.execute(query, {'table_name': table_name, 'column_name': column_name})
    return result.fetchone() is not None

def add_delivery_employee_fields_postgresql():
    """Ajoute les champs de livreur à la table orders (PostgreSQL)"""
    with app.app_context():
        try:
            print("🔄 Début de la migration PostgreSQL...")
            
            # Liste des colonnes à ajouter
            columns_to_add = [
                ('delivery_employee_id', 'INTEGER'),
                ('delivery_employee_email', 'VARCHAR(120)'),
                ('delivery_employee_name', 'VARCHAR(200)'),
                ('delivery_employee_phone', 'VARCHAR(20)'),
                ('assigned_at', 'TIMESTAMP')
            ]
            
            added_columns = 0
            
            for column_name, column_type in columns_to_add:
                if not check_column_exists('orders', column_name):
                    try:
                        alter_query = text(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
                        db.session.execute(alter_query)
                        db.session.commit()
                        print(f"✓ Colonne {column_name} ajoutée")
                        added_columns += 1
                    except Exception as e:
                        print(f"⚠️  Erreur lors de l'ajout de {column_name}: {e}")
                        db.session.rollback()
                else:
                    print(f"✓ Colonne {column_name} existe déjà")
            
            # Ajouter la contrainte de clé étrangère si nécessaire
            if added_columns > 0:
                try:
                    # Vérifier si la contrainte existe déjà
                    constraint_query = text("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = 'orders' 
                        AND constraint_name = 'fk_orders_delivery_employee'
                    """)
                    result = db.session.execute(constraint_query)
                    
                    if not result.fetchone():
                        # Ajouter la contrainte de clé étrangère
                        fk_query = text("""
                            ALTER TABLE orders 
                            ADD CONSTRAINT fk_orders_delivery_employee 
                            FOREIGN KEY (delivery_employee_id) 
                            REFERENCES employees(id)
                        """)
                        db.session.execute(fk_query)
                        db.session.commit()
                        print("✓ Contrainte de clé étrangère ajoutée")
                    else:
                        print("✓ Contrainte de clé étrangère existe déjà")
                        
                except Exception as e:
                    print(f"⚠️  Contrainte de clé étrangère ignorée: {e}")
                    db.session.rollback()
            
            print(f"🎉 Migration terminée! {added_columns} colonnes ajoutées")
            
        except Exception as e:
            print(f"❌ Erreur lors de la migration: {e}")
            db.session.rollback()
            raise

def verify_migration():
    """Vérifie que toutes les colonnes ont été ajoutées"""
    with app.app_context():
        try:
            # Tester une requête SELECT avec toutes les nouvelles colonnes
            test_query = text("""
                SELECT delivery_employee_id, delivery_employee_email, 
                       delivery_employee_name, delivery_employee_phone, assigned_at
                FROM orders LIMIT 1
            """)
            db.session.execute(test_query)
            print("✅ Vérification réussie: toutes les colonnes sont présentes")
            return True
        except Exception as e:
            print(f"❌ Vérification échouée: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Migration PostgreSQL pour Render.com")
    print("=" * 50)
    
    try:
        add_delivery_employee_fields_postgresql()
        
        # Vérifier que la migration a fonctionné
        if verify_migration():
            print("\n✅ Migration complète et vérifiée!")
        else:
            print("\n❌ Migration incomplète")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Erreur critique: {e}")
        sys.exit(1)
