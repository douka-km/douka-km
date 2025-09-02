#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour créer quelques commandes livrées pour tester l'historique
"""

from app_final_with_db import app, db
from models import Order, Employee
from datetime import datetime, timedelta

def create_test_delivered_orders():
    """Créer quelques commandes livrées pour tester l'historique"""
    with app.app_context():
        try:
            # Trouver un employé livreur
            livreur = Employee.query.filter_by(role='livreur').first()
            if not livreur:
                print("❌ Aucun employé livreur trouvé")
                return
            
            print(f"📦 Test avec le livreur: {livreur.first_name} {livreur.last_name} ({livreur.email})")
            
            # Créer 3 commandes test livrées
            for i in range(3):
                # Trouver une commande existante sans livreur assigné
                order = Order.query.filter(
                    Order.delivery_employee_email.is_(None),
                    Order.status != 'delivered'
                ).first()
                
                if order:
                    # Assigner le livreur
                    order.delivery_employee_id = livreur.id
                    order.delivery_employee_email = livreur.email
                    order.delivery_employee_name = f"{livreur.first_name} {livreur.last_name}"
                    order.delivery_employee_phone = livreur.phone
                    order.assigned_at = datetime.now() - timedelta(days=i+1)
                    
                    # Marquer comme livrée
                    order.status = 'delivered'
                    order.delivery_date = datetime.now() - timedelta(hours=i*2)
                    
                    print(f"✅ Commande #{order.id} assignée et marquée comme livrée")
                else:
                    print(f"⚠️  Pas de commande disponible pour test #{i+1}")
            
            db.session.commit()
            print("🎉 Commandes test créées avec succès!")
            
            # Afficher le résumé
            delivered_count = Order.query.filter_by(
                delivery_employee_email=livreur.email,
                status='delivered'
            ).count()
            print(f"📊 Total commandes livrées par {livreur.first_name}: {delivered_count}")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_test_delivered_orders()
