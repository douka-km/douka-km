#!/usr/bin/env python3
"""
Script pour assigner un livreur par défaut aux commandes livrées orphelines.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_final_with_db import app
from models import db, Order, Employee
from datetime import datetime

def assign_default_livreur_to_orphans():
    """Assigner un livreur par défaut aux commandes livrées sans livreur"""
    
    with app.app_context():
        print("🔄 Assignation d'un livreur par défaut aux commandes orphelines...")
        
        # Trouver les commandes livrées sans livreur
        orphan_orders = Order.query.filter_by(status='delivered').filter(
            Order.delivery_employee_email.is_(None)
        ).all()
        
        if not orphan_orders:
            print("✅ Aucune commande orpheline trouvée")
            return True
            
        print(f"📦 Commandes orphelines trouvées: {len(orphan_orders)}")
        
        # Trouver le premier livreur actif disponible
        default_livreur = Employee.query.filter_by(role='livreur', status='active').first()
        
        if not default_livreur:
            print("❌ Aucun livreur actif trouvé dans le système")
            return False
            
        print(f"👤 Livreur par défaut: {default_livreur.first_name} {default_livreur.last_name} ({default_livreur.email})")
        
        # Assigner le livreur par défaut à toutes les commandes orphelines
        updated_count = 0
        for order in orphan_orders:
            order_type = 'Admin' if order.merchant_id is None else 'Marchand'
            
            order.delivery_employee_id = default_livreur.id
            order.delivery_employee_email = default_livreur.email
            order.delivery_employee_name = f"{default_livreur.first_name} {default_livreur.last_name}"
            order.delivery_employee_phone = default_livreur.phone
            order.assigned_at = order.created_at  # Utiliser la date de création comme date d'assignation
            
            print(f"✅ {order_type} Order {order.id} -> Livreur: {default_livreur.first_name} {default_livreur.last_name}")
            updated_count += 1
        
        # Sauvegarder les changements
        try:
            db.session.commit()
            print(f"\n✅ Assignation terminée avec succès !")
            print(f"📊 {updated_count} commandes mises à jour")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la sauvegarde: {e}")
            return False

def list_available_livreurs():
    """Lister les livreurs disponibles"""
    
    with app.app_context():
        livreurs = Employee.query.filter_by(role='livreur').all()
        
        print("\n👥 Livreurs disponibles:")
        for i, livreur in enumerate(livreurs, 1):
            status_icon = "✅" if livreur.status == 'active' else "❌"
            print(f"   {i}. {status_icon} {livreur.first_name} {livreur.last_name} ({livreur.email}) - {livreur.status}")
        
        return livreurs

if __name__ == "__main__":
    print("🚀 Assignment de livreur par défaut aux commandes orphelines")
    print("=" * 60)
    
    # Lister les livreurs disponibles
    livreurs = list_available_livreurs()
    
    if not livreurs:
        print("❌ Aucun livreur trouvé dans le système")
        sys.exit(1)
    
    # Demander confirmation
    response = input("\n❓ Voulez-vous assigner le premier livreur actif aux commandes orphelines ? (y/N): ")
    if response.lower() in ['y', 'yes', 'oui']:
        success = assign_default_livreur_to_orphans()
        if not success:
            sys.exit(1)
    else:
        print("❌ Assignation annulée")
