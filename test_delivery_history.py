#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier le système d'historique des livreurs
"""

from app_final_with_db import app, db
from models import Order
from sqlalchemy import text

def test_delivery_history():
    """Test du système d'historique des livreurs"""
    with app.app_context():
        try:
            # Vérifier que les nouvelles colonnes existent
            result = db.session.execute(text("PRAGMA table_info(orders)"))
            columns = [row[1] for row in result.fetchall()]
            
            delivery_columns = [
                'delivery_employee_id',
                'delivery_employee_email', 
                'delivery_employee_name',
                'delivery_employee_phone',
                'assigned_at'
            ]
            
            print("🔍 Vérification des colonnes de l'historique des livreurs:")
            for col in delivery_columns:
                if col in columns:
                    print(f"✅ {col} - OK")
                else:
                    print(f"❌ {col} - MANQUANT")
            
            # Tester une requête sur une commande
            order = Order.query.first()
            if order:
                print(f"\n🧪 Test sur la commande #{order.id}:")
                print(f"   - Email livreur: {order.delivery_employee_email}")
                print(f"   - Nom livreur: {order.delivery_employee_name}")
                print(f"   - Téléphone livreur: {order.delivery_employee_phone}")
                print(f"   - Assigné le: {order.assigned_at}")
            else:
                print("\n⚠️  Aucune commande trouvée pour test")
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")

if __name__ == "__main__":
    test_delivery_history()
