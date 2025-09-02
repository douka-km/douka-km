#!/usr/bin/env python3
"""
Script pour sauvegarder et restaurer la base de données SQLite
"""

import os
import shutil
from datetime import datetime

def backup_sqlite():
    """Créer une sauvegarde de la base SQLite"""
    sqlite_path = "douka_km.db"
    instance_sqlite_path = "instance/douka_km.db"
    
    # Créer le dossier de sauvegarde s'il n'existe pas
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Nom de fichier avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Vérifier quel fichier existe
    source_file = None
    if os.path.exists(sqlite_path):
        source_file = sqlite_path
    elif os.path.exists(instance_sqlite_path):
        source_file = instance_sqlite_path
    
    if source_file:
        backup_file = f"{backup_dir}/douka_km_backup_{timestamp}.db"
        shutil.copy2(source_file, backup_file)
        print(f"✅ Sauvegarde créée: {backup_file}")
        print(f"📄 Taille: {os.path.getsize(backup_file)} bytes")
    else:
        print("❌ Aucune base de données SQLite trouvée")

def list_backups():
    """Lister les sauvegardes disponibles"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        print("📁 Aucune sauvegarde trouvée")
        return
    
    backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
    if backups:
        print("📁 Sauvegardes disponibles:")
        for i, backup in enumerate(sorted(backups, reverse=True), 1):
            backup_path = os.path.join(backup_dir, backup)
            size = os.path.getsize(backup_path)
            mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
            print(f"  {i}. {backup} ({size} bytes, {mtime.strftime('%d/%m/%Y %H:%M')})")
    else:
        print("📁 Aucune sauvegarde trouvée")

def main():
    """Menu principal"""
    print("=== GESTIONNAIRE DE SAUVEGARDES SQLITE ===")
    print()
    
    print("Choisissez une option :")
    print("1. Créer une sauvegarde de la base SQLite")
    print("2. Lister les sauvegardes disponibles")
    print("3. Quitter")
    print()
    
    choice = input("Votre choix (1-3) : ").strip()
    
    if choice == '1':
        backup_sqlite()
    elif choice == '2':
        list_backups()
    elif choice == '3':
        print("Au revoir !")
    else:
        print("❌ Choix invalide")

if __name__ == "__main__":
    main()
