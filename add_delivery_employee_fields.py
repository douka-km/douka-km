#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour ajouter les champs de livreur à la table orders
"""

from app_final_with_db import app, db
from sqlalchemy import text

def add_delivery_employee_fields():
    """Ajoute les champs de livreur à la table orders"""
    with app.app_context():
        try:
            # Vérifier si les colonnes existent déjà
            result = db.session.execute(text("PRAGMA table_info(orders)"))
            columns = [row[1] for row in result.fetchall()]
            
            # Ajouter les colonnes si elles n'existent pas
            if 'delivery_employee_id' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN delivery_employee_id INTEGER"))
                print("✓ Colonne delivery_employee_id ajoutée")
            
            if 'delivery_employee_email' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN delivery_employee_email VARCHAR(120)"))
                print("✓ Colonne delivery_employee_email ajoutée")
            
            if 'delivery_employee_name' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN delivery_employee_name VARCHAR(200)"))
                print("✓ Colonne delivery_employee_name ajoutée")
            
            if 'delivery_employee_phone' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN delivery_employee_phone VARCHAR(20)"))
                print("✓ Colonne delivery_employee_phone ajoutée")
            
            if 'assigned_at' not in columns:
                db.session.execute(text("ALTER TABLE orders ADD COLUMN assigned_at DATETIME"))
                print("✓ Colonne assigned_at ajoutée")
            
            db.session.commit()
            print("🎉 Migration terminée avec succès!")
            
        except Exception as e:
            print(f"❌ Erreur lors de la migration: {e}")
            db.session.rollback()

if __name__ == "__main__":
    add_delivery_employee_fields()
