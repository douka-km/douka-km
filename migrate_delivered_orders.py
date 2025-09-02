#!/usr/bin/env python3
"""
Script de migration pour ajouter les informations du livreur aux commandes déjà livrées.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_final_with_db import app, livreur_assignments_db
from models import db, Order, Employee
from datetime import datetime

def migrate_delivered_orders():
    """Migrer les informations du livreur pour les commandes déjà livrées"""
    
    with app.app_context():
        print("🔄 Début de la migration des commandes livrées...")
        
        # Statistiques
        merchant_orders_updated = 0
        admin_orders_updated = 0
        
        # Récupérer toutes les commandes livrées sans informations de livreur
        delivered_orders = Order.query.filter_by(status='delivered').all()
        
        print(f"📦 Commandes livrées trouvées: {len(delivered_orders)}")
        
        for order in delivered_orders:
            if not order.delivery_employee_email:  # Seulement si pas déjà migré
                # Déterminer le type de commande
                order_type = 'admin' if order.merchant_id is None else 'merchant'
                
                # Chercher dans les assignations en mémoire
                livreur_found = False
                
                for livreur_email, assignments in livreur_assignments_db.items():
                    for assignment in assignments:
                        if (str(assignment['order_id']) == str(order.id) and 
                            assignment['order_type'] == order_type):
                            
                            # Vérifier le merchant_email pour les commandes marchands
                            if order_type == 'merchant' and order.merchant_id:
                                from db_helpers import get_merchant_by_id
                                merchant = get_merchant_by_id(order.merchant_id)
                                if merchant and assignment.get('merchant_email') != merchant.email:
                                    continue  # Pas le bon marchand
                            
                            # Récupérer les infos du livreur
                            employee = Employee.query.filter_by(email=livreur_email, role='livreur').first()
                            
                            if employee:
                                # Sauvegarder les informations du livreur
                                order.delivery_employee_id = employee.id
                                order.delivery_employee_email = employee.email
                                order.delivery_employee_name = f"{employee.first_name} {employee.last_name}"
                                order.delivery_employee_phone = employee.phone
                                order.assigned_at = datetime.now()  # Date approximative
                                
                                if order_type == 'admin':
                                    print(f"✅ Commande Admin {order.id} -> Livreur: {employee.first_name} {employee.last_name}")
                                    admin_orders_updated += 1
                                else:
                                    print(f"✅ Commande Marchand {order.id} -> Livreur: {employee.first_name} {employee.last_name}")
                                    merchant_orders_updated += 1
                                    
                                livreur_found = True
                                break
                    if livreur_found:
                        break
                        
                if not livreur_found:
                    order_label = f"Admin {order.id}" if order_type == 'admin' else f"Marchand {order.id}"
                    print(f"⚠️  Commande {order_label} - Livreur non trouvé dans les assignations")
        
        # Sauvegarder les changements
        try:
            db.session.commit()
            print(f"\n✅ Migration terminée avec succès !")
            print(f"📊 Statistiques:")
            print(f"   - Commandes marchands mises à jour: {merchant_orders_updated}")
            print(f"   - Commandes admin mises à jour: {admin_orders_updated}")
            print(f"   - Total: {merchant_orders_updated + admin_orders_updated}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la sauvegarde: {e}")
            return False
            
        return True

def check_delivered_orders_status():
    """Vérifier l'état des commandes livrées après migration"""
    
    with app.app_context():
        print("\n🔍 Vérification de l'état post-migration...")
        
        # Toutes les commandes livrées
        all_delivered_orders = Order.query.filter_by(status='delivered').all()
        
        # Séparer par type
        merchant_orders = [o for o in all_delivered_orders if o.merchant_id is not None]
        admin_orders = [o for o in all_delivered_orders if o.merchant_id is None]
        
        # Compter celles avec livreur
        merchant_with_livreur = sum(1 for o in merchant_orders if o.delivery_employee_email)
        admin_with_livreur = sum(1 for o in admin_orders if o.delivery_employee_email)
        
        print(f"📦 Commandes marchands livrées: {len(merchant_orders)}")
        print(f"   - Avec livreur assigné: {merchant_with_livreur}")
        print(f"   - Sans livreur: {len(merchant_orders) - merchant_with_livreur}")
        
        print(f"🏢 Commandes admin livrées: {len(admin_orders)}")
        print(f"   - Avec livreur assigné: {admin_with_livreur}")
        print(f"   - Sans livreur: {len(admin_orders) - admin_with_livreur}")

if __name__ == "__main__":
    print("🚀 Script de migration des commandes livrées")
    print("=" * 50)
    
    # Vérifier l'état avant migration
    check_delivered_orders_status()
    
    # Demander confirmation
    response = input("\n❓ Voulez-vous procéder à la migration ? (y/N): ")
    if response.lower() in ['y', 'yes', 'oui']:
        success = migrate_delivered_orders()
        if success:
            # Vérifier l'état après migration
            check_delivered_orders_status()
    else:
        print("❌ Migration annulée")
