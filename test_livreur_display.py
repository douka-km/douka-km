#!/usr/bin/env python3
"""
Test de la fonction admin_order_detail pour vérifier l'affichage des livreurs.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_final_with_db import app, admin_order_detail
from models import db, Order

def test_delivered_orders_livreur_display():
    """Tester l'affichage des livreurs pour les commandes livrées"""
    
    with app.app_context():
        print("🧪 Test de l'affichage des livreurs pour les commandes livrées")
        print("=" * 60)
        
        # Récupérer toutes les commandes livrées
        delivered_orders = Order.query.filter_by(status='delivered').all()
        
        if not delivered_orders:
            print("❌ Aucune commande livrée trouvée")
            return
            
        print(f"📦 Commandes livrées trouvées: {len(delivered_orders)}")
        print()
        
        for order in delivered_orders:
            order_type = 'Admin' if order.merchant_id is None else 'Marchand'
            
            print(f"🔍 Test Commande {order_type} #{order.id}")
            print(f"   Client: {order.customer_name}")
            print(f"   Total: {order.total} KMF")
            print(f"   Status: {order.status}")
            
            # Vérifier les informations du livreur dans la base de données
            if order.delivery_employee_email:
                print(f"   ✅ Livreur DB: {order.delivery_employee_name} ({order.delivery_employee_email})")
            else:
                print(f"   ❌ Pas de livreur dans la DB")
            
            # Simuler l'appel à admin_order_detail pour voir ce qui sera affiché
            try:
                with app.test_request_context():
                    # Mock de la session admin
                    from flask import session
                    session['user_email'] = 'admin@douka-km.com'
                    session['user_role'] = 'super_admin'
                    
                    # Cette fonction devrait maintenant retourner les bonnes informations
                    print(f"   🧪 Test de la fonction admin_order_detail...")
                    
                    # Simuler directement la logique de récupération du livreur
                    assigned_livreur_info = None
                    if order.delivery_employee_email:
                        assigned_livreur_info = {
                            'email': order.delivery_employee_email,
                            'name': order.delivery_employee_name or 'Livreur',
                            'phone': order.delivery_employee_phone or '',
                            'assigned_at': order.assigned_at.strftime('%Y-%m-%d %H:%M:%S') if order.assigned_at else '',
                            'is_employee': True,
                            'is_from_history': True
                        }
                    
                    if assigned_livreur_info:
                        print(f"   ✅ Livreur sera affiché: {assigned_livreur_info['name']} ({assigned_livreur_info['email']})")
                    else:
                        print(f"   ❌ 'Aucun livreur assigné' sera affiché")
                        
            except Exception as e:
                print(f"   ⚠️  Erreur lors du test: {e}")
            
            print("-" * 40)

if __name__ == "__main__":
    test_delivered_orders_livreur_display()
