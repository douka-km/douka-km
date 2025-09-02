#!/usr/bin/env python3
"""
Script pour basculer entre SQLite local et PostgreSQL de Render
"""

import os
import sys

def switch_to_sqlite():
    """Basculer vers SQLite local"""
    env_content = """# Configuration de la base de données - SQLite LOCAL
DATABASE_URL=sqlite:///instance/douka_km.db

# Autres variables d'environnement
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Configuration basculée vers SQLite LOCAL")
    print("📄 Fichier .env mis à jour")
    print("🔄 Redémarrez l'application pour appliquer les changements")

def switch_to_postgresql():
    """Basculer vers PostgreSQL de Render"""
    print("🔗 Pour utiliser PostgreSQL de Render, vous devez :")
    print("1. Aller sur https://dashboard.render.com")
    print("2. Sélectionner votre service PostgreSQL")
    print("3. Copier l'URL de connexion (External Database URL)")
    print("4. Coller l'URL ci-dessous")
    print()
    
    database_url = input("Collez l'URL PostgreSQL de Render : ").strip()
    
    if not database_url:
        print("❌ URL vide. Opération annulée.")
        return
    
    if not database_url.startswith(('postgres://', 'postgresql://')):
        print("❌ URL invalide. Elle doit commencer par 'postgres://' ou 'postgresql://'")
        return
    
    env_content = f"""# Configuration de la base de données - PostgreSQL RENDER
DATABASE_URL={database_url}

# Autres variables d'environnement
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Configuration basculée vers PostgreSQL RENDER")
    print("📄 Fichier .env mis à jour")
    print("🔄 Redémarrez l'application pour appliquer les changements")
    print()
    print("⚠️  ATTENTION: Vous travaillez maintenant sur la base de données de PRODUCTION!")

def show_current_config():
    """Afficher la configuration actuelle"""
    if os.path.exists('.env'):
        print("📄 Configuration actuelle (.env):")
        print("-" * 50)
        with open('.env', 'r') as f:
            content = f.read()
            # Masquer les mots de passe dans l'affichage
            lines = content.split('\n')
            for line in lines:
                if line.startswith('DATABASE_URL=') and '@' in line:
                    # Masquer le mot de passe
                    parts = line.split('@')
                    if len(parts) == 2:
                        before_at = parts[0]
                        after_at = parts[1]
                        if ':' in before_at:
                            user_pass = before_at.split(':')
                            if len(user_pass) >= 3:
                                masked = ':'.join(user_pass[:-1]) + ':****'
                                print(f"{masked}@{after_at}")
                            else:
                                print(line)
                        else:
                            print(line)
                    else:
                        print(line)
                else:
                    print(line)
        print("-" * 50)
    else:
        print("📄 Aucun fichier .env trouvé (utilise SQLite par défaut)")

def main():
    """Menu principal"""
    print("=== GESTIONNAIRE DE BASE DE DONNÉES DOUKA KM ===")
    print()
    
    show_current_config()
    print()
    
    print("Choisissez une option :")
    print("1. Basculer vers SQLite LOCAL")
    print("2. Basculer vers PostgreSQL RENDER")
    print("3. Afficher la configuration actuelle")
    print("4. Quitter")
    print()
    
    choice = input("Votre choix (1-4) : ").strip()
    
    if choice == '1':
        switch_to_sqlite()
    elif choice == '2':
        switch_to_postgresql()
    elif choice == '3':
        show_current_config()
    elif choice == '4':
        print("Au revoir !")
        sys.exit(0)
    else:
        print("❌ Choix invalide")
        sys.exit(1)

if __name__ == "__main__":
    main()
