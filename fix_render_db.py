#!/usr/bin/env python3
"""
Script pour corriger la base de données sur Render.com
Ajoute les colonnes 'updated_at' manquantes aux tables categories et subcategories
"""
import os
import sys
from datetime import datetime

# S'assurer qu'on est en mode production
os.environ['RENDER'] = '1'

def fix_render_database():
    """Corrige la base de données sur Render en ajoutant les colonnes manquantes"""
    print("🔧 Correction de la base de données...")
    
    try:
        from app_final_with_db import app, db
        from models import Category, Subcategory
        from sqlalchemy import text, inspect
        
        with app.app_context():
            # Détecter le type de base de données
            engine = db.engine
            db_dialect = engine.dialect.name
            print(f"📊 Type de base de données détecté: {db_dialect}")
            
            # Utiliser l'inspecteur SQLAlchemy pour une approche plus générique
            inspector = inspect(engine)
            
            # Vérifier les tables existantes
            tables = inspector.get_table_names()
            print(f"Tables existantes: {tables}")
            
            # Fonction pour vérifier et ajouter une colonne
            def add_column_if_missing(table_name, column_name, column_type="TIMESTAMP"):
                try:
                    columns = inspector.get_columns(table_name)
                    column_names = [col['name'] for col in columns]
                    print(f"Colonnes de '{table_name}': {column_names}")
                    
                    if column_name not in column_names:
                        print(f"➕ Ajout de la colonne '{column_name}' à la table '{table_name}'...")
                        
                        # Adapter la syntaxe selon le type de DB
                        if db_dialect == 'postgresql':
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                        elif db_dialect == 'sqlite':
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} DATETIME DEFAULT CURRENT_TIMESTAMP"
                        else:
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                        
                        db.session.execute(text(sql))
                        print(f"✅ Colonne '{column_name}' ajoutée à '{table_name}'")
                        return True
                    else:
                        print(f"✅ Colonne '{column_name}' déjà présente dans '{table_name}'")
                        return False
                        
                except Exception as e:
                    print(f"⚠️ Erreur avec la table {table_name}: {e}")
                    return False
            
            # Ajouter les colonnes manquantes
            changes_made = False
            
            if 'categories' in tables:
                if add_column_if_missing('categories', 'updated_at'):
                    changes_made = True
            else:
                print("⚠️ Table 'categories' non trouvée")
            
            if 'subcategories' in tables:
                if add_column_if_missing('subcategories', 'updated_at'):
                    changes_made = True
            else:
                print("⚠️ Table 'subcategories' non trouvée")
            
            # Commiter les changements seulement si nécessaire
            if changes_made:
                db.session.commit()
                print("💾 Changements sauvegardés")
            else:
                print("✅ Aucune modification nécessaire")
            
            # Tester l'accès aux catégories
            print("🧪 Test d'accès aux catégories...")
            categories = Category.query.all()
            print(f"✅ {len(categories)} catégories trouvées")
            
            subcategories = Subcategory.query.all()
            print(f"✅ {len(subcategories)} sous-catégories trouvées")
            
            print("🎉 Base de données corrigée avec succès!")
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la correction: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def create_sample_categories():
    """Crée quelques catégories d'exemple si aucune n'existe"""
    try:
        from app_final_with_db import app, db
        from models import Category, Subcategory
        
        with app.app_context():
            # Vérifier si des catégories existent déjà
            if Category.query.count() == 0:
                print("📝 Création de catégories d'exemple...")
                
                # Catégories d'exemple pour les Comores
                sample_categories = [
                    {"name": "Alimentation", "description": "Produits alimentaires locaux et importés", "icon": "fas fa-apple-alt"},
                    {"name": "Vêtements", "description": "Mode et accessoires", "icon": "fas fa-tshirt"},
                    {"name": "Électronique", "description": "Appareils électroniques et gadgets", "icon": "fas fa-mobile-alt"},
                    {"name": "Maison & Jardin", "description": "Articles pour la maison et le jardin", "icon": "fas fa-home"},
                    {"name": "Santé & Beauté", "description": "Produits de santé et cosmétiques", "icon": "fas fa-heart"}
                ]
                
                created_count = 0
                for cat_data in sample_categories:
                    try:
                        category = Category(
                            name=cat_data["name"],
                            description=cat_data["description"],
                            icon=cat_data["icon"],
                            active=True,
                            created_by="system@doukakm.com"
                        )
                        db.session.add(category)
                        created_count += 1
                    except Exception as e:
                        print(f"⚠️ Erreur création catégorie {cat_data['name']}: {e}")
                
                db.session.commit()
                print(f"✅ {created_count} catégories d'exemple créées")
            else:
                print(f"✅ {Category.query.count()} catégories déjà présentes")
                
    except Exception as e:
        print(f"❌ Erreur lors de la création des catégories d'exemple: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage de la correction de la base de données Render...")
    
    if fix_render_database():
        create_sample_categories()
        print("🎉 Correction terminée avec succès!")
        sys.exit(0)
    else:
        print("❌ Échec de la correction")
        sys.exit(1)
