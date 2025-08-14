#!/usr/bin/env python3
"""
Script de nettoyage final du projet DOUKA KM
Supprime tous les fichiers inutiles et optimise pour la production
"""
import os
import shutil
import glob

def clean_project():
    """Nettoyer le projet pour la production"""
    
    print("🧹 NETTOYAGE FINAL DU PROJET DOUKA KM")
    print("="*60)
    
    # Fichiers et dossiers à supprimer
    files_to_remove = [
        # Fichiers de cache Python
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        
        # Fichiers temporaires
        "*.tmp",
        "*.temp",
        "*.log",
        "*.bak",
        "*.swp",
        "*.swo",
        
        # Fichiers OS
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        
        # Fichiers de développement
        "*.orig",
        "*.rej",
        "*~",
    ]
    
    dirs_to_remove = [
        "__pycache__",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        ".tox",
        ".cache",
        "node_modules",
        ".sass-cache",
        "dist",
        "build",
        "*.egg-info",
    ]
    
    removed_count = 0
    
    # Supprimer les fichiers
    print("🗑️  Suppression des fichiers temporaires...")
    for pattern in files_to_remove:
        for filepath in glob.glob(pattern, recursive=True):
            if os.path.isfile(filepath):
                os.remove(filepath)
                removed_count += 1
                print(f"  ✅ Supprimé: {filepath}")
    
    # Supprimer les dossiers
    print("🗑️  Suppression des dossiers temporaires...")
    for pattern in dirs_to_remove:
        for dirpath in glob.glob(pattern, recursive=True):
            if os.path.isdir(dirpath):
                shutil.rmtree(dirpath)
                removed_count += 1
                print(f"  ✅ Supprimé: {dirpath}/")
    
    # Parcourir récursivement pour nettoyer
    for root, dirs, files in os.walk('.'):
        # Ignorer les dossiers spéciaux
        if any(skip in root for skip in ['.git', 'static', 'templates', 'venv', 'env']):
            continue
            
        # Nettoyer les fichiers
        for file in files:
            filepath = os.path.join(root, file)
            
            # Supprimer les fichiers de cache Python
            if file.endswith(('.pyc', '.pyo', '.pyd')) or file.startswith('.'):
                if file not in ['.env.example', '.gitignore']:
                    try:
                        os.remove(filepath)
                        removed_count += 1
                        print(f"  ✅ Supprimé: {filepath}")
                    except:
                        pass
        
        # Nettoyer les dossiers
        for dir_name in dirs[:]:  # Copie pour éviter les modifications pendant l'itération
            if dir_name.startswith('.') and dir_name not in ['.git']:
                dirpath = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(dirpath)
                    dirs.remove(dir_name)
                    removed_count += 1
                    print(f"  ✅ Supprimé: {dirpath}/")
                except:
                    pass
    
    print(f"\n📊 RÉSUMÉ DU NETTOYAGE:")
    print(f"🗑️  {removed_count} éléments supprimés")
    
    # Lister les fichiers finaux
    print(f"\n📁 FICHIERS RESTANTS:")
    for root, dirs, files in os.walk('.'):
        if root == '.':
            for file in sorted(files):
                if not file.startswith('.'):
                    size = os.path.getsize(file)
                    size_str = f"{size:,} bytes" if size < 1024 else f"{size//1024:,} KB"
                    print(f"  📄 {file} ({size_str})")
            
            for dir_name in sorted(dirs):
                if not dir_name.startswith('.'):
                    print(f"  📁 {dir_name}/")
            break
    
    print(f"\n🎉 PROJET NETTOYÉ POUR LA PRODUCTION!")
    print(f"✅ Prêt pour le déploiement sur Render.com")

if __name__ == '__main__':
    clean_project()
