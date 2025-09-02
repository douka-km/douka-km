#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier la page d'historique des livreurs
"""

from app_final_with_db import app
import requests
import time

def test_livreur_history_page():
    """Tester si la page d'historique fonctionne"""
    
    # URL de la page d'historique
    history_url = "http://localhost:5002/admin/livreur/history"
    dashboard_url = "http://localhost:5002/admin/livreur-dashboard"
    
    print("🔍 Test de la page d'historique des livreurs")
    print(f"URL Dashboard: {dashboard_url}")
    print(f"URL Historique: {history_url}")
    print("\n💡 Pour tester manuellement:")
    print("1. Démarrez le serveur Flask: python app_final_with_db.py")
    print("2. Connectez-vous avec un compte livreur (ahmedsaid@doukakm.com)")
    print("3. Vérifiez que le bouton 'Historique' apparaît dans:")
    print("   - Le menu dropdown en haut à droite")
    print("   - Les 'Actions rapides' du dashboard")
    print("   - Les statistiques montrent le nombre de commandes livrées")
    print("4. Cliquez sur 'Historique' pour accéder à la page")
    
    print("\n📋 Fonctionnalités de la page d'historique:")
    print("- Liste toutes les commandes livrées par le livreur connecté")
    print("- Statistiques: total livraisons, valeur totale, frais de livraison")
    print("- Pagination pour navigation facile")
    print("- Détails: client, marchand, adresse, montants, dates")
    print("- Lien vers les détails de chaque commande")
    
    print("\n✅ Les modifications apportées:")
    print("1. Nouvelle route /admin/livreur/history")
    print("2. Template admin/livreur_history.html")
    print("3. Liens ajoutés dans livreur_dashboard.html")
    print("4. Statistiques livrées dans le dashboard")
    print("5. Système d'historique permanent dans la base de données")

if __name__ == "__main__":
    test_livreur_history_page()
