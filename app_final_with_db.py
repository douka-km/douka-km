from flask import Flask, render_template, request, session, send_from_directory, redirect, url_for, flash, jsonify
import os
import json
import hashlib
import functools
from datetime import datetime, timedelta
import random
import uuid
import re
import secrets
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib

# Configuration pour les variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# Ajouter ces imports en haut du fichier
from email_config import send_email, CURRENT_EMAIL_CONFIG

# Import des modèles de base de données
from models import db, User, Merchant, Product, Category, Subcategory, Order, OrderItem, Cart, CartItem, WishlistItem

# Imports pour la base de données
from models import db, User, Merchant, Admin, Product, Order, OrderItem, Review, Category, Subcategory, PromoCode, WithdrawalRequest, WishlistItem, EmailVerificationToken, PasswordResetToken, SiteSettings, Employee, Address, CategoryCommissionRate
from db_helpers import *

# =============================================
# FONCTIONS DE NOTIFICATION ADMIN
# =============================================

def send_admin_notification_new_order(order):
    """Envoie une notification email à l'admin pour une nouvelle commande"""
    try:
        # Récupérer l'email admin depuis la configuration ou utiliser l'email par défaut
        admin_email = os.environ.get('ADMIN_EMAIL', 'ledouka.km@gmail.com')
        
        # Construire l'URL de base pour l'admin
        base_url = CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']
        admin_url = f"{base_url}/admin"
        
        # Préparer les données de la commande pour le template
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'created_at': order.created_at.strftime('%d/%m/%Y à %H:%M'),
            'customer_name': order.customer_name,
            'customer_email': order.customer_email,
            'customer_phone': order.customer_phone,
            'status': order.status.title(),
            'total': order.total,
            'subtotal': order.total - order.shipping_fee + order.discount,
            'shipping_fee': order.shipping_fee,
            'discount': order.discount,
            'promo_code': order.promo_code,
            'shipping_method': order.shipping_method,
            'payment_method': order.payment_method,
            'merchant_email': getattr(order.merchant, 'email', None) if order.merchant else None,
            'shipping_address': {
                'full_name': order.shipping_address_line1 or order.customer_name,
                'street': order.shipping_address_line1 or '',
                'city': order.shipping_address_city or '',
                'region': order.shipping_address_region or '',
                'phone': order.customer_phone or ''
            },
            'items': []
        }
        
        # Ajouter les articles de la commande
        for item in order.items:
            order_data['items'].append({
                'name': item.name,
                'price': item.price,
                'quantity': item.quantity,
                'variant_details': item.variant_details or ''
            })
        
        # Rendre le template HTML
        html_content = render_template('emails/admin_new_order.html', 
                                     order=order_data, 
                                     admin_url=admin_url)
        
        # Contenu texte alternatif
        text_content = f"""
Nouvelle commande reçue - DOUKA KM

Numéro de commande: {order_data['order_number']}
Client: {order_data['customer_name']} ({order_data['customer_email']})
Total: {order_data['total']:,.0f} KMF
Statut: {order_data['status']}

Connectez-vous à votre panneau d'administration pour gérer cette commande:
{admin_url}/orders/{order_data['id']}
        """
        
        # Envoyer l'email
        subject = f"🛍️ Nouvelle commande #{order_data['order_number']} - {order_data['total']:,.0f} KMF"
        
        success = send_email(admin_email, subject, html_content, text_content)
        
        if success:
            print(f"✅ Notification admin envoyée pour la commande #{order_data['order_number']}")
        else:
            print(f"❌ Échec envoi notification admin pour la commande #{order_data['order_number']}")
            
        return success
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de notification admin (commande): {str(e)}")
        return False

def send_admin_notification_new_merchant(merchant):
    """Envoie une notification email à l'admin pour un nouveau compte marchand"""
    try:
        # Récupérer l'email admin depuis la configuration ou utiliser l'email par défaut
        admin_email = os.environ.get('ADMIN_EMAIL', 'ledouka.km@gmail.com')
        
        # Construire l'URL de base pour l'admin
        base_url = CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']
        admin_url = f"{base_url}/admin"
        
        # Préparer les données du marchand pour le template
        merchant_data = {
            'id': merchant.id,
            'email': merchant.email,
            'first_name': merchant.first_name,
            'last_name': merchant.last_name,
            'phone': merchant.phone,
            'store_name': merchant.store_name,
            'store_description': merchant.store_description,
            'store_address': merchant.store_address,
            'store_city': merchant.store_city,
            'store_region': merchant.store_region,
            'latitude': merchant.latitude,
            'longitude': merchant.longitude,
            'created_at': merchant.created_at.strftime('%d/%m/%Y à %H:%M'),
            'bank_info': None
        }
        
        # Récupérer les informations bancaires si disponibles
        if hasattr(merchant, 'get_bank_info'):
            bank_info = merchant.get_bank_info()
            if bank_info:
                merchant_data['bank_info'] = bank_info
        
        # Rendre le template HTML
        html_content = render_template('emails/admin_new_merchant.html', 
                                     merchant=merchant_data, 
                                     admin_url=admin_url)
        
        # Contenu texte alternatif
        text_content = f"""
Nouveau compte marchand - DOUKA KM

Marchand: {merchant_data['first_name']} {merchant_data['last_name']}
Email: {merchant_data['email']}
Boutique: {merchant_data['store_name']}
Téléphone: {merchant_data['phone']}
Date d'inscription: {merchant_data['created_at']}

Ce compte nécessite votre vérification avant de pouvoir vendre sur la plateforme.

Connectez-vous à votre panneau d'administration pour examiner ce compte:
{admin_url}/merchants/{merchant_data['id']}
        """
        
        # Envoyer l'email
        subject = f"🏪 Nouveau marchand inscrit: {merchant_data['store_name']}"
        
        success = send_email(admin_email, subject, html_content, text_content)
        
        if success:
            print(f"✅ Notification admin envoyée pour le nouveau marchand: {merchant_data['email']}")
        else:
            print(f"❌ Échec envoi notification admin pour le marchand: {merchant_data['email']}")
            
        return success
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de notification admin (marchand): {str(e)}")
        return False

app = Flask(__name__)

# Configuration pour la production
if os.environ.get('RENDER'):
    # Configuration pour Render.com
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Gestion adaptative de la base de données PostgreSQL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Adapter l'URL pour la version de psycopg utilisée
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://')
        # S'assurer que l'URL utilise psycopg v3
        elif database_url.startswith('postgresql://') and '+psycopg' not in database_url:
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
        
        print(f"🔗 Database URL configurée: {database_url[:50]}...")
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///douka_km.db'
    
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
else:
    # Configuration pour développement local
    app.config['SECRET_KEY'] = 'dev_secret_key_change_in_production'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "douka_km.db")}'
    app.config['DEBUG'] = True

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration des uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialiser SQLAlchemy
db.init_app(app)

# =============================================
# FONCTIONS DE COMPATIBILITÉ POUR LA MIGRATION
# =============================================

# Dictionnaires temporaires pour fonctionnalités non migrées
verification_tokens_db = {}
password_reset_tokens_db = {}
withdrawal_requests_db = {}

# Variables globales simulées - seront initialisées dans le contexte de l'application
users_db = {}
merchants_db = {}
employees_db = {}
admin_categories_db = {}
admin_subcategories_db = {}
promo_codes_db = {}
site_settings = {}

def initialize_db_proxies():
    """Initialiser les proxies de base de données dans le contexte de l'application"""
    global users_db, merchants_db, employees_db, admin_categories_db, admin_subcategories_db, promo_codes_db, site_settings
    
    # Vérifier si on est en production
    is_production = os.environ.get('RENDER') == '1'
    
    if is_production:
        print("MODE PRODUCTION: Chargement uniquement depuis la base de données")
    else:
        print("MODE DÉVELOPPEMENT: Chargement avec données de test")
    
    try:
        # S'assurer que la session est propre
        try:
            db.session.rollback()
        except Exception:
            pass
            
        # En production, ne pas charger les données de test du code
        if is_production:
            # PRODUCTION: Charger uniquement depuis la base de données avec gestion d'erreur
            try:
                users_db_from_db = {}
                users = User.query.all()
                for user in users:
                    users_db_from_db[user.email] = user.to_dict()
                
                # Remplacer complètement users_db avec les données de la DB
                users_db.clear()
                users_db.update(users_db_from_db)
                print(f"Utilisateurs chargés: {len(users_db)}")
                
            except Exception as users_error:
                print(f"Erreur lors du chargement des utilisateurs: {users_error}")
                # Rollback et continuer
                try:
                    db.session.rollback()
                except Exception:
                    pass
            
        else:
            # DÉVELOPPEMENT: Conserver les utilisateurs définis dans le code
            
            # Charger les utilisateurs depuis la base de données ET conserver ceux du code
            existing_users = dict(users_db)  # Sauvegarder les utilisateurs du code
            users_db_from_db = {}
            users = User.query.all()
            for user in users:
                users_db_from_db[user.email] = user.to_dict()
            
            # Fusionner : utilisateurs du code + utilisateurs de la base de données
            # Les utilisateurs du code ont la priorité (écrasent ceux de la DB si même email)
            users_db.update(users_db_from_db)  # D'abord ceux de la DB
            users_db.update(existing_users)    # Puis ceux du code (priorité)
        
        # Gestion des marchands selon l'environnement
        if is_production:
            # PRODUCTION: Charger uniquement depuis la base de données
            merchants_db_from_db = {}
            
            merchants = Merchant.query.all()
            for merchant in merchants:
                merchant_dict = merchant.to_dict()
                
                # Mapper le statut de la base de données vers le format attendu
                merchant_dict['account_suspended'] = (merchant_dict['status'] == 'suspended')
                
                # Charger les produits de ce marchand depuis la base de données
                merchant_products = Product.query.filter_by(merchant_id=merchant.id).all()
                merchant_dict['products'] = []
                
                for product in merchant_products:
                    product_dict = product.to_dict()
                    product_dict['merchant_email'] = merchant.email  # Ajouter l'email pour compatibilité
                    merchant_dict['products'].append(product_dict)
                
                # Initialiser les commandes (sera implémenté plus tard)
                if 'orders' not in merchant_dict:
                    merchant_dict['orders'] = []
                
                merchants_db_from_db[merchant.email] = merchant_dict
            
            # Remplacer complètement merchants_db avec les données de la DB
            merchants_db.clear()
            merchants_db.update(merchants_db_from_db)
            
        else:
            # DÉVELOPPEMENT: Conserver les marchands du code
            
            # Sauvegarder les marchands existants du code
            existing_merchants = dict(merchants_db)
            merchants_db_from_db = {}
            
            merchants = Merchant.query.all()
            for merchant in merchants:
                merchant_dict = merchant.to_dict()
                
                # Mapper le statut de la base de données vers le format attendu
                merchant_dict['account_suspended'] = (merchant_dict['status'] == 'suspended')
                
                # Charger les produits de ce marchand depuis la base de données
                merchant_products = Product.query.filter_by(merchant_id=merchant.id).all()
                merchant_dict['products'] = []
                
                for product in merchant_products:
                    product_dict = product.to_dict()
                    product_dict['merchant_email'] = merchant.email  # Ajouter l'email pour compatibilité
                    merchant_dict['products'].append(product_dict)
                
                # Initialiser les commandes (sera implémenté plus tard)
                if 'orders' not in merchant_dict:
                    merchant_dict['orders'] = []
                
                merchants_db_from_db[merchant.email] = merchant_dict
            
            # Fusionner : marchands de la DB + marchands du code (code a priorité)
            merchants_db.clear()  # Vider d'abord
            merchants_db.update(merchants_db_from_db)  # D'abord ceux de la DB
            merchants_db.update(existing_merchants)    # Puis ceux du code (priorité)

        
        # Simulation de employees_db - Charger depuis Admin ET Employee
        existing_employees = dict(employees_db) if 'employees_db' in globals() else {}
        employees_db = {}
        
        # Charger les admins
        admins = Admin.query.all()
        for admin in admins:
            employees_db[admin.email] = admin.to_dict()
        
        # Charger les employés depuis la table Employee
        db_employees = Employee.query.all()
        for employee in db_employees:
            employees_db[employee.email] = employee.to_dict()
            
        # Fusionner avec les employés existants du code (code a priorité)
        employees_db.update(existing_employees)
        
        total_admins = len(admins)
        total_employees = len(db_employees)
        
        # Simulation de admin_categories_db
        admin_categories_db = {}
        try:
            # S'assurer que la session est propre
            try:
                db.session.rollback()
            except Exception:
                pass
            
            from db_helpers import get_all_categories_safe
            categories = get_all_categories_safe()
            for category in categories:
                admin_categories_db[category.id] = category.to_dict()
            print(f"Catégories chargées: {len(admin_categories_db)}")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des catégories: {e}")
            # Rollback en cas d'erreur de transaction
            try:
                db.session.rollback()
            except Exception:
                pass
            print("💡 Les catégories seront chargées après la correction de la base de données")

        # Simulation de admin_subcategories_db
        admin_subcategories_db = {}
        try:
            from db_helpers import get_all_subcategories_safe
            subcategories = get_all_subcategories_safe()
            for subcat in subcategories:
                admin_subcategories_db[subcat.id] = subcat.to_dict()
            print(f"Sous-catégories chargées: {len(admin_subcategories_db)}")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des sous-catégories: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            print("💡 Les sous-catégories seront chargées après la correction de la base de données")
        
        # Simulation de promo_codes_db
        promo_codes_db = {}
        try:
            promo_codes = PromoCode.query.all()
            for promo in promo_codes:
                promo_codes_db[promo.code] = promo.to_dict()
            print(f"Codes promo chargés: {len(promo_codes_db)}")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des codes promo: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
        
        # Simulation de site_settings
        site_settings = get_all_site_settings()
        
        # **GESTION DES AVIS SELON L'ENVIRONNEMENT**
        global reviews_db
        reviews_db_from_db = []
        reviews = Review.query.all()
        for review in reviews:
            review_dict = review.to_dict()
            reviews_db_from_db.append(review_dict)
        
        if is_production:
            # PRODUCTION: Avis uniquement depuis la base de données
            reviews_db = list(reviews_db_from_db)
            
        else:
            # DÉVELOPPEMENT: Fusionner avis code + base de données
            # Créer une copie des avis existants du code
            existing_reviews = list(reviews_db) if isinstance(reviews_db, list) else []
            
            # Fusionner intelligemment : avis de la DB + avis du code (éviter doublons)
            existing_titles = {r.get('title') for r in existing_reviews if r.get('title')}
            existing_db_ids = {r.get('id') for r in reviews_db_from_db}
            
            # D'abord ajouter tous les avis de la base de données
            merged_reviews = list(reviews_db_from_db)
            
            # Ensuite ajouter les avis du code qui ne sont pas déjà en base
            for review_code in existing_reviews:
                title = review_code.get('title', '')
                # Ne pas ajouter si c'est un doublon basé sur le titre
                if title and title not in {r.get('title') for r in merged_reviews}:
                    # Ajuster l'ID pour éviter les conflits
                    max_id = max(existing_db_ids) if existing_db_ids else 0
                    review_code['id'] = max_id + len([r for r in merged_reviews if r.get('id', 0) > max_id]) + 1
                    merged_reviews.append(review_code)
            
            reviews_db = merged_reviews
    
        # **NOUVELLE FONCTIONNALITÉ: Charger les demandes de retrait depuis la base de données**
        global withdrawal_requests_db
        try:
            withdrawal_records = WithdrawalRequest.query.all()
            
            # Organiser les demandes par email de marchand pour compatibilité
            for withdrawal in withdrawal_records:
                merchant = Merchant.query.filter_by(id=withdrawal.merchant_id).first()
                if merchant:
                    merchant_email = merchant.email
                    if merchant_email not in withdrawal_requests_db:
                        withdrawal_requests_db[merchant_email] = []
                    
                    # Convertir en dictionnaire pour compatibilité
                    withdrawal_dict = withdrawal.to_dict()
                    withdrawal_dict['merchant_email'] = merchant_email
                    withdrawal_requests_db[merchant_email].append(withdrawal_dict)
            
            total_withdrawals = sum(len(requests) for requests in withdrawal_requests_db.values())
            print(f"✅ Chargé {total_withdrawals} demandes de retrait depuis la base de données")
            
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des demandes de retrait: {e}")

        # **NOUVEAU: Nettoyer les anciens tokens de vérification expirés**
        try:
            expired_count = cleanup_expired_verification_tokens()
            if expired_count > 0:
                print(f"🧹 {expired_count} tokens de vérification expirés nettoyés au démarrage")
        except Exception as e:
            print(f"⚠️ Erreur lors du nettoyage des tokens expirés: {e}")
        
    except Exception as e:
        print(f"⚠️ Attention: Erreur lors de l'initialisation des proxies DB: {e}")
        print(f"📍 Traceback complet: {traceback.format_exc()}")
        print("💡 L'application utilisera des dictionnaires vides temporairement")

def reload_categories_and_subcategories():
    """Recharge les catégories et sous-catégories après correction de la base de données"""
    global admin_categories_db, admin_subcategories_db
    
    try:
        # Recharger les catégories
        admin_categories_db = {}
        from db_helpers import get_all_categories_safe
        categories = get_all_categories_safe()
        for category in categories:
            admin_categories_db[category.id] = category.to_dict()
        print(f"✅ {len(categories)} catégories rechargées avec succès")
        
        # Recharger les sous-catégories
        admin_subcategories_db = {}
        from db_helpers import get_all_subcategories_safe
        subcategories = get_all_subcategories_safe()
        for subcat in subcategories:
            admin_subcategories_db[subcat.id] = subcat.to_dict()
        print(f"✅ {len(subcategories)} sous-catégories rechargées avec succès")
        
    except Exception as e:
        print(f"❌ Erreur lors du rechargement des catégories: {e}")

def get_all_site_settings():
    """Récupère tous les paramètres du site depuis la base de données"""
    try:
        site_settings = {}
        settings_records = SiteSettings.query.all()
        
        for setting in settings_records:
            # Convertir la valeur selon le type
            value = setting.value
            if value and setting.key in ['commission_rate', 'shipping_fee', 'default_shipping_fee', 'free_shipping_threshold']:
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    pass
            elif value and setting.key in ['shipping_rates', 'shipping_price_ranges']:
                try:
                    import json
                    value = json.loads(value)
                except (ValueError, TypeError):
                    pass
            
            site_settings[setting.key] = value
        
        # Valeurs par défaut si la base est vide
        if not site_settings:
            return {
                'site_name': 'DOUKA KM',
                'site_description': "La première plateforme de commerce aux Comores. Connectant acheteurs et vendeurs à travers l'archipel.",
                'contact_email': 'ledouka.km@gmail.com',
                'contact_phone': '+269 342 40 19',
                'commission_rate': 15.0,
                'shipping_fee': 2000,
                'default_shipping_fee': 2000,
                'free_shipping_threshold': 50000,
                'logo_url': '/static/img/logo.svg',
                'logo_alt_text': 'DOUKA KM - Marketplace des Comores'
            }
        
        # Ajouter les valeurs manquantes importantes
        defaults = {
            'site_name': 'DOUKA KM',
            'site_description': "La première plateforme de commerce aux Comores. Connectant acheteurs et vendeurs à travers l'archipel.",
            'contact_email': 'ledouka.km@gmail.com',
            'contact_phone': '+269 342 40 19',
            'commission_rate': 15.0,
            'shipping_fee': 2000,
            'default_shipping_fee': 2000,
            'free_shipping_threshold': 50000,
            'logo_url': '/static/img/logo.svg',
            'logo_alt_text': 'DOUKA KM - Marketplace des Comores'
        }
        
        # Ajouter les valeurs par défaut pour les clés manquantes
        for key, default_value in defaults.items():
            if key not in site_settings or site_settings[key] is None or site_settings[key] == '':
                site_settings[key] = default_value
        
        return site_settings
        
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement des paramètres: {e}")
        # Retourner des paramètres par défaut
        return {
            'site_name': 'DOUKA KM',
            'site_description': "La première plateforme de commerce aux Comores. Connectant acheteurs et vendeurs à travers l'archipel",
            'contact_email': 'ledouka.km@gmail.com',
            'contact_phone': '+269 342 40 19',
            'commission_rate': 15.0,
            'shipping_fee': 2000,
            'default_shipping_fee': 2000,
            'free_shipping_threshold': 50000,
            'logo_url': '/static/img/logo.svg',
            'logo_alt_text': 'DOUKA KM - Marketplace des Comores'
        }

def update_site_setting(key, value, description=None):
    """Met à jour ou crée un paramètre du site dans la base de données"""
    try:
        setting = SiteSettings.query.filter_by(key=key).first()
        
        if setting:
            # Mise à jour
            if isinstance(value, (dict, list)):
                import json
                setting.value = json.dumps(value)
            else:
                setting.value = str(value)
            setting.updated_at = datetime.now()
            if description:
                setting.description = description
        else:
            # Création
            if isinstance(value, (dict, list)):
                import json
                value_str = json.dumps(value)
            else:
                value_str = str(value)
                
            setting = SiteSettings(
                key=key,
                value=value_str,
                description=description
            )
            db.session.add(setting)
        
        db.session.commit()
        
        # Mettre à jour la variable globale
        global site_settings
        site_settings[key] = value
        
        print(f"✅ Paramètre '{key}' mis à jour dans la base de données")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la mise à jour du paramètre '{key}': {str(e)}")
        return False
app.secret_key = 'your_secret_key'  # Needed for session management

# Configuration pour les sessions permanentes ("Se souvenir de moi")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)  # 31 jours

# Base de données pour les tokens de vérification email
verification_tokens_db = {}

# Base de données pour les tokens de récupération de mot de passe
password_reset_tokens_db = {}

# Fonctions utilitaires pour la vérification email
def generate_verification_token():
    """Génère un token de vérification unique"""
    return str(uuid.uuid4())

def send_verification_email(email, token):
    """Envoie un email de vérification réel"""
    # Debug: vérifier la configuration URL
    print(f"🔧 DEBUG: RENDER env = {os.environ.get('RENDER')}")
    print(f"🔧 DEBUG: VERIFICATION_URL_BASE env = {os.environ.get('VERIFICATION_URL_BASE')}")
    print(f"🔧 DEBUG: CURRENT_EMAIL_CONFIG URL = {CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}")
    
    verification_url = f"{CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}/verify-email?token={token}"
    
    # Rendu du template HTML
    html_content = render_template('emails/email_verification.html',
        verification_url=verification_url,
        site_name=get_site_settings().get('site_name', 'DOUKA KM')
    )
    
    # Contenu texte simple (fallback)
    text_content = f"""
Bienvenue sur DOUKA KM !

Pour activer votre compte, cliquez sur ce lien :
{verification_url}

Ce lien expirera dans 24 heures.

Cordialement,
L'équipe DOUKA KM
    """
    
    subject = "Vérification de votre adresse email - DOUKA KM"
    
    # Envoyer l'email réel
    success = send_email(email, subject, html_content, text_content)
    
    if success:
        print(f"✅ Email de vérification envoyé à {email}")
    else:
        print(f"❌ Échec de l'envoi de l'email à {email}")
    
    print(f"================================")
    print(f"URL de vérification: {verification_url}")
    print(f"Token de vérification: {token}")
    return success

def cleanup_expired_verification_tokens():
    """Nettoie les tokens de vérification expirés de la base de données"""
    try:
        expired_count = EmailVerificationToken.query.filter(
            EmailVerificationToken.expires_at < datetime.now()
        ).delete()
        
        db.session.commit()
        
        if expired_count > 0:
            print(f"🧹 {expired_count} tokens de vérification expirés supprimés de la base")
        
        return expired_count
        
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage des tokens expirés: {e}")
        db.session.rollback()
        return 0

def send_order_status_email(customer_email, order_data, old_status, new_status):
    """Envoie un email de notification de changement de statut de commande"""
    
    # Messages selon le statut
    status_messages = {
        'confirmed': {
            'subject': 'Commande confirmée !',
            'message': 'Nous avons bien reçu votre commande et elle est en cours de préparation.',
            'emoji': '✅'
        },
        'processing': {
            'subject': 'Commande en préparation',
            'message': 'Votre commande est actuellement en cours de préparation par nos marchands.',
            'emoji': '⚙️'
        },
        'shipped': {
            'subject': 'Commande expédiée !',
            'message': 'Bonne nouvelle ! Votre commande a été expédiée et est en route vers vous.',
            'emoji': '🚚'
        },
        'delivered': {
            'subject': 'Commande livrée !',
            'message': 'Votre commande a été livrée avec succès. Merci pour votre confiance !',
            'emoji': '📦'
        },
        'cancelled': {
            'subject': 'Commande annulée',
            'message': 'Votre commande a été annulée. Si vous avez des questions, contactez-nous.',
            'emoji': '❌'
        }
    }
    
    status_info = status_messages.get(new_status, {
        'subject': 'Mise à jour de commande',
        'message': f'Le statut de votre commande a été mis à jour : {new_status}',
        'emoji': '📢'
    })
    
    # Préparer les données pour le template
    order_template_data = {
        'id': order_data.get('id', 'N/A'),
        'status': new_status,
        'status_text': new_status.replace('_', ' ').title(),
        'created_at': order_data.get('created_at', 'N/A'),
        'total': order_data.get('total', 0),
        'products': []
    }
    
    # Ajouter les produits si disponibles
    if 'items' in order_data:
        for item in order_data['items']:
            order_template_data['products'].append({
                'name': item.get('name', 'Produit'),
                'quantity': item.get('quantity', 1),
                'price': item.get('price', 0)
            })
    
    try:
        # Utiliser le template HTML existant
        html_content = render_template('emails/order_status_notification.html', 
                                     order=order_template_data, 
                                     status_info=status_info)
        
        # Contenu texte simple (fallback)
        text_content = f"""
{status_info['emoji']} {status_info['subject']}

Bonjour,

{status_info['message']}

Détails de votre commande #{order_template_data['id']}:
- Nouveau statut: {new_status.replace('_', ' ').title()}
- Date de commande: {order_template_data['created_at']}
- Total: {order_template_data['total']:,.0f} KMF

Vous pouvez suivre vos commandes sur votre compte DOUKA KM.

Si vous avez des questions, contactez-nous à ledouka.km@gmail.com

Cordialement,
L'équipe DOUKA KM
        """
        
        # Envoyer l'email
        subject = f"[DOUKA KM] {status_info['emoji']} {status_info['subject']} - Commande #{order_template_data['id']}"
        success = send_email(customer_email, subject, html_content, text_content)
        
        if success:
            print(f"✅ Email de notification envoyé avec succès à {customer_email}")
        else:
            print(f"❌ Échec envoi email de notification à {customer_email}")
            
        return success
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de notification de statut: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_verification_token(email):
    """Crée un token de vérification pour un email - Version DATABASE-FIRST"""
    token = generate_verification_token()
    expires_at = datetime.now() + timedelta(hours=24)
    
    try:
        # **NOUVEAU: Sauvegarder dans la base de données d'abord**
        # Supprimer les anciens tokens pour cet email
        EmailVerificationToken.query.filter_by(email=email).delete()
        
        # Créer le nouveau token en base
        verification_token = EmailVerificationToken(
            token=token,
            email=email,
            expires_at=expires_at,
            used=False
        )
        db.session.add(verification_token)
        db.session.commit()
        
        print(f"✅ Token de vérification sauvegardé en base pour {email}")
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la sauvegarde du token en base pour {email}: {e}")
        db.session.rollback()
    
    # **COMPATIBILITÉ: Sauvegarder aussi dans le dictionnaire**
    verification_tokens_db[token] = {
        'email': email,
        'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return token

def verify_email_token(token):
    """Vérifie un token de vérification email - Version DATABASE-FIRST"""
    try:
        # **NOUVEAU: Priorité à la base de données**
        db_token = EmailVerificationToken.query.filter_by(token=token, used=False).first()
        
        if db_token:
            # Vérifier l'expiration
            if datetime.now() > db_token.expires_at:
                # Token expiré - le supprimer
                db.session.delete(db_token)
                db.session.commit()
                print(f"🗑️ Token expiré supprimé de la base: {token[:8]}...")
                return None, "Token expiré"
            
            # Token valide - le marquer comme utilisé
            email = db_token.email
            db_token.used = True
            db.session.commit()
            
            # Supprimer aussi du dictionnaire si présent
            if token in verification_tokens_db:
                del verification_tokens_db[token]
            
            print(f"✅ Token vérifié avec succès depuis la base: {email}")
            return email, None
        
        print(f"🔍 Token non trouvé en base, vérification dans le dictionnaire: {token[:8]}...")
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification du token en base: {e}")
        db.session.rollback()
    
    # **FALLBACK: Vérification dans le dictionnaire en mémoire**
    if token not in verification_tokens_db:
        print(f"❌ Token introuvable partout: {token[:8]}...")
        return None, "Token invalide"
    
    token_data = verification_tokens_db[token]
    
    # Vérifier l'expiration
    expires_at = datetime.strptime(token_data['expires_at'], '%Y-%m-%d %H:%M:%S')
    if datetime.now() > expires_at:
        del verification_tokens_db[token]
        print(f"🗑️ Token expiré supprimé du dictionnaire: {token[:8]}...")
        return None, "Token expiré"
    
    email = token_data['email']
    del verification_tokens_db[token]
    
    print(f"✅ Token vérifié depuis le dictionnaire: {email}")
    return email, None

# Fonctions pour la récupération de mot de passe
def generate_password_reset_token():
    """Génère un token de récupération de mot de passe unique"""
    return str(uuid.uuid4())

def create_password_reset_token(email):
    """Crée un token de récupération de mot de passe pour un email"""
    token = generate_password_reset_token()
    expires_at = datetime.now() + timedelta(hours=1)  # Expire dans 1 heure
    
    password_reset_tokens_db[token] = {
        'email': email,
        'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S'),
        'used': False
    }
    
    return token

def verify_password_reset_token(token):
    """Vérifie un token de récupération de mot de passe"""
    if token not in password_reset_tokens_db:
        return None, "Token invalide"
    
    token_data = password_reset_tokens_db[token]
    
    # Vérifier si le token a déjà été utilisé
    if token_data.get('used', False):
        return None, "Token déjà utilisé"
    
    # Vérifier l'expiration
    expires_at = datetime.strptime(token_data['expires_at'], '%Y-%m-%d %H:%M:%S')
    if datetime.now() > expires_at:
        del password_reset_tokens_db[token]
        return None, "Token expiré"
    
    return token_data['email'], None

def mark_password_reset_token_used(token):
    """Marque un token de récupération comme utilisé"""
    try:
        # Marquer en base de données
        token_record = PasswordResetToken.query.filter_by(token=token).first()
        if token_record:
            token_record.used = True
            db.session.commit()
            print(f"✅ Token marqué comme utilisé en base: {token[:20]}...")
        else:
            print(f"⚠️ Token non trouvé en base: {token[:20]}...")
        
        # Compatibilité: marquer aussi dans le dictionnaire
        if token in password_reset_tokens_db:
            password_reset_tokens_db[token]['used'] = True
            print(f"✅ Token marqué comme utilisé en mémoire: {token[:20]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du marquage du token: {str(e)}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return False

def send_merchant_new_order_notification(merchant_email, order_data):
    """Envoie une notification email au marchand pour une nouvelle commande"""
    try:
        # Récupérer les informations du marchand depuis la base de données
        merchant_record = Merchant.query.filter_by(email=merchant_email).first()
        
        if not merchant_record:
            print(f"Marchand {merchant_email} non trouvé dans la base de données")
            return False
        
        merchant_data = merchant_record.to_dict()
        notifications = merchant_data.get('notifications', {})
        
        # Par défaut, envoyer les notifications si pas configuré
        if not notifications.get('email_orders', True):
            print(f"Notifications email désactivées pour le marchand {merchant_email}")
            return False
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        merchants_db[merchant_email] = merchant_data
        
        # Récupérer les informations du marchand
        merchant_name = merchant_data.get('store_name', 'Marchand')
        
        # Informations de la commande
        order_number = order_data.get('order_number', 'N/A')
        customer_name = order_data.get('customer_name', 'Client')
        customer_email = order_data.get('customer_email', '')
        customer_phone = order_data.get('customer_phone', '')
        order_total = order_data.get('total', 0)
        order_date = order_data.get('created_at', order_data.get('date', 'N/A'))
        shipping_address = order_data.get('shipping_address', {})
        
        # Construire la liste des produits
        products_list_html = ""
        products_list_text = ""
        
        if 'items' in order_data:
            items = order_data['items']
        elif 'products' in order_data:
            items = order_data['products']
        else:
            items = []
        
        for item in items:
            product_name = item.get('name', 'Produit')
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)
            subtotal = item.get('subtotal', price * quantity)
            options = item.get('options', {})
            
            products_list_html += f"""
            <div style="border-bottom: 1px solid #eee; padding: 15px 0;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <strong style="color: #333; font-size: 16px;">{product_name}</strong><br>
                        <span style="color: #666;">Quantité: {quantity}</span><br>
                        <span style="color: #666;">Prix unitaire: {price:,} KMF</span>
                        {f'<br><small style="color: #888;">Options: {", ".join([f"{k}: {v}" for k, v in options.items()])}</small>' if options else ''}
                    </div>
                    <div style="text-align: right;">
                        <strong style="color: #28a745; font-size: 16px;">{subtotal:,} KMF</strong>
                    </div>
                </div>
            </div>
            """
            
            products_list_text += f"- {product_name} (x{quantity}) - {price:,} KMF = {subtotal:,} KMF"
            if options:
                products_list_text += f" - Options: {', '.join([f'{k}: {v}' for k, v in options.items()])}"
            products_list_text += "\n"
        
        # Informations d'adresse
        address_html = ""
        address_text = ""
        
        if shipping_address:
            address_html = f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h4 style="margin: 0 0 10px 0; color: #333;">📍 Adresse de livraison :</h4>
                <p style="margin: 5px 0;"><strong>Adresse :</strong> {shipping_address.get('address', 'Non spécifiée')}</p>
                <p style="margin: 5px 0;"><strong>Ville :</strong> {shipping_address.get('city', 'Non spécifiée')}</p>
                <p style="margin: 5px 0;"><strong>Région :</strong> {shipping_address.get('region', 'Non spécifiée')}</p>
                {f'<p style="margin: 5px 0;"><strong>Code postal :</strong> {shipping_address.get("postal_code", "")}</p>' if shipping_address.get('postal_code') else ''}
                {f'<p style="margin: 5px 0;"><strong>Instructions :</strong> {shipping_address.get("instructions", "")}</p>' if shipping_address.get('instructions') else ''}
            </div>
            """
            
            address_text += f"""
Adresse de livraison :
- Adresse : {shipping_address.get('address', 'Non spécifiée')}
- Ville : {shipping_address.get('city', 'Non spécifiée')}
- Région : {shipping_address.get('region', 'Non spécifiée')}
{f"- Code postal : {shipping_address.get('postal_code', '')}" if shipping_address.get('postal_code') else ''}
{f"- Instructions : {shipping_address.get('instructions', '')}" if shipping_address.get('instructions') else ''}
            """
        
        # Construire le contenu HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nouvelle commande reçue</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .email-container {{
                    max-width: 700px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .email-header {{
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .email-header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 300;
                }}
                .email-body {{
                    padding: 40px 30px;
                }}
                .email-footer {{
                    background-color: #f8f9fa;
                    padding: 20px 30px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                }}
                .order-details {{
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 25px;
                    margin: 20px 0;
                }}
                .customer-info {{
                    background-color: #fff3cd;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    border-left: 4px solid #ffc107;
                }}
                .total-badge {{
                    display: inline-block;
                    padding: 12px 20px;
                    border-radius: 25px;
                    font-weight: bold;
                    font-size: 18px;
                    background-color: #28a745;
                    color: white;
                    margin: 15px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .urgent {{
                    background-color: #dc3545;
                    color: white;
                    padding: 10px 15px;
                    border-radius: 5px;
                    margin: 15px 0;
                    text-align: center;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>🛍️ DOUKA KM - Espace Marchand</h1>
                </div>
                <div class="email-body">
                    <h2>🎉 Nouvelle commande reçue !</h2>
                    
                    <p>Bonjour <strong>{merchant_name}</strong>,</p>
                    
                    <div class="urgent">
                        ⚡ NOUVELLE COMMANDE À TRAITER IMMÉDIATEMENT
                    </div>
                    
                    <p>Félicitations ! Vous avez reçu une nouvelle commande sur votre boutique DOUKA KM.</p>
                    
                    <div class="order-details">
                        <h3>📋 Détails de la commande</h3>
                        
                        <p><strong>Numéro de commande :</strong> <span style="color: #007bff; font-weight: bold;">{order_number}</span></p>
                        <p><strong>Date :</strong> {order_date}</p>
                        <p><strong>Statut :</strong> <span style="background-color: #ffc107; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold;">EN COURS DE PRÉPARATION</span></p>
                        
                        <div class="total-badge">
                            💰 Total : {order_total:,} KMF
                        </div>
                        
                        <h4>🛒 Articles commandés :</h4>
                        {products_list_html}
                    </div>
                    
                    <div class="customer-info">
                        <h3>👤 Informations client</h3>
                        <p><strong>Nom :</strong> {customer_name}</p>
                        <p><strong>Email :</strong> {customer_email}</p>
                        <p><strong>Téléphone :</strong> {customer_phone if customer_phone else 'Non renseigné'}</p>
                    </div>
                    
                    {address_html}
                    
                    <div style="background-color: #d1ecf1; border-radius: 8px; padding: 20px; margin: 25px 0; border-left: 4px solid #bee5eb;">
                        <h4 style="margin: 0 0 10px 0; color: #0c5460;">📝 Actions à effectuer :</h4>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>✅ Confirmer la commande dans votre espace marchand</li>
                            <li>📦 Préparer les articles commandés</li>
                            <li>📞 Contacter le client si nécessaire</li>
                            <li>🚚 Coordonner la livraison</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}/merchant/orders" class="button">
                            🎛️ Gérer cette commande
                        </a>
                    </div>
                    
                    <p style="margin-top: 30px;"><strong>Important :</strong> Veuillez traiter cette commande dans les plus brefs délais pour garantir la satisfaction de votre client.</p>
                    
                    <p>Si vous avez des questions, contactez-nous à <a href="mailto:support@doukakm.com">support@doukakm.com</a></p>
                    
                    <p>Cordialement,<br>L'équipe DOUKA KM</p>
                </div>
                <div class="email-footer">
                    <p><strong>DOUKA KM - Espace Marchand</strong></p>
                    <p>Votre partenaire e-commerce aux Comores</p>
                    <p>📧 support@doukakm.com | 📞 +269 342 40 19</p>
                    <p style="font-size: 12px; margin-top: 20px;">
                        Vous recevez cet email car vous avez activé les notifications de commandes.<br>
                        Gérez vos préférences dans votre espace marchand.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Contenu texte simple (fallback)
        text_content = f"""
🎉 NOUVELLE COMMANDE REÇUE - DOUKA KM

Bonjour {merchant_name},

🛍️ Vous avez reçu une nouvelle commande !

DÉTAILS DE LA COMMANDE :
- Numéro : {order_number}
- Date : {order_date}
- Total : {order_total:,} KMF

INFORMATIONS CLIENT :
- Nom : {customer_name}
- Email : {customer_email}
- Téléphone : {customer_phone if customer_phone else 'Non renseigné'}

{address_text}

ARTICLES COMMANDÉS :
{products_list_text}

ACTIONS À EFFECTUER :
✅ Confirmer la commande dans votre espace marchand
📦 Préparer les articles commandés
📞 Contacter le client si nécessaire
🚚 Coordonner la livraison

Connectez-vous à votre espace marchand pour gérer cette commande :
{CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}/merchant/orders

Important : Veuillez traiter cette commande rapidement pour garantir la satisfaction du client.

Cordialement,
L'équipe DOUKA KM
        """
        
        # Envoyer l'email
        subject = f"🎉 [DOUKA KM] Nouvelle commande #{order_number} - {order_total:,} KMF"
        success = send_email(merchant_email, subject, html_content, text_content)
        
        if success:
            print(f"✅ Notification de nouvelle commande envoyée au marchand {merchant_email}")
        else:
            print(f"❌ Échec de l'envoi de la notification au marchand {merchant_email}")
        
        return success
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de la notification au marchand {merchant_email}: {str(e)}")
        return False

def send_merchant_withdrawal_status_notification(merchant_email, withdrawal_data, old_status, new_status):
    """Envoie une notification email au marchand pour un changement de statut de demande de retrait - Version migrée database-first"""
    try:
        # **DATABASE-FIRST: Récupérer le marchand depuis la base de données d'abord**
        from db_helpers import get_merchant_by_email
        merchant_record = get_merchant_by_email(merchant_email)
        
        if merchant_record:
            # Utiliser les données depuis la base de données
            merchant_name = merchant_record.store_name or 'Marchand'
            notifications = merchant_record.notifications or {}
            
            print(f"✅ Marchand {merchant_email} récupéré depuis la base de données")
        else:
            # Fallback: récupérer depuis le dictionnaire
            merchant_data = merchants_db.get(merchant_email, {})
            notifications = merchant_data.get('notifications', {})
            merchant_name = merchant_data.get('store_name', 'Marchand')
            
            print(f"🔄 Marchand {merchant_email} récupéré depuis le dictionnaire (fallback)")
        
        # Par défaut, envoyer les notifications si pas configuré
        if not notifications.get('email_payment_changes', True):
            print(f"Notifications email pour changements de paiement désactivées pour le marchand {merchant_email}")
            return False
        
        # Informations de la demande de retrait
        request_id = withdrawal_data.get('id', 'N/A')
        amount = withdrawal_data.get('amount', 0)
        method = withdrawal_data.get('method', 'bank_transfer')
        requested_at = withdrawal_data.get('requested_at', 'N/A')
        reference = withdrawal_data.get('reference', '')
        admin_notes = withdrawal_data.get('admin_notes', '')
        
        # Messages selon le statut
        status_messages = {
            'pending': {
                'title': 'Demande de retrait en attente',
                'message': 'Votre demande de retrait a été soumise et est en cours d\'examen.',
                'emoji': '⏳',
                'color': '#ffc107',
                'urgency': 'low'
            },
            'approved': {
                'title': 'Demande de retrait approuvée !',
                'message': 'Excellente nouvelle ! Votre demande de retrait a été approuvée et va être traitée.',
                'emoji': '✅',
                'color': '#28a745',
                'urgency': 'medium'
            },
            'processing': {
                'title': 'Retrait en cours de traitement',
                'message': 'Votre retrait est actuellement en cours de traitement. Le paiement sera effectué sous peu.',
                'emoji': '🔄',
                'color': '#17a2b8',
                'urgency': 'medium'
            },
            'completed': {
                'title': 'Retrait complété avec succès !',
                'message': 'Votre retrait a été complété avec succès. Les fonds ont été transférés.',
                'emoji': '🎉',
                'color': '#007bff',
                'urgency': 'high'
            },
            'rejected': {
                'title': 'Demande de retrait rejetée',
                'message': 'Votre demande de retrait a été rejetée. Veuillez consulter les notes administratives.',
                'emoji': '❌',
                'color': '#dc3545',
                'urgency': 'high'
            },
            'cancelled': {
                'title': 'Demande de retrait annulée',
                'message': 'Votre demande de retrait a été annulée.',
                'emoji': '🚫',
                'color': '#6c757d',
                'urgency': 'medium'
            }
        }
        
        status_info = status_messages.get(new_status, {
            'title': 'Mise à jour de demande de retrait',
            'message': f'Le statut de votre demande de retrait a été mis à jour : {new_status}',
            'emoji': '📢',
            'color': '#6c757d',
            'urgency': 'low'
        })
        
        # Noms des méthodes de paiement
        method_names = {
            'bank_transfer': 'Virement bancaire',
            'mobile_money': 'Mobile Money',
            'cash_pickup': 'Retrait en espèces'
        }
        method_name = method_names.get(method, method)
        
        # Statuts en français
        status_french = {
            'pending': 'En cours de préparation',
            'approved': 'Approuvée',
            'processing': 'En traitement',
            'completed': 'Complété',
            'rejected': 'Rejeté',
            'cancelled': 'Annulé'
        }
        
        # Notes administratives
        admin_notes_html = ""
        admin_notes_text = ""
        if admin_notes:
            admin_notes_html = f"""
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <h4 style="margin: 0 0 10px 0; color: #856404;">💬 Notes administratives :</h4>
                <p style="margin: 0; color: #856404;">{admin_notes}</p>
            </div>
            """
            admin_notes_text = f"\nNotes administratives :\n{admin_notes}\n"
        
        # Référence
        reference_html = ""
        reference_text = ""
        if reference:
            reference_html = f'<p style="margin: 5px 0;"><strong>Référence :</strong> {reference}</p>'
            reference_text = f"- Référence : {reference}\n"
        
        # Construire le contenu HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{status_info['title']}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .email-container {{
                    max-width: 650px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .email-header {{
                    background: linear-gradient(135deg, {status_info['color']} 0%, {status_info['color']}AA 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .email-header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 300;
                }}
                .email-body {{
                    padding: 40px 30px;
                }}
                .email-footer {{
                    background-color: #f8f9fa;
                    padding: 20px 30px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                }}
                .withdrawal-details {{
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 25px;
                    margin: 20px 0;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 10px 20px;
                    border-radius: 25px;
                    font-weight: bold;
                    font-size: 16px;
                    background-color: {status_info['color']};
                    color: white;
                    margin: 15px 0;
                }}
                .amount-badge {{
                    display: inline-block;
                    padding: 15px 25px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 24px;
                    background-color: #e8f5e8;
                    color: #155724;
                    margin: 15px 0;
                    border: 2px solid #28a745;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .urgent {{
                    background-color: {status_info['color']};
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    text-align: center;
                    font-weight: bold;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>💰 DOUKA KM - Gestion des paiements</h1>
                </div>
                <div class="email-body">
                    <h2>{status_info['emoji']} {status_info['title']}</h2>
                    
                    <p>Bonjour <strong>{merchant_name}</strong>,</p>
                    
                    <div class="urgent">
                        {status_info['emoji']} MISE À JOUR DE VOTRE DEMANDE DE RETRAIT
                    </div>
                    
                    <p>{status_info['message']}</p>
                    
                    <div class="withdrawal-details">
                        <h3>💼 Détails de la demande</h3>
                        
                        <p><strong>Numéro de demande :</strong> <span style="color: #007bff; font-weight: bold;">{request_id}</span></p>
                        <p><strong>Date de demande :</strong> {requested_at}</p>
                        <p><strong>Méthode de paiement :</strong> {method_name}</p>
                        {reference_html}
                        
                        <div class="amount-badge">
                            💰 Montant : {amount:,} KMF
                        </div>
                        
                        <p><strong>Ancien statut :</strong> <span style="color: #6c757d;">{status_french.get(old_status, old_status)}</span></p>
                        <p><strong>Nouveau statut :</strong></p>
                        <div class="status-badge">
                            {status_info['emoji']} {status_french.get(new_status, new_status).upper()}
                        </div>
                    </div>
                    
                    {admin_notes_html}
                    
                    <div style="background-color: #d1ecf1; border-radius: 8px; padding: 20px; margin: 25px 0; border-left: 4px solid #bee5eb;">
                        <h4 style="margin: 0 0 10px 0; color: #0c5460;">📋 Informations importantes :</h4>
                        <ul style="margin: 10px 0; padding-left: 20px; color: #0c5460;">
                            <li>Vous pouvez suivre le statut de vos demandes dans votre espace marchand</li>
                            <li>Les fonds seront transférés selon la méthode choisie une fois le retrait complété</li>
                            <li>En cas de questions, contactez notre équipe support</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}/merchant/dashboard" class="button">
                            🎛️ Accéder à mon espace marchand
                        </a>
                    </div>
                    
                    <p>Pour toute question concernant cette demande, n'hésitez pas à nous contacter à <a href="mailto:finance@doukakm.com">finance@doukakm.com</a></p>
                    
                    <p>Cordialement,<br>L'équipe Finance DOUKA KM</p>
                </div>
                <div class="email-footer">
                    <p><strong>DOUKA KM - Gestion des paiements</strong></p>
                    <p>Votre partenaire e-commerce aux Comores</p>
                    <p>📧 finance@doukakm.com | 📞 +269 342 40 19</p>
                    <p style="font-size: 12px; margin-top: 20px;">
                        Vous recevez cet email car vous avez activé les notifications de gestion de paiement.<br>
                        Gérez vos préférences dans votre espace marchand.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Contenu texte simple (fallback)
        text_content = f"""
💰 MISE À JOUR DEMANDE DE RETRAIT - DOUKA KM

Bonjour {merchant_name},

{status_info['emoji']} {status_info['title']}

{status_info['message']}

DÉTAILS DE LA DEMANDE :
- Numéro : {request_id}
- Date de demande : {requested_at}
- Montant : {amount:,} KMF
- Méthode : {method_name}
{reference_text}

CHANGEMENT DE STATUT :
- Ancien statut : {status_french.get(old_status, old_status)}
- Nouveau statut : {status_french.get(new_status, new_status)}

{admin_notes_text}

INFORMATIONS IMPORTANTES :
- Suivez vos demandes dans votre espace marchand
- Les fonds seront transférés selon la méthode choisie
- Contactez finance@doukakm.com pour toute question

Accédez à votre espace marchand :
{CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}/merchant/dashboard

Cordialement,
L'équipe Finance DOUKA KM
        """
        
        # Envoyer l'email
        subject = f"💰 [DOUKA KM] {status_info['emoji']} {status_info['title']} - {amount:,} KMF"
        success = send_email(merchant_email, subject, html_content, text_content)
        
        if success:
            print(f"✅ Notification de changement de statut de retrait envoyée au marchand {merchant_email}")
        else:
            print(f"❌ Échec de l'envoi de la notification de retrait au marchand {merchant_email}")
        
        return success
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de la notification de retrait au marchand {merchant_email}: {str(e)}")
        return False

def send_password_reset_email(email, token):
    """Envoie un email de récupération de mot de passe"""
    reset_url = f"{CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}/reset-password?token={token}"
    
    # Contenu HTML de l'email
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }}
            .email-header {{
                background: linear-gradient(135deg, #0066cc 0%, #004499 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .email-body {{
                padding: 40px 30px;
            }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                background-color: #0066cc;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .warning-box {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
            }}
            .email-footer {{
                background-color: #f8f9fa;
                padding: 20px 30px;
                text-align: center;
                font-size: 14px;
                color: #6c757d;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <h1>🔐 DOUKA KM</h1>
            </div>
            <div class="email-body">
                <h2>Réinitialisation de mot de passe</h2>
                
                <p>Bonjour,</p>
                
                <p>Vous avez demandé à réinitialiser votre mot de passe pour votre compte DOUKA KM.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" class="button">Réinitialiser mon mot de passe</a>
                </div>
                
                <p>Si le bouton ne fonctionne pas, vous pouvez copier et coller ce lien dans votre navigateur :</p>
                <p style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; word-break: break-all;">
                    {reset_url}
                </p>
                
                <div class="warning-box">
                    <h4>⚠️ Informations importantes :</h4>
                    <ul>
                        <li><strong>Ce lien expire dans 1 heure</strong> pour votre sécurité</li>
                        <li>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email</li>
                        <li>Ne partagez jamais ce lien avec qui que ce soit</li>
                    </ul>
                </div>
                
                <p>Si vous avez des questions, contactez-nous à ledouka.km@gmail.com</p>
                
                <p>Cordialement,<br>L'équipe DOUKA KM</p>
            </div>
            <div class="email-footer">
                <p><strong>DOUKA KM</strong></p>
                <p>Votre marketplace de confiance aux Comores</p>
                <p>📧 ledouka.km@gmail.com | 📞 +269 342 40 19</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Contenu texte simple (fallback)
    text_content = f"""
Réinitialisation de mot de passe - DOUKA KM

Bonjour,

Vous avez demandé à réinitialiser votre mot de passe pour votre compte DOUKA KM.

Pour créer un nouveau mot de passe, cliquez sur ce lien :
{reset_url}

IMPORTANT :
- Ce lien expire dans 1 heure
- Si vous n'avez pas demandé cette réinitialisation, ignorez cet email
- Ne partagez jamais ce lien

Si vous avez des questions, contactez-nous à ledouka.km@gmail.com

Cordialement,
L'équipe DOUKA KM
    """
    
    subject = "🔐 Réinitialisation de votre mot de passe - DOUKA KM"
    
    # Envoyer l'email réel
    success = send_email(email, subject, html_content, text_content)
    
    if success:
        print(f"✅ Email de récupération de mot de passe envoyé à {email}")
    else:
        print(f"❌ Échec de l'envoi de l'email de récupération à {email}")
    
    return success

# Ajout du filtre format_number pour formater correctement les nombres dans les templates
@app.template_filter('format_number')
def format_number(value):
    """Format un nombre pour l'affichage (ex: 1000 -> 1 000)"""
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except (ValueError, TypeError):
        return value

# Ajout du filtre clean_shipping_method pour nettoyer l'affichage du mode de livraison
@app.template_filter('clean_shipping_method')
def clean_shipping_method(value):
    """Nettoie et standardise l'affichage du mode de livraison"""
    if not value:
        return "Standard (3 jours)"
    
    value = str(value).strip()
    
    # Cas des anciens formats "Livraison Standard" ou "Livraison Express"
    if "Livraison Standard" in value:
        if "1" in value:
            return "Standard (24h)"
        elif "3" in value:
            return "Standard (3 jours)"
        else:
            return "Standard (3 jours)"
    
    elif "Livraison Express" in value:
        if "même jour" in value:
            return "Express (même jour)"
        elif "24-48h" in value:
            return "Express (24-48h)"
        else:
            return "Express (24-48h)"
    
    # Si c'est déjà au bon format (commence par Express ou Standard)
    elif value.startswith('Express') or value.startswith('Standard'):
        return value
    
    # Fallback par défaut
    else:
        return "Standard (3 jours)"

# Variables globales pour stocker les catégories et sous-catégories dynamiques
admin_categories_db = {}

admin_subcategories_db = {}

# =============================================
# DONNÉES DE TEST - SEULEMENT EN DÉVELOPPEMENT
# =============================================

# Initialiser les dictionnaires vides par défaut
users_db = {}
merchants_db = {}
employees_db = {}
admin_categories_db = {}
admin_subcategories_db = {}
promo_codes_db = {}
site_settings = {}
reviews_db = []

# Charger les données de test UNIQUEMENT en mode développement
if os.environ.get('RENDER') != '1':
    
    # Base de données utilisateur simulée avec plus d'informations
    users_db = {}

    # Base de données marchands simulée
    merchants_db = {}

# Base de données pour les demandes de retrait (en mémoire pour le développement)
withdrawal_requests_db = {}

# Base de données des codes promo (en mémoire pour le développement)
promo_codes_db = {}

# Base de données administrateurs simulée
admins_db = {}

# Liste globale pour stocker les produits ajoutés par les administrateurs
admin_created_products = []

# Base de données des employés avec différents rôles
employees_db = {}

# Base de données pour gérer les assignations des commandes aux livreurs
# Structure: { 'livreur_email': [{'order_id': int, 'order_type': 'merchant'|'admin', 'assigned_at': str, 'merchant_email': str}] }
livreur_assignments_db = {}


# Base de données des avis/évaluations produits
reviews_db = []

# =============================================
# NETTOYAGE DES DONNÉES DE TEST EN PRODUCTION
# =============================================

# En mode production, vider toutes les données de test
if os.environ.get('RENDER') == '1':
    print("🚀 MODE PRODUCTION: Suppression des données de test")
    users_db.clear()
    merchants_db.clear() 
    employees_db.clear()
    admin_categories_db.clear()
    admin_subcategories_db.clear()
    promo_codes_db.clear()
    reviews_db.clear()
    print("✅ Toutes les données de test supprimées")
else:
    print("🔧 MODE DÉVELOPPEMENT: Données de test conservées")

# Fonction utilitaire pour récupérer un utilisateur de manière robuste
def get_user_by_email(email):
    """Récupère un utilisateur d'abord depuis la DB, puis le dictionnaire en mémoire"""
    if not email:
        return None
    
    try:
        # D'abord chercher dans la base de données (priorité)
        db_user = User.query.filter_by(email=email).first()
        if db_user:
            return {
                'id': db_user.id,
                'email': db_user.email,
                'first_name': db_user.first_name,
                'last_name': db_user.last_name,
                'phone': getattr(db_user, 'phone', ''),
                'source': 'database'
            }
        
        # Fallback: chercher dans le dictionnaire en mémoire
        user = users_db.get(email)
        if user:
            user['source'] = 'memory'
            return user
            
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération utilisateur {email}: {e}")
    
    return None

# Fonction pour ajouter un avis
def add_review(product_id, user_id, rating, title, comment, user_name):
    """Ajouter un nouvel avis pour un produit"""
    # **NOUVELLE VERSION: Sauvegarder dans la base de données SQLite**
    try:
        # Créer l'avis dans la base de données
        new_review = Review(
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            comment=comment,
            verified_purchase=True  # Pour l'instant, on considère tous comme vérifiés
        )
        
        db.session.add(new_review)
        db.session.commit()
        
        # Convertir en dictionnaire pour compatibilité avec le code existant
        review_dict = new_review.to_dict()
        
        # Si user_name est fourni manuellement, l'utiliser (pour compatibilité)
        if user_name and not review_dict.get('user_name'):
            review_dict['user_name'] = user_name
        
        # Ajouter aussi à la variable en mémoire pour la session courante
        reviews_db.append(review_dict)
        
        print(f"✅ Avis ajouté avec succès : ID {new_review.id} pour produit {product_id}")
        return review_dict
        
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout de l'avis: {str(e)}")
        db.session.rollback()
        
        # Fallback: ajouter seulement en mémoire (ancienne méthode)
        review = {
            'id': len(reviews_db) + 1,
            'product_id': product_id,
            'user_id': user_id,
            'user_name': user_name,
            'rating': rating,
            'title': title,
            'comment': comment,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'verified_purchase': True
        }
        reviews_db.append(review)
        return review

# Fonction pour récupérer les avis d'un produit
def get_product_reviews(product_id):
    """Récupérer tous les avis d'un produit, triés du plus récent au moins récent"""
    try:
        # Priorité à la base de données
        reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
        
        if reviews:
            # Utiliser les données de la base de données
            return [review.to_dict() for review in reviews]
        else:
            # Fallback vers le dictionnaire si pas de données en base
            product_reviews = [review for review in reviews_db if review['product_id'] == product_id]
            product_reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return product_reviews
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des avis du produit {product_id}: {e}")
        # Fallback vers le dictionnaire en cas d'erreur
        product_reviews = [review for review in reviews_db if review['product_id'] == product_id]
        product_reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return product_reviews

# Fonction pour calculer la note moyenne d'un produit
def calculate_average_rating(product_id):
    """Calculer la note moyenne d'un produit basée sur les avis"""
    product_reviews = get_product_reviews(product_id)
    if not product_reviews:
        return 0, 0
    
    total_rating = sum(review['rating'] for review in product_reviews)
    avg_rating = total_rating / len(product_reviews)
    return round(avg_rating, 1), len(product_reviews)

# Fonctions pour les marchands et leurs évaluations
def get_merchant_reviews(merchant_email):
    """Récupérer tous les avis des produits d'un marchand - Version migrée database-first"""
    try:
        # **DATABASE-FIRST: Priorité à la base de données**
        merchant_record = Merchant.query.filter_by(email=merchant_email).first()
        
        if merchant_record:
            # Obtenir tous les produits du marchand depuis la base de données
            merchant_products = Product.query.filter_by(merchant_id=merchant_record.id).all()
            
            merchant_reviews = []
            for product in merchant_products:
                # Obtenir les avis de ce produit depuis la base de données
                product_reviews = Review.query.filter_by(product_id=product.id).order_by(Review.created_at.desc()).all()
                
                # Ajouter les informations du produit à chaque avis
                for review in product_reviews:
                    review_dict = review.to_dict()
                    review_dict['product_name'] = product.name
                    review_dict['product_image'] = product.image
                    merchant_reviews.append(review_dict)
            
            # Trier par date de création (plus récents en premier)
            merchant_reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            print(f"✅ {len(merchant_reviews)} avis récupérés depuis la base de données pour {merchant_email}")
            return merchant_reviews
        else:
            # Fallback vers le dictionnaire si pas de marchand en base
            merchant = merchants_db.get(merchant_email, {})
            merchant_products = merchant.get('products', [])
            
            print(f"🔄 Utilisation du dictionnaire pour {merchant_email} ({len(merchant_products)} produits)")
            
            merchant_reviews = []
            for product in merchant_products:
                product_id = product['id']
                product_reviews = get_product_reviews(product_id)
                
                # Ajouter les informations du produit à chaque avis
                for review in product_reviews:
                    review_with_product = review.copy()
                    review_with_product['product_name'] = product['name']
                    review_with_product['product_image'] = product.get('image', '')
                    merchant_reviews.append(review_with_product)
            
            # Trier par date de création (plus récents en premier)
            merchant_reviews.sort(key=lambda x: x['created_at'], reverse=True)
            return merchant_reviews
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des avis du marchand {merchant_email}: {e}")
        # Fallback vers le dictionnaire en cas d'erreur
        merchant = merchants_db.get(merchant_email, {})
        merchant_products = merchant.get('products', [])
        
        merchant_reviews = []
        for product in merchant_products:
            product_id = product['id']
            product_reviews = get_product_reviews(product_id)
            
            # Ajouter les informations du produit à chaque avis
            for review in product_reviews:
                review_with_product = review.copy()
                review_with_product['product_name'] = product['name']
                review_with_product['product_image'] = product.get('image', '')
                merchant_reviews.append(review_with_product)
        
        # Trier par date de création (plus récents en premier)
        merchant_reviews.sort(key=lambda x: x['created_at'], reverse=True)
        return merchant_reviews

def calculate_merchant_average_rating(merchant_email):
    """Calculer la note moyenne globale d'un marchand basée sur tous ses produits"""
    merchant_reviews = get_merchant_reviews(merchant_email)
    
    if not merchant_reviews:
        return 0, 0
    
    total_rating = sum(review['rating'] for review in merchant_reviews)
    avg_rating = total_rating / len(merchant_reviews)
    return round(avg_rating, 1), len(merchant_reviews)

def get_merchant_rating_distribution(merchant_email):
    """Obtenir la répartition des notes pour un marchand"""
    merchant_reviews = get_merchant_reviews(merchant_email)
    
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in merchant_reviews:
        rating = review['rating']
        if rating in distribution:
            distribution[rating] += 1
    
    total_reviews = len(merchant_reviews)
    if total_reviews > 0:
        # Convertir en pourcentages
        distribution_percent = {}
        for rating, count in distribution.items():
            distribution_percent[rating] = round((count / total_reviews) * 100, 1)
        return distribution_percent, total_reviews
    
    return distribution, 0

# Fonction pour récupérer les paramètres globaux du système
# Fonctions de gestion des codes promo

def validate_promo_code(code, cart_total, user_email=None, cart_items=None):
    """
    Valide un code promo et calcule la remise applicable
    
    Args:
        code (str): Code promo à valider
        cart_total (float): Montant total du panier
        user_email (str): Email de l'utilisateur (optionnel)
        cart_items (list): Articles du panier (optionnel)
    
    Returns:
        dict: Résultat de la validation avec remise calculée
    """
    # Rechercher le code promo dans la base de données
    promo_record = PromoCode.query.filter_by(code=code).first()
    
    if not code or not promo_record:
        return {
            'valid': False,
            'error': 'Code promo invalide ou inexistant',
            'discount': 0,
            'eligible_items': []
        }
    
    # Convertir en dictionnaire pour compatibilité
    promo = promo_record.to_dict()
    
    # Aussi mettre à jour le dictionnaire en mémoire pour compatibilité
    promo_codes_db[code] = promo
    
    # Vérifier si le code est actif
    if not promo.get('active', False):
        return {
            'valid': False,
            'error': 'Ce code promo n\'est plus actif',
            'discount': 0,
            'eligible_items': []
        }
    
    # Vérifier les dates de validité
    today = datetime.now().strftime('%Y-%m-%d')
    
    if promo.get('start_date') and today < promo.get('start_date'):
        return {
            'valid': False,
            'error': 'Ce code promo n\'est pas encore valide',
            'discount': 0,
            'eligible_items': []
        }
    
    if promo.get('end_date') and today > promo.get('end_date'):
        return {
            'valid': False,
            'error': 'Ce code promo a expiré',
            'discount': 0,
            'eligible_items': []
        }
    
    # Vérifier les restrictions par catégories/produits/marchands
    eligible_total = cart_total
    eligible_items = []
    
    if promo.get('applicable_to', 'all') != 'all':
        if not cart_items:
            # Si des restrictions sont définies mais que cart_items n'est pas fourni,
            # nous ne pouvons pas valider correctement les restrictions
            return {
                'valid': False,
                'error': 'Impossible de valider les restrictions sans les détails du panier',
                'discount': 0,
                'eligible_items': []
            }
        
        eligible_total = 0
        
        for item in cart_items:
            is_eligible = False
            
            if promo.get('applicable_to') == 'categories':
                # Vérifier si le produit appartient à une catégorie autorisée
                if item.get('category_id') in promo.get('applicable_categories', []):
                    is_eligible = True
            
            elif promo.get('applicable_to') == 'subcategories':
                # Vérifier si le produit appartient à une sous-catégorie autorisée
                if item.get('subcategory_id') in promo.get('applicable_subcategories', []):
                    is_eligible = True
            
            elif promo.get('applicable_to') == 'products':
                # Vérifier si le produit est dans la liste des produits autorisés
                if item.get('id') in promo.get('applicable_products', []):
                    is_eligible = True
            
            elif promo.get('applicable_to') == 'merchants':
                # Vérifier si le produit vient d'un marchand autorisé
                merchant_email = item.get('merchant_email', 'admin_products')
                if merchant_email in promo.get('applicable_merchants', []):
                    is_eligible = True
            
            if is_eligible:
                item_total = item.get('price', 0) * item.get('quantity', 1)
                eligible_total += item_total
                eligible_items.append(item)
        
        # Si aucun produit n'est éligible
        if eligible_total == 0:
            applicable_names = []
            if promo.get('applicable_to') == 'categories':
                applicable_names = [admin_categories_db.get(cat_id, {}).get('name', f'Catégorie {cat_id}') 
                                  for cat_id in promo.get('applicable_categories', [])]
            elif promo.get('applicable_to') == 'subcategories':
                applicable_names = [admin_subcategories_db.get(sub_id, {}).get('name', f'Sous-catégorie {sub_id}') 
                                  for sub_id in promo.get('applicable_subcategories', [])]
            
            restriction_text = ', '.join(applicable_names) if applicable_names else 'certains produits'
            return {
                'valid': False,
                'error': f'Ce code promo s\'applique uniquement à: {restriction_text}',
                'discount': 0,
                'eligible_items': []
            }
    
    # Vérifier le montant minimum (sur le total éligible)
    if eligible_total < promo.get('min_amount', 0):
        return {
            'valid': False,
            'error': f'Montant minimum requis: {promo.get("min_amount", 0):,} KMF (sur les produits éligibles)',
            'discount': 0,
            'eligible_items': eligible_items
        }
    
    # Vérifier le nombre d'utilisations global
    if promo.get('usage_limit') and promo.get('used_count', 0) >= promo.get('usage_limit'):
        return {
            'valid': False,
            'error': 'Ce code promo a atteint sa limite d\'utilisation',
            'discount': 0,
            'eligible_items': eligible_items
        }
    
    # Vérifier le nombre d'utilisations par utilisateur
    if user_email and promo.get('user_limit'):
        user_usage = promo.get('used_by', {}).get(user_email, 0)
        if user_usage >= promo.get('user_limit'):
            return {
                'valid': False,
                'error': 'Vous avez déjà utilisé ce code promo le nombre maximum de fois',
                'discount': 0,
                'eligible_items': eligible_items
            }
    
    # Calculer la remise (sur le montant éligible uniquement)
    discount = 0
    if promo['type'] == 'percentage':
        discount = (eligible_total * promo['value']) / 100
        # Appliquer la remise maximum si définie
        if promo.get('max_discount') and discount > promo.get('max_discount'):
            discount = promo.get('max_discount')
    elif promo['type'] == 'fixed':
        discount = promo['value']
        # La remise ne peut pas être supérieure au montant éligible
        if discount > eligible_total:
            discount = eligible_total
    
    return {
        'valid': True,
        'discount': discount,
        'eligible_total': eligible_total,
        'eligible_items': eligible_items,
        'promo_name': promo.get('name', code),
        'promo_description': promo.get('description', ''),
        'error': None
    }

def apply_promo_code(code, user_email=None):
    """
    Applique un code promo (incrémente le compteur d'utilisation)
    
    Args:
        code (str): Code promo utilisé
        user_email (str): Email de l'utilisateur (optionnel)
    
    Returns:
        bool: True si l'application a réussi
    """
    # Rechercher le code promo dans la base de données
    promo_record = PromoCode.query.filter_by(code=code).first()
    
    if not promo_record:
        return False
    
    try:
        # Incrémenter le compteur global
        promo_record.used_count = (promo_record.used_count or 0) + 1
        
        # Incrémenter le compteur par utilisateur
        if user_email:
            if promo_record.used_by:
                try:
                    used_by = json.loads(promo_record.used_by)
                except (json.JSONDecodeError, TypeError):
                    used_by = {}
            else:
                used_by = {}
            
            used_by[user_email] = used_by.get(user_email, 0) + 1
            promo_record.used_by = json.dumps(used_by)
        
        # Sauvegarder en base de données
        db.session.commit()
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        promo_codes_db[code] = promo_record.to_dict()
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'application du code promo {code}: {e}")
        db.session.rollback()
        return False

def get_active_promo_codes():
    """
    Récupère tous les codes promo actifs
    
    Returns:
        list: Liste des codes promo actifs
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    active_codes = []
    # Récupérer depuis la base de données
    promo_records = PromoCode.query.filter_by(active=True).all()
    
    for promo_record in promo_records:
        promo = promo_record.to_dict()
        
        # Vérifier les critères de validité
        if ((not promo.get('start_date') or today >= promo.get('start_date')) and
            (not promo.get('end_date') or today <= promo.get('end_date')) and
            (not promo.get('usage_limit') or promo.get('used_count', 0) < promo.get('usage_limit'))):
            active_codes.append(promo)
    
    return active_codes

def get_public_promo_codes():
    """
    Récupère les codes promo actifs destinés à être affichés publiquement
    
    Returns:
        list: Liste des codes promo publics avec informations d'affichage
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    public_codes = []
    
    # Récupérer depuis la base de données
    promo_records = PromoCode.query.filter_by(active=True, public_display=True).all()
    
    for promo_record in promo_records:
        promo = promo_record.to_dict()
        
        # Vérifier si le code promo est actif et public
        if ((not promo.get('start_date') or today >= promo.get('start_date')) and
            (not promo.get('end_date') or today <= promo.get('end_date')) and
            (not promo.get('usage_limit') or promo.get('used_count', 0) < promo.get('usage_limit'))):
            
            # Formatage des informations pour l'affichage
            display_info = {
                'code': promo['code'],
                'name': promo.get('name', promo['code']),
                'description': promo.get('description', ''),
                'type': promo.get('type', 'percentage'),
                'value': promo.get('value', 0),
                'min_amount': promo.get('min_amount', 0),
                'max_discount': promo.get('max_discount'),
                'end_date': promo.get('end_date'),
                'usage_limit': promo.get('usage_limit'),
                'used_count': promo.get('used_count', 0),
                'applicable_to': promo.get('applicable_to', 'all'),
                'display_priority': promo.get('display_priority', 0)  # Pour l'ordre d'affichage
            }
            
            # Ajouter une description formatée pour l'affichage
            if display_info['type'] == 'percentage':
                display_info['formatted_discount'] = f"{display_info['value']:.0f}%"
                if display_info['max_discount']:
                    display_info['discount_text'] = f"{display_info['value']:.0f}% de réduction (max {display_info['max_discount']:,.0f} KMF)"
                else:
                    display_info['discount_text'] = f"{display_info['value']:.0f}% de réduction"
            else:
                display_info['formatted_discount'] = f"{display_info['value']:,.0f} KMF"
                display_info['discount_text'] = f"{display_info['value']:,.0f} KMF de réduction"
            
            # Ajouter condition minimale si applicable
            if display_info['min_amount'] > 0:
                display_info['condition_text'] = f"Commande minimum: {display_info['min_amount']:,.0f} KMF"
            else:
                display_info['condition_text'] = "Aucune commande minimum"
            
            # Informations de disponibilité
            if display_info['usage_limit']:
                remaining = display_info['usage_limit'] - display_info['used_count']
                display_info['availability_text'] = f"{remaining} utilisations restantes"
                display_info['urgency_level'] = 'high' if remaining <= 5 else 'medium' if remaining <= 20 else 'low'
            else:
                display_info['availability_text'] = "Utilisation illimitée"
                display_info['urgency_level'] = 'low'
            
            # Date d'expiration
            if display_info['end_date']:
                try:
                    end_date_obj = datetime.strptime(display_info['end_date'], '%Y-%m-%d')
                    today_obj = datetime.strptime(today, '%Y-%m-%d')
                    days_remaining = (end_date_obj - today_obj).days
                    
                    if days_remaining <= 0:
                        continue  # Skip expired codes
                    elif days_remaining == 1:
                        display_info['expiry_text'] = "Expire demain"
                        display_info['urgency_level'] = 'high'
                    elif days_remaining <= 3:
                        display_info['expiry_text'] = f"Expire dans {days_remaining} jours"
                        display_info['urgency_level'] = 'high'
                    elif days_remaining <= 7:
                        display_info['expiry_text'] = f"Expire dans {days_remaining} jours"
                        display_info['urgency_level'] = 'medium'
                    else:
                        display_info['expiry_text'] = f"Valide jusqu'au {display_info['end_date']}"
                        display_info['urgency_level'] = 'low'
                except:
                    display_info['expiry_text'] = f"Valide jusqu'au {display_info['end_date']}"
                    display_info['urgency_level'] = 'low'
            else:
                display_info['expiry_text'] = "Pas de date d'expiration"
                display_info['urgency_level'] = 'low'
            
            public_codes.append(display_info)
    
    # Trier par priorité d'affichage (plus élevée en premier) puis par urgence
    public_codes.sort(key=lambda x: (
        x.get('display_priority', 0),
        x.get('urgency_level') == 'high',
        x.get('urgency_level') == 'medium'
    ), reverse=True)
    
    return public_codes

def generate_promo_code():
    """
    Génère un code promo unique
    
    Returns:
        str: Code promo généré
    """
    import random
    import string
    
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in promo_codes_db:
            return code

def get_site_settings():
    """
    Récupère les paramètres globaux du site
    
    Returns:
        dict: Dictionnaire contenant les paramètres du site
    """
    default_settings = {
        'site_name': 'DOUKA KM',
        'site_description': "La première plateforme de commerce aux Comores. Connectant acheteurs et vendeurs à travers l'archipel.",
        'contact_email': 'ledouka.km@gmail.com',
        'contact_phone': '+269 342 40 19',
        'commission_rate': 15.0,  # Pourcentage
        'shipping_fee': 2000,  # KMF (frais par défaut)
        'default_shipping_fee': 2000,  # KMF (pour la compatibilité)
        'free_shipping_threshold': 50000,  # KMF
        # Nouveaux paramètres de livraison par région
        'shipping_rates': {
            'grande-comore': {
                'standard': 2000,  # KMF
                'express': 4000    # KMF
            },
            'anjouan': {
                'standard': 2500,  # KMF
                'express': 5000    # KMF
            },
            'moheli': {
                'standard': 3000,  # KMF
                'express': 6000    # KMF
            },
            'default': {
                'standard': 2000,  # KMF
                'express': 4000    # KMF
            }
        },
        # Nouveaux paramètres de livraison par tranches de prix
        'shipping_price_ranges': {
            'enabled': True,  # Active/désactive le système de tranches
            'ranges': [
                {'min': 0, 'max': 10000, 'standard': 3000, 'express': 6000},
                {'min': 10001, 'max': 30000, 'standard': 2000, 'express': 4000},
                {'min': 30001, 'max': 50000, 'standard': 1500, 'express': 3000},
                {'min': 50001, 'max': None, 'standard': 0, 'express': 1000}  # Livraison gratuite ou très réduite (None = infini)
            ]
        }
    }
    
    # Récupérer les paramètres depuis la variable globale si elle existe
    if 'site_settings' in globals():
        settings = globals()['site_settings'].copy()
        # Fusionner avec les valeurs par défaut pour s'assurer que toutes les clés existent
        default_settings.update(settings)
        
        # S'assurer que shipping_rates existe même si pas défini
        if 'shipping_rates' not in settings:
            settings['shipping_rates'] = default_settings['shipping_rates']
        
        # S'assurer que shipping_price_ranges existe même si pas défini
        if 'shipping_price_ranges' not in settings:
            settings['shipping_price_ranges'] = default_settings['shipping_price_ranges']
    
    return default_settings

# Fonction pour calculer les commissions admin avec le nouveau système par catégorie
def calculate_admin_commission_revenue():
    """
    Calcule le revenu admin basé sur les commissions des marchands 
    en utilisant les taux de commission personnalisés par catégorie
    
    Returns:
        float: Total des commissions en KMF
    """
    try:
        # Récupérer les paramètres globaux du site pour le taux par défaut
        site_settings = get_site_settings()
        default_commission_rate = float(site_settings['commission_rate']) / 100  # Convertir en décimal
        
        # Récupérer toutes les commandes livrées des marchands
        merchant_orders_db = Order.query.filter(
            Order.merchant_id.isnot(None),
            Order.status.in_(['completed', 'delivered']),
            Order.payment_status == 'completed'
        ).all()
        
        total_commission_fees = 0
        
        for db_order in merchant_orders_db:
            # Calculer la commission par item selon la catégorie (comme dans calculate_merchant_balance)
            order_commission = 0
            
            # Parcourir chaque item de la commande pour appliquer le bon taux
            for item in db_order.items:
                try:
                    # Récupérer le produit pour connaître sa catégorie
                    product = Product.query.get(item.product_id)
                    if product and product.category_id:
                        # Utiliser le taux spécifique à la catégorie
                        category_rate = get_category_commission_rate(product.category_id, default_commission_rate)
                    else:
                        # Utiliser le taux par défaut si pas de catégorie
                        category_rate = default_commission_rate
                    
                    # Calculer la commission sur le sous-total de cet item
                    item_commission = item.subtotal * category_rate
                    order_commission += item_commission
                    
                except Exception as e:
                    print(f"Erreur lors du calcul de commission admin pour l'item {item.id}: {e}")
                    # Fallback sur l'ancien calcul
                    item_commission = item.subtotal * default_commission_rate
                    order_commission += item_commission
            
            total_commission_fees += order_commission
        
        return total_commission_fees
        
    except Exception as e:
        print(f"Erreur lors du calcul des commissions admin: {e}")
        return 0

# Fonction pour obtenir le taux de commission par catégorie avec fallback
def get_category_commission_rate(category_id, default_rate):
    """
    Récupère le taux de commission personnalisé pour une catégorie ou utilise le taux par défaut
    
    Args:
        category_id (int): ID de la catégorie
        default_rate (float): Taux par défaut en décimal (ex: 0.05 pour 5%)
    
    Returns:
        float: Taux de commission en décimal
    """
    try:
        # Chercher le taux personnalisé pour cette catégorie
        custom_rate = CategoryCommissionRate.query.filter_by(category_id=category_id).first()
        if custom_rate:
            return custom_rate.commission_rate / 100  # Convertir en décimal
        return default_rate
    except Exception as e:
        print(f"Erreur lors de la récupération du taux de commission pour la catégorie {category_id}: {e}")
        return default_rate

# Fonction pour calculer le solde dynamique d'un marchand
def calculate_merchant_balance(merchant_email):
    """
    Calcule le solde dynamique d'un marchand basé sur les commandes livrées
    Version migrée vers la base de données complète
    
    Args:
        merchant_email (str): L'email du marchand
    
    Returns:
        dict: Dictionnaire contenant les détails du calcul du solde
    """
    # Récupérer le marchand depuis la base de données d'abord
    from db_helpers import get_merchant_by_email, get_merchant_orders, get_merchant_withdrawal_requests
    merchant_record = get_merchant_by_email(merchant_email)
    
    # Récupérer les paramètres globaux du site
    site_settings = get_site_settings()
    default_commission_rate = float(site_settings['commission_rate']) / 100  # Convertir en décimal
    
    if not merchant_record:
        # Fallback: chercher dans les dictionnaires
        merchant = merchants_db.get(merchant_email, {})
        if not merchant:
            return {
                'total_earnings': 0,
                'commission_fees': 0,
                'available_balance': 0,
                'delivered_orders_count': 0,
                'commission_rate': default_commission_rate,
                'pending_withdrawals': 0,
                'completed_withdrawals': 0,
                'total_withdrawals': 0,
                'gross_balance': 0
            }
    
    # **MIGRATION COMPLÈTE: Utiliser la base de données**
    total_earnings = 0
    delivered_orders_count = 0
    total_commission_fees = 0
    
    if merchant_record:
        # Récupérer toutes les commandes livrées depuis la base de données
        db_orders = get_merchant_orders(merchant_record.id)
        
        for db_order in db_orders:
            if db_order.status == 'delivered' and db_order.payment_status == 'completed':
                # Calculer les gains (total - frais de livraison)
                order_earnings = db_order.total - (db_order.shipping_fee or 0)
                total_earnings += order_earnings
                delivered_orders_count += 1
                
                # Calculer la commission par item selon la catégorie
                order_commission = 0
                
                # Parcourir chaque item de la commande pour appliquer le bon taux
                for item in db_order.items:
                    try:
                        # Récupérer le produit pour connaître sa catégorie
                        product = Product.query.get(item.product_id)
                        if product and product.category_id:
                            # Utiliser le taux spécifique à la catégorie
                            category_rate = get_category_commission_rate(product.category_id, default_commission_rate)
                        else:
                            # Utiliser le taux par défaut si pas de catégorie
                            category_rate = default_commission_rate
                        
                        # Calculer la commission sur le sous-total de cet item
                        item_commission = item.subtotal * category_rate
                        order_commission += item_commission
                        
                    except Exception as e:
                        print(f"Erreur lors du calcul de commission pour l'item {item.id}: {e}")
                        # Fallback sur l'ancien calcul
                        item_commission = item.subtotal * default_commission_rate
                        order_commission += item_commission
                
                total_commission_fees += order_commission
        
        # Calculer les retraits depuis la base de données
        withdrawal_requests = get_merchant_withdrawal_requests(merchant_record.id)
        
        pending_withdrawals = sum(
            req.amount for req in withdrawal_requests 
            if req.status in ['pending', 'approved', 'processing']
        )
        
        completed_withdrawals = sum(
            req.amount for req in withdrawal_requests 
            if req.status == 'completed'
        )
    else:
        # Fallback: utiliser l'ancien système de dictionnaires
        merchant = merchants_db.get(merchant_email, {})
        
        for order in merchant.get('orders', []):
            if order.get('status') == 'delivered':
                order_total = order.get('total', 0)
                shipping_fee = order.get('shipping_fee', 0)
                order_earnings = order_total - shipping_fee
                total_earnings += order_earnings
                delivered_orders_count += 1
                
                # Utiliser le taux de commission par défaut
                order_commission = order_earnings * default_commission_rate
                total_commission_fees += order_commission
        
        # Retraits depuis l'ancien système
        withdrawal_requests = withdrawal_requests_db.get(merchant_email, [])
        
        pending_withdrawals = sum(
            req['amount'] for req in withdrawal_requests 
            if req['status'] in ['pending', 'approved', 'processing']
        )
        
        completed_withdrawals = sum(
            req['amount'] for req in withdrawal_requests 
            if req['status'] == 'completed'
        )
    
    # Calculer le solde disponible (gains nets - commission - retraits)
    net_earnings = total_earnings - total_commission_fees
    available_balance = net_earnings - pending_withdrawals - completed_withdrawals
    
    return {
        'total_earnings': int(total_earnings),
        'commission_fees': int(total_commission_fees),
        'net_earnings': int(net_earnings),  # Nouveaux: gains nets (après commission)
        'available_balance': int(max(0, available_balance)),  # Ne peut pas être négatif
        'gross_balance': int(net_earnings),  # Solde brut avant retraits (gains nets)
        'pending_withdrawals': int(pending_withdrawals),
        'completed_withdrawals': int(completed_withdrawals),
        'total_withdrawals': int(pending_withdrawals + completed_withdrawals),
        'delivered_orders_count': delivered_orders_count,
        'commission_rate': default_commission_rate
    }

# Fonction pour calculer les frais de livraison dynamiques
def calculate_dynamic_shipping_fee(cart_items, cart_total, region=None, shipping_type='standard'):
    """
    Calcule les frais de livraison basés sur les tarifs dynamiques par catégorie
    
    Args:
        cart_items (list): Liste des articles du panier
        cart_total (float): Montant total du panier
        region (str): Région de livraison (optionnel)
        shipping_type (str): Type de livraison ('standard' ou 'express')
    
    Returns:
        dict: Dictionnaire contenant les détails des frais de livraison
    """
    import json
    
    # Récupérer les paramètres de base
    site_settings = get_all_site_settings()
    free_shipping_threshold = site_settings.get('free_shipping_threshold', 15000)
    
    # Récupérer les tarifs personnalisés depuis la table ShippingRate
    try:
        shipping_rates = ShippingRate.query.filter_by(active=True).all()
        custom_rates = []
        for rate in shipping_rates:
            custom_rates.append({
                'id': rate.id,
                'name': rate.name,
                'rate_type': rate.rate_type,
                'category_id': rate.category_id,
                'subcategory_id': rate.subcategory_id,
                'standard_rate': rate.standard_rate,
                'express_rate': rate.express_rate,
                'standard_delivery_days': rate.standard_delivery_days,
                'standard_delivery_hours': rate.standard_delivery_hours,
                'express_delivery_days': rate.express_delivery_days,
                'express_delivery_hours': rate.express_delivery_hours,
                'priority': rate.priority,
                'active': rate.active,
                'is_system_default': rate.rate_type == 'default',
                'created_at': rate.created_at.strftime('%Y-%m-%d %H:%M:%S.%f') if rate.created_at else None,
                'updated_at': rate.updated_at.strftime('%Y-%m-%d %H:%M:%S.%f') if rate.updated_at else None
            })
    except Exception as e:
        print(f"Erreur lors du chargement des tarifs ShippingRate: {e}")
        custom_rates = []
    
    # Analyser les catégories des produits dans le panier
    categories_in_cart = set()
    subcategories_in_cart = set()
    
    for item in cart_items:
        # Récupérer l'ID du produit
        if 'original_product_id' in item:
            product_id = item['original_product_id']
        else:
            product_id = item['product_id']
        
        # Récupérer le produit pour obtenir sa catégorie
        product = get_product_by_id(product_id)
        if product:
            if product.get('category_id'):
                categories_in_cart.add(product['category_id'])
            if product.get('subcategory_id'):
                subcategories_in_cart.add(product['subcategory_id'])
    
    # Trouver le tarif le plus élevé parmi tous les tarifs applicables
    # 1. Collecter d'abord tous les tarifs spécifiques (catégorie/sous-catégorie)
    # 2. Si aucun tarif spécifique, utiliser le tarif par défaut
    # 3. Si plusieurs tarifs spécifiques, prendre le plus élevé
    
    specific_rates = []  # Tarifs spécifiques (catégorie/sous-catégorie)
    default_rates = []   # Tarifs par défaut
    
    for rate in custom_rates:
        if not rate.get('active', True):
            continue
            
        matches = False
        rate_type = ""
        is_specific = False
        
        # Vérifier les sous-catégories (priorité la plus haute)
        if rate.get('rate_type') == 'subcategory' and rate.get('subcategory_id'):
            if rate['subcategory_id'] in subcategories_in_cart:
                matches = True
                rate_type = "subcategory"
                is_specific = True
        
        # Vérifier les catégories
        elif rate.get('rate_type') == 'category' and rate.get('category_id'):
            if rate['category_id'] in categories_in_cart:
                matches = True
                rate_type = "category"
                is_specific = True
        
        # Tarif par défaut (système)
        elif rate.get('is_system_default', False):
            matches = True
            rate_type = "default"
            is_specific = False
        
        if matches:
            # Calculer le prix pour ce tarif selon le type de livraison
            if shipping_type == 'express':
                rate_price = rate.get('express_rate', rate.get('standard_rate', 0) + 1000)
            else:
                rate_price = rate.get('standard_rate', 0)
            
            rate_info = {
                'rate': rate,
                'price': rate_price,
                'type': rate_type
            }
            
            if is_specific:
                specific_rates.append(rate_info)
            else:
                default_rates.append(rate_info)
    
    # Choisir les tarifs à utiliser : spécifiques en priorité, sinon par défaut
    applicable_rates = specific_rates if specific_rates else default_rates
    
    # Trier par prix décroissant puis par priorité (subcategory > category > default)
    priority_order = {'subcategory': 3, 'category': 2, 'default': 1}
    applicable_rates.sort(key=lambda x: (x['price'], priority_order.get(x['type'], 0)), reverse=True)
    
    # Prendre le tarif avec le prix le plus élevé
    selected_rate = applicable_rates[0]['rate'] if applicable_rates else None
    selected_price = applicable_rates[0]['price'] if applicable_rates else None
    
    # Si aucun tarif trouvé, utiliser les paramètres par défaut
    if not selected_rate:
        default_shipping_fee = site_settings.get('shipping_fee', 1500)
        shipping_fee = default_shipping_fee + (1000 if shipping_type == 'express' else 0)
    else:
        # Utiliser le prix calculé (déjà selon le type de livraison)
        shipping_fee = selected_price
    
    # Vérifier si la livraison est gratuite selon le seuil global
    is_free_shipping = cart_total >= free_shipping_threshold
    final_shipping_fee = 0 if is_free_shipping else shipping_fee
    
    return {
        'shipping_fee': final_shipping_fee,
        'base_shipping_fee': shipping_fee,  # Prix avant application du seuil gratuit
        'is_free_shipping': is_free_shipping,
        'free_shipping_threshold': free_shipping_threshold,
        'amount_needed_for_free_shipping': max(0, free_shipping_threshold - cart_total) if not is_free_shipping else 0,
        'region': region,
        'shipping_type': shipping_type,
        'selected_rate': selected_rate,
        'categories_analyzed': list(categories_in_cart),
        'subcategories_analyzed': list(subcategories_in_cart),
        'rate_priority': len(specific_rates) if specific_rates else len(default_rates),  # Nombre de tarifs applicables
        'selected_price': selected_price,
        'all_applicable_rates': [r['price'] for r in applicable_rates]  # Debug: tous les prix trouvés
    }

def calculate_shipping_fee(cart_total, region=None, shipping_type='standard'):
    """
    Calcule les frais de livraison basés sur les paramètres globaux
    
    Args:
        cart_total (float): Montant total du panier
        region (str): Région de livraison (optionnel pour des frais spéciaux)
        shipping_type (str): Type de livraison ('standard' ou 'express')
    
    Returns:
        dict: Dictionnaire contenant les détails des frais de livraison
    """
    site_settings = get_site_settings()
    free_shipping_threshold = site_settings['free_shipping_threshold']
    
    # Vérifier si le système de tranches de prix est activé
    price_ranges_config = site_settings.get('shipping_price_ranges', {})
    price_ranges_enabled = price_ranges_config.get('enabled', False)
    
    shipping_fee = 0
    price_range_used = None
    
    if price_ranges_enabled:
        # Utiliser le système de tranches de prix
        price_ranges = price_ranges_config.get('ranges', [])
        
        for price_range in price_ranges:
            min_price = price_range.get('min', 0)
            max_price = price_range.get('max')  # None signifie infini
            
            # Vérifier si le montant du panier correspond à cette tranche
            if max_price is None:  # Tranche ouverte (infinie)
                is_in_range = cart_total >= min_price
            else:
                is_in_range = min_price <= cart_total <= max_price
            
            if is_in_range:
                shipping_fee = price_range.get(shipping_type, price_range.get('standard', 0))
                price_range_used = {
                    'min': min_price,
                    'max': max_price,
                    'range_text': f"{min_price:,} - {max_price:,} KMF" if max_price is not None else f"Plus de {min_price:,} KMF"
                }
                break
        
        # Si aucune tranche ne correspond, utiliser les tarifs par défaut
        if price_range_used is None:
            shipping_rates = site_settings.get('shipping_rates', {})
            region_key = region if region in shipping_rates else 'default'
            region_rates = shipping_rates.get(region_key, shipping_rates['default'])
            shipping_fee = region_rates.get(shipping_type, region_rates.get('standard', site_settings['shipping_fee']))
    
    else:
        # Utiliser le système de tarifs par région
        shipping_rates = site_settings.get('shipping_rates', {})
        
        # Déterminer la région à utiliser
        region_key = region if region in shipping_rates else 'default'
        region_rates = shipping_rates.get(region_key, shipping_rates['default'])
        
        # Récupérer le prix selon le type de livraison
        shipping_fee = region_rates.get(shipping_type, region_rates.get('standard', site_settings['shipping_fee']))
    
    # Vérifier si la livraison est gratuite selon le seuil global
    is_free_shipping = cart_total >= free_shipping_threshold
    final_shipping_fee = 0 if is_free_shipping else shipping_fee
    
    return {
        'shipping_fee': final_shipping_fee,
        'base_shipping_fee': shipping_fee,  # Prix avant application du seuil gratuit
        'is_free_shipping': is_free_shipping,
        'free_shipping_threshold': free_shipping_threshold,
        'amount_needed_for_free_shipping': max(0, free_shipping_threshold - cart_total) if not is_free_shipping else 0,
        'region': region,
        'shipping_type': shipping_type,
        'price_ranges_enabled': price_ranges_enabled,
        'price_range_used': price_range_used
    }

# Fonctions de gestion du stock

def update_product_stock(product_id, quantity_change, reason=""):
    """
    Met à jour le stock d'un produit - Version migrée database-first
    Args:
        product_id: ID du produit
        quantity_change: Quantité à ajouter (positive) ou retirer (négative)
        reason: Raison du changement (pour logs)
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    print(f"[STOCK] Tentative de mise à jour du stock - Produit ID: {product_id}, Changement: {quantity_change}, Raison: {reason}")
    
    # **DATABASE-FIRST: Chercher le produit dans la base de données d'abord**
    try:
        product_record = Product.query.filter_by(id=product_id).first()
        if product_record:
            old_stock = product_record.stock
            new_stock = max(0, old_stock + quantity_change)
            
            # Mise à jour dans la base de données
            product_record.stock = new_stock
            product_record.updated_at = datetime.now()
            db.session.commit()
            
            print(f"[STOCK] ✅ Stock mis à jour dans la base de données pour produit {product_id}: {old_stock} -> {new_stock} ({reason})")
            
            # COMPATIBILITÉ: Synchroniser avec les dictionnaires pour fallback
            # Mettre à jour dans les produits marchands si c'est un produit marchand
            if product_record.merchant_id:
                for merchant_email, merchant_data in merchants_db.items():
                    if 'products' in merchant_data:
                        for product in merchant_data['products']:
                            if product['id'] == product_id:
                                product['stock'] = new_stock
                                print(f"[STOCK] 🔄 Synchronisé avec dictionnaire marchand pour produit {product_id}")
                                break
            
            return True
            
    except Exception as e:
        print(f"[STOCK] ❌ Erreur lors de la mise à jour en base de données: {str(e)}")
        db.session.rollback()
    
    # Fallback: mise à jour dans les anciens dictionnaires
    print(f"[STOCK] 🔄 Fallback vers les dictionnaires pour produit {product_id}")
    
    # Vérifier dans les produits d'admin
    for product in admin_created_products:
        if product['id'] == product_id:
            old_stock = product.get('stock', 0)
            new_stock = max(0, old_stock + quantity_change)
            product['stock'] = new_stock
            print(f"[STOCK] ✅ Stock mis à jour pour produit admin {product_id}: {old_stock} -> {new_stock} ({reason})")
            return True
    
    # Vérifier dans les produits des marchands
    for merchant_email, merchant_data in merchants_db.items():
        if 'products' in merchant_data:
            for product in merchant_data['products']:
                if product['id'] == product_id:
                    old_stock = product.get('stock', 0)
                    new_stock = max(0, old_stock + quantity_change)
                    product['stock'] = new_stock
                    print(f"[STOCK] ✅ Stock mis à jour pour produit marchand {product_id}: {old_stock} -> {new_stock} ({reason})")
                    return True
    
    print(f"[STOCK] ❌ Produit {product_id} non trouvé pour mise à jour de stock")
    return False

def reserve_stock(order_items):
    """
    Réserve le stock pour une commande (diminue temporairement)
    Args:
        order_items: Liste des articles de la commande avec 'product_id' et 'quantity'
    Returns:
        dict: {'success': bool, 'message': str, 'reserved_items': list}
    """
    reserved_items = []
    
    for item in order_items:
        product_id = item.get('original_product_id', item.get('product_id'))
        quantity = item.get('quantity', 1)
        
        try:
            # Convertir en entier si c'est une chaîne
            if isinstance(product_id, str) and product_id.isdigit():
                product_id = int(product_id)
        except:
            pass
        
        # Vérifier le stock disponible
        product = get_product_by_id(product_id)
        
        # Si pas trouvé dans la DB, chercher dans admin_created_products
        if not product:
            for admin_product in admin_created_products:
                if admin_product['id'] == product_id:
                    product = admin_product
                    break
        
        # Si pas trouvé dans admin, chercher dans merchants_db
        if not product:
            for merchant_email, merchant_data in merchants_db.items():
                if 'products' in merchant_data:
                    for merchant_product in merchant_data['products']:
                        if merchant_product['id'] == product_id:
                            product = merchant_product
                            break
                if product:
                    break
        
        if not product:
            return {
                'success': False,
                'message': f'Produit {product_id} non trouvé',
                'reserved_items': reserved_items
            }
        
        current_stock = product.get('stock', 0)
        if current_stock < quantity:
            # Annuler les réservations déjà faites
            for reserved_item in reserved_items:
                update_product_stock(reserved_item['product_id'], reserved_item['quantity'], "Annulation réservation")
            
            return {
                'success': False,
                'message': f'Stock insuffisant pour {product["name"]} (disponible: {current_stock}, demandé: {quantity})',
                'reserved_items': []
            }
        
        # Réserver le stock (diminuer)
        if update_product_stock(product_id, -quantity, f"Réservation commande - {quantity} unités"):
            reserved_items.append({
                'product_id': product_id,
                'quantity': quantity,
                'product_name': product['name']
            })
        else:
            # Annuler les réservations déjà faites
            for reserved_item in reserved_items:
                update_product_stock(reserved_item['product_id'], reserved_item['quantity'], "Annulation réservation")
            
            return {
                'success': False,
                'message': f'Erreur lors de la réservation du stock pour {product["name"]}',
                'reserved_items': []
            }
    
    return {
        'success': True,
        'message': 'Stock réservé avec succès',
        'reserved_items': reserved_items
    }

def release_reserved_stock(reserved_items):
    """
    Libère le stock réservé après une commande réussie
    Args:
        reserved_items: Liste des items réservés retournée par reserve_stock
    Returns:
        bool: True si la libération a réussi, False sinon
    """
    print(f"[STOCK] Libération du stock réservé pour {len(reserved_items)} produits")
    success = True
    
    for reserved_item in reserved_items:
        product_id = reserved_item['product_id']
        quantity = reserved_item['quantity']
        product_name = reserved_item['product_name']
        
        # Restaurer le stock (ajouter la quantité réservée)
        if update_product_stock(product_id, quantity, f"Libération réservation après commande - {quantity} unités"):
            print(f"[STOCK] ✅ Stock libéré pour {product_name} (ID: {product_id}): +{quantity}")
        else:
            print(f"[STOCK] ❌ Erreur lors de la libération du stock pour {product_name} (ID: {product_id})")
            success = False
    
    return success

def check_product_stock_availability(product_id, requested_quantity):
    """
    Vérifie si un produit a suffisamment de stock pour la quantité demandée
    
    Args:
        product_id (int): ID du produit
        requested_quantity (int): Quantité demandée
    
    Returns:
        dict: {
            'available': bool,
            'current_stock': int,
            'requested': int,
            'message': str
        }
    """
    try:
        # Récupérer le produit depuis la base de données
        product_record = Product.query.filter_by(id=product_id).first()
        
        if not product_record:
            return {
                'available': False,
                'current_stock': 0,
                'requested': requested_quantity,
                'message': 'Produit non trouvé'
            }
        
        current_stock = product_record.stock or 0
        
        if current_stock < requested_quantity:
            return {
                'available': False,
                'current_stock': current_stock,
                'requested': requested_quantity,
                'message': f'Stock insuffisant. Disponible: {current_stock}, Demandé: {requested_quantity}'
            }
        
        return {
            'available': True,
            'current_stock': current_stock,
            'requested': requested_quantity,
            'message': 'Stock suffisant'
        }
        
    except Exception as e:
        print(f"Erreur lors de la vérification du stock pour le produit {product_id}: {e}")
        return {
            'available': False,
            'current_stock': 0,
            'requested': requested_quantity,
            'message': f'Erreur lors de la vérification: {str(e)}'
        }

def release_stock(order_items):
    """
    Libère le stock réservé (remet les quantités)
    Args:
        order_items: Liste des articles avec 'product_id' et 'quantity'
    """
    print(f"[RELEASE_STOCK] Début de libération pour {len(order_items)} articles")
    
    for item in order_items:
        product_id = item.get('original_product_id', item.get('product_id'))
        quantity = item.get('quantity', 1)
        product_name = item.get('product_name', 'Produit inconnu')
        
        print(f"[RELEASE_STOCK] Article: {product_name} (ID: {product_id}) - Quantité: +{quantity}")
        
        try:
            if isinstance(product_id, str) and product_id.isdigit():
                product_id = int(product_id)
        except:
            pass
        
        success = update_product_stock(product_id, quantity, f"Libération stock - annulation commande - {product_name}")
        if success:
            print(f"[RELEASE_STOCK] ✅ Stock libéré avec succès pour {product_name}")
        else:
            print(f"[RELEASE_STOCK] ❌ Échec de libération pour {product_name}")
    
    print(f"[RELEASE_STOCK] Fin de libération")

def confirm_stock_deduction(order_items):
    """
    Confirme la déduction du stock (lors de la livraison)
    MODIFIÉ: Diminue réellement le stock car il n'était pas déduit définitivement avant
    """
    for item in order_items:
        product_id = item.get('original_product_id', item.get('product_id'))
        quantity = item.get('quantity', 1)
        
        try:
            if isinstance(product_id, str) and product_id.isdigit():
                product_id = int(product_id)
        except:
            pass
        
        product = get_product_by_id(product_id)
        if product:
            # CORRECTION: Déduire réellement le stock lors de la livraison
            old_stock = product.get('stock', 0)
            if update_product_stock(product_id, -quantity, f"Déduction définitive livraison - {product['name']}"):
                print(f"✅ Stock déduit pour livraison - Produit: {product['name']}, Quantité: -{quantity}, Stock avant: {old_stock}, Stock après: {old_stock - quantity}")
            else:
                print(f"❌ Erreur lors de la déduction du stock pour {product['name']} (ID: {product_id})")
        else:
            print(f"❌ Produit {product_id} non trouvé pour déduction de stock")

def get_stock_summary():
    """
    Retourne un résumé de tous les stocks des produits - Version migrée database-first
    Returns:
        list: Liste des produits avec leurs informations de stock
    """
    stock_summary = []
    
    # **DATABASE-FIRST: Récupérer les produits depuis la base de données d'abord**
    try:
        all_products = Product.query.all()
        
        for product_record in all_products:
            stock_info = {
                'id': product_record.id,
                'name': product_record.name,
                'stock': product_record.stock,
                'price': float(product_record.price),
                'created_at': product_record.created_at.strftime('%Y-%m-%d') if product_record.created_at else None
            }
            
            if product_record.merchant_id:
                # Récupérer les informations du marchand depuis la DB
                merchant_record = Merchant.query.get(product_record.merchant_id)
                if merchant_record:
                    stock_info.update({
                        'source': 'merchant',
                        'merchant_email': merchant_record.email,
                        'merchant_name': merchant_record.store_name or 'Boutique sans nom'
                    })
                else:
                    stock_info.update({
                        'source': 'merchant',
                        'merchant_email': 'unknown',
                        'merchant_name': 'Marchand inconnu'
                    })
            else:
                stock_info['source'] = 'admin'
            
            stock_summary.append(stock_info)
        
        print(f"[STOCK] ✅ {len(stock_summary)} produits récupérés depuis la base de données")
        
    except Exception as e:
        print(f"[STOCK] ❌ Erreur lors de la récupération depuis la DB: {str(e)}")
        # Fallback vers les dictionnaires
        pass
    
    # Fallback: ajouter les produits des dictionnaires non encore migrés
    fallback_count = 0
    
    # Produits admin
    for product in admin_created_products:
        # Vérifier si ce produit n'est pas déjà dans stock_summary
        if not any(p['id'] == product['id'] for p in stock_summary):
            stock_summary.append({
                'id': product['id'],
                'name': product['name'],
                'stock': product.get('stock', 0),
                'source': 'admin',
                'price': product.get('price', 0)
            })
            fallback_count += 1
    
    # Produits des marchands
    for merchant_email, merchant_data in merchants_db.items():
        if 'products' in merchant_data:
            for product in merchant_data['products']:
                # Vérifier si ce produit n'est pas déjà dans stock_summary
                if not any(p['id'] == product['id'] for p in stock_summary):
                    stock_summary.append({
                        'id': product['id'],
                        'name': product['name'],
                        'stock': product.get('stock', 0),
                        'source': 'merchant',
                        'merchant_email': merchant_email,
                        'merchant_name': merchant_data.get('store_name', 'Marchand inconnu'),
                        'price': product.get('price', 0)
                    })
                    fallback_count += 1
    
    if fallback_count > 0:
        print(f"[STOCK] 🔄 {fallback_count} produits ajoutés depuis les dictionnaires (fallback)")
    
    print(f"[STOCK] 📊 Total des produits dans le résumé: {len(stock_summary)}")
    return stock_summary

# Fonctions utilitaires pour la gestion des IDs et authentification

def parse_admin_id(session_admin_id):
    """Parse l'ID de session admin pour extraire le type, l'ID réel et l'email si disponible"""
    if not session_admin_id:
        return None, None, None
    
    admin_id_str = str(session_admin_id)
    
    if admin_id_str.startswith('ADMIN_'):
        parts = admin_id_str.replace('ADMIN_', '').split('_')
        real_id = parts[0]
        email = '_'.join(parts[1:]) if len(parts) > 1 else None
        return 'admin', real_id, email
    elif admin_id_str.startswith('EMP_LEGACY_'):
        parts = admin_id_str.replace('EMP_LEGACY_', '').split('_')
        real_id = parts[0]
        email = '_'.join(parts[1:]) if len(parts) > 1 else None
        return 'employee_legacy', real_id, email
    elif admin_id_str.startswith('EMP_'):
        real_id = admin_id_str.replace('EMP_', '')
        return 'employee', real_id, None
    else:
        # Pour compatibilité avec l'ancien système
        return 'legacy', admin_id_str, None

def get_current_user_info():
    """Récupère les informations complètes de l'utilisateur connecté"""
    if 'admin_id' not in session:
        return None
    
    user_type, real_id, parsed_email = parse_admin_id(session.get('admin_id'))
    user_email = session.get('admin_email')
    
    user_info = {
        'type': user_type,
        'id': real_id,
        'parsed_email': parsed_email,
        'email': user_email,
        'role': session.get('admin_role'),
        'name': session.get('admin_name'),
        'session_type': session.get('user_type')
    }
    
    return user_info

def get_user_permissions():
    """Récupère les permissions de l'utilisateur connecté"""
    user_info = get_current_user_info()
    if not user_info:
        return []
    
    user_type = user_info['type']
    user_email = user_info['email']
    user_role = user_info['role']
    
    # Si c'est un employé de la base de données, récupérer ses permissions
    if user_type == 'employee':
        try:
            db_employee = Employee.query.filter_by(email=user_email, status='active').first()
            if db_employee:
                return db_employee.get_permissions()
        except Exception as e:
            print(f"Erreur récupération permissions employé DB: {e}")
    
    # Permissions par défaut basées sur le rôle
    role_permissions = {
        'super_admin': ['all'],
        'admin': ['manage_orders', 'manage_merchants', 'view_dashboard', 'view_users'],
        'manager': ['manage_orders', 'view_dashboard', 'view_merchants'],
        'livreur': ['view_orders', 'update_order_status', 'view_dashboard', 'view_history']
    }
    
    return role_permissions.get(user_role, [])

# Fonctions de gestion des permissions des employés
def get_employee_by_email(email):
    """Récupère un employé par son email"""
    return employees_db.get(email)

def get_user_role():
    """Récupère le rôle de l'utilisateur connecté (version mise à jour avec IDs préfixés)"""
    user_info = get_current_user_info()
    if not user_info:
        return None
    
    return user_info['role']

def has_permission(required_permission):
    """Vérifie si l'utilisateur a la permission requise"""
    user_role = get_user_role()
    
    if not user_role:
        return False
    
    # Définition des permissions par rôle
    permissions = {
        'super_admin': [
            'view_dashboard', 'view_orders', 'view_merchants', 'view_products', 
            'view_categories', 'view_users', 'view_settings', 'view_employees',
            'manage_orders', 'manage_merchants', 'manage_products', 
            'manage_categories', 'manage_users', 'manage_settings', 'manage_employees'
        ],
        'admin': [
            'view_dashboard', 'view_orders', 'view_merchants', 'view_products', 
            'view_categories', 'manage_orders', 'manage_merchants', 'manage_products', 
            'manage_categories'
        ],
        'manager': [
            'view_dashboard', 'view_orders', 'view_merchants', 'view_products', 
            'view_categories', 'manage_orders', 'manage_merchants', 'manage_products', 
            'manage_categories'
        ],
        'livreur': [
            'view_orders'
        ]
    }
    
    user_permissions = permissions.get(user_role, [])
    return required_permission in user_permissions

def permission_required(required_roles):
    """Décorateur pour vérifier les permissions basé sur les rôles"""
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(*args, **kwargs):
            # Vérifier si l'utilisateur est connecté en tant qu'admin ou employé
            if 'admin_id' not in session:
                flash('Vous devez être connecté en tant qu\'administrateur pour accéder à cette page.', 'warning')
                return redirect(url_for('admin_login'))
            
            # Vérifier le rôle de l'utilisateur
            user_role = get_user_role()
            if not user_role:
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('admin_login'))
            
            # Vérifier si le rôle de l'utilisateur est autorisé
            if user_role not in required_roles:
                flash('Vous n\'avez pas les permissions nécessaires pour accéder à cette page.', 'danger')
                return redirect(url_for('admin_dashboard'))
            
            return view(*args, **kwargs)
        return wrapped_view
    return decorator

# Décorateur pour les routes qui nécessitent une authentification
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            # Sauvegarder l'URL actuelle pour y revenir après connexion
            session['next_page'] = request.url
            return redirect(url_for('login'))  # Rediriger vers login au lieu d'access_denied
        
        # **NOUVELLE VÉRIFICATION : Vérifier si l'utilisateur est actif**
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        
        # Vérifier d'abord en base de données
        try:
            from models import User
            user_record = User.query.filter_by(id=user_id).first()
            if user_record and not user_record.is_active:
                # Déconnecter l'utilisateur désactivé
                session.clear()
                flash('Votre compte a été désactivé par un administrateur. Contactez le support si vous pensez qu\'il s\'agit d\'une erreur.', 'danger')
                return redirect(url_for('login'))
        except Exception as e:
            print(f"❌ Erreur vérification utilisateur actif DB: {e}")
            
        # Fallback: vérifier dans le dictionnaire
        if user_email and user_email in users_db:
            if not users_db[user_email].get('is_active', True):
                # Déconnecter l'utilisateur désactivé
                session.clear()
                flash('Votre compte a été désactivé par un administrateur. Contactez le support si vous pensez qu\'il s\'agit d\'une erreur.', 'danger')
                return redirect(url_for('login'))
        
        return view(*args, **kwargs)
    return wrapped_view

# Décorateur pour les routes qui nécessitent une authentification de marchand
def merchant_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'merchant_id' not in session:
            flash('Vous devez être connecté en tant que marchand pour accéder à cette page.', 'warning')
            # Sauvegarder l'URL actuelle pour y revenir après connexion
            session['next_page'] = request.url
            return redirect(url_for('merchant_login'))
        
        # Vérification du statut de suspension du marchand
        merchant_email = session.get('merchant_email')
        if merchant_email:
            # Vérifier d'abord dans la base de données
            merchant_db = Merchant.query.filter_by(email=merchant_email).first()
            if merchant_db and merchant_db.status == 'suspended':
                # Nettoyer la session du marchand suspendu
                keys_to_remove = [k for k in session if k.startswith('merchant_')]
                for key in keys_to_remove:
                    session.pop(key, None)
                flash('Votre compte marchand a été suspendu. Contactez l\'administration pour plus d\'informations.', 'danger')
                return redirect(url_for('merchant_account_suspended'))
            
            # Vérifier aussi dans le dictionnaire en mémoire (compatibilité)
            merchant_data = merchants_db.get(merchant_email)
            if merchant_data and (merchant_data.get('status') == 'suspended' or merchant_data.get('is_suspended', False)):
                # Nettoyer la session du marchand suspendu
                keys_to_remove = [k for k in session if k.startswith('merchant_')]
                for key in keys_to_remove:
                    session.pop(key, None)
                flash('Votre compte marchand a été suspendu. Contactez l\'administration pour plus d\'informations.', 'danger')
                return redirect(url_for('merchant_account_suspended'))
        
        return view(*args, **kwargs)
    return wrapped_view

# Décorateur pour les routes qui nécessitent une authentification administrateur
def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        # Vérifier si l'utilisateur est connecté en tant qu'admin ou employé
        if 'admin_id' not in session and 'admin_email' not in session:
            print(f"Tentative d'accès non autorisé au dashboard admin")  # Log pour déboguer
            flash('Vous devez être connecté en tant qu\'administrateur pour accéder à cette page.', 'warning')
            return redirect(url_for('admin_login'))
        
        # Vérifier le rôle de l'utilisateur
        user_role = get_user_role()
        if not user_role:
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('admin_login'))
        
        print(f"Accès autorisé au dashboard admin pour {session.get('admin_email')} (rôle: {user_role})")  # Log pour déboguer
        return view(*args, **kwargs)
    return wrapped_view

# Fonctions utilitaires pour gérer les assignations des commandes aux livreurs

def get_livreur_assigned_orders_count(livreur_email):
    """Retourne le nombre de commandes actuellement assignées à un livreur"""
    if livreur_email not in livreur_assignments_db:
        return 0
    return len(livreur_assignments_db[livreur_email])

def can_livreur_take_order(livreur_email):
    """Vérifie si un livreur peut prendre une nouvelle commande (max 3)"""
    return get_livreur_assigned_orders_count(livreur_email) < 3

def is_order_assigned(order_id, order_type='merchant', merchant_email=None):
    """Vérifie si une commande est déjà assignée à un livreur"""
    for livreur_email, assignments in livreur_assignments_db.items():
        for assignment in assignments:
            if (assignment['order_id'] == order_id and 
                assignment['order_type'] == order_type):
                # Pour les commandes marchands, vérifier aussi l'email du marchand
                if order_type == 'merchant' and merchant_email:
                    if assignment.get('merchant_email') == merchant_email:
                        return True, livreur_email
                else:
                    return True, livreur_email
    return False, None

def assign_order_to_livreur(order_id, order_type, livreur_email, merchant_email=None):
    """Assigne une commande à un livreur"""
    if not can_livreur_take_order(livreur_email):
        return False, "Le livreur a déjà atteint le maximum de 3 commandes"
    
    # Vérifier si la commande n'est pas déjà assignée
    is_assigned, assigned_to = is_order_assigned(order_id, order_type, merchant_email)
    if is_assigned:
        return False, f"Cette commande est déjà assignée au livreur {assigned_to}"
    
    # Récupérer les informations du livreur pour l'historique permanent
    from models import Employee
    employee = Employee.query.filter_by(email=livreur_email, role='livreur').first()
    
    # Sauvegarder dans la base de données pour historique permanent
    try:
        if order_type == 'merchant':
            from db_helpers import get_order_by_id
            db_order = get_order_by_id(order_id)
            if db_order and employee:
                db_order.delivery_employee_id = employee.id
                db_order.delivery_employee_email = employee.email
                db_order.delivery_employee_name = f"{employee.first_name} {employee.last_name}"
                db_order.delivery_employee_phone = employee.phone
                db_order.assigned_at = datetime.now()
                db.session.commit()
        elif order_type == 'admin':
            from db_helpers import get_admin_order_by_id
            admin_order = get_admin_order_by_id(order_id)
            if admin_order and employee:
                admin_order.delivery_employee_id = employee.id
                admin_order.delivery_employee_email = employee.email
                admin_order.delivery_employee_name = f"{employee.first_name} {employee.last_name}"
                admin_order.delivery_employee_phone = employee.phone
                admin_order.assigned_at = datetime.now()
                db.session.commit()
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde de l'assignation en DB: {e}")
    
    # Initialiser la liste d'assignations pour ce livreur si elle n'existe pas
    if livreur_email not in livreur_assignments_db:
        livreur_assignments_db[livreur_email] = []
    
    # Créer l'assignation
    assignment = {
        'order_id': order_id,
        'order_type': order_type,
        'assigned_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'merchant_email': merchant_email
    }
    
    livreur_assignments_db[livreur_email].append(assignment)
    return True, "Commande assignée avec succès"

def unassign_order_from_livreur(order_id, order_type, merchant_email=None):
    """Désassigne une commande d'un livreur (quand la commande est livrée ou annulée)"""
    for livreur_email, assignments in livreur_assignments_db.items():
        for i, assignment in enumerate(assignments):
            if (assignment['order_id'] == order_id and 
                assignment['order_type'] == order_type):
                # Pour les commandes marchands, vérifier aussi l'email du marchand
                if order_type == 'merchant' and merchant_email:
                    if assignment.get('merchant_email') == merchant_email:
                        del livreur_assignments_db[livreur_email][i]
                        return True
                else:
                    del livreur_assignments_db[livreur_email][i]
                    return True
    return False

def get_livreur_assigned_orders(livreur_email):
    """Retourne les commandes assignées à un livreur avec leurs détails (exclut automatiquement les commandes livrées/annulées)"""
    if livreur_email not in livreur_assignments_db:
        return []
    
    assigned_orders = []
    # Nettoyer automatiquement les assignations obsolètes
    assignments_to_remove = []
    
    for i, assignment in enumerate(livreur_assignments_db[livreur_email]):
        order_id = assignment['order_id']
        order_type = assignment['order_type']
        merchant_email = assignment.get('merchant_email')
        
        # **DATABASE-ONLY: Récupérer les détails de la commande depuis la DB uniquement**
        if order_type == 'merchant' and merchant_email:
            # Rechercher uniquement dans la base de données
            from db_helpers import get_order_by_id, get_merchant_by_email
            db_order = get_order_by_id(order_id)
            
            if db_order and db_order.merchant_id:
                # Filtrer automatiquement les commandes livrées ou annulées
                if db_order.status in ['delivered', 'cancelled']:
                    print(f"🧹 Commande marchand {order_id} ({db_order.status}) automatiquement filtrée du dashboard livreur")
                    assignments_to_remove.append(i)
                    continue
                
                merchant_record = get_merchant_by_email(merchant_email)
                if merchant_record and merchant_record.id == db_order.merchant_id:
                    order_copy = {
                        'id': db_order.id,
                        'order_number': db_order.order_number,
                        'customer_name': db_order.customer_name,
                        'customer_email': db_order.customer_email,
                        'total': db_order.total,
                        'status': db_order.status,
                        'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'merchant_name': merchant_record.store_name,
                        'merchant_email': merchant_email,
                        'assigned_at': assignment['assigned_at'],
                        'source': 'database'
                    }
                    # Enrichir avec les informations de statut
                    order_copy = enrich_order_with_status_info(order_copy)
                    assigned_orders.append(order_copy)
                else:
                    print(f"⚠️ Commande assignée {order_id} non trouvée en DB pour marchand {merchant_email}")
                    assignments_to_remove.append(i)
            else:
                print(f"⚠️ Commande assignée {order_id} non trouvée en DB")
                assignments_to_remove.append(i)
                
        elif order_type == 'admin':
            # **DATABASE-ONLY: Rechercher uniquement dans la base de données**
            from db_helpers import get_admin_order_by_id
            admin_order = get_admin_order_by_id(order_id)
            if admin_order:
                # Filtrer automatiquement les commandes livrées ou annulées
                if admin_order.status in ['delivered', 'cancelled']:
                    print(f"🧹 Commande admin {order_id} ({admin_order.status}) automatiquement filtrée du dashboard livreur")
                    assignments_to_remove.append(i)
                    continue
                    
                order_copy = {
                    'id': admin_order.id,
                    'order_number': admin_order.order_number,
                    'customer_name': admin_order.customer_name,
                    'customer_email': admin_order.customer_email,
                    'total': admin_order.total,
                    'status': admin_order.status,
                    'created_at': admin_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'merchant_name': 'DOUKA KM',
                    'merchant_email': 'admin',
                    'assigned_at': assignment['assigned_at'],
                    'source': 'database'
                }
                # Enrichir avec les informations de statut
                order_copy = enrich_order_with_status_info(order_copy)
                assigned_orders.append(order_copy)
            else:
                print(f"⚠️ Commande admin assignée {order_id} non trouvée en DB")
                assignments_to_remove.append(i)
    
    # Nettoyer les assignations obsolètes (en ordre inverse pour éviter les décalages d'index)
    for i in reversed(assignments_to_remove):
        print(f"🧹 Suppression assignation obsolète à l'index {i} pour livreur {livreur_email}")
        del livreur_assignments_db[livreur_email][i]
    
    if assignments_to_remove:
        print(f"✅ Dashboard livreur {livreur_email} nettoyé: {len(assignments_to_remove)} assignations obsolètes supprimées")
    
    return assigned_orders

def get_available_orders_for_livreur():
    """Retourne les commandes disponibles (non assignées) pour les livreurs - Version 100% migrée vers base de données"""
    available_orders = []
    
    # **DATABASE-ONLY: Récupérer uniquement les commandes des marchands depuis la base de données**
    from db_helpers import get_all_merchant_orders, get_merchant_by_id
    
    # Récupérer les commandes des marchands depuis la DB
    db_orders = get_all_merchant_orders()
    
    print(f"🔍 Commandes marchands trouvées en DB: {len(db_orders)}")
    
    for db_order in db_orders:
        # Seules les commandes processing et shipped peuvent être assignées
        if db_order.status in ['processing', 'shipped']:
            is_assigned, _ = is_order_assigned(db_order.id, 'merchant', None)
            if not is_assigned:
                merchant_info = get_merchant_by_id(db_order.merchant_id) if db_order.merchant_id else None
                
                order_copy = {
                    'id': db_order.id,
                    'order_number': db_order.order_number,
                    'customer_name': db_order.customer_name,
                    'total': db_order.total,
                    'status': db_order.status,
                    'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'merchant_name': merchant_info.store_name if merchant_info else 'Marchand',
                    'merchant_email': merchant_info.email if merchant_info else 'unknown',
                    'type': 'merchant',
                    'source': 'database'
                }
                # Enrichir avec les informations de statut
                order_copy = enrich_order_with_status_info(order_copy)
                available_orders.append(order_copy)
    
    print(f"🔍 Commandes marchands disponibles pour livreur: {len([o for o in available_orders if o['type'] == 'merchant'])}")
    
    # **DATABASE-ONLY: Commandes admin depuis la base de données uniquement**
    from db_helpers import get_admin_orders_by_status_list
    admin_orders = get_admin_orders_by_status_list(['processing', 'shipped'])
    
    print(f"🔍 Commandes admin trouvées en DB: {len(admin_orders)}")
    
    for order in admin_orders:
        # Vérifier si la commande n'est pas déjà assignée
        is_assigned, _ = is_order_assigned(order.id, 'admin')
        if not is_assigned:
            order_copy = {
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'customer_email': order.customer_email,
                'total': order.total,
                'status': order.status,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'merchant_name': 'DOUKA KM',
                'merchant_email': 'admin',
                'type': 'admin',
                'source': 'database'
            }
            # Enrichir avec les informations de statut
            order_copy = enrich_order_with_status_info(order_copy)
            available_orders.append(order_copy)
    
    print(f"🔍 Commandes admin disponibles pour livreur: {len([o for o in available_orders if o['type'] == 'admin'])}")
    print(f"✅ Total commandes disponibles pour livreur: {len(available_orders)}")
    
    # Trier par date (plus récent en premier)
    available_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return available_orders

def can_order_be_cancelled(order):
    """
    Vérifie si une commande peut être annulée par le client
    
    RÈGLE STRICTE: Seulement les commandes "Processing" avec "Paiement à la livraison" peuvent être annulées
    
    Args:
        order (dict): Dictionnaire contenant les informations de la commande
    
    Returns:
        tuple: (can_cancel: bool, reason: str)
    """
    current_status = order.get('status', '')
    payment_method = order.get('payment_method', '').lower()
    
    # RÈGLE UNIQUE: Seulement Processing + Paiement à la livraison (ou cash) peut être annulé
    if current_status == 'processing' and ('paiement à la livraison' in payment_method or 'cash' in payment_method):
        return True, ''
    
    # Tous les autres cas ne peuvent pas être annulés
    if current_status == 'shipped':
        return False, 'Cette commande ne peut plus être annulée car elle est déjà expédiée'
    elif current_status == 'delivered':
        return False, 'Cette commande ne peut plus être annulée car elle est déjà livrée'
    elif current_status == 'cancelled':
        return False, 'Cette commande est déjà annulée'
    elif current_status == 'pending':
        return False, 'Cette commande est en attente de confirmation et ne peut pas être annulée'
    elif current_status == 'confirmed':
        return False, 'Cette commande confirmée ne peut pas être annulée'
    elif current_status == 'processing':
        # Processing mais pas paiement à la livraison
        return False, f'Cette commande ne peut pas être annulée car vous avez choisi le paiement par {order.get("payment_method", "méthode électronique")}'
    else:
        return False, f'Cette commande ne peut plus être annulée (statut: {current_status})'

def enrich_order_with_status_info(order_data):
    """
    Enrichit une commande avec les informations de statut formatées (status_text et status_color)
    
    Args:
        order_data (dict): Dictionnaire de commande
    
    Returns:
        dict: Commande enrichie avec status_text et status_color
    """
    status_mappings = {
        'processing': {
            'text': 'En cours de préparation',
            'color': 'primary'
        },
        'shipped': {
            'text': 'Expédiée',
            'color': 'info'
        },
        'delivered': {
            'text': 'Livrée',
            'color': 'success'
        },
        'cancelled': {
            'text': 'Annulée',
            'color': 'danger'
        }
    }
    
    status = order_data.get('status', 'processing')
    status_info = status_mappings.get(status, status_mappings['processing'])
    
    # Enrichir avec les informations de statut
    order_data['status_text'] = status_info['text']
    order_data['status_color'] = status_info['color']
    
    return order_data

def get_payment_method_info(payment_method):
    """
    Retourne les informations sur une méthode de paiement
    
    Args:
        payment_method (str): Nom de la méthode de paiement
    
    Returns:
        dict: Informations sur la méthode de paiement
    """
    payment_methods = {
        'mvola': {
            'name': 'Mvola',
            'type': 'mobile_money',
            'allows_cancellation': False,
            'icon': 'fas fa-mobile-alt',
            'color': 'warning'
        },
        'holo': {
            'name': 'Holo',
            'type': 'mobile_money',
            'allows_cancellation': False,
            'icon': 'fas fa-mobile-alt',
            'color': 'info'
        },
        'carte bancaire': {
            'name': 'Carte Bancaire',
            'type': 'card',
            'allows_cancellation': False,
            'icon': 'fas fa-credit-card',
            'color': 'primary'
        },
        'paiement à la livraison': {
            'name': 'Paiement à la livraison',
            'type': 'cash_on_delivery',
            'allows_cancellation': True,
            'icon': 'fas fa-hand-holding-usd',
            'color': 'success'
        },
        'cash': {
            'name': 'Cash',
            'type': 'cash_on_delivery',
            'allows_cancellation': True,
            'icon': 'fas fa-hand-holding-usd',
            'color': 'success'
        }
    }
    
    method_key = payment_method.lower()
    return payment_methods.get(method_key, {
        'name': payment_method,
        'type': 'unknown',
        'allows_cancellation': True,
        'icon': 'fas fa-question-circle',
        'color': 'secondary'
    })

def generate_slug(text):
    """Génère un slug à partir d'un texte"""
    import re
    import unicodedata
    
    # Convertir en minuscules et normaliser les caractères unicode
    slug = unicodedata.normalize('NFKD', text.lower())
    
    # Remplacer les caractères spéciaux
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ýÿ]', 'y', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    slug = re.sub(r'[ñ]', 'n', slug)
    
    # Remplacer les espaces et caractères non alphanumériques par des tirets
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Supprimer les tirets en début et fin
    slug = slug.strip('-')
    
    return slug

def get_commission_rate_for_product(product_id):
    """Récupère le taux de commission applicable pour un produit donné"""
    try:
        # Récupérer le produit et sa catégorie
        from models import Product
        product = Product.query.get(product_id)
        
        if not product or not product.category_id:
            # Utiliser le taux par défaut si pas de catégorie
            site_settings = get_site_settings()
            return float(site_settings.get('commission_rate', 15.0)) / 100
        
        # Chercher un taux spécifique pour cette catégorie
        category_rate = CategoryCommissionRate.query.filter_by(
            category_id=product.category_id,
            active=True
        ).first()
        
        if category_rate:
            return float(category_rate.commission_rate) / 100
        
        # Utiliser le taux par défaut
        site_settings = get_site_settings()
        return float(site_settings.get('commission_rate', 15.0)) / 100
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du taux de commission: {e}")
        # Retourner le taux par défaut en cas d'erreur
        return 0.15  # 15%

def get_commission_rate_for_category(category_id):
    """Récupère le taux de commission pour une catégorie donnée"""
    try:
        if not category_id:
            site_settings = get_site_settings()
            return float(site_settings.get('commission_rate', 15.0)) / 100
        
        # Chercher un taux spécifique pour cette catégorie
        category_rate = CategoryCommissionRate.query.filter_by(
            category_id=category_id,
            active=True
        ).first()
        
        if category_rate:
            return float(category_rate.commission_rate) / 100
        
        # Utiliser le taux par défaut
        site_settings = get_site_settings()
        return float(site_settings.get('commission_rate', 15.0)) / 100
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du taux de commission pour la catégorie: {e}")
        return 0.15  # 15%

def get_categories_for_display():
    """Récupère les catégories actives pour l'affichage sur la page d'accueil (maximum 4)"""
    try:
        # Récupérer les catégories actives depuis la base de données, limitées à 4
        categories = Category.query.filter_by(active=True).order_by(Category.name).limit(4).all()
        
        categories_list = []
        for category in categories:
            # Générer un slug pour la catégorie
            category_slug = generate_slug(category.name)
            
            # Générer une image par défaut basée sur le nom de la catégorie
            category_image = generate_category_image(category.name, category.id)
            
            categories_list.append({
                'id': category.id,
                'name': category.name,
                'description': category.description or f'Découvrez nos produits {category.name.lower()}',
                'image': category_image,
                'icon': category.icon or 'fas fa-folder',
                'url': f'/category/{category_slug}'
            })
        
        return categories_list
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des catégories pour affichage: {e}")
        # Retourner des catégories par défaut en cas d'erreur
        return get_default_categories()

def generate_category_image(category_name, category_id):
    """Génère le chemin de l'image pour une catégorie avec intelligence artificielle"""
    import os
    
    # Mappage intelligent des noms de catégories vers des images
    category_mappings = {
        # Bébé et enfants
        'bébé': 'img/categories/baby.jpg',
        'bebe': 'img/categories/baby.jpg',
        'baby': 'img/categories/baby.jpg',
        'enfant': 'img/categories/baby.jpg',
        'enfants': 'img/categories/baby.jpg',
        'children': 'img/categories/baby.jpg',
        'kids': 'img/categories/baby.jpg',
        'puériculture': 'img/categories/baby.jpg',
        'nourrisson': 'img/categories/baby.jpg',
        'bambin': 'img/categories/baby.jpg',
        'petite enfance': 'img/categories/baby.jpg',
        
        # Électronique et technologie
        'électronique': 'img/category1.jpg',
        'electronique': 'img/category1.jpg',
        'electronics': 'img/category1.jpg',
        'technologie': 'img/category1.jpg',
        'informatique': 'img/category1.jpg',
        'téléphones': 'img/category1.jpg',
        'ordinateurs': 'img/category1.jpg',
        'appareils': 'img/category1.jpg',
        'gadgets': 'img/category1.jpg',
        'smartphones': 'img/category1.jpg',
        
        # Mode et vêtements
        'vêtements': 'img/category2.jpg',
        'vetements': 'img/category2.jpg',
        'clothing': 'img/category2.jpg',
        'mode': 'img/category2.jpg',
        'fashion': 'img/category2.jpg',
        'chaussures': 'img/category2.jpg',
        'accessoires': 'img/category2.jpg',
        'textile': 'img/category2.jpg',
        'habits': 'img/category2.jpg',
        'tenues': 'img/category2.jpg',
        
        # Alimentation et produits frais
        'alimentation': 'img/category3.jpg',
        'food': 'img/category3.jpg',
        'nourriture': 'img/category3.jpg',
        'cuisine': 'img/category3.jpg',
        'épicerie': 'img/category3.jpg',
        'boissons': 'img/category3.jpg',
        'fruits': 'img/category3.jpg',
        'légumes': 'img/category3.jpg',
        'bio': 'img/category3.jpg',
        'alimentaire': 'img/category3.jpg',
        
        # Artisanat et culture locale
        'artisanat': 'img/category4.jpg',
        'artisanat local': 'img/category4.jpg',
        'crafts': 'img/category4.jpg',
        'fait main': 'img/category4.jpg',
        'traditionnel': 'img/category4.jpg',
        'local': 'img/category4.jpg',
        'culture': 'img/category4.jpg',
        'art': 'img/category4.jpg',
        
        # Beauté et cosmétiques
        'beauté': 'img/categories/beauty.jpg',
        'cosmétiques': 'img/categories/beauty.jpg',
        'cosmetics': 'img/categories/beauty.jpg',
        'beauty': 'img/categories/beauty.jpg',
        'maquillage': 'img/categories/beauty.jpg',
        'parfum': 'img/categories/beauty.jpg',
        'soins': 'img/categories/beauty.jpg',
        'skincare': 'img/categories/beauty.jpg',
        
        # Sport et fitness
        'sport': 'img/categories/sports.jpg',
        'sports': 'img/categories/sports.jpg',
        'fitness': 'img/categories/sports.jpg',
        'gym': 'img/categories/sports.jpg',
        'équipement sportif': 'img/categories/sports.jpg',
        'musculation': 'img/categories/sports.jpg',
        'course': 'img/categories/sports.jpg',
        'natation': 'img/categories/sports.jpg',
        
        # Maison et jardin
        'maison': 'img/categories/home.jpg',
        'home': 'img/categories/home.jpg',
        'décoration': 'img/categories/home.jpg',
        'meubles': 'img/categories/home.jpg',
        'jardin': 'img/categories/home.jpg',
        'garden': 'img/categories/home.jpg',
        'bricolage': 'img/categories/home.jpg',
        'électroménager': 'img/categories/home.jpg',
        'home & garden': 'img/categories/home.jpg',
        
        # Livres et éducation
        'livres': 'img/categories/books.jpg',
        'books': 'img/categories/books.jpg',
        'éducation': 'img/categories/books.jpg',
        'education': 'img/categories/books.jpg',
        'apprentissage': 'img/categories/books.jpg',
        'lecture': 'img/categories/books.jpg',
        'formation': 'img/categories/books.jpg',
        'cours': 'img/categories/books.jpg',
        
        # Santé et bien-être
        'santé': 'img/categories/health.jpg',
        'health': 'img/categories/health.jpg',
        'bien-être': 'img/categories/health.jpg',
        'wellness': 'img/categories/health.jpg',
        'médical': 'img/categories/health.jpg',
        'pharmacie': 'img/categories/health.jpg',
        'vitamines': 'img/categories/health.jpg',
        'supplements': 'img/categories/health.jpg',
        
        # Automobile
        'automobile': 'img/categories/auto.jpg',
        'auto': 'img/categories/auto.jpg',
        'voiture': 'img/categories/auto.jpg',
        'véhicule': 'img/categories/auto.jpg',
        'moto': 'img/categories/auto.jpg',
        'pièces auto': 'img/categories/auto.jpg',
        'automotive': 'img/categories/auto.jpg',
        
        # Animaux
        'animaux': 'img/categories/pets.jpg',
        'pets': 'img/categories/pets.jpg',
        'chien': 'img/categories/pets.jpg',
        'chat': 'img/categories/pets.jpg',
        'animalerie': 'img/categories/pets.jpg',
        'pet supplies': 'img/categories/pets.jpg',
        
        # Musique et instruments
        'musique': 'img/categories/music.jpg',
        'music': 'img/categories/music.jpg',
        'instruments': 'img/categories/music.jpg',
        'audio': 'img/categories/music.jpg',
        'sound': 'img/categories/music.jpg',
        'musical': 'img/categories/music.jpg',
        
        # Jeux et jouets
        'jeux': 'img/categories/toys.jpg',
        'jouets': 'img/categories/toys.jpg',
        'toys': 'img/categories/toys.jpg',
        'games': 'img/categories/toys.jpg',
        'gaming': 'img/categories/toys.jpg',
        'console': 'img/categories/toys.jpg',
        'divertissement': 'img/categories/toys.jpg'
    }
    
    # Normaliser le nom de la catégorie
    category_name_clean = category_name.lower().strip()
    
    # Recherche exacte
    if category_name_clean in category_mappings:
        return category_mappings[category_name_clean]
    
    # Recherche par mots-clés
    for keyword, image in category_mappings.items():
        if keyword in category_name_clean or category_name_clean in keyword:
            return category_mappings[keyword]
    
    # Vérifier si des images personnalisées existent pour cette catégorie
    custom_image_path = f'img/categories/category_{category_id}.jpg'
    full_path = os.path.join('static', custom_image_path)
    
    if os.path.exists(full_path):
        return custom_image_path
    
    # Images par défaut avec rotation intelligente
    default_images = [
        'img/category1.jpg',  # Électronique (bleu)
        'img/category2.jpg',  # Mode (rose/violet) 
        'img/category3.jpg',  # Alimentation (vert)
        'img/category4.jpg'   # Artisanat (orange/marron)
    ]
    
    # Utiliser le hash du nom de catégorie pour une distribution plus équitable
    import hashlib
    category_hash = hashlib.md5(category_name_clean.encode()).hexdigest()
    image_index = int(category_hash[:2], 16) % len(default_images)
    
    return default_images[image_index]

def get_default_categories():
    """Retourne des catégories par défaut en cas d'erreur"""
    return [
        {
            'id': 1,
            'name': 'Électronique',
            'description': 'Découvrez nos produits électroniques',
            'image': 'img/category1.jpg',
            'icon': 'fas fa-laptop',
            'url': '/products?category_filter=1'
        },
        {
            'id': 2,
            'name': 'Vêtements',
            'description': 'Mode et vêtements pour tous',
            'image': 'img/category2.jpg',
            'icon': 'fas fa-tshirt',
            'url': '/products?category_filter=2'
        },
        {
            'id': 3,
            'name': 'Alimentation',
            'description': 'Produits alimentaires frais',
            'image': 'img/category3.jpg',
            'icon': 'fas fa-apple-alt',
            'url': '/products?category_filter=3'
        },
        {
            'id': 4,
            'name': 'Artisanat local',
            'description': 'Artisanat traditionnel comorien',
            'image': 'img/category4.jpg',
            'icon': 'fas fa-palette',
            'url': '/products?category_filter=4'
        }
    ]

@app.route('/')
def home():
    # Get all products from active categories for public display
    all_products = get_public_products()
    
    # Sample featured products for homepage - mix of admin, merchant and static products
    featured_products = []
    
    # Séparer les produits par source
    admin_products = [p for p in all_products if p.get('source') == 'admin']
    merchant_products = [p for p in all_products if p.get('source') == 'merchant']
    static_products = [p for p in all_products if p.get('source') == 'static']
    
    # Trier tous les produits par date de création (plus récents en premier)
    admin_products = sorted(admin_products, key=lambda x: x.get('created_at', ''), reverse=True)
    merchant_products = sorted(merchant_products, key=lambda x: x.get('created_at', ''), reverse=True)
    static_products = sorted(static_products, key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Priorité aux produits récents : admin d'abord, puis marchands, puis statiques
    # Add 2 most recent admin products first
    featured_products.extend(admin_products[:2])
    
    # Add 2 most recent merchant products
    remaining_slots = 6 - len(featured_products)
    if remaining_slots > 0:
        featured_products.extend(merchant_products[:min(2, remaining_slots)])
    
    # Fill remaining slots with static products if needed
    remaining_slots = 6 - len(featured_products)
    if remaining_slots > 0:
        featured_products.extend(static_products[:remaining_slots])
    
    # Limit to 6 featured products for display
    featured_products = featured_products[:6]
    
    # Produits recommandés basés sur l'historique du client
    recommended_products = []
    
    # Vérifier si l'utilisateur est authentifié et a un historique
    user_id = session.get('user_id')
    if user_id:
        # Dans une application réelle, cela viendrait d'une base de données
        # Ici, nous simulons des recommandations basées sur l'historique
        viewed_products = session.get('viewed_products', [])
        
        if viewed_products:
            # Prioritize recent admin and merchant products for recommendations
            recent_admin_products = [p for p in all_products if p.get('source') == 'admin'][:1]
            recent_merchant_products = [p for p in all_products if p.get('source') == 'merchant'][:1]
            other_products = [p for p in all_products if p not in featured_products and p not in recent_admin_products and p not in recent_merchant_products]
            
            # Create recommendations with recent admin and merchant products first
            recommendations = recent_admin_products + recent_merchant_products + other_products
            recommended_products = recommendations[:4]
        else:
            # For users without history, show recent admin and merchant products
            recent_admin_products = [p for p in all_products if p.get('source') == 'admin'][:1]
            recent_merchant_products = [p for p in all_products if p.get('source') == 'merchant'][:1]
            other_trending = [p for p in all_products if p not in featured_products and p not in recent_admin_products and p not in recent_merchant_products]
            
            recommendations = recent_admin_products + recent_merchant_products + other_trending
            recommended_products = recommendations[:4]
    else:
        # Pour les utilisateurs non connectés, afficher les produits récents admin et marchands en priorité
        recent_admin_products = [p for p in all_products if p.get('source') == 'admin'][:1]
        recent_merchant_products = [p for p in all_products if p.get('source') == 'merchant'][:1]
        other_trending = [p for p in all_products if p not in featured_products and p not in recent_admin_products and p not in recent_merchant_products]
        
        recommendations = recent_admin_products + recent_merchant_products + other_trending
        recommended_products = recommendations[:4]
    
    # Récupérer les catégories actives pour la section "Nos catégories"
    categories_for_display = get_categories_for_display()
    
    return render_template('home.html', 
                         products=featured_products, 
                         recommended_products=recommended_products,
                         display_categories=categories_for_display)

@app.route('/api/search-suggestions')
def search_suggestions():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    # Récupérer tous les produits publics
    all_products = get_public_products()
    
    # Filtrer les produits qui correspondent à la recherche
    filtered_products = []
    for product in all_products:
        name_match = query.lower() in product['name'].lower()
        desc_match = query.lower() in product['description'].lower()
        if name_match or desc_match:
            # Récupérer le nom de la catégorie
            category_name = get_category_name(product.get('category_id'))
            
            filtered_products.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'category': category_name
            })
    
    # Limiter à 10 suggestions maximum
    filtered_products = filtered_products[:10]
    
    return jsonify(filtered_products)

@app.route('/products')
def products():
    # Récupérer les catégories avec leurs sous-catégories pour l'affichage public
    categories = get_categories_with_subcategories()
    
    # Extended product list for products page - Now uses public products (from active categories)
    all_products = get_public_products()
    
    # Récupérer les paramètres de filtrage et de pagination
    search_query = request.args.get('q', '').lower()
    category_filters = request.args.getlist('category_filter')
    subcategory_filters = request.args.getlist('subcategory_filter')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    in_stock = request.args.get('in_stock', '')
    sort_option = request.args.get('sort', 'newest')  # Défaut: plus récents en premier
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 20 produits par page
    
    # Log pour déboguer
    print(f"Sort option received: {sort_option}")
    
    # Convertir les paramètres numériques
    try:
        min_price = int(min_price) if min_price else None
    except ValueError:
        min_price = None
        
    try:
        max_price = int(max_price) if max_price else None
    except ValueError:
        max_price = None
    
    # Filtrer les produits
    filtered_products = all_products
    
    # Filtrer par recherche
    if search_query:
        filtered_products = [p for p in filtered_products if 
                            search_query in p['name'].lower() or 
                            search_query in p['description'].lower()]
    
    # Filtrer par catégorie
    if category_filters:
        category_ids = [int(cat_id) for cat_id in category_filters]
        filtered_products = [p for p in filtered_products if p['category_id'] in category_ids]
    
    # Filtrer par sous-catégorie
    if subcategory_filters:
        subcategory_ids = [int(subcat_id) for subcat_id in subcategory_filters]
        filtered_products = [p for p in filtered_products if p.get('subcategory_id') in subcategory_ids]
    # Filtrer par prix
    if min_price is not None:
        filtered_products = [p for p in filtered_products if p['price'] >= min_price]
    if max_price is not None:
        filtered_products = [p for p in filtered_products if p['price'] <= max_price]
    
    # Filtrer par disponibilité
    if in_stock:
        filtered_products = [p for p in filtered_products if p.get('in_stock', True)]
    
    # CORRECTION: Tri des produits - Vérifier le type et appliquer le tri
    print(f"Applying sort: {sort_option}")
    if sort_option == 'price_asc':
        filtered_products = sorted(filtered_products, key=lambda p: p['price'])
        print("Sorting by price ascending")
    elif sort_option == 'price_desc':
        filtered_products = sorted(filtered_products, key=lambda p: p['price'], reverse=True)
        print("Sorting by price descending")
    elif sort_option == 'name_asc':
        filtered_products = sorted(filtered_products, key=lambda p: p['name'])
        print("Sorting by name A-Z")
    elif sort_option == 'name_desc':
        filtered_products = sorted(filtered_products, key=lambda p: p['name'], reverse=True)
        print("Sorting by name Z-A")
    elif sort_option == 'newest' or sort_option == 'default':
        # Tri par date de création (plus récent en premier)
        filtered_products = sorted(filtered_products, key=lambda p: p.get('created_at', ''), reverse=True)
        print("Sorting by newest first")
    elif sort_option == 'oldest':
        # Tri par date de création (plus ancien en premier)
        filtered_products = sorted(filtered_products, key=lambda p: p.get('created_at', ''))
        print("Sorting by oldest first")
    else:
        # Par défaut: produits les plus récents en premier
        filtered_products = sorted(filtered_products, key=lambda p: p.get('created_at', ''), reverse=True)
        print("Using fallback sort: newest first")
    
    # Calcul de la pagination
    total_products = len(filtered_products)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    products_for_page = filtered_products[start_index:end_index]
    
    # Calcul des pages
    total_pages = (total_products + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    # Information de pagination
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_products,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': prev_page,
        'next_page': next_page,
        'start_index': start_index + 1,
        'end_index': min(end_index, total_products)
    }
    
    # Ajouter des logs pour inspecter les produits triés
    if products_for_page:
        print(f"First few products after sorting:")
        for i, p in enumerate(products_for_page[:3]):
            print(f"{i+1}. {p['name']} - {p['price']} KMF")
    
    print(f"Pagination: Page {page}/{total_pages}, Produits {start_index + 1}-{min(end_index, total_products)} sur {total_products}")
    
    # S'assurer que sort_option est correctement passé au template
    return render_template('products.html', 
                          products=products_for_page, 
                          categories=categories,
                          search_query=search_query,
                          sort_option=sort_option,
                          pagination=pagination_info)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    # Utiliser la fonction get_product_by_id pour récupérer les produits (statiques + marchands)
    product = get_product_by_id(product_id)
    
    if product:
        # Vérifier si l'utilisateur est admin ou si le produit est accessible au public
        is_admin = session.get('admin_email') is not None
        
        if not is_admin and not is_product_public(product):
            flash('Ce produit n\'est plus disponible.', 'warning')
            return redirect(url_for('products'))
        
        # Vérifier si le produit est dans la liste d'envies de l'utilisateur
        in_wishlist = False
        if 'user_id' in session:
            user_id = session.get('user_id')
            # Vérifier dans la base de données si le produit est dans la wishlist
            existing_wishlist_item = WishlistItem.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()
            in_wishlist = existing_wishlist_item is not None
        
        # Enregistrement du produit vu dans l'historique de l'utilisateur
        if 'user_id' in session:
            viewed_products = session.get('viewed_products', [])
            
            # Éviter les doublons en vérifiant si le produit est déjà dans l'historique
            if product_id not in viewed_products:
                viewed_products.append(product_id)
                # Limiter la taille de l'historique (garder les 10 derniers produits vus)
                if len(viewed_products) > 10:
                    viewed_products = viewed_products[-10:]
                
                session['viewed_products'] = viewed_products
        
        # Récupérer les avis du produit
        product_reviews = get_product_reviews(product_id)
        avg_rating, reviews_count = calculate_average_rating(product_id)
        
        # Mettre à jour la note du produit avec les avis réels
        product['rating'] = avg_rating if avg_rating > 0 else product.get('rating', 0)
        product['reviews_count'] = reviews_count
        
        # Ajouter le nom de la catégorie au produit pour l'affichage
        if product.get('category_id'):
            product['category_name'] = get_category_name(product['category_id'])
        else:
            product['category_name'] = None
        
        # Get related products based on category
        all_products = get_public_products()  # Utiliser get_public_products pour exclure les produits non disponibles
        
        # D'abord, essayer de trouver des produits de la même catégorie
        related_products = []
        product_category_id = product.get('category_id')
        
        if product_category_id:
            # Récupérer les produits de la même catégorie (exclure le produit actuel)
            same_category_products = [
                p for p in all_products 
                if p.get('category_id') == product_category_id and p['id'] != product_id
            ]
            # Trier par popularité/note puis prendre les 4 premiers
            same_category_products.sort(key=lambda x: (
                x.get('rating', 0), 
                len(x.get('reviews', [])),  # Nombre d'avis
                x.get('id', 0)  # ID comme critère de tri stable
            ), reverse=True)
            related_products = same_category_products[:4]
        
        # Si pas assez de produits de la même catégorie, compléter avec d'autres produits
        if len(related_products) < 4:
            # Récupérer des produits d'autres catégories
            other_products = [
                p for p in all_products 
                if p['id'] != product_id and p['id'] not in [rp['id'] for rp in related_products]
            ]
            # Trier par popularité
            other_products.sort(key=lambda x: (
                x.get('rating', 0), 
                len(x.get('reviews', [])),
                x.get('id', 0)
            ), reverse=True)
            
            # Compléter jusqu'à 4 produits max
            needed = 4 - len(related_products)
            related_products.extend(other_products[:needed])
        
        # Récupérer les informations de livraison dynamiques pour ce produit
        product_shipping = get_shipping_rates_for_product(product)
        site_settings = get_site_settings()
        
        shipping_info = {
            'shipping_fee': product_shipping['standard_rate'],
            'express_rate': product_shipping['express_rate'],
            'free_shipping_threshold': product_shipping['free_shipping_threshold'],
            'delivery_times': {
                'Grande Comore': product_shipping['standard_delivery_time'],
                'Anjouan': product_shipping['standard_delivery_time'], 
                'Mohéli': product_shipping['standard_delivery_time'],
                'express': product_shipping['express_delivery_time']
            }
        }
        
        # Debug pour vérifier les données du produit côté admin
        if product.get('source') == 'admin':
            print(f"DEBUG Affichage produit admin ID {product_id}:")
            print(f"  - Couleurs: {product.get('colors', [])}")
            print(f"  - Tailles: {product.get('sizes', [])}")
            print(f"  - Combinaisons prix: {product.get('price_combinations', [])}")
        
        return render_template('product_detail.html', 
                             product=product, 
                             related_products=related_products, 
                             in_wishlist=in_wishlist,
                             reviews=product_reviews,
                             avg_rating=avg_rating,
                             reviews_count=reviews_count,
                             shipping_info=shipping_info)
    else:
        # Handle product not found
        return render_template('404.html'), 404

@app.route('/about')
def about():
    # Statistiques de la plateforme
    total_products = len(get_all_products())
    total_merchants = len(merchants_db)
    total_categories = len(get_active_categories())
    
    # Témoignages clients
    testimonials = [
        {
            'name': 'Fatima Ahmed',
            'location': 'Moroni, Grande Comore',
            'comment': 'DOUKA KM a révolutionné ma façon de faire mes achats. Je trouve tout ce dont j\'ai besoin avec une livraison rapide.',
            'rating': 5,
            'avatar': 'https://images.unsplash.com/photo-1494790108755-2616b612b786?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&h=150&q=80'
        },
    ]
    
    # Équipe dirigeante
    team_members = [
        {
            'name': 'Mohamed Abdallah',
            'role': 'CEO & Fondateur',
            'description': 'Entrepreneur passionné par le développement technologique aux Comores.',
            'avatar': '',
            'linkedin': '#',
            'twitter': '#'
        },
        {
            'name': 'N/A',
            'role': 'CTO',
            'description': 'Ingénieure logiciel avec plus de 10 ans d\'expérience dans le e-commerce.',
            'avatar': '',
            'linkedin': '#',
            'twitter': '#'
        },
        {
            'name': 'N/A',
            'role': 'Directeur Commercial',
            'description': 'Expert en développement des partenariats et relations marchands.',
            'avatar': '',
            'linkedin': '#',
            'twitter': '#'
        }
    ]
    
    # Partenaires
    partners = [
        {
            'name': 'Banque des Comores',
            'logo': 'https://via.placeholder.com/150x80/0066cc/ffffff?text=BDC',
            'type': 'Partenaire financier'
        },
        {
            'name': 'Poste Comores',
            'logo': 'https://via.placeholder.com/150x80/ff6600/ffffff?text=POSTE',
            'type': 'Partenaire logistique'
        },
        {
            'name': 'Orange Comores',
            'logo': 'https://via.placeholder.com/150x80/ff8800/ffffff?text=ORANGE',
            'type': 'Partenaire technologique'
        },
        {
            'name': 'Chambre de Commerce',
            'logo': 'https://via.placeholder.com/150x80/2e7d32/ffffff?text=CCI',
            'type': 'Partenaire institutionnel'
        }
    ]
    
    return render_template('about.html', 
                         total_products=total_products,
                         total_merchants=total_merchants,
                         total_categories=total_categories,
                         testimonials=testimonials,
                         team_members=team_members,
                         partners=partners)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Traitement du formulaire de contact
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        contact_type = request.form.get('contact_type', 'general')
        
        # Validation des champs obligatoires
        if not all([name, email, subject, message]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Tous les champs obligatoires doivent être remplis.'
                })
            flash('Tous les champs obligatoires doivent être remplis.', 'error')
            return redirect(url_for('contact'))
        
        # Validation de l'email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Veuillez saisir une adresse email valide.'
                })
            flash('Veuillez saisir une adresse email valide.', 'error')
            return redirect(url_for('contact'))
        
        # Créer un message de contact
        contact_message = {
            'id': len(globals().get('contact_messages', [])) + 1,
            'name': name,
            'email': email,
            'phone': phone,
            'subject': subject,
            'message': message,
            'contact_type': contact_type,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'new',
            'read': False
        }
        
        # Sauvegarder le message (en production, cela irait dans une base de données)
        if 'contact_messages' not in globals():
            globals()['contact_messages'] = []
        globals()['contact_messages'].append(contact_message)
        
        # Envoyer l'email de contact
        try:
            # Contenu HTML de l'email
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                    .content {{ background-color: #f8f9fa; padding: 20px; }}
                    .info-item {{ margin-bottom: 15px; }}
                    .label {{ font-weight: bold; color: #2c3e50; }}
                    .message-box {{ background-color: white; padding: 15px; border-left: 4px solid #3498db; margin-top: 15px; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>📨 Nouveau message de contact - DOUKA KM</h2>
                    </div>
                    <div class="content">
                        <div class="info-item">
                            <span class="label">Nom:</span> {name}
                        </div>
                        <div class="info-item">
                            <span class="label">Email:</span> {email}
                        </div>
                        {"<div class='info-item'><span class='label'>Téléphone:</span> " + phone + "</div>" if phone else ""}
                        <div class="info-item">
                            <span class="label">Type de contact:</span> {contact_type.replace('_', ' ').title()}
                        </div>
                        <div class="info-item">
                            <span class="label">Sujet:</span> {subject}
                        </div>
                        <div class="message-box">
                            <div class="label">Message:</div>
                            <p>{message}</p>
                        </div>
                        <div class="info-item">
                            <span class="label">Date:</span> {contact_message['created_at']}
                        </div>
                    </div>
                    <div class="footer">
                        <p>Message envoyé automatiquement depuis le formulaire de contact du site DOUKA KM</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Contenu texte simple
            text_content = f"""
            Nouveau message de contact - DOUKA KM
            
            Nom: {name}
            Email: {email}
            {"Téléphone: " + phone if phone else ""}
            Type de contact: {contact_type.replace('_', ' ').title()}
            Sujet: {subject}
            
            Message:
            {message}
            
            Date: {contact_message['created_at']}
            """
            
            # Envoyer l'email
            subject_email = f"[DOUKA KM] Contact: {subject} - {name}"
            success = send_email('ledouka.km@gmail.com', subject_email, html_content, text_content)
            
            if success:
                print(f"✅ Email de contact envoyé avec succès de {name} ({email}): {subject}")
            else:
                print(f"❌ Échec de l'envoi de l'email de contact de {name} ({email}): {subject}")
                
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi de l'email de contact: {str(e)}")
        
        # Réponse pour les requêtes AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Votre message a été envoyé avec succès. Nous vous répondrons dans les plus brefs délais.'
            })
        
        flash('Votre message a été envoyé avec succès. Nous vous répondrons dans les plus brefs délais.', 'success')
        return redirect(url_for('contact'))
    
    # Récupérer les paramètres du site pour les informations de contact
    site_settings = get_site_settings()
    
    return render_template('contact.html', site_settings=site_settings)

@app.route('/privacy-policy')
def privacy_policy():
    """Page de politique de confidentialité"""
    return render_template('legal/privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    """Page des conditions d'utilisation"""
    return render_template('legal/terms_of_service.html')

@app.route('/legal-notice')
def legal_notice():
    """Page des mentions légales"""
    return render_template('legal/legal_notice.html')

@app.route('/search')
def search():
    # Get search query and category
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    sort_option = request.args.get('sort', 'default')  # Récupérer l'option de tri
    
    # Récupérer les catégories avec leurs sous-catégories pour l'affichage public
    categories = get_categories_with_subcategories()
    
    # Récupérer tous les produits publics
    all_products = get_public_products()
    
    # Filter products based on search query and category
    filtered_products = []
    
    # Déterminer si c'est une catégorie ou sous-catégorie
    is_subcategory = category.startswith('sub_')
    subcategory_id = None
    category_id = None
    
    if is_subcategory:
        # Extraction de l'ID de sous-catégorie
        try:
            subcategory_id = int(category.replace('sub_', ''))
        except ValueError:
            subcategory_id = None
    elif category and category.isdigit():
        # C'est une catégorie
        category_id = int(category)
    
    for product in all_products:
        # Vérifier si le produit correspond aux critères de recherche
        query_match = True
        if query.strip():
            name_match = query.lower() in product['name'].lower()
            desc_match = query.lower() in product['description'].lower()
            query_match = name_match or desc_match
        
        # Vérifier la correspondance de catégorie/sous-catégorie
        category_match = True
        if is_subcategory and subcategory_id:
            # Filtrer par sous-catégorie
            category_match = product.get('subcategory_id') == subcategory_id
        elif category_id:
            # Filtrer par catégorie
            category_match = product.get('category_id') == category_id
        
        # Ajouter le produit s'il correspond aux critères
        if query_match and category_match:
            filtered_products.append(product)
    
    # Appliquer le tri
    if sort_option == 'price_asc':
        filtered_products = sorted(filtered_products, key=lambda p: p['price'])
    elif sort_option == 'price_desc':
        filtered_products = sorted(filtered_products, key=lambda p: p['price'], reverse=True)
    elif sort_option == 'name_asc':
        filtered_products = sorted(filtered_products, key=lambda p: p['name'])
    elif sort_option == 'name_desc':
        filtered_products = sorted(filtered_products, key=lambda p: p['name'], reverse=True)
    
    return render_template('products.html', 
                           products=filtered_products, 
                           categories=categories, 
                           search_query=query,
                           selected_category=category,
                           sort_option=sort_option)  # Passer l'option de tri au template

@app.route('/category/<category_slug>')
@app.route('/category/<category_slug>/<subcategory_slug>')
def category(category_slug, subcategory_slug=None):
    # Rediriger la catégorie food vers la page produits (food delivery supprimé)
    if category_slug == 'food':
        flash('La section alimentation a été intégrée dans la page produits générale.', 'info')
        return redirect(url_for('products'))
    
    try:
        # Récupérer les catégories et sous-catégories depuis la base de données
        categories_records = Category.query.filter_by(active=True).all()
        subcategories_records = Subcategory.query.filter_by(active=True).all()
        
        # Créer la structure des catégories avec leurs sous-catégories
        categories_structure = {}
        
        # D'abord, ajouter toutes les catégories
        for cat in categories_records:
            cat_slug = generate_slug(cat.name)
            categories_structure[cat_slug] = {
                'id': cat.id,
                'name': cat.name,
                'slug': cat_slug,
                'subcategories': {}
            }
        
        # Ensuite, ajouter les sous-catégories à leurs catégories parentes
        for subcat in subcategories_records:
            parent_cat = next((cat for cat in categories_records if cat.id == subcat.category_id), None)
            if parent_cat:
                parent_slug = generate_slug(parent_cat.name)
                subcat_slug = generate_slug(subcat.name)
                if parent_slug in categories_structure:
                    categories_structure[parent_slug]['subcategories'][subcat_slug] = {
                        'id': subcat.id,
                        'name': subcat.name,
                        'slug': subcat_slug,
                        'category_id': subcat.category_id
                    }
        
        # Vérifier si la catégorie principale existe
        if category_slug not in categories_structure:
            print(f"❌ Catégorie non trouvée: {category_slug}")
            return render_template('404.html'), 404
        
        current_category = categories_structure[category_slug]
        current_subcategory = None
        
        # Vérifier si une sous-catégorie a été spécifiée et existe
        if subcategory_slug:
            if subcategory_slug not in current_category['subcategories']:
                print(f"❌ Sous-catégorie non trouvée: {subcategory_slug} dans {category_slug}")
                return render_template('404.html'), 404
            current_subcategory = current_category['subcategories'][subcategory_slug]
        
        # Liste de toutes les catégories pour les menus
        categories = []
        for slug, cat in categories_structure.items():
            categories.append({
                'id': cat['id'], 
                'name': cat['name'], 
                'slug': slug
            })
        
        # Récupérer tous les produits
        all_products = get_all_products()
        
        # Filtrer les produits selon la catégorie/sous-catégorie
        if subcategory_slug and current_subcategory:
            # Filtrer par sous-catégorie
            filtered_products = [p for p in all_products if p.get('subcategory_id') == current_subcategory['id']]
            page_title = f"{current_subcategory['name']} - {current_category['name']}"
            print(f"🔍 Filtrage par sous-catégorie {current_subcategory['id']}: {len(filtered_products)} produits trouvés")
        else:
            # Filtrer par catégorie
            filtered_products = [p for p in all_products if p.get('category_id') == current_category['id']]
            page_title = current_category['name']
            print(f"🔍 Filtrage par catégorie {current_category['id']}: {len(filtered_products)} produits trouvés")
        
        print(f"✅ Affichage de {len(filtered_products)} produits pour {page_title}")
        
        return render_template(
            'products.html',
            products=filtered_products,
            categories=categories,
            current_category=current_category,
            current_subcategory=current_subcategory,
            title=f"{page_title} - DOUKA KM"
        )
        
    except Exception as e:
        print(f"❌ Erreur dans la fonction category: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('404.html'), 404

# Ajout d'une route pour le favicon.svg
@app.route('/favicon.svg')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'favicon.svg', mimetype='image/vnd.microsoft.icon')

# Fonctions utilitaires pour la gestion du panier persistant
def get_or_create_cart():
    """Récupère ou crée un panier pour l'utilisateur connecté"""
    user_id = session.get('user_id')
    
    if user_id:
        # Utilisateur connecté - utiliser la base de données
        cart = Cart.query.filter_by(user_id=user_id).first()
        
        if not cart:
            # Créer un nouveau panier pour cet utilisateur
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()
            
        return cart
    else:
        # Utilisateur non connecté - utiliser la session
        return None

def get_cart():
    """Obtient le panier actuel - version compatible avec persistance DB"""
    user_id = session.get('user_id')
    
    if user_id:
        # Utilisateur connecté - récupérer depuis la base de données
        from models import Cart
        cart = Cart.query.filter_by(user_id=user_id).first()
        
        if cart:
            # Convertir les items de la DB au format session pour compatibilité
            cart_items = []
            for item in cart.items:
                cart_items.append(item.to_dict())
            return cart_items
        else:
            # Pas de panier en DB, vérifier s'il y a des items en session
            session_cart = session.get('cart', [])
            if session_cart:
                # Migrer le panier de session vers la DB
                migrate_session_cart_to_db()
                # Récupérer le panier nouvellement créé
                cart = Cart.query.filter_by(user_id=user_id).first()
                if cart:
                    cart_items = []
                    for item in cart.items:
                        cart_items.append(item.to_dict())
                    return cart_items
            return []
    else:
        # Utilisateur non connecté - utiliser la session
        if 'cart' not in session:
            session['cart'] = []
        return session['cart']

def migrate_session_cart_to_db():
    """Migre un panier de session vers la base de données lors de la connexion"""
    user_id = session.get('user_id')
    session_cart = session.get('cart', [])
    
    if not user_id or not session_cart:
        return False
    
    try:
        # Récupérer ou créer le panier de l'utilisateur
        cart = get_or_create_cart()
        
        # Ajouter les items de session au panier de la DB
        for item in session_cart:
            product_id = item.get('original_product_id', item['product_id'])
            unique_product_id = item.get('unique_id', item['product_id'])
            
            # Vérifier si cet item existe déjà dans le panier DB
            existing_item = CartItem.query.filter_by(
                cart_id=cart.id,
                unique_product_id=str(unique_product_id)
            ).first()
            
            if existing_item:
                # Mettre à jour la quantité
                existing_item.quantity += item['quantity']
            else:
                # Créer un nouvel item
                cart_item = CartItem(
                    cart_id=cart.id,
                    product_id=int(product_id) if str(product_id).isdigit() else 1,
                    unique_product_id=str(unique_product_id),
                    original_product_id=int(product_id) if str(product_id).isdigit() else 1,
                    quantity=item['quantity']
                )
                
                if item.get('options'):
                    cart_item.set_options(item['options'])
                if item.get('modified_price'):
                    cart_item.modified_price = item['modified_price']
                    
                db.session.add(cart_item)
        
        # Sauvegarder en base
        db.session.commit()
        
        # Vider le panier de session après migration
        session['cart'] = []
        
        print(f"✅ Panier de session migré vers DB pour utilisateur {user_id}")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur migration panier vers DB: {e}")
        return False

def add_to_cart_db(product_id, quantity, options=None, modified_price=None):
    """Ajoute un produit au panier persistant"""
    user_id = session.get('user_id')
    
    if not user_id:
        # Utilisateur non connecté - utiliser la session comme avant
        return add_to_session_cart(product_id, quantity, options, modified_price)
    
    try:
        import hashlib
        import json
        
        # Générer un ID unique basé sur les options
        unique_product_id = str(product_id)
        if options:
            options_hash = hashlib.md5(json.dumps(options, sort_keys=True).encode()).hexdigest()[:8]
            unique_product_id = f"{product_id}_{options_hash}"
        
        # Récupérer ou créer le panier
        cart = get_or_create_cart()
        
        # Vérifier si cet item existe déjà
        existing_item = CartItem.query.filter_by(
            cart_id=cart.id,
            unique_product_id=unique_product_id
        ).first()
        
        if existing_item:
            # Mettre à jour la quantité
            existing_item.quantity += quantity
            existing_item.updated_at = datetime.now()
        else:
            # Créer un nouvel item
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=int(product_id) if str(product_id).isdigit() else 1,
                unique_product_id=unique_product_id,
                original_product_id=int(product_id) if str(product_id).isdigit() else 1,
                quantity=quantity
            )
            
            if options:
                cart_item.set_options(options)
            if modified_price:
                cart_item.modified_price = modified_price
                
            db.session.add(cart_item)
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur ajout au panier DB: {e}")
        return False

def add_to_session_cart(product_id, quantity, options=None, modified_price=None):
    """Ajoute un produit au panier de session (utilisateur non connecté)"""
    import hashlib
    import json
    
    cart = session.get('cart', [])
    
    # Générer un ID unique basé sur les options
    unique_product_id = str(product_id)
    if options:
        options_hash = hashlib.md5(json.dumps(options, sort_keys=True).encode()).hexdigest()[:8]
        unique_product_id = f"{product_id}_{options_hash}"
    
    # Vérifier si le produit avec les mêmes options existe déjà
    product_in_cart = False
    for item in cart:
        if str(item.get('unique_id', item['product_id'])) == unique_product_id:
            item['quantity'] += quantity
            product_in_cart = True
            break
    
    # Si le produit n'est pas dans le panier, l'ajouter
    if not product_in_cart:
        new_item = {
            'product_id': unique_product_id,
            'original_product_id': int(product_id) if str(product_id).isdigit() else 1,
            'unique_id': unique_product_id,
            'quantity': quantity,
            'is_food': False,
            'options': options or {}
        }
        
        if modified_price:
            new_item['modified_price'] = modified_price
            
        cart.append(new_item)
    
    session['cart'] = cart
    return True

def remove_from_cart_db(unique_product_id):
    """Supprime un produit du panier persistant"""
    user_id = session.get('user_id')
    
    if not user_id:
        # Utilisateur non connecté - utiliser la session
        cart = session.get('cart', [])
        session['cart'] = [item for item in cart if str(item.get('unique_id', item['product_id'])) != str(unique_product_id)]
        return True
    
    try:
        # Trouver l'item à supprimer
        cart_item = CartItem.query.join(Cart).filter(
            Cart.user_id == user_id,
            CartItem.unique_product_id == str(unique_product_id)
        ).first()
        
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            return True
        return False
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur suppression du panier DB: {e}")
        return False

def update_cart_quantity_db(unique_product_id, quantity):
    """Met à jour la quantité d'un produit dans le panier"""
    user_id = session.get('user_id')
    
    if not user_id:
        # Utilisateur non connecté - utiliser la session
        cart = session.get('cart', [])
        for item in cart:
            if str(item.get('unique_id', item['product_id'])) == str(unique_product_id):
                if quantity > 0:
                    item['quantity'] = quantity
                else:
                    cart.remove(item)
                break
        session['cart'] = cart
        return True
    
    try:
        if quantity <= 0:
            return remove_from_cart_db(unique_product_id)
        
        # Trouver l'item à mettre à jour
        cart_item = CartItem.query.join(Cart).filter(
            Cart.user_id == user_id,
            CartItem.unique_product_id == str(unique_product_id)
        ).first()
        
        if cart_item:
            cart_item.quantity = quantity
            cart_item.updated_at = datetime.now()
            db.session.commit()
            return True
        return False
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur mise à jour quantité panier DB: {e}")
        return False

def clear_cart_db():
    """Vide le panier"""
    user_id = session.get('user_id')
    
    if not user_id:
        # Utilisateur non connecté - vider la session
        session['cart'] = []
        return True
    
    try:
        # Supprimer tous les items du panier de l'utilisateur
        cart = Cart.query.filter_by(user_id=user_id).first()
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur vidage panier DB: {e}")
        return False

# Note: La fonction get_cart() est définie plus haut dans le fichier (ligne ~4753)

# Route pour afficher le panier
@app.route('/cart')
def cart():
    # Nettoyer les sessions de checkout quand l'utilisateur retourne au panier
    # Cela force le système à utiliser les données à jour du panier
    if 'checkout_cart' in session:
        del session['checkout_cart']
    if 'checkout_type' in session:
        del session['checkout_type']
    if 'partial_checkout' in session:
        del session['partial_checkout']
    
    cart_items = get_cart()
    total = 0
    products = []
    
    # Récupération des informations sur les produits dans le panier
    for item in cart_items:
        # Récupérer les informations de base
        product_id = item['product_id']  # Cet ID peut être unique avec options
        original_product_id = item.get('original_product_id', product_id)  # ID original du produit
        quantity = item['quantity']
        options = item.get('options', {})
        
        # Traiter les produits normaux
        # Utiliser original_product_id pour récupérer les données du produit
        product = get_product_by_id(original_product_id)
        if product:
            if 'modified_price' in item:
                base_price = item['modified_price']
            else:
                base_price = product['price']
            
            # Calculer le prix des options
            options_price = 0
            for option_key, option_value in options.items():
                # Logique de calcul des prix d'options (couleurs, tailles, etc.)
                # Simplifié pour cette correction
                pass
            
            total_item_price = (base_price + options_price) * quantity
            total += total_item_price
            
            # Préparer l'affichage des options
            display_options = {}
            if options:
                for group_name, group_options in options.items():
                    if isinstance(group_options, list):
                        # Options multiples
                        option_names = []
                        for option in group_options:
                            if isinstance(option, dict):
                                # Ancien format avec objets
                                option_text = option['name']
                                if option.get('price', 0) > 0:
                                    option_text += f" (+{option['price']:,} KMF)".replace(',', ' ')
                            else:
                                # Nouveau format avec chaînes simples
                                option_text = str(option)
                            option_names.append(option_text)
                        display_options[group_name] = ', '.join(option_names)
                    else:
                        # Option unique
                        if isinstance(group_options, dict):
                            # Ancien format avec objet
                            option_text = group_options['name']
                            if group_options.get('price', 0) > 0:
                                option_text += f" (+{group_options['price']:,} KMF)".replace(',', ' ')
                        else:
                            # Nouveau format avec chaîne simple
                            option_text = str(group_options)
                        display_options[group_name] = option_text
            
            products.append({
                'id': product_id,  # Conserver l'ID unique pour les actions sur le panier
                'original_id': original_product_id,  # ID original pour l'affichage
                'name': product['name'],
                'image': product.get('image', ''),
                'price': base_price,
                'quantity': quantity,
                'subtotal': total_item_price,
                'stock': product.get('stock', 0),  # Ajouter le stock disponible
                'is_food': False,
                'options': display_options  # Ajouter les options formatées
            })
    
    # Passer les informations au template
    return render_template('cart.html', 
                          products=products, 
                          total=total, 
                          has_food_items=False, 
                          has_regular_items=True)

# Fonction utilitaire pour récupérer les informations d'un produit par son ID
# This function was moved and updated above to support merchant products

# Fonction utilitaire pour récupérer tous les produits (statiques + marchands)
def get_all_products():
    """Récupère tous les produits depuis la base de données, triés par date de création (plus récent en premier)"""
    try:
        all_products = []
        
        # Récupérer tous les produits depuis la base de données, triés par created_at DESC
        products_from_db = Product.query.order_by(Product.created_at.desc()).all()
        
        for product_record in products_from_db:
            product_dict = product_record.to_dict()
            
            # Ajouter les informations source et merchant
            if product_record.merchant_id:
                product_dict['source'] = 'merchant'
                merchant_record = Merchant.query.get(product_record.merchant_id)
                if merchant_record:
                    product_dict['merchant_email'] = merchant_record.email
                    product_dict['merchant_name'] = merchant_record.store_name
                    product_dict['merchant_logo'] = merchant_record.store_logo
                else:
                    product_dict['merchant_name'] = 'Marchand inconnu'
                    product_dict['merchant_logo'] = 'static/img/merchants/store_logo_default.png'
            else:
                product_dict['source'] = 'admin'
                product_dict['merchant_name'] = 'DOUKA KM'
                product_dict['merchant_logo'] = 'static/img/logo.svg'
            
            all_products.append(product_dict)
        
        print(f"✅ Récupéré {len(all_products)} produits depuis la base de données (triés par date)")
        return all_products
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des produits: {str(e)}")
        return []

def get_product_by_id(product_id):
    """Récupère un produit par son ID depuis la base de données"""
    try:
        # Convertir product_id en int si c'est une string
        product_id = int(product_id)
    except (ValueError, TypeError):
        return None
    
    # Récupérer le produit depuis la base de données
    product_record = Product.query.get(product_id)
    
    if not product_record:
        return None
    
    # Convertir en dictionnaire
    product_dict = product_record.to_dict()
    
    # Ajouter les informations source et merchant
    if product_record.merchant_id:
        product_dict['source'] = 'merchant'
        merchant_record = Merchant.query.get(product_record.merchant_id)
        if merchant_record:
            product_dict['merchant_email'] = merchant_record.email
            product_dict['merchant_name'] = merchant_record.store_name
            product_dict['merchant_id'] = merchant_record.id
            product_dict['merchant_logo'] = merchant_record.store_logo
            product_dict['merchant_banner'] = merchant_record.store_banner
        else:
            product_dict['merchant_name'] = 'Marchand inconnu'
            product_dict['merchant_logo'] = 'static/img/merchants/store_logo_default.png'
    else:
        product_dict['source'] = 'admin'
        product_dict['merchant_name'] = 'DOUKA KM'
        product_dict['merchant_logo'] = 'static/img/logo.svg'
    
    return product_dict

def get_active_categories():
    """Récupère uniquement les catégories actives pour l'affichage public - Version DATABASE-FIRST"""
    try:
        # **DATABASE-FIRST: Priorité à la base de données**
        categories = Category.query.filter_by(active=True).order_by(Category.name).all()
        
        if categories:
            # Convertir en dictionnaire avec ID comme clé pour compatibilité
            categories_dict = {}
            for cat in categories:
                cat_dict = cat.to_dict()
                categories_dict[cat.id] = cat_dict
                # Mettre à jour le dictionnaire en mémoire pour compatibilité
                admin_categories_db[cat.id] = cat_dict
            
            return categories_dict
        else:
            # Fallback vers le dictionnaire en mémoire
            return {cat_id: cat for cat_id, cat in admin_categories_db.items() if cat.get('active', True)}
            
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement des catégories actives depuis la DB: {e}")
        # Fallback vers le dictionnaire en mémoire
        return {cat_id: cat for cat_id, cat in admin_categories_db.items() if cat.get('active', True)}

def get_categories_with_subcategories():
    """Prépare les catégories avec leurs sous-catégories pour les templates - Version DATABASE-FIRST"""
    categories_list = []
    try:
        # **DATABASE-FIRST: Priorité à la base de données**
        categories = Category.query.filter_by(active=True).order_by(Category.name).all()
        
        if categories:
            for cat in categories:
                category_data = {
                    'id': cat.id,
                    'name': cat.name,
                    'description': cat.description,
                    'icon': cat.icon,
                    'subcategories': []
                }
                
                # Récupérer les sous-catégories actives de cette catégorie depuis la DB
                subcategories = Subcategory.query.filter_by(
                    category_id=cat.id, 
                    active=True
                ).order_by(Subcategory.name).all()
                
                for sub in subcategories:
                    category_data['subcategories'].append({
                        'id': sub.id,
                        'name': sub.name,
                        'description': sub.description
                    })
                
                categories_list.append(category_data)
            
            return categories_list
        else:
            # Fallback vers le dictionnaire en mémoire
            for cat_id, cat in admin_categories_db.items():
                if cat.get('active', True):  # Seulement les catégories actives
                    category_data = {
                        'id': cat_id,
                        'name': cat['name'],
                        'subcategories': []
                    }
                    
                    # Ajouter les sous-catégories actives de cette catégorie
                    for sub_id, sub in admin_subcategories_db.items():
                        if sub.get('category_id') == cat_id and sub.get('active', True):
                            category_data['subcategories'].append({
                                'id': sub_id,
                                'name': sub['name']
                            })
                    
                    categories_list.append(category_data)
            
            return categories_list
            
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement des catégories avec sous-catégories depuis la DB: {e}")
        # Fallback vers le dictionnaire en mémoire
        for cat_id, cat in admin_categories_db.items():
            if cat.get('active', True):  # Seulement les catégories actives
                category_data = {
                    'id': cat_id,
                    'name': cat['name'],
                    'subcategories': []
                }
                
                # Ajouter les sous-catégories actives de cette catégorie
                for sub_id, sub in admin_subcategories_db.items():
                    if sub.get('category_id') == cat_id and sub.get('active', True):
                        category_data['subcategories'].append({
                            'id': sub_id,
                            'name': sub['name']
                        })
                
                categories_list.append(category_data)
        
        return categories_list

def is_product_public(product):
    """Vérifie si un produit est accessible au public (actif et dans une catégorie active)"""
    if not product:
        return False
    
    # Vérifier le statut du produit
    product_status = product.get('status', 'active')
    if product_status != 'active':
        return False
    
    # Note: Vérification du marchand suspendu désactivée temporairement
    # car la fonctionnalité account_suspended n'est pas encore implémentée en base de données
    
    # Vérifier la catégorie (si définie)
    category_id = product.get('category_id')
    if category_id is not None:
        active_categories = get_active_categories()
        if category_id not in active_categories:
            return False
    
    return True

def get_public_products():
    """Récupère tous les produits actifs des catégories actives pour l'affichage public"""
    all_products = get_all_products()
    
    # Filtrer les produits accessibles au public
    public_products = []
    for product in all_products:
        if is_product_public(product):
            public_products.append(product)
    
    return public_products

def get_category_name(category_id):
    """Récupère le nom d'une catégorie par son ID"""
    # D'abord vérifier la base de données
    category_record = Category.query.filter_by(id=category_id).first()
    if category_record:
        # Mettre à jour le dictionnaire en mémoire pour compatibilité
        admin_categories_db[category_id] = category_record.to_dict()
        return category_record.name
    
    # Fallback vers le dictionnaire en mémoire
    if category_id in admin_categories_db:
        return admin_categories_db[category_id]['name']
    
    return 'Non classé'

@app.route('/add-to-cart/<product_id>', methods=['POST', 'GET'])
def add_to_cart(product_id):
    try:
        # Vérifier d'abord que le produit existe et est actif
        product = get_product_by_id(int(product_id))
        if not product:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Produit non trouvé'})
            flash('Produit non trouvé', 'error')
            return redirect(url_for('products'))
    except Exception as e:
        print(f"Erreur lors de la récupération du produit: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Erreur lors de la récupération du produit'})
        flash('Erreur lors de la récupération du produit', 'error')
        return redirect(url_for('products'))
    
    # Vérifier si l'utilisateur est admin ou si le produit est accessible au public
    is_admin = session.get('admin_email') is not None
    
    if not is_admin and not is_product_public(product):
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'Ce produit n\'est plus disponible'})
        flash('Ce produit n\'est plus disponible', 'error')
        return redirect(url_for('products'))
    
    quantity = int(request.form.get('quantity', 1))
    # Option pour gérer la redirection
    should_redirect = request.form.get('redirect', 'false') == 'true'
    
    # ✅ NOUVEAU: Vérifier le stock avant d'ajouter au panier
    stock_check = check_product_stock_availability(int(product_id), quantity)
    if not stock_check['available']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False, 
                'message': stock_check['message'],
                'stock_error': True,
                'available_stock': stock_check['current_stock']
            })
        flash(stock_check['message'], 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    
    # Récupération des options du produit (couleur, taille, etc.)
    options = {}
    try:
        options_str = request.form.get('options', '{}')
        options = json.loads(options_str)
    except Exception as e:
        # En cas d'erreur, ignorer les options
        pass
    
    # Récupération du prix final selon les combinaisons d'options
    final_price = None
    
    # Tenter de récupérer le prix selon les options sélectionnées
    try:
        product = get_product_by_id(int(product_id))
        if product:
            base_price = product['price']
            
            # Vérifier s'il y a des combinaisons de prix spécifiques
            if 'price_combinations' in product and product['price_combinations']:
                # Chercher une combinaison qui correspond aux options sélectionnées
                selected_color = options.get('color')
                selected_size = options.get('size')
                
                for combination in product['price_combinations']:
                    # Vérifier si cette combinaison correspond
                    color_match = True
                    size_match = True
                    
                    # Si une couleur est spécifiée dans la combinaison, elle doit correspondre
                    if 'color' in combination and combination['color'] != selected_color:
                        color_match = False
                    
                    # Si une taille est spécifiée dans la combinaison, elle doit correspondre
                    if 'size' in combination and combination['size'] != selected_size:
                        size_match = False
                    
                    
                    # Si les deux correspondent, utiliser ce prix
                    if color_match and size_match:
                        final_price = combination['price']
                        break
            
            # Si aucune combinaison trouvée, utiliser le prix de base
            if final_price is None:
                final_price = base_price
    except Exception as e:
        pass
    
    # Vérifier si nous avons affaire à un produit alimentaire
    
    # Obtenir le panier actuel
    cart = get_cart()
    
    # Générer un ID unique pour ce produit avec ses options
    unique_product_id = product_id
    if options:
        # Créer un hash des options pour différencier les mêmes produits avec des options différentes
        options_hash = hashlib.md5(json.dumps(options, sort_keys=True).encode()).hexdigest()[:8]
        unique_product_id = f"{product_id}_{options_hash}"

    # Traitement pour produits normaux - NOUVELLE VERSION AVEC PERSISTANCE
    product = get_product_by_id(int(product_id))
    if not product:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Produit non trouvé'})
        flash('Produit non trouvé', 'error')
        return redirect(url_for('products'))

    # Ajouter au panier persistant (DB ou session selon connexion)
    success = add_to_cart_db(product_id, quantity, options, final_price)
    
    if not success:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Erreur lors de l\'ajout au panier'})
        flash('Erreur lors de l\'ajout au panier', 'error')
        return redirect(url_for('products'))

    # Nom du produit pour la notification
    product_name = product['name']

    # Récupérer le panier mis à jour pour compter les items
    updated_cart = get_cart()
    cart_count = len(updated_cart)

    # Si la requête est AJAX, retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':        
        return jsonify({
            'success': True, 
            'message': f"{product_name} ajouté au panier",
            'product_name': product_name,
            'cart_count': cart_count,
            'redirect': url_for('cart') if should_redirect else None
        })

    # Pour les requêtes non AJAX, toujours rediriger vers le panier
    flash('Produit ajouté au panier avec succès!', 'success')
    return redirect(url_for('cart'))

@app.route('/get-cart-count')
def get_cart_count():
    """Route pour obtenir le nombre d'articles dans le panier"""
    try:
        cart = get_cart()
        cart_count = len(cart) if cart else 0
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'cart_count': cart_count})
        
        return str(cart_count)
    except Exception as e:
        print(f"Erreur dans get_cart_count: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'cart_count': 0, 'error': str(e)})
        return "0"

# Modifier la route pour supprimer un produit du panier
@app.route('/remove-from-cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    # Nettoyer les sessions de checkout car le panier a été modifié
    if 'checkout_cart' in session:
        del session['checkout_cart']
    if 'checkout_type' in session:
        del session['checkout_type']
    if 'partial_checkout' in session:
        del session['partial_checkout']
    
    # Supprimer du panier persistant
    success = remove_from_cart_db(product_id)
    
    # Si c'est une requête AJAX, retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if success:
            cart = get_cart()
            cart_count = len(cart) if cart else 0
            return jsonify({
                'success': True,
                'cart_count': cart_count,
                'message': 'Produit supprimé du panier',
                'reload': cart_count == 0  # Indiquer s'il faut recharger la page (panier vide)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erreur lors de la suppression'
            })
    
    # Requête normale : redirection avec message flash
    if success:
        flash('Produit supprimé du panier', 'success')
    else:
        flash('Erreur lors de la suppression', 'error')
    
    return redirect(url_for('cart'))

@app.route('/remove-selected-from-cart', methods=['POST'])
def remove_selected_from_cart():
    """Supprimer plusieurs produits sélectionnés du panier"""
    
    selected_products = request.form.getlist('selected_products[]')
    
    if not selected_products:
        flash('Aucun produit sélectionné', 'warning')
        return redirect(url_for('cart'))
    
    # Nettoyer les sessions de checkout car le panier a été modifié
    if 'checkout_cart' in session:
        del session['checkout_cart']
    if 'checkout_type' in session:
        del session['checkout_type']
    if 'partial_checkout' in session:
        del session['partial_checkout']
    
    # Supprimer les produits sélectionnés du panier persistant
    removed_count = 0
    for product_id in selected_products:
        success = remove_from_cart_db(product_id)
        if success:
            removed_count += 1
    
    if removed_count > 0:
        flash(f'{removed_count} produit(s) supprimé(s) du panier', 'success')
    else:
        flash('Aucun produit trouvé à supprimer', 'warning')
    
    return redirect(url_for('cart'))

# Modifier la route pour mettre à jour la quantité d'un produit
@app.route('/update-cart/<product_id>', methods=['POST'])
def update_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    
    # Nettoyer les sessions de checkout car le panier a été modifié
    if 'checkout_cart' in session:
        del session['checkout_cart']
    if 'checkout_type' in session:
        del session['checkout_type']
    if 'partial_checkout' in session:
        del session['partial_checkout']
    
    # Mettre à jour la quantité dans le panier persistant
    success = update_cart_quantity_db(product_id, quantity)
    
    # Retourner JSON pour les requêtes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if success:
            # Récupérer le panier mis à jour pour compter les items
            updated_cart = get_cart()
            cart_count = len(updated_cart)
            
            return jsonify({
                'success': True, 
                'message': 'Panier mis à jour',
                'cart_count': cart_count
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Erreur lors de la mise à jour'
            })
    
    # Sinon, rediriger vers le panier
    if success:
        flash('Panier mis à jour avec succès!', 'success')
    else:
        flash('Erreur lors de la mise à jour', 'error')
    return redirect(url_for('cart'))

# Route pour vider le panier
@app.route('/clear-cart', methods=['POST'])
def clear_cart():
    # Nettoyer les sessions de checkout car le panier a été modifié
    if 'checkout_cart' in session:
        del session['checkout_cart']
    if 'checkout_type' in session:
        del session['checkout_type']
    if 'partial_checkout' in session:
        del session['partial_checkout']
    
    # Vider le panier persistant
    success = clear_cart_db()
    
    # Retourner JSON pour les requêtes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': success, 
            'message': 'Panier vidé' if success else 'Erreur lors du vidage',
            'cart_count': 0
        })
    
    # Sinon, rediriger vers le panier avec message
    if success:
        flash('Panier vidé avec succès!', 'success')
    else:
        flash('Erreur lors du vidage du panier', 'error')
    return redirect(url_for('cart'))

# Route pour passer à la caisse
@app.route('/checkout', methods=['GET', 'POST'])
@login_required  # Exiger que l'utilisateur soit connecté
def checkout():
    # Gérer la sélection partielle de produits
    if request.method == 'POST':
        selected_products = request.form.getlist('selected_products[]')
        partial_checkout = request.form.get('partial_checkout') == 'true'
        
        if partial_checkout and selected_products:
            # Créer un panier filtré avec seulement les produits sélectionnés
            full_cart = get_cart()
            selected_cart = []
            
            for item in full_cart:
                item_id = str(item.get('unique_id', item['product_id']))
                if item_id in selected_products:
                    selected_cart.append(item)
            
            # Sauvegarder le panier sélectionné en session
            session['checkout_cart'] = selected_cart
            session['checkout_type'] = 'regular'
            session['partial_checkout'] = True
    
    # Vérifier si nous avons un panier filtré pour le checkout
    checkout_cart = session.get('checkout_cart', [])
    checkout_type = session.get('checkout_type', '')
    
    # Utiliser soit le panier filtré, soit le panier complet
    cart_items = checkout_cart if checkout_cart else get_cart()
    
    if not cart_items:
        flash('Votre panier est vide!', 'warning')
        return redirect(url_for('cart'))
    
    # Calculer le total et récupérer les détails des produits
    total = 0
    products = []
    
    for item in cart_items:
        product_id = item['product_id']
        quantity = item['quantity']
        
        # Utiliser l'original_product_id pour récupérer les informations du produit
        original_product_id = item.get('original_product_id', product_id)
        
        # Essayer de convertir en entier si c'est une chaîne numérique
        try:
            if isinstance(original_product_id, str) and original_product_id.isdigit():
                original_product_id = int(original_product_id)
            elif isinstance(original_product_id, str):
                # Si ce n'est pas numérique, essayer d'extraire l'ID du début
                original_product_id = int(original_product_id.split('_')[0])
        except (ValueError, AttributeError):
            original_product_id = product_id
        
        product = get_product_by_id(original_product_id)
        
        if product:
            # Utiliser le prix modifié s'il est stocké dans l'élément du panier
            if 'modified_price' in item:
                product_price = item['modified_price']
            else:
                product_price = product['price']
                
            subtotal = product_price * quantity
            total += subtotal
            
            products.append({
                'id': product_id,
                'name': product['name'],
                'image': product['image'],
                'price': product_price,
                'quantity': quantity,
                'subtotal': subtotal,
                'options': item.get('options', {}),
                'is_food': False,
                'category_id': product.get('category_id'),
                'subcategory_id': product.get('subcategory_id'),
                'merchant_email': product.get('merchant_email', 'admin_products')
            })
    
    # Récupérer les paramètres de livraison dynamiques
    site_settings = get_site_settings()
    shipping_rates = site_settings.get('shipping_rates', {})
    
    # Utiliser les tarifs par défaut pour l'affichage initial
    default_rates = shipping_rates.get('default', {
        'standard': site_settings['shipping_fee'],
        'express': site_settings['shipping_fee'] * 2
    })
    
    # Récupérer les informations de livraison dynamiques pour le panier
    cart_items = []
    for product in products:
        cart_items.append({
            'product_id': product['id'],  # Utiliser 'product_id' au lieu de 'id'
            'category_id': product.get('category_id'),
            'subcategory_id': product.get('subcategory_id'),
            'quantity': product['quantity'],
            'price': product['price']
        })
    
    # Calculer le total du panier
    cart_total = sum(product['price'] * product['quantity'] for product in products)
    
    # Calculer les tarifs dynamiques pour le panier
    shipping_info = calculate_dynamic_shipping_fee(cart_items, cart_total, '', 'standard')
    
    # Créer les options de livraison avec les informations dynamiques
    if shipping_info.get('selected_rate'):
        rate_data = shipping_info['selected_rate']
        standard_days = rate_data.get('standard_delivery_days', 3)
        standard_hours = rate_data.get('standard_delivery_hours', 0)
        express_days = rate_data.get('express_delivery_days', 1)
        express_hours = rate_data.get('express_delivery_hours', 0)
        
        # Formatage des durées pour l'affichage - Standard
        if standard_days == 0 and standard_hours > 0:
            standard_label = f"Standard ({standard_hours}h)"
        elif standard_days == 0:
            standard_label = "Standard (même jour)"
        elif standard_days == 1:
            standard_label = "Standard (24h)"
        else:
            standard_label = f"Standard ({standard_days} jours)"
            
        # Formatage des durées pour l'affichage - Express
        if express_days == 0 and express_hours > 0:
            express_label = f"Express ({express_hours}h)"
        elif express_days == 0:
            express_label = "Express (même jour)"
        elif express_days == 1:
            express_label = "Express (24-48h)"
        else:
            express_label = f"Express ({express_days} jours)"
    else:
        # Valeurs par défaut si aucun tarif personnalisé
        standard_label = "Standard (3 jours)"
        express_label = "Express (24-48h)"
    
    # Calculer les tarifs basés sur les produits du panier
    calculated_shipping = calculate_dynamic_shipping_fee(cart_items, cart_total, None, 'standard')
    standard_shipping_cost = calculated_shipping.get('shipping_fee', default_rates.get('standard', site_settings['shipping_fee']))
    
    calculated_express = calculate_dynamic_shipping_fee(cart_items, cart_total, None, 'express')
    express_shipping_cost = calculated_express.get('shipping_fee', default_rates.get('express', site_settings['shipping_fee'] * 2))
    
    # Options de livraison avec prix et durées dynamiques
    shipping_options = [
        {
            'id': 1, 
            'name': standard_label, 
            'type': 'standard',
            'price': standard_shipping_cost
        },
        {
            'id': 2, 
            'name': express_label, 
            'type': 'express',
            'price': express_shipping_cost
        }
    ]
    
    # Debug: Afficher les options de livraison préparées
    print("🚚 DEBUG CHECKOUT - Options de livraison:")
    for option in shipping_options:
        print(f"   - {option['name']}: {option['price']} KMF")
    
    # Préparer les tarifs par région pour JavaScript
    regional_rates = {}
    for region, rates in shipping_rates.items():
        regional_rates[region] = {
            'standard': rates.get('standard', default_rates['standard']),
            'express': rates.get('express', default_rates['express'])
        }
    
    # Générer un jeton unique pour cette session de checkout
    import uuid
    order_token = str(uuid.uuid4())
    
    return render_template('checkout.html', 
                          products=products, 
                          total=total,
                          shipping_options=shipping_options,
                          regional_rates=regional_rates,
                          free_shipping_threshold=site_settings.get('free_shipping_threshold', 50000),
                          is_food_delivery=False,
                          order_token=order_token)

@app.route('/api/shipping-rates', methods=['POST'])
@login_required
def api_shipping_rates():
    """API pour récupérer les tarifs de livraison selon la région et le total du panier"""
    try:
        data = request.get_json()
        region = data.get('region', 'default')
        cart_total = float(data.get('cart_total', 0))
        shipping_type = data.get('shipping_type', 'standard')
        
        # Récupérer les items du panier pour analyser les catégories
        checkout_cart = session.get('checkout_cart', [])
        cart_items = checkout_cart if checkout_cart else get_cart()
        
        # Calculer les frais pour les deux types de livraison avec analyse des catégories
        standard_info = calculate_dynamic_shipping_fee(cart_items, cart_total, region, 'standard')
        express_info = calculate_dynamic_shipping_fee(cart_items, cart_total, region, 'express')
        
        # Obtenir les tarifs de base pour information
        site_settings = get_site_settings()
        shipping_rates = site_settings.get('shipping_rates', {})
        region_rates = shipping_rates.get(region, shipping_rates.get('default', {
            'standard': site_settings['shipping_fee'],
            'express': site_settings['shipping_fee'] * 2
        }))
        
        response_data = {
            'success': True,
            'rates': {
                'standard': {
                    'base_price': region_rates.get('standard', site_settings['shipping_fee']),
                    'final_price': standard_info['shipping_fee'],
                    'is_free': standard_info['is_free_shipping']
                },
                'express': {
                    'base_price': region_rates.get('express', site_settings['shipping_fee'] * 2),
                    'final_price': express_info['shipping_fee'],
                    'is_free': express_info['is_free_shipping']
                }
            },
            'free_shipping_threshold': site_settings.get('free_shipping_threshold', 50000),
            'amount_needed_for_free': standard_info.get('amount_needed_for_free_shipping', 0),
            'region': region,
            'cart_total': cart_total
        }
        
        # Ajouter des informations sur les tranches de prix si utilisées
        if standard_info.get('price_ranges_enabled'):
            response_data['price_ranges_enabled'] = True
            if standard_info.get('price_range_used'):
                response_data['price_range_used'] = standard_info['price_range_used']
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def optimize_shipping_fees_for_multiple_orders(merchant_groups, shipping_info, shipping_fee):
    """
    Optimise les frais de livraison pour plusieurs commandes d'un même client
    Applique les frais les plus élevés à une seule commande, 0 aux autres
    
    Args:
        merchant_groups (dict): Groupes de produits par marchand
        shipping_info (dict): Informations de livraison calculées
        shipping_fee (float): Frais de livraison calculés
    
    Returns:
        dict: Dictionnaire avec merchant_email -> shipping_fee optimisé
    """
    optimized_fees = {}
    
    # Si une seule commande, pas d'optimisation nécessaire
    if len(merchant_groups) <= 1:
        for merchant_email in merchant_groups.keys():
            optimized_fees[merchant_email] = shipping_fee
        return optimized_fees
    
    # Pour plusieurs commandes, appliquer les frais au marchand avec le montant le plus élevé
    print(f"🚚 OPTIMISATION LIVRAISON: {len(merchant_groups)} commandes détectées")
    
    # Calculer le total par marchand pour déterminer qui paie les frais
    merchant_totals = {}
    for merchant_email, products in merchant_groups.items():
        total = sum(product['subtotal'] for product in products)
        merchant_totals[merchant_email] = total
        print(f"   - {merchant_email}: {total} KMF")
    
    # Trouver le marchand avec le montant le plus élevé
    highest_merchant = max(merchant_totals.items(), key=lambda x: x[1])
    highest_merchant_email = highest_merchant[0]
    highest_amount = highest_merchant[1]
    
    print(f"🎯 Frais de livraison ({shipping_fee} KMF) appliqués à {highest_merchant_email} (montant le plus élevé: {highest_amount} KMF)")
    
    # Assigner les frais
    for merchant_email in merchant_groups.keys():
        if merchant_email == highest_merchant_email:
            optimized_fees[merchant_email] = shipping_fee
            print(f"   ✅ {merchant_email}: {shipping_fee} KMF")
        else:
            optimized_fees[merchant_email] = 0
            print(f"   💰 {merchant_email}: 0 KMF (économie)")
    
    return optimized_fees

def calculate_max_delivery_times_for_cart(cart_items):
    """
    Calcule les délais de livraison maximaux pour un panier donné
    
    Args:
        cart_items: Liste des articles du panier
    
    Returns:
        dict: {
            'max_standard_days': int,
            'max_standard_hours': int, 
            'max_express_days': int,
            'max_express_hours': int,
            'standard_label': str,
            'express_label': str
        }
    """
    max_standard_days = 0
    max_standard_hours = 0
    max_express_days = 0
    max_express_hours = 0
    
    # Analyser chaque produit du panier
    for item in cart_items:
        # Récupérer l'ID du produit
        product_id = item.get('original_product_id', item.get('product_id'))
        if isinstance(product_id, str):
            try:
                if product_id.startswith('product_'):
                    product_id = int(product_id.replace('product_', ''))
                else:
                    product_id = int(product_id.split('_')[0])
            except:
                continue
        
        try:
            # Récupérer le produit et sa catégorie
            product = Product.query.get(product_id)
            if not product:
                continue
            
            # Chercher le tarif spécifique pour ce produit
            rate = None
            
            # Sous-catégorie en priorité
            if product.subcategory_id:
                rate = ShippingRate.query.filter_by(
                    rate_type='subcategory',
                    subcategory_id=product.subcategory_id,
                    active=True
                ).first()
            
            # Catégorie si pas de sous-catégorie
            if not rate and product.category_id:
                rate = ShippingRate.query.filter_by(
                    rate_type='category',
                    category_id=product.category_id,
                    active=True
                ).first()
            
            # Tarif par défaut si pas de tarif spécifique
            if not rate:
                rate = ShippingRate.query.filter_by(
                    rate_type='default',
                    active=True
                ).first()
            
            if rate:
                # Comparer les délais standard
                std_days = rate.standard_delivery_days or 0
                std_hours = rate.standard_delivery_hours or 0
                
                # Convertir tout en heures pour comparer
                total_std_hours = (std_days * 24) + std_hours
                max_total_std_hours = (max_standard_days * 24) + max_standard_hours
                
                if total_std_hours > max_total_std_hours:
                    max_standard_days = std_days
                    max_standard_hours = std_hours
                
                # Comparer les délais express
                exp_days = rate.express_delivery_days or 0
                exp_hours = rate.express_delivery_hours or 0
                
                total_exp_hours = (exp_days * 24) + exp_hours
                max_total_exp_hours = (max_express_days * 24) + max_express_hours
                
                if total_exp_hours > max_total_exp_hours:
                    max_express_days = exp_days
                    max_express_hours = exp_hours
                    
        except Exception as e:
            print(f"Erreur lors du calcul des délais pour produit {product_id}: {e}")
            continue
    
    # Si aucun délai trouvé, utiliser les valeurs par défaut
    if max_standard_days == 0 and max_standard_hours == 0:
        max_standard_days = 3
    if max_express_days == 0 and max_express_hours == 0:
        max_express_days = 1
    
    # Générer les labels
    # Standard
    if max_standard_days == 0 and max_standard_hours > 0:
        standard_label = f"Standard ({max_standard_hours}h)"
    elif max_standard_days == 0:
        standard_label = "Standard (même jour)"
    elif max_standard_days == 1:
        standard_label = "Standard (24h)"
    else:
        standard_label = f"Standard ({max_standard_days} jours)"
    
    # Express
    if max_express_days == 0 and max_express_hours > 0:
        express_label = f"Express ({max_express_hours}h)"
    elif max_express_days == 0:
        express_label = "Express (même jour)"
    elif max_express_days == 1:
        express_label = "Express (24-48h)"
    else:
        express_label = f"Express ({max_express_days} jours)"
    
    return {
        'max_standard_days': max_standard_days,
        'max_standard_hours': max_standard_hours,
        'max_express_days': max_express_days,
        'max_express_hours': max_express_hours,
        'standard_label': standard_label,
        'express_label': express_label
    }


def calculate_product_shipping_method(product_id, shipping_type='standard'):
    """
    Calcule le mode de livraison spécifique pour un produit donné
    
    Args:
        product_id: ID du produit
        shipping_type: 'standard' ou 'express'
    
    Returns:
        str: Mode de livraison formaté (ex: "Standard (7h)", "Express (3h)")
    """
    try:
        # Récupérer le produit et sa catégorie
        product = Product.query.get(product_id)
        if not product:
            return f"{shipping_type.title()} (délai inconnu)"
        
        # Chercher un tarif spécifique pour la sous-catégorie d'abord
        rate = None
        if product.subcategory_id:
            rate = ShippingRate.query.filter_by(
                rate_type='subcategory',
                subcategory_id=product.subcategory_id,
                active=True
            ).first()
        
        # Si pas de tarif sous-catégorie, chercher par catégorie
        if not rate and product.category_id:
            rate = ShippingRate.query.filter_by(
                rate_type='category',
                category_id=product.category_id,
                active=True
            ).first()
        
        # Si pas de tarif spécifique, utiliser le tarif par défaut
        if not rate:
            rate = ShippingRate.query.filter_by(
                rate_type='default',
                active=True
            ).first()
        
        if not rate:
            # Fallback ultime
            return f"{shipping_type.title()} (délai non configuré)"
        
        # Récupérer les délais selon le type de livraison
        if shipping_type == 'express':
            days = rate.express_delivery_days or 0
            hours = rate.express_delivery_hours or 0
        else:
            days = rate.standard_delivery_days or 0
            hours = rate.standard_delivery_hours or 0
        
        # Formater le label
        if days == 0 and hours > 0:
            return f"{shipping_type.title()} ({hours}h)"
        elif days == 0:
            return f"{shipping_type.title()} (même jour)"
        elif days == 1:
            return f"{shipping_type.title()} (24h)" if shipping_type == 'standard' else f"{shipping_type.title()} (24-48h)"
        else:
            return f"{shipping_type.title()} ({days} jours)"
            
    except Exception as e:
        print(f"Erreur calcul shipping method pour produit {product_id}: {e}")
        return f"{shipping_type.title()} (erreur)"


def calculate_delivery_details(shipping_method, cart_items):
    """
    Calcule les délais de livraison selon le mode choisi et les produits du panier
    
    Args:
        shipping_method (str): Mode de livraison choisi (ex: "Standard (3 jours)", "Express (24-48h)")
        cart_items (list): Liste des produits du panier
    
    Returns:
        dict: Délais calculés avec delivery_days, delivery_hours, estimated_delivery_date
    """
    from datetime import datetime, timedelta
    from models import ShippingRate, Product, Category, Subcategory
    
    # Déterminer le type de livraison (standard ou express)
    shipping_type = 'express' if 'express' in shipping_method.lower() or 'rapide' in shipping_method.lower() else 'standard'
    
    print(f"🚚 CALCUL DÉLAIS: Mode={shipping_method}, Type={shipping_type}")
    
    # Analyser les produits pour trouver les tarifs applicables
    max_delivery_days = 0
    max_delivery_hours = 0
    applicable_rates = []
    
    for item in cart_items:
        # Récupérer l'ID du produit original
        product_id = item.get('original_product_id', item.get('product_id'))
        if isinstance(product_id, str):
            try:
                if product_id.startswith('f_'):
                    product_id = int(product_id[2:].split('_')[0])
                else:
                    product_id = int(product_id.split('_')[0])
            except:
                continue
        
        # Récupérer le produit et ses catégories
        try:
            product = Product.query.get(product_id)
            if product:
                # Chercher un tarif spécifique pour la sous-catégorie
                if product.subcategory_id:
                    rate = ShippingRate.query.filter_by(
                        rate_type='subcategory',
                        subcategory_id=product.subcategory_id,
                        active=True
                    ).first()
                    if rate:
                        applicable_rates.append(rate)
                        continue
                
                # Chercher un tarif pour la catégorie
                if product.category_id:
                    rate = ShippingRate.query.filter_by(
                        rate_type='category',
                        category_id=product.category_id,
                        active=True
                    ).first()
                    if rate:
                        applicable_rates.append(rate)
                        continue
        except Exception as e:
            print(f"Erreur lors de la récupération du produit {product_id}: {e}")
    
    # Si aucun tarif spécifique, utiliser le tarif par défaut
    if not applicable_rates:
        default_rate = ShippingRate.query.filter_by(
            rate_type='default',
            active=True
        ).first()
        if default_rate:
            applicable_rates.append(default_rate)
    
    # Calculer les délais maximaux (le plus long délai l'emporte)
    for rate in applicable_rates:
        if shipping_type == 'express':
            days = rate.express_delivery_days or 1
            hours = rate.express_delivery_hours or 0
        else:
            days = rate.standard_delivery_days or 3
            hours = rate.standard_delivery_hours or 0
        
        # Prendre le délai le plus long
        if days > max_delivery_days or (days == max_delivery_days and hours > max_delivery_hours):
            max_delivery_days = days
            max_delivery_hours = hours
        
        print(f"   Tarif {rate.name}: {days}j {hours}h")
    
    # Valeurs par défaut si aucun tarif trouvé
    if max_delivery_days == 0:
        if shipping_type == 'express':
            max_delivery_days = 1
        else:
            max_delivery_days = 3
    
    # Calculer la date estimée de livraison
    estimated_date = datetime.now() + timedelta(days=max_delivery_days, hours=max_delivery_hours)
    
    # Exclure les week-ends (optionnel)
    while estimated_date.weekday() >= 5:  # 5=Samedi, 6=Dimanche
        estimated_date += timedelta(days=1)
    
    print(f"✅ DÉLAIS CALCULÉS: {max_delivery_days} jours, {max_delivery_hours} heures")
    print(f"   Date estimée: {estimated_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        'delivery_days': max_delivery_days,
        'delivery_hours': max_delivery_hours,
        'estimated_delivery_date': estimated_date
    }

@app.route('/complete-order', methods=['POST'])
@login_required  # Exiger que l'utilisateur soit connecté
def complete_order():
    """Finalise une commande et retire les produits commandés du panier"""
    # **NOUVELLE VERSION: Utilise la base de données au lieu des dictionnaires**
    
    # **PROTECTION CONTRE LES SOUMISSIONS MULTIPLES**
    order_token = request.form.get('order_token', '')
    last_order_token = session.get('last_order_token', '')
    
    if order_token and order_token == last_order_token:
        # Commande déjà traitée avec ce jeton
        return jsonify({
            'success': False,
            'message': 'Cette commande a déjà été traitée. Veuillez vérifier votre historique de commandes.',
            'error_type': 'duplicate_order',
            'redirect': url_for('profile')
        })
    
    # Marquer ce jeton comme utilisé
    if order_token:
        session['last_order_token'] = order_token
    
    # Récupérer les informations de code promo
    promo_code = request.form.get('promo_code', '').strip().upper()
    promo_discount = float(request.form.get('promo_discount', 0))
    
    # Debug logs pour les codes promo
    if promo_code:
        print(f"DEBUG PROMO: Code promo reçu: {promo_code}, discount: {promo_discount}")
    
    # Récupérer le type de checkout depuis le formulaire ou la session
    form_checkout_type = request.form.get('checkout_type', '')
    session_checkout_type = session.get('checkout_type', '')
    checkout_type = form_checkout_type or session_checkout_type
    
    checkout_cart = session.get('checkout_cart', [])
    
    # Debug logs
    print(f"DEBUG CHECKOUT: checkout_type={checkout_type}, cart_items_count={len(checkout_cart)}")
    
    # Si aucun type de checkout n'est spécifié, utiliser tout le panier
    if not checkout_type:
        checkout_cart = get_cart()
    
    # Vérifier si le panier est vide
    if not checkout_cart:
        return jsonify({
            'success': False,
            'message': 'Votre panier est vide',
            'redirect': url_for('cart')
        })
    
    # **NOUVELLE FONCTIONNALITÉ: Réserver le stock avant de traiter la commande**
    stock_reservation = reserve_stock(checkout_cart)
    if not stock_reservation['success']:
        return jsonify({
            'success': False,
            'message': stock_reservation['message'],
            'error_type': 'stock_insufficient'
        })
    
    # Stock réservé avec succès, continuer le traitement
    
    # Récupérer les informations sur la livraison et le paiement
    shipping_method_raw = request.form.get('shipping_method', 'Standard')
    payment_method = request.form.get('payment_method', 'Paiement à la livraison')
    address_id = request.form.get('address_id')
    
    # Récupérer la région et déterminer le type de livraison depuis le formulaire
    delivery_region = request.form.get('region', 'default')
    
    # Déterminer le type de livraison (standard ou express) depuis shipping_method
    if 'express' in shipping_method_raw.lower() or 'rapide' in shipping_method_raw.lower():
        shipping_type = 'express'
    else:
        shipping_type = 'standard'
    
    # Récupérer les informations de l'utilisateur connecté
    user_email = session.get('user_email')
    
    # **NOUVELLE VERSION: Utiliser la base de données**
    print(f"🔍 Recherche utilisateur par email: {user_email}")
    user_record_dict = get_user_by_email(user_email)
    if not user_record_dict:
        print(f"❌ Utilisateur non trouvé avec email: {user_email}")
        return jsonify({
            'success': False,
            'message': 'Utilisateur non trouvé',
            'redirect': url_for('login')
        })
    
    # Récupérer aussi l'objet User réel de la base de données pour les opérations qui en ont besoin
    user_record = User.query.filter_by(email=user_email).first()
    if not user_record:
        # Fallback si pas trouvé en base, créer un objet temporaire avec les données du dictionnaire
        user_record = type('UserRecord', (), user_record_dict)()
    
    print(f"✅ Utilisateur trouvé: {user_record_dict['email']} (ID: {user_record_dict['id']})")
    print(f"   Nom: {user_record_dict['first_name']} {user_record_dict['last_name']}")
    print(f"   Téléphone: {user_record_dict.get('phone', 'N/A')}")
    
    # **CORRECTION CRITIQUE: Utiliser directement les données de la base de données**
    # Créer l'adresse de livraison depuis les informations de l'utilisateur
    shipping_address = {
        'full_name': f"{user_record_dict['first_name']} {user_record_dict['last_name']}",
        'street': user_record_dict.get('address', ''),
        'city': user_record_dict.get('city', ''),
        'region': delivery_region or user_record_dict.get('region', 'default'),  # Priorité au formulaire
        'phone': user_record_dict.get('phone', '')
    }
    
    print(f"✅ Adresse de livraison créée: {shipping_address}")
    
    # user_record_dict est déjà un dictionnaire depuis get_user_by_email()
    user = user_record_dict
    
    # Grouper les produits par marchand dès le début
    merchant_groups = {}
        
    # Traiter les produits du panier et les grouper par marchand
    for item in checkout_cart:
        
        # Récupérer l'ID du produit original (pas l'unique_id avec options)
        if 'original_product_id' in item:
            product_id = item['original_product_id']
        else:
            # Fallback pour les anciens produits sans original_product_id
            product_id_str = str(item['product_id'])
            
            # Gérer les différents formats d'ID
            if product_id_str.startswith('f_'):
                # Produits alimentaires: f_101, f_101_hash, etc.
                parts = product_id_str[2:].split('_')  # Enlever le préfixe 'f_'
                try:
                    product_id = int(parts[0])
                except ValueError:
                    # Si ce n'est pas un nombre, utiliser l'ID tel quel
                    product_id = product_id_str
            elif '_' in product_id_str and not product_id_str.startswith('f_'):
                # C'est probablement un unique_id avec options, extraire l'ID original
                parts = product_id_str.split('_')
                try:
                    product_id = int(parts[0])
                except ValueError:
                    # Si le premier élément n'est pas un nombre, utiliser l'ID tel quel
                    product_id = product_id_str
            else:
                # ID simple, essayer de le convertir en entier
                try:
                    product_id = int(product_id_str)
                except ValueError:
                    # Si ce n'est pas un nombre, utiliser l'ID tel quel
                    product_id = product_id_str
        
        quantity = item['quantity']
        options = item.get('options', {})
        
        # Produits normaux - grouper par marchand
        try:
            product = get_product_by_id(product_id)
        except Exception as e:
            product = None
        
        if product:
            # Utiliser le prix modifié s'il est stocké dans l'élément du panier
            if 'modified_price' in item:
                product_price = item['modified_price']
            else:
                product_price = product['price']
            
            # Enrichir les options avec des noms plus descriptifs
            display_options = {}
            
            # Enrichir l'option "couleur"
            if 'color' in options and 'colors' in product:
                color_value = options['color']
                color_info = next((c for c in product['colors'] if c['value'] == color_value), None)
                if color_info:
                    display_options['color'] = color_info.get('name', color_value)
                    # Ajouter le modificateur de prix s'il existe
                    price_mod = color_info.get('price_modifier', 0)
                    if price_mod > 0:
                        display_options['color'] += f" (+{price_mod:,} KMF)".replace(',', ' ')
                else:
                    display_options['color'] = color_value
            
            # Enrichir l'option "taille"
            if 'size' in options and 'sizes' in product:
                size_value = options['size']
                size_info = next((s for s in product['sizes'] if s.get('value') == size_value or s == size_value), None)
                if size_info:
                    if isinstance(size_info, dict):
                        display_options['size'] = size_info.get('label', size_value)
                        price_mod = size_info.get('price_modifier', 0)
                        if price_mod > 0:
                            display_options['size'] += f" (+{price_mod:,} KMF)".replace(',', ' ')
                    else:
                        display_options['size'] = size_value
                else:
                    display_options['size'] = size_value
            
            # Enrichir l'option "stockage"
            if 'storage' in options and 'storage_options' in product:
                storage_value = options['storage']
                storage_info = next((s for s in product['storage_options'] if s['value'] == storage_value), None)
                if storage_info:
                    display_options['storage'] = storage_info['label']
                    price_mod = storage_info.get('price_modifier', 0)
                    if price_mod > 0:
                        display_options['storage'] += f" (+{price_mod:,} KMF)".replace(',', ' ')
                else:
                    display_options['storage'] = storage_value
            
            # Copier les autres options telles quelles
            for key, value in options.items():
                if key not in display_options:
                    display_options[key] = value
            
            # Identifier le marchand propriétaire du produit
            product_dict = product.to_dict() if hasattr(product, 'to_dict') else product
            merchant_email = product_dict.get('merchant_email')
            
            
            # Vérifier si c'est un produit admin (source='admin')
            if product_dict.get('source') == 'admin':
                merchant_email = 'admin_products'  # Clé spéciale pour les produits admin
            elif not merchant_email:
                # Pour les produits statiques, utiliser une clé spéciale
                merchant_email = 'static_products'
            
            
            # Initialiser le groupe du marchand s'il n'existe pas
            if merchant_email not in merchant_groups:
                merchant_groups[merchant_email] = []
            
            # Ajouter le produit au groupe du marchand
            merchant_groups[merchant_email].append({
                'id': product_id,
                'name': product_dict['name'],
                'price': product_price,
                'quantity': quantity,
                'subtotal': product_price * quantity,
                'image': product_dict['image'],
                'options': display_options,  # Utiliser les options enrichies
                'is_food': False,
                'merchant_email': merchant_email
            })
        else:
            print(f"❌ Produit introuvable: {product_id}")
    
    # Résumé du groupement
    for merchant_email, products in merchant_groups.items():
        print(f"👥 Marchand {merchant_email}: {len(products)} produit(s)")
        for j, prod in enumerate(products):
            print(f"  {j+1}. {prod['name']} x{prod['quantity']} = {prod['subtotal']} KMF")
    
    
    # Calculer le total global du panier pour déterminer les frais de livraison et les promos
    import random
    now = datetime.now()
    created_orders = []
    
    cart_total = 0
    for item in checkout_cart:
        # Récupérer l'ID du produit original
        if 'original_product_id' in item:
            product_id = item['original_product_id']
        else:
            product_id = item['product_id']
        
        quantity = item['quantity']
        
        # Récupérer le produit pour obtenir le prix
        product = get_product_by_id(product_id)
        if product:
            # Utiliser le prix modifié s'il existe, sinon le prix de base
            if 'modified_price' in item:
                price = float(item['modified_price'])
            else:
                price = float(product['price'])
            
            cart_total += price * quantity
    
    # Debug: Total du panier avant application du code promo
    
    # Utiliser la nouvelle fonction de calcul des frais de livraison dynamiques
    # avec analyse des catégories des produits dans le panier
    shipping_region = shipping_address.get('region', 'default')
    shipping_info = calculate_dynamic_shipping_fee(checkout_cart, cart_total, shipping_region, shipping_type)
    shipping_fee = shipping_info['shipping_fee']
    
    # Debug: Afficher les informations de livraison calculées
    print(f"DEBUG SHIPPING: Total panier={cart_total}, Région={shipping_region}, Type={shipping_type}")
    print(f"DEBUG SHIPPING: Frais calculés={shipping_fee}, Livraison gratuite={shipping_info['is_free_shipping']}")
    print(f"DEBUG SHIPPING: Catégories analysées={shipping_info['categories_analyzed']}")
    print(f"DEBUG SHIPPING: Sous-catégories analysées={shipping_info['subcategories_analyzed']}")
    if shipping_info.get('selected_rate'):
        print(f"DEBUG SHIPPING: Tarif sélectionné: {shipping_info['selected_rate'].get('name', 'N/A')} (priorité: {shipping_info['rate_priority']})")
    else:
        print(f"DEBUG SHIPPING: Utilisation des tarifs par défaut système")
    
    # Créer un shipping_method descriptif basé sur les informations calculées
    if shipping_info.get('selected_rate'):
        if shipping_type == 'express':
            delivery_days = shipping_info['selected_rate'].get('express_delivery_days', 1)
            delivery_hours = shipping_info['selected_rate'].get('express_delivery_hours', 0)
            
            if delivery_days == 0 and delivery_hours > 0:
                shipping_method = f"Express ({delivery_hours}h)"
            elif delivery_days == 0:
                shipping_method = "Express (même jour)"
            elif delivery_days == 1:
                shipping_method = "Express (24-48h)"
            else:
                shipping_method = f"Express ({delivery_days} jours)"
        else:
            delivery_days = shipping_info['selected_rate'].get('standard_delivery_days', 3)
            delivery_hours = shipping_info['selected_rate'].get('standard_delivery_hours', 0)
            
            if delivery_days == 0 and delivery_hours > 0:
                shipping_method = f"Standard ({delivery_hours}h)"
            elif delivery_days == 0:
                shipping_method = "Standard (même jour)"
            elif delivery_days == 1:
                shipping_method = "Standard (24h)"
            else:
                shipping_method = f"Standard ({delivery_days} jours)"
    else:
        # Utilisation des tarifs par défaut
        if shipping_type == 'express':
            shipping_method = "Express (24-48h)"
        else:
            shipping_method = "Standard (3 jours)"
    
    # Debug: Afficher les groupes de marchands
    for merchant_email, products in merchant_groups.items():
        print(f"🛍️ Marchand: {merchant_email}, Produits: {len(products)}")
    
    # Variable pour suivre si le code promo a déjà été appliqué
    promo_validation_result = None
    eligible_items = []
    
    # Re-valider le code promo avec les articles du panier si un code est fourni
    if promo_code and promo_discount > 0:
        # Convertir checkout_cart en format attendu par validate_promo_code
        cart_items_for_validation = []
        for item in checkout_cart:
            # Récupérer les informations du produit original
            original_product_id = item.get('original_product_id', item['product_id'])
            try:
                if isinstance(original_product_id, str) and original_product_id.isdigit():
                    original_product_id = int(original_product_id)
                elif isinstance(original_product_id, str):
                    original_product_id = int(original_product_id.split('_')[0])
            except (ValueError, AttributeError):
                original_product_id = item['product_id']
            
            product = get_product_by_id(original_product_id)
            if product:
                cart_items_for_validation.append({
                    'id': original_product_id,
                    'name': product['name'],
                    'price': item.get('modified_price', product['price']),
                    'quantity': item['quantity'],
                    'category_id': product.get('category_id'),
                    'subcategory_id': product.get('subcategory_id'),
                    'merchant_email': product.get('merchant_email', 'admin_products')
                })
        
        # Valider le code promo avec les articles réels
        user_email = session.get('user_email')
        promo_validation_result = validate_promo_code(promo_code, cart_total, user_email, cart_items_for_validation)
        
        if promo_validation_result.get('valid'):
            eligible_items = promo_validation_result.get('eligible_items', [])
        else:
            promo_code = None  # Annuler le code promo
            promo_discount = 0
    
    # **OPTIMISATION LIVRAISON: Calculer les frais optimisés pour commandes multiples**
    optimized_shipping_fees = optimize_shipping_fees_for_multiple_orders(
        merchant_groups, shipping_info, shipping_fee
    )
    
    # **NOUVELLE VERSION: Créer les commandes en base de données pour chaque marchand**
    for merchant_email, products in merchant_groups.items():
        # Récupérer les frais de livraison optimisés pour ce marchand
        merchant_shipping_fee = optimized_shipping_fees.get(merchant_email, 0)
        
        print(f"💳 COMMANDE {merchant_email}: Frais de livraison = {merchant_shipping_fee} KMF")
        
        # Calculer le total pour ce marchand
        total = sum(product['subtotal'] for product in products)
        
        # Calculer la réduction applicable à ce groupe de produits
        applied_discount = 0
        if promo_code and promo_discount > 0 and promo_validation_result:
            # Calculer la réduction pour les produits éligibles de ce marchand
            eligible_total = 0
            for product in products:
                for eligible_item in eligible_items:
                    if eligible_item['id'] == product['id']:
                        eligible_total += product['subtotal']
                        break
            
            if eligible_total > 0:
                # Récupérer les informations du code promo depuis la base de données
                from models import PromoCode
                promo_record = PromoCode.query.filter_by(code=promo_code).first()
                
                if promo_record:
                    if promo_record.type == 'percentage':
                        discount_amount = eligible_total * (promo_record.value / 100)
                        max_discount = promo_record.max_discount or float('inf')
                        applied_discount = min(discount_amount, max_discount)
                    elif promo_record.type == 'fixed':
                        applied_discount = min(promo_record.value, eligible_total)
        
        total_with_shipping = total + merchant_shipping_fee - applied_discount
        
        # **NOUVELLE VERSION: Déterminer le marchand ou créer la commande admin**
        merchant_id = None
        customer_id = user_record_dict['id']
        
        if merchant_email not in ['static_products', 'admin_products']:
            # Commande pour un vrai marchand
            merchant_record = get_merchant_by_email(merchant_email)
            if merchant_record:
                merchant_id = merchant_record.id
        
        # Préparer les données des articles pour create_complete_order
        order_items = []
        for product in products:
            order_items.append({
                'product_id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': product['quantity'],
                'image': product['image'],
                'variant_details': ', '.join([f"{k}: {v}" for k, v in product.get('options', {}).items()]),
                'options': product.get('options', {})
            })
        
        # **NOUVELLE VERSION: Créer la commande en base de données**
        try:
            print(f"🔍 Tentative de création de commande...")
            print(f"   customer_id: {customer_id}")
            print(f"   merchant_id: {merchant_id}")
            print(f"   order_items count: {len(order_items)}")
            print(f"   shipping_address: {shipping_address}")
            print(f"   total: {total_with_shipping}")
            
            # **NOUVEAU: Calculer les délais de livraison selon le mode choisi**
            delivery_details = calculate_delivery_details(shipping_method, products)
            
            db_order = create_complete_order(
                customer_id=customer_id,
                merchant_id=merchant_id,
                cart_items=order_items,
                shipping_address=shipping_address,
                shipping_method=shipping_method,
                payment_method=payment_method,
                shipping_fee=merchant_shipping_fee,
                discount=applied_discount,
                promo_code=promo_code if applied_discount > 0 else None,
                total=total_with_shipping,
                status='processing',
                delivery_days=delivery_details['delivery_days'],
                delivery_hours=delivery_details['delivery_hours'],
                estimated_delivery_date=delivery_details['estimated_delivery_date']
            )
            
            if db_order:
                print(f"✅ Commande créée en base de données: {db_order.order_number}")
                
                # **NOUVELLE FONCTIONNALITÉ: Envoyer notification à l'admin**
                try:
                    print(f"🔔 Tentative d'envoi de notification admin pour commande {db_order.order_number}")
                    admin_notification_result = send_admin_notification_new_order(db_order)
                    if admin_notification_result:
                        print(f"✅ Notification admin envoyée avec succès pour commande {db_order.order_number}")
                    else:
                        print(f"❌ Échec notification admin pour commande {db_order.order_number}")
                except Exception as e:
                    print(f"⚠️ Erreur notification admin: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                # **NOUVELLE FONCTIONNALITÉ: Synchroniser avec merchants_db pour compatibilité avec l'interface**
                if merchant_email not in ['static_products', 'admin_products'] and merchant_email in merchants_db:
                    # Créer un objet commande pour le dictionnaire en mémoire
                    memory_order = {
                        'id': db_order.id,
                        'order_number': db_order.order_number,
                        'customer_name': db_order.customer_name,
                        'customer_email': db_order.customer_email,
                        'customer_phone': db_order.customer_phone,
                        'items': order_items,
                        'total': db_order.total,
                        'status': db_order.status,
                        'status_text': db_order.status_text,
                        'status_color': db_order.status_color,
                        'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'payment_method': payment_method,
                        'payment_status': 'pending',
                        'shipping_method': shipping_method,
                        'shipping_address': shipping_address,
                        'shipping_fee': merchant_shipping_fee,
                        'discount': applied_discount,
                        'promo_code': promo_code if applied_discount > 0 else None
                    }
                    
                    # Ajouter la commande au dictionnaire du marchand
                    if 'orders' not in merchants_db[merchant_email]:
                        merchants_db[merchant_email]['orders'] = []
                    merchants_db[merchant_email]['orders'].append(memory_order)
                    print(f"✅ Commande ajoutée au dictionnaire en mémoire pour {merchant_email}")
                
                # Créer l'objet pour la réponse (compatibilité)
                order_response = {
                    'id': db_order.id,
                    'order_number': db_order.order_number,
                    'customer_name': db_order.customer_name,
                    'customer_email': db_order.customer_email,
                    'total': db_order.total,
                    'status': db_order.status,
                    'items': order_items,
                    'merchant_email': merchant_email
                }
                
                created_orders.append(order_response)
                
                # Envoyer les notifications email
                if merchant_id and merchant_record:
                    send_merchant_new_order_notification(merchant_email, order_response)
                
            else:
                print(f"❌ Échec de création de commande pour {merchant_email}")
                return jsonify({
                    'success': False,
                    'message': f'Échec de création de commande pour {merchant_email}'
                })
                
        except Exception as e:
            print(f"❌ Erreur lors de la création de commande: {str(e)}")
            print(f"❌ Type d'erreur: {type(e).__name__}")
            import traceback
            print(f"❌ Stack trace: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'Erreur lors de la création de commande: {str(e)}'
            })
    
    # **CORRECTION: Ne PAS libérer le stock après création réussie des commandes**
    # Le stock doit rester déduit jusqu'à la livraison ou l'annulation
    # On ne libère le stock réservé QUE en cas d'échec de création de commande
    if stock_reservation.get('reserved_items'):
        print("✅ Stock réservé conservé jusqu'à livraison ou annulation de commande")
        # Note: Le stock sera définitivement déduit lors du passage au statut 'delivered'
        # ou remis en cas d'annulation de commande
        
    # Vider le panier persistant après création réussie des commandes
    try:
        clear_success = clear_cart_db()
        if clear_success:
            print("✅ Panier persistant vidé après commande réussie")
        else:
            print("⚠️ Échec vidage panier persistant, nettoyage session seulement")
        
        # Nettoyer également les sessions de checkout
        session.pop('checkout_cart', None)
        session.pop('checkout_type', None)
    except Exception as e:
        print(f"Erreur lors du nettoyage du panier: {str(e)}")
    
    # **NOUVEAU: Appliquer le code promo (incrémenter le compteur d'utilisation)**
    if promo_code and promo_validation_result and promo_validation_result.get('valid'):
        print(f"📊 Application du code promo: {promo_code}")
        promo_applied = apply_promo_code(promo_code, user_email)
        if promo_applied:
            print(f"✅ Compteur d'utilisation du code promo '{promo_code}' mis à jour")
        else:
            print(f"⚠️ Échec de la mise à jour du compteur pour le code promo '{promo_code}'")
    
    # **CORRECTION CRITIQUE: Définir les variables de session pour la page de confirmation**
    order_ids = [order['id'] for order in created_orders]
    order_numbers = [order['order_number'] for order in created_orders]
    
    session['last_order_ids'] = order_ids
    session['last_order_numbers'] = order_numbers  
    session['orders_count'] = len(created_orders)
    
    print(f"✅ Variables de session définies pour confirmation:")
    print(f"   last_order_ids: {order_ids}")
    print(f"   last_order_numbers: {order_numbers}")
    print(f"   orders_count: {len(created_orders)}")
    
    # Réponse de succès
    return jsonify({
        'success': True,
        'message': f"Commande{'s' if len(created_orders) > 1 else ''} créée{'s' if len(created_orders) > 1 else ''} avec succès !",
        'orders': created_orders,
        'total_orders': len(created_orders),
        'redirect': url_for('order_confirmation')
    })

@app.route('/validate-promo-code', methods=['POST'])
def validate_promo_code_route():
    """Valide un code promo et calcule la réduction"""
    try:
        data = request.get_json()
        code = data.get('code', '').upper().strip()
        total = float(data.get('total', 0))
        cart_items = data.get('cart_items', [])  # Ajouter les articles du panier
        
        # Récupérer l'email de l'utilisateur connecté
        user_email = None
        if 'user_id' in session:
            user_email = session.get('user_email')
        
        if not code:
            return jsonify({
                'success': False,
                'message': 'Code promo manquant'
            })
        
        # Valider le code promo avec l'email de l'utilisateur et les articles du panier
        validation = validate_promo_code(code, total, user_email, cart_items)
        
        if validation['valid']:
            # La réduction est déjà calculée dans validate_promo_code
            discount = validation['discount']
            eligible_total = validation.get('eligible_total', total)
            
            # S'assurer que la réduction ne dépasse pas le total éligible
            discount = min(discount, eligible_total)
            new_total = total - discount
            
            return jsonify({
                'success': True,
                'message': f'Code promo "{code}" appliqué avec succès!',
                'discount': discount,
                'new_total': new_total
            })
        else:
            return jsonify({
                'success': False,
                'message': validation['message']
            })
            
    except Exception as e:
        print(f"Erreur lors de la validation du code promo: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la validation du code promo'
        })

# Ajouter une route pour la page de confirmation de commande
@app.route('/order-confirmation')
def order_confirmation():
    """Affiche la page de confirmation après une commande réussie"""
    # Récupérer les données des dernières commandes (nouvelles)
    last_order_ids = session.get('last_order_ids', [])
    last_order_numbers = session.get('last_order_numbers', [])
    orders_count = session.get('orders_count', 0)
    
    # Si nouvelles données disponibles, les utiliser
    if last_order_ids and last_order_numbers:
        return render_template('order_confirmation.html', 
                             order_ids=last_order_ids, 
                             order_numbers=last_order_numbers,
                             orders_count=orders_count)
    
    # Fallback pour l'ancien système (compatibilité)
    last_order_id = session.get('last_order_id')
    order_number = session.get('last_order_number')
    
    if last_order_id and order_number:
        return render_template('order_confirmation.html', 
                             order_ids=[last_order_id], 
                             order_numbers=[order_number],
                             orders_count=1)
    
    # Si aucune donnée, rediriger vers les commandes
    return redirect(url_for('orders'))

@app.route('/orders')
@login_required
def orders():
    """Affiche la page des commandes de l'utilisateur"""
    # Récupérer l'email de l'utilisateur à partir de la session
    user_email = session.get('user_email')
    
    # Récupérer les commandes de l'utilisateur depuis la base de données
    user_orders = get_user_orders(user_email)
    
    # S'assurer que les commandes sont des dictionnaires normaux et non des objets
    # Cela aide à éviter les problèmes d'accès avec les dictionnaires vs objets
    # (order.items vs order["items"])
    for order in user_orders:
        # S'assurer que les clés sont accessibles avec la notation par crochets
        if 'items' not in order or not isinstance(order['items'], list):
            order['items'] = []  # S'assurer que items est toujours une liste même vide
    
    # Détecter si nous venons de compléter une commande pour ouvrir automatiquement l'accordéon
    new_order = request.args.get('new_order') == 'true'
    
    return render_template('orders.html', orders=user_orders, new_order=new_order)

@app.route('/addresses')
@login_required
def addresses():
    """Affiche la page des adresses de l'utilisateur - Version multi-adresses"""
    user_email = session.get('user_email')
    
    # Récupérer l'utilisateur depuis la base de données
    user_record = User.query.filter_by(email=user_email).first()
    
    if user_record:
        # Utiliser les nouvelles adresses de la table Address
        user_addresses = []
        
        # Récupérer toutes les adresses de l'utilisateur
        db_addresses = Address.query.filter_by(user_id=user_record.id).order_by(Address.is_default.desc(), Address.created_at.asc()).all()
        
        for addr in db_addresses:
            user_addresses.append({
                'id': addr.id,
                'name': addr.name,
                'full_name': addr.full_name,
                'street': addr.street,
                'city': addr.city,
                'region': addr.region,
                'phone': addr.phone,
                'is_default': addr.is_default
            })
        
        # Si aucune adresse dans la nouvelle table, fallback vers l'ancienne adresse du profil
        if not user_addresses and user_record.address:
            # Migration automatique de l'adresse du profil
            try:
                new_address = Address(
                    user_id=user_record.id,
                    name='Adresse principale',
                    full_name=f"{user_record.first_name} {user_record.last_name}",
                    street=user_record.address,
                    city=user_record.city or 'N/A',
                    region=user_record.region or 'N/A',
                    phone=user_record.phone or 'N/A',
                    is_default=True
                )
                
                db.session.add(new_address)
                db.session.commit()
                
                # Ajouter à la liste pour l'affichage
                user_addresses.append({
                    'id': new_address.id,
                    'name': new_address.name,
                    'full_name': new_address.full_name,
                    'street': new_address.street,
                    'city': new_address.city,
                    'region': new_address.region,
                    'phone': new_address.phone,
                    'is_default': new_address.is_default
                })
                
            except Exception as e:
                print(f"Erreur migration automatique: {e}")
                db.session.rollback()
        
    else:
        # Fallback: utiliser l'ancien système (pour compatibilité)
        user = users_db.get(user_email, {})
        user_addresses = user.get('addresses', [])
        
        if not user_addresses and user.get('address'):
            user_addresses = [{
                'id': 1,
                'name': 'Domicile',
                'full_name': f"{user.get('first_name', '')} {user.get('last_name', '')}",
                'street': user.get('address', ''),
                'city': user.get('city', ''),
                'region': user.get('region', ''),
                'phone': user.get('phone', ''),
                'is_default': True
            }]
    
    return render_template('addresses.html', addresses=user_addresses)

@app.route('/add-address', methods=['POST'])
@login_required
def add_address():
    """Ajouter une nouvelle adresse - Version multi-adresses complète"""
    user_email = session.get('user_email')
    
    # Récupérer l'utilisateur depuis la base de données
    user_record = User.query.filter_by(email=user_email).first()
    
    if not user_record:
        flash('Utilisateur non trouvé.', 'danger')
        return redirect(url_for('addresses'))
    
    # Récupérer les données du formulaire
    name = request.form.get('name', '').strip()
    full_name = request.form.get('full_name', '').strip()
    street = request.form.get('street', '').strip()
    city = request.form.get('city', '').strip()
    region = request.form.get('region', '').strip()
    phone = request.form.get('phone', '').strip()
    is_default = 'is_default' in request.form
    
    # Valider les données du formulaire
    if not all([name, full_name, street, city, region, phone]):
        flash('Tous les champs sont requis.', 'danger')
        return redirect(url_for('addresses'))
    
    try:
        # Si cette adresse doit être par défaut, retirer le statut des autres
        if is_default:
            existing_default = Address.query.filter_by(user_id=user_record.id, is_default=True).all()
            for addr in existing_default:
                addr.is_default = False
        
        # Créer la nouvelle adresse
        new_address = Address(
            user_id=user_record.id,
            name=name,
            full_name=full_name,
            street=street,
            city=city,
            region=region,
            phone=phone,
            is_default=is_default
        )
        
        db.session.add(new_address)
        db.session.commit()
        
        flash('Adresse ajoutée avec succès.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'ajout d'adresse: {e}")
        flash('Erreur lors de l\'ajout de l\'adresse.', 'danger')
    
    return redirect(url_for('addresses'))

@app.route('/set-default-address/<int:address_id>', methods=['POST'])
@login_required
def set_default_address(address_id):
    """Définir une adresse comme adresse par défaut - Version multi-adresses"""
    user_email = session.get('user_email')
    
    # Récupérer l'utilisateur depuis la base de données
    user_record = User.query.filter_by(email=user_email).first()
    
    if not user_record:
        flash('Utilisateur non trouvé.', 'danger')
        return redirect(url_for('addresses'))
    
    try:
        # Récupérer l'adresse à définir par défaut
        target_address = Address.query.filter_by(id=address_id, user_id=user_record.id).first()
        
        if not target_address:
            flash('Adresse non trouvée.', 'danger')
            return redirect(url_for('addresses'))
        
        # Retirer le statut par défaut de toutes les autres adresses
        other_addresses = Address.query.filter_by(user_id=user_record.id, is_default=True).all()
        for addr in other_addresses:
            addr.is_default = False
        
        # Définir la nouvelle adresse par défaut
        target_address.is_default = True
        
        db.session.commit()
        flash('Adresse définie comme adresse par défaut.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la définition de l'adresse par défaut: {e}")
        flash('Erreur lors de la mise à jour.', 'danger')
    
    return redirect(url_for('addresses'))

@app.route('/delete-address/<int:address_id>', methods=['POST'])
@login_required
def delete_address(address_id):
    """Supprimer une adresse - Version multi-adresses"""
    user_email = session.get('user_email')
    
    # Récupérer l'utilisateur depuis la base de données
    user_record = User.query.filter_by(email=user_email).first()
    
    if not user_record:
        flash('Utilisateur non trouvé.', 'danger')
        return redirect(url_for('addresses'))
    
    try:
        # Récupérer l'adresse à supprimer
        address_to_delete = Address.query.filter_by(id=address_id, user_id=user_record.id).first()
        
        if not address_to_delete:
            flash('Adresse non trouvée.', 'danger')
            return redirect(url_for('addresses'))
        
        # Vérifier qu'il reste au moins une autre adresse si celle-ci est par défaut
        remaining_addresses = Address.query.filter_by(user_id=user_record.id).count()
        
        if remaining_addresses <= 1:
            flash('Vous ne pouvez pas supprimer votre dernière adresse.', 'warning')
            return redirect(url_for('addresses'))
        
        was_default = address_to_delete.is_default
        
        # Supprimer l'adresse
        db.session.delete(address_to_delete)
        
        # Si l'adresse supprimée était par défaut, définir une autre comme par défaut
        if was_default:
            next_address = Address.query.filter_by(user_id=user_record.id).first()
            if next_address:
                next_address.is_default = True
        
        db.session.commit()
        flash('Adresse supprimée avec succès.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la suppression d'adresse: {e}")
        flash('Erreur lors de la suppression.', 'danger')
    
    return redirect(url_for('addresses'))

@app.route('/edit-address/<int:address_id>', methods=['POST'])
@login_required
def edit_address(address_id):
    """Route pour modifier une adresse existante"""
    user_email = session.get('user_email')
    user = users_db.get(user_email)
    
    if not user or 'addresses' not in user:
        flash('Utilisateur ou adresses non trouvés.', 'danger')
        return redirect(url_for('addresses'))
    
    # Récupérer les données du formulaire
    name = request.form.get('name', '')
    full_name = request.form.get('full_name', '')
    street = request.form.get('street', '')
    city = request.form.get('city', '')
    region = request.form.get('region', '')
    phone = request.form.get('phone', '')
    is_default = 'is_default' in request.form
    
    # Valider les données du formulaire
    if not all([name, full_name, street, city, region, phone]):
        flash('Tous les champs sont requis.', 'danger')
        return redirect(url_for('addresses'))
    
    # Trouver l'adresse à modifier
    address_found = False
    for addr in user['addresses']:
        if addr['id'] == address_id:
            # Mettre à jour les informations de l'adresse
            addr['name'] = name
            addr['full_name'] = full_name
            addr['street'] = street
            addr['city'] = city
            addr['region'] = region
            addr['phone'] = phone
            addr['is_default'] = is_default
            
            # Si cette adresse est définie par défaut, mettre à jour les autres adresses
            if is_default:
                for other_addr in user['addresses']:
                    if other_addr['id'] != address_id:
                        other_addr['is_default'] = False
            
            address_found = True
            break
    
    if not address_found:
        flash('Adresse non trouvée.', 'danger')
    else:
        flash('Adresse modifiée avec succès.', 'success')
    
    return redirect(url_for('addresses'))

@app.route('/wishlist')
@login_required
def wishlist():
    """Affiche la liste d'envies de l'utilisateur"""
    # Récupérer l'ID de l'utilisateur connecté depuis la session
    user_id = session.get('user_id')
    
    if not user_id:
        flash('Vous devez être connecté pour accéder à votre liste d\'envies.', 'warning')
        return redirect(url_for('login'))
    
    # Récupérer les items de la wishlist depuis la base de données
    wishlist_items = []
    wishlist_records = WishlistItem.query.filter_by(user_id=user_id).all()
    
    # Récupérer les détails de chaque produit dans la liste d'envies
    for wishlist_item in wishlist_records:
        product = get_product_by_id(wishlist_item.product_id)
        if product:
            wishlist_items.append(product)
    
    return render_template('wishlist.html', wishlist_items=wishlist_items)

@app.route('/add-to-wishlist/<int:product_id>', methods=['GET', 'POST'])
@login_required
def add_to_wishlist(product_id):
    """Ajoute un produit à la liste d'envies de l'utilisateur"""
    # Vérifier d'abord que le produit existe et est actif
    product = get_product_by_id(product_id)
    if not product:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Produit non trouvé'})
        flash('Produit non trouvé', 'error')
        return redirect(url_for('products'))
    
    # Vérifier si l'utilisateur est admin ou si le produit est accessible au public
    is_admin = session.get('admin_email') is not None
    
    if not is_admin and not is_product_public(product):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Ce produit n\'est plus disponible'})
        flash('Ce produit n\'est plus disponible', 'error')
        return redirect(url_for('products'))
    
    user_id = session.get('user_id')
    
    if not user_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Vous devez être connecté'})
        flash('Vous devez être connecté pour ajouter des produits à vos favoris', 'warning')
        return redirect(url_for('login'))
    
    # Vérifier si l'item est déjà dans la wishlist
    existing_item = WishlistItem.query.filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()
    
    if not existing_item:
        # Créer un nouvel item de wishlist dans la base de données
        try:
            wishlist_item = WishlistItem(
                user_id=user_id,
                product_id=product_id
            )
            db.session.add(wishlist_item)
            db.session.commit()
            
            flash('Produit ajouté à votre liste d\'envies!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de l\'ajout à la liste d\'envies', 'error')
            print(f"Erreur wishlist: {e}")
    else:
        flash('Ce produit est déjà dans votre liste d\'envies.', 'info')
    
    # Compter les items de la wishlist pour l'utilisateur
    wishlist_count = WishlistItem.query.filter_by(user_id=user_id).count()
    
    # Si la requête vient d'AJAX, retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': 'Produit ajouté à votre liste d\'envies' if not existing_item else 'Produit déjà dans la liste d\'envies',
            'wishlist_count': wishlist_count
        })
    
    # Rediriger vers la page précédente ou la page du produit
    referer = request.referrer
    if referer and referer != request.url:
        return redirect(referer)
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/remove-from-wishlist/<int:product_id>', methods=['POST'])
@login_required
def remove_from_wishlist(product_id):
    """Retire un produit de la liste d'envies de l'utilisateur"""
    user_id = session.get('user_id')
    
    if not user_id:
        flash('Vous devez être connecté pour effectuer cette action', 'warning')
        return redirect(url_for('login'))
    
    # Rechercher et supprimer l'item de la wishlist dans la base de données
    wishlist_item = WishlistItem.query.filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()
    
    if wishlist_item:
        try:
            db.session.delete(wishlist_item)
            db.session.commit()
            flash('Produit retiré de votre liste d\'envies', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de la suppression', 'error')
            print(f"Erreur suppression wishlist: {e}")
    else:
        flash('Produit non trouvé dans votre liste d\'envies', 'info')
    
    # Compter les items restants
    wishlist_count = WishlistItem.query.filter_by(user_id=user_id).count()
    
    # Si la requête vient d'AJAX, retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': 'Produit retiré de votre liste d\'envies',
            'wishlist_count': wishlist_count
        })
    
    return redirect(url_for('wishlist'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Page de profil de l'utilisateur - Version migrée vers la base de données"""
    user_email = session.get('user_email')
    
    # Récupérer l'utilisateur depuis la base de données d'abord
    user_record = User.query.filter_by(email=user_email).first()
    
    if not user_record:
        # Fallback vers l'ancien système
        user = users_db.get(user_email, {})
        if not user:
            flash('Erreur: Profil utilisateur introuvable.', 'danger')
            return redirect(url_for('logout'))
    
    if request.method == 'POST':
        # Mise à jour des informations du profil
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        region = request.form.get('region', '').strip()
        
        if user_record:
            # Mise à jour dans la base de données
            try:
                user_record.first_name = first_name
                user_record.last_name = last_name
                user_record.phone = phone
                user_record.address = address
                user_record.city = city
                user_record.region = region
                user_record.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                # Synchroniser avec le dictionnaire en mémoire pour compatibilité
                if user_email in users_db:
                    users_db[user_email].update({
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone': phone,
                        'address': address,
                        'city': city,
                        'region': region
                    })
                
                flash('Profil mis à jour avec succès.', 'success')
                return redirect(url_for('profile'))
                
            except Exception as e:
                db.session.rollback()
                flash('Erreur lors de la mise à jour du profil.', 'error')
                print(f"Erreur mise à jour profil utilisateur: {e}")
                return redirect(url_for('profile'))
        else:
            # Fallback: mise à jour dans l'ancien système
            user = users_db.get(user_email, {})
            user.update({
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'address': address,
                'city': city,
                'region': region
            })
            users_db[user_email] = user
            
            flash('Profil mis à jour avec succès.', 'success')
            return redirect(url_for('profile'))
    
    # Préparer les données utilisateur pour l'affichage
    if user_record:
        user_data = user_record.to_dict()
        user_data['email'] = user_email
    else:
        # Fallback vers l'ancien système
        user_data = users_db.get(user_email, {}).copy()
        user_data['email'] = user_email
    
    # Calculer les statistiques utilisateur depuis la base de données
    user_stats = get_user_order_stats(user_email)
    
    # Ajouter les statistiques de wishlist
    if user_record:
        from db_helpers import get_user_wishlist
        user_wishlist = get_user_wishlist(user_record.id)
        user_stats['wishlist'] = len(user_wishlist) if user_wishlist else 0
    else:
        user_stats['wishlist'] = len(users_db.get(user_email, {}).get('wishlist', []))
    
    # Ajouter le nombre d'avis depuis la base de données
    from models import Review
    user_reviews_count = Review.query.filter_by(user_id=user_record.id).count() if user_record else 0
    user_stats['reviews'] = user_reviews_count
    
    # Renommer pour compatibilité avec le template
    user_stats['orders'] = user_stats['total_orders']
    
    return render_template('profile.html', user=user_data, user_stats=user_stats)

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Permet à l'utilisateur de changer son mot de passe"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Vérifier les données du formulaire
        if not current_password or not new_password or not confirm_password:
            flash('Tous les champs sont requis', 'danger')
           
            return redirect(url_for('change_password'))
        
        if new_password != confirm_password:
            flash('Les nouveaux mots de passe ne correspondent pas', 'danger')
            return redirect(url_for('change_password'))
        
        # Vérifier que l'ancien mot de passe est correct
        user_email = session.get('user_email')
        user_record = User.query.filter_by(email=user_email).first()
        
        if not user_record or not check_password_hash(user_record.password_hash, current_password):
            flash('Mot de passe actuel incorrect', 'danger')
            return redirect(url_for('change_password'))
        
        # Mettre à jour le mot de passe dans la base de données
        try:
            user_record.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
            if user_email in users_db:
                users_db[user_email]['password_hash'] = user_record.password_hash
            
            flash('Votre mot de passe a été modifié avec succès', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de la modification du mot de passe', 'error')
            print(f"Erreur changement mot de passe: {e}")
            return redirect(url_for('change_password'))
    
    return render_template('change_password.html')

@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Affiche les détails d'une commande spécifique"""
    
    # Récupérer l'email de l'utilisateur connecté
    user_email = session.get('user_email')
    
    # Récupérer la commande spécifique depuis la base de données
    order_data = get_user_order_by_id(user_email, order_id)
    
    # Si la commande n'est pas trouvée, afficher une page d'erreur
    if not order_data:
        flash('Commande non trouvée', 'danger')
        return redirect(url_for('orders'))
    
    # S'assurer que toutes les informations nécessaires sont présentes
    if 'items' not in order_data:
        order_data['items'] = []
    
    # S'assurer que les statuts et dates sont cohérents
    if 'status' not in order_data:
        order_data['status'] = 'processing'
    
    if 'status_text' not in order_data:
        status_texts = {
            'processing': 'En préparation',
            'shipped': 'Expédiée',
            'delivered': 'Livrée',
            'cancelled': 'Annulée'
        }
        order_data['status_text'] = status_texts.get(order_data['status'], 'En traitement')
    
    if 'status_color' not in order_data:
        status_colors = {
            'processing': 'primary',
            'shipped': 'info',
            'delivered': 'success',
            'cancelled': 'danger'
        }
        order_data['status_color'] = status_colors.get(order_data['status'], 'secondary')
    
    # S'assurer que la date de commande est disponible sous le nom 'date' pour compatibilité
    if 'date' not in order_data and 'created_at' in order_data:
        order_data['date'] = order_data['created_at']
    elif 'date' not in order_data:
        order_data['date'] = '--'
    
    # S'assurer que les dates spécifiques sont présentes
    if 'processing_date' not in order_data or not order_data['processing_date']:
        # Si la commande est au moins en traitement, utiliser la date de création
        if order_data['status'] in ['processing', 'shipped', 'delivered']:
            order_data['processing_date'] = order_data.get('created_at', order_data.get('date', ''))
        else:
            order_data['processing_date'] = None
    
    if 'shipping_date' not in order_data or not order_data['shipping_date']:
        # Si la commande est au moins expédiée, utiliser la date de création ou de traitement
        if order_data['status'] in ['shipped', 'delivered']:
            order_data['shipping_date'] = order_data.get('created_at', order_data.get('date', ''))
        else:
            order_data['shipping_date'] = None
    
    if 'delivery_date' not in order_data or not order_data['delivery_date']:
        # Si la commande est livrée, utiliser la date de création
        if order_data['status'] == 'delivered':
            order_data['delivery_date'] = order_data.get('created_at', order_data.get('date', ''))
        else:
            order_data['delivery_date'] = None
    
    return render_template('order_detail.html', order=order_data)

@app.route('/api/order/<int:order_id>/can-cancel', methods=['GET'])
@login_required
def api_check_order_cancellation(order_id):
    """API pour vérifier si une commande peut être annulée"""
    user_email = session.get('user_email')
    
    # Récupérer la commande spécifique depuis la base de données
    order = get_user_order_by_id(user_email, order_id)
    
    if not order:
        return jsonify({'success': False, 'message': 'Commande non trouvée'}), 404
    
    # Vérifier si la commande peut être annulée
    can_cancel, reason = can_order_be_cancelled(order)
    
    # Obtenir les informations sur la méthode de paiement
    payment_info = get_payment_method_info(order.get('payment_method', ''))
    
    return jsonify({
        'success': True,
        'can_cancel': can_cancel,
        'reason': reason,
        'payment_method': order.get('payment_method'),
        'payment_info': payment_info,
        'order_status': order.get('status')
    })

@app.route('/cancel-order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Permet au client d'annuler une commande en cours de préparation"""
    user_email = session.get('user_email')
    
    # Récupérer la commande depuis la base de données
    order_to_cancel = get_user_order_by_id(user_email, order_id)
    
    if not order_to_cancel:
        return jsonify({'success': False, 'message': 'Commande non trouvée'}), 404
    
    # Vérifier que la commande peut être annulée (utiliser la fonction can_order_be_cancelled)
    can_cancel, cancel_reason = can_order_be_cancelled(order_to_cancel)
    if not can_cancel:
        return jsonify({
            'success': False, 
            'message': cancel_reason
        }), 400
    
    # Annuler la commande dans la base de données
    success, message = cancel_user_order(user_email, order_id)
    
    if not success:
        return jsonify({'success': False, 'message': message}), 400
    
    # **LIBÉRATION DU STOCK LORS DE L'ANNULATION**
    try:
        # Récupérer les items de la commande pour libérer le stock réservé
        order_items = order_to_cancel.get('items', [])
        if order_items:
            # Libérer le stock réservé (remettre les quantités)
            release_stock(order_items)
            print(f"✅ Stock libéré pour commande annulée {order_id} ({len(order_items)} articles)")
    except Exception as e:
        print(f"⚠️ Erreur lors de la libération du stock pour commande annulée {order_id}: {e}")
    
    # **ENVOYER EMAIL DE NOTIFICATION D'ANNULATION AU CLIENT**
    try:
        send_order_status_email(user_email, order_to_cancel, 'processing', 'cancelled')
        print(f"Email de notification d'annulation envoyé à {user_email} pour commande {order_id}")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email d'annulation à {user_email}: {str(e)}")
    
    return jsonify({
        'success': True,
        'message': 'Commande annulée avec succès',
        'status': 'cancelled',
        'status_text': 'Annulée par le client',
        'status_color': 'danger'
    })

@app.route('/merchant/order/<int:order_id>/update-status', methods=['POST'])
@merchant_required
def merchant_update_order_status(order_id):
    """Met à jour le statut d'une commande"""
    merchant_email = session.get('merchant_email')
    
    status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    # Validation des données
    if not status:
        return jsonify({'success': False, 'message': 'Le statut est requis'})
    
    # **NOUVELLE VERSION: Récupérer la commande depuis la base de données**
    from db_helpers import get_order_by_id, get_merchant_by_email, update_order_status
    
    # Récupérer la commande depuis la DB
    db_order = get_order_by_id(order_id)
    
    if not db_order:
        return jsonify({'success': False, 'message': 'Commande non trouvée'})
    
    # Vérifier que cette commande appartient à ce marchand
    merchant_record = get_merchant_by_email(merchant_email)
    if not merchant_record or db_order.merchant_id != merchant_record.id:
        return jsonify({'success': False, 'message': 'Commande non trouvée pour ce marchand'})
    
    # Définir les mappings de statuts
    status_colors = {
        'processing': 'primary',
        'shipped': 'info',
        'delivered': 'success',
        'cancelled': 'danger'
    }
    status_texts = {
        'processing': 'En cours de préparation',
        'shipped': 'Expédiée',
        'delivered': 'Livrée',
        'cancelled': 'Annulée'
    }
    
    # Ajouter des notes automatiques selon le statut
    auto_notes = {
        'shipped': 'Expédié vers le Dépôt Douka KM',
        'delivered': 'Le colis est livré'
    }
    
    # Si pas de note fournie et qu'il y a une note automatique pour ce statut
    if not notes and status in auto_notes:
        notes = auto_notes[status]
    # Si il y a déjà une note et qu'il y a une note automatique, les combiner
    elif notes and status in auto_notes:
        notes = f"{notes} - {auto_notes[status]}"
    
    # Vérifier si la commande est déjà livrée
    current_status = db_order.status
    if current_status == 'delivered':
        return jsonify({
            'success': False, 
            'message': 'Impossible de modifier le statut d\'une commande déjà livrée'
        })
    
    # Empêcher de revenir à un statut antérieur
    status_hierarchy = ['processing', 'shipped', 'delivered']
    if current_status in status_hierarchy and status in status_hierarchy:
        current_index = status_hierarchy.index(current_status)
        new_index = status_hierarchy.index(status)
        if new_index < current_index:
            return jsonify({
                'success': False, 
                'message': f'Impossible de revenir de "{status_texts.get(current_status, current_status)}" vers "{status_texts.get(status, status)}"'
            })
    
    # Mettre à jour le statut dans la base de données
    try:
        result = update_order_status(order_id, status, notes, 'Marchand')
        
        if not result:
            return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour du statut'})
        
        # Récupérer la commande mise à jour
        updated_order = result['order']
        
        # **NOUVELLE FONCTIONNALITÉ: Confirmer la déduction du stock définitive lors de la livraison**
        if status == 'delivered' and current_status != 'delivered':
            try:
                # Récupérer les items de la commande depuis la base de données
                import json
                order_items_raw = updated_order.items
                if isinstance(order_items_raw, str):
                    order_items = json.loads(order_items_raw)
                else:
                    order_items = order_items_raw or []
                
                # Confirmer la déduction du stock final (le stock était déjà réservé lors de la création de commande)
                confirm_stock_deduction(order_items)
                print(f"✅ Stock confirmé définitivement pour commande {order_id} - {len(order_items)} articles")
                
            except Exception as e:
                print(f"⚠️ Erreur lors de la confirmation du stock pour commande {order_id}: {e}")
        
        # **LIBÉRATION DU STOCK LORS DE L'ANNULATION PAR LE MARCHAND**
        if status == 'cancelled' and current_status != 'cancelled':
            try:
                # Récupérer les items de la commande depuis la base de données
                import json
                order_items_raw = updated_order.items
                if isinstance(order_items_raw, str):
                    order_items = json.loads(order_items_raw)
                else:
                    order_items = order_items_raw or []
                
                # Libérer le stock réservé (remettre les quantités)
                release_stock(order_items)
                print(f"✅ Stock libéré pour commande annulée par marchand {order_id} ({len(order_items)} articles)")
                
            except Exception as e:
                print(f"⚠️ Erreur lors de la libération du stock pour commande annulée {order_id}: {e}")
        
        # Envoyer notification email au client si le statut a changé significativement
        customer_email = updated_order.customer_email
        if customer_email and status in ['processing', 'shipped', 'delivered', 'cancelled']:
            try:
                # Récupérer les détails de la commande pour l'email
                order_data = get_user_order_by_id(customer_email, order_id)
                if order_data:
                    send_order_status_email(customer_email, order_data, current_status, status)
                    print(f"Email de notification envoyé à {customer_email} pour commande {order_id}")
                else:
                    print(f"⚠️ Commande {order_id} non trouvée pour l'email à {customer_email}")
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email à {customer_email}: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Statut mis à jour avec succès',
            'status': status,
            'status_text': status_texts.get(status, status),
            'status_color': status_colors.get(status, 'secondary')
        })
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour du statut: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour du statut'})

# Fonction pour s'assurer que les répertoires nécessaires existent
def ensure_directories_exist():
    """Vérifie et crée les répertoires nécessaires pour le stockage des fichiers"""
    directories = [
        os.path.join(app.root_path, 'static', 'img', 'merchants'),
        os.path.join(app.root_path, 'static', 'img', 'products')
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Vérifié/créé répertoire: {directory}")

# Appeler la fonction au démarrage de l'application
ensure_directories_exist()

# Fonction pour créer des demandes de retrait de test
def create_test_withdrawal_requests():
    """Créer des demandes de retrait de test pour le développement"""
    import uuid
    
    # Vérifier s'il y a déjà des demandes
    if withdrawal_requests_db:
        return
    
    # Créer quelques demandes de test pour les marchands existants
    test_requests = []
    
    merchant_emails = list(merchants_db.keys())
    
    for i, req_data in enumerate(test_requests):
        if not merchant_emails:
            break
        
        merchant_email = merchant_emails[i % len(merchant_emails)]
        
        # Générer un ID unique
        request_id = f"WR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        withdrawal_request = {
            'id': request_id,
            'merchant_email': merchant_email,
            'amount': float(req_data['amount']),
            'method': req_data['method'],
            'status': req_data['status'],
            'requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S') if req_data['status'] in ['completed', 'rejected'] else None,
            'notes': req_data['notes'],
            'admin_notes': req_data.get('admin_notes', ''),
            'reference': req_data.get('reference', '')
        }
        
        # Initialiser la liste si elle n'existe pas
        if merchant_email not in withdrawal_requests_db:
            withdrawal_requests_db[merchant_email] = []
        
        withdrawal_requests_db[merchant_email].append(withdrawal_request)
        print(f"Demande de retrait test créée: {request_id} ({req_data['status']}) pour {merchant_email}")

# Créer les données de test
create_test_withdrawal_requests()

# Variable globale pour le context processor
@app.context_processor
def inject_user():
    """Make user info available to all templates - Version migrée database-first"""
    user = None
    if 'user_id' in session:
        email = session.get('user_email')
        
        # **DATABASE-FIRST: Récupérer l'utilisateur depuis la base de données d'abord**
        user_record = User.query.filter_by(email=email).first()
        
        if user_record:
            # Utiliser les données de la base de données
            user = {
                'id': user_record.id,
                'first_name': user_record.first_name or '',
                'last_name': user_record.last_name or '',
                'email': email,
                'phone': user_record.phone or '',
                'address': user_record.address or '',
                'city': user_record.city or '',
                'region': user_record.region or '',
                'addresses': []  # Pour l'instant, une seule adresse principale supportée
            }
            
            # Ajouter l'adresse principale comme adresse dans la liste si elle existe
            if user_record.address:
                user['addresses'] = [{
                    'id': 1,
                    'name': 'Adresse principale',
                    'full_name': f"{user_record.first_name or ''} {user_record.last_name or ''}".strip(),
                    'street': user_record.address,
                    'city': user_record.city or '',
                    'region': user_record.region or '',
                    'phone': user_record.phone or '',
                    'is_default': True
                }]
                
        elif email and email in users_db:
            # Fallback: utiliser l'ancien dictionnaire
            user_data = users_db[email]
            user = {
                'id': user_data.get('id', session.get('user_id')),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'email': email,
                'phone': user_data.get('phone', ''),
                'address': user_data.get('address', ''),
                'city': user_data.get('city', ''),
                'region': user_data.get('region', ''),
                'addresses': user_data.get('addresses', [])
            }
    
    return {'user': user}

# Injecter les informations du marchand dans tous les templates
@app.context_processor
def inject_merchant():
    """Make merchant info available to merchant templates - Version migrée database-first"""
    merchant = None
    if 'merchant_id' in session:
        email = session.get('merchant_email')
        
        # **DATABASE-FIRST: Récupérer le marchand depuis la base de données d'abord**
        merchant_record = Merchant.query.filter_by(email=email).first()
        
        if merchant_record:
            # Utiliser les données de la base de données
            merchant = merchant_record.to_dict()
            merchant['email'] = email
        elif email and email in merchants_db:
            # Fallback: utiliser l'ancien dictionnaire
            merchant = dict(merchants_db[email])
            merchant['email'] = email
    
    return {'merchant': merchant}

# Variable globale pour le context processor admin
@app.context_processor
def inject_admin():
    """Make admin info available to admin templates"""
    admin = None
    if 'admin_id' in session:
        email = session.get('admin_email')
        admin_role = session.get('admin_role')
        
        # Chercher d'abord dans la base de données
        try:
            db_admin = Admin.query.filter_by(email=email).first()
            if db_admin:
                admin = {
                    'id': db_admin.id,
                    'email': db_admin.email,
                    'first_name': db_admin.first_name,
                    'last_name': db_admin.last_name,
                    'role': db_admin.role,
                    'status': db_admin.status
                }
            else:
                # Fallback: chercher dans le dictionnaire en mémoire
                if email in admins_db:
                    admin = admins_db[email].copy()
                    admin['email'] = email
                
                # Toujours ajouter le rôle depuis la session
                if admin_role:
                    if admin is None:
                        admin = {'email': email}
                    admin['role'] = admin_role
        except Exception as e:
            print(f"❌ Erreur lors de la récupération de l'admin {email}: {e}")
            # Fallback: utiliser les données de session
            if admin_role:
                admin = {
                    'email': email,
                    'role': admin_role
                }
    
    return {'admin': admin}

# Ajouter un contexte processor pour la date/heure actuelle
@app.context_processor
def inject_now():
    """Injecte la date et l'heure actuelles dans tous les templates"""
    return {'now': datetime.now()}

# Ajouter un context processor pour le nombre d'articles dans le panier
@app.context_processor
def inject_cart_count():
    """Injecte le nombre d'articles dans le panier pour tous les templates - Version persistante DB"""
    try:
        # Utiliser get_cart() qui gère la persistance DB automatiquement
        cart_items = get_cart()
        cart_count = len(cart_items) if cart_items else 0
        return {'cart_count': cart_count}
    except Exception as e:
        # En cas d'erreur, utiliser la session comme fallback
        cart_count = len(session.get('cart', []))
        return {'cart_count': cart_count}

# Ajouter un context processor pour les catégories
@app.context_processor
def inject_categories():
    """Injecte les catégories actives dans tous les templates"""
    active_categories = get_active_categories()
    categories_with_subcategories = get_categories_with_subcategories()
    return {
        'active_categories': active_categories,
        'categories': active_categories,  # Pour la compatibilité avec les templates existants
        'categories_with_subcategories': categories_with_subcategories,
        'get_category_name': get_category_name
    }

# Ajouter un context processor pour les paramètres du site
@app.context_processor
def inject_site_settings():
    """Injecte les paramètres globaux du site dans tous les templates"""
    site_settings = get_site_settings()
    return {
        'site_settings': site_settings,
        'current_commission_rate': site_settings['commission_rate'],
        'current_shipping_fee': site_settings['default_shipping_fee'],
        'free_shipping_threshold': site_settings['free_shipping_threshold']
    }

# Ajouter un context processor pour les codes promo publics
@app.context_processor
def inject_public_promo_codes():
    """Injecte les codes promo publics actifs dans tous les templates"""
    try:
        # Obtenir les codes promo actifs qui sont publics
        public_promo_codes = get_public_promo_codes()
        return {
            'public_promo_codes': public_promo_codes,
            'has_active_promos': len(public_promo_codes) > 0
        }
    except Exception as e:
        print(f"Erreur lors de l'injection des codes promo: {str(e)}")
        return {
            'public_promo_codes': [],
            'has_active_promos': False
        }

# Route pour la page de connexion - Assurez-vous que cette route est correctement définie
@app.route('/login', methods=['GET', 'POST'])
def login():
    now = datetime.now()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Debug
        print(f"Tentative de connexion pour: {email}")
        
        # **DATABASE-FIRST: Récupérer l'utilisateur depuis la base de données d'abord**
        from db_helpers import get_user_by_email
        user_record = get_user_by_email(email)
        user = None
        
        if user_record:
            # Convertir l'enregistrement de la base de données en dictionnaire
            user = user_record.to_dict()
            print(f"✅ Utilisateur trouvé dans la base de données: {email}")
        else:
            # Fallback: chercher dans l'ancien dictionnaire
            user = users_db.get(email)
            if user:
                print(f"🔄 Utilisateur trouvé dans l'ancien dictionnaire: {email}")
        
        # Debug détaillé
        print(f"DEBUG - Utilisateur trouvé: {user is not None}")
        if user:
            print(f"DEBUG - Clés utilisateur: {list(user.keys())}")
            print(f"DEBUG - Has password_hash: {'password_hash' in user}")
            if 'password_hash' in user:
                print(f"DEBUG - Password hash: {user['password_hash'][:50]}...")
                password_check = check_password_hash(user['password_hash'], password)
                print(f"DEBUG - Password check result: {password_check}")
        else:
            print(f"DEBUG - Aucun utilisateur trouvé pour: {email}")
        
        # Vérifier si l'utilisateur existe et a un mot de passe valide
        if user and 'password_hash' in user and check_password_hash(user['password_hash'], password):
            # Vérifier si l'utilisateur est actif
            if not user.get('is_active', True):
                flash('Votre compte a été désactivé par un administrateur. Contactez le support si vous pensez qu\'il s\'agit d\'une erreur.', 'danger')
                return render_template('login.html', now=now)
            
            # Vérifier si l'email est vérifié
            if not user.get('email_verified', False):
                flash('Vous devez vérifier votre email avant de vous connecter. Vérifiez votre boîte mail.', 'warning')
                return redirect(url_for('email_verification_required'))
            
            # Sauvegarder le panier actuel avant de vider la session
            current_cart = session.get('cart', [])
            
            # Connexion réussie
            session.clear()
            
            # Configurer les données de session utilisateur
            session['user_id'] = user['id']
            session['user_email'] = email
            session['user_first_name'] = user.get('first_name', '')
            
            # Restaurer le panier après avoir effacé la session
            if current_cart:
                session['cart'] = current_cart
                
            # Migrer le panier de session vers la base de données pour persistance
            if current_cart:
                try:
                    migrate_success = migrate_session_cart_to_db()
                    if migrate_success:
                        print(f"✅ Panier migré vers DB pour {email}")
                    else:
                        # En cas d'échec, restaurer en session
                        session['cart'] = current_cart
                        print(f"⚠️ Échec migration panier, conservé en session pour {email}")
                except Exception as e:
                    # En cas d'erreur, restaurer en session
                    session['cart'] = current_cart
                    print(f"❌ Erreur migration panier pour {email}: {e}")
            
            # Gérer la fonctionnalité "Se souvenir de moi"
            if remember:
                # Session permanente (31 jours) - doit être défini AVANT les autres données de session
                session.permanent = True
                print(f"[LOGIN] Session permanente activée pour {email} - Durée: {app.config['PERMANENT_SESSION_LIFETIME']}")
            else:
                # Session temporaire (se termine à la fermeture du navigateur)
                session.permanent = False
                print(f"[LOGIN] Session temporaire pour {email}")
            
            # Debug
            print(f"Connexion réussie pour: {email}, Remember: {remember}, Session permanent: {session.permanent}")
            
            flash('Vous êtes maintenant connecté.', 'success')
            
            # Rediriger vers la page précédente si elle existe, sinon vers la page d'accueil
            next_page = session.get('next_page', url_for('home'))
            session.pop('next_page', None)
            return redirect(next_page)
        else:
            # Debug
            print(f"Échec de connexion pour: {email}")
            flash('Email ou mot de passe incorrect.', 'danger')
    
    return render_template('login.html', now=now)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Page de demande de récupération de mot de passe"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Veuillez entrer votre adresse email.', 'danger')
            return render_template('forgot_password.html')
        
        # **DATABASE-FIRST: Vérifier si l'utilisateur existe dans la base de données d'abord**
        from db_helpers import get_user_by_email
        user_record = get_user_by_email(email)
        user = None
        
        if user_record:
            user = user_record.to_dict()
            print(f"✅ Utilisateur trouvé dans la base de données pour récupération: {email}")
        else:
            # Fallback: chercher dans l'ancien dictionnaire
            user = users_db.get(email)
            if user:
                print(f"🔄 Utilisateur trouvé dans l'ancien dictionnaire pour récupération: {email}")
        
        if not user:
            # Pour la sécurité, on affiche le même message même si l'utilisateur n'existe pas
            flash('Si cette adresse email existe dans notre système, vous recevrez un lien de réinitialisation.', 'success')
            return render_template('forgot_password.html', success=True)
        
        try:
            # Créer un token de récupération
            token = create_password_reset_token(email)
            
            # Envoyer l'email de récupération
            success = send_password_reset_email(email, token)
            
            if success:
                flash('Un email de récupération a été envoyé à votre adresse. Vérifiez votre boîte de réception.', 'success')
                return render_template('forgot_password.html', success=True)
            else:
                flash('Une erreur est survenue lors de l\'envoi de l\'email. Veuillez réessayer.', 'danger')
                
        except Exception as e:
            print(f"Erreur lors de la création du token de récupération : {str(e)}")
            flash('Une erreur est survenue. Veuillez réessayer plus tard.', 'danger')
    
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Page de réinitialisation du mot de passe"""
    token = request.args.get('token') or request.form.get('token')
    
    if not token:
        flash('Token de récupération manquant.', 'danger')
        return redirect(url_for('forgot_password'))
    
    # Vérifier la validité du token
    email, error = verify_password_reset_token(token)
    if error:
        flash(f'Lien de récupération invalide : {error}', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation des mots de passe
        if not password or not confirm_password:
            flash('Veuillez remplir tous les champs.', 'danger')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 8:
            flash('Le mot de passe doit contenir au moins 8 caractères.', 'danger')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('reset_password.html', token=token)
        
        # Vérifications de sécurité du mot de passe
        if not re.search(r'[A-Z]', password):
            flash('Le mot de passe doit contenir au moins une majuscule.', 'danger')
            return render_template('reset_password.html', token=token)
        
        if not re.search(r'[a-z]', password):
            flash('Le mot de passe doit contenir au moins une minuscule.', 'danger')
            return render_template('reset_password.html', token=token)
        
        if not re.search(r'\d', password):
            flash('Le mot de passe doit contenir au moins un chiffre.', 'danger')
            return render_template('reset_password.html', token=token)
        
        try:
            print(f"🔄 Début de mise à jour du mot de passe pour: {email}")
            
            # **DATABASE-FIRST: Mettre à jour le mot de passe dans la base de données d'abord**
            from db_helpers import get_user_by_email, update_user_password
            
            user_record = get_user_by_email(email)
            if user_record:
                print(f"✅ Utilisateur trouvé en base: {email}")
                # Mise à jour dans la base de données
                success = update_user_password(email, generate_password_hash(password))
                if success:
                    print(f"✅ Mot de passe mis à jour dans la base de données pour: {email}")
                    
                    # COMPATIBILITÉ: Mise à jour dans le dictionnaire pour fallback
                    if email in users_db:
                        users_db[email]['password_hash'] = generate_password_hash(password)
                        print(f"🔄 Mot de passe mis à jour dans l'ancien dictionnaire pour: {email}")
                else:
                    print(f"❌ Échec de mise à jour dans la base de données pour: {email}")
                    raise Exception("Échec de mise à jour en base de données")
                    
            else:
                print(f"⚠️ Utilisateur non trouvé en base, recherche en mémoire: {email}")
                # Fallback: mise à jour dans l'ancien dictionnaire seulement
                user = users_db.get(email)
                if user:
                    user['password_hash'] = generate_password_hash(password)
                    print(f"🔄 Mot de passe mis à jour uniquement dans l'ancien dictionnaire pour: {email}")
                else:
                    print(f"❌ Utilisateur non trouvé ni en base ni en mémoire: {email}")
                    flash('Utilisateur non trouvé.', 'danger')
                    return render_template('reset_password.html', token=token)
            
            # Marquer le token comme utilisé
            print(f"🔄 Marquage du token comme utilisé: {token[:20]}...")
            mark_password_reset_token_used(token)
            
            flash('Votre mot de passe a été mis à jour avec succès. Vous pouvez maintenant vous connecter.', 'success')
            print(f"✅ Réinitialisation mot de passe réussie pour: {email}")
            return redirect(url_for('login'))
                
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du mot de passe pour {email}: {str(e)}")
            print(f"❌ Type d'erreur: {type(e).__name__}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            flash('Une erreur est survenue lors de la mise à jour du mot de passe.', 'danger')
    
    return render_template('reset_password.html', token=token)

@app.route('/logout')
def logout():
    """Route de déconnexion pour les utilisateurs clients"""
    user_id = session.get('user_id')
    
    # Le panier est maintenant persistant en DB, pas besoin de le sauvegarder en session
    # Il sera automatiquement récupéré lors de la prochaine connexion
    
    # Vider la session utilisateur
    session.clear()
    
    print(f"✅ Utilisateur {user_id} déconnecté - panier conservé en base de données")
    
    flash('Vous avez été déconnecté avec succès. Votre panier a été sauvegardé.', 'info')
    return redirect(url_for('home'))


# Routes pour la vérification email
@app.route('/email-verification-required')
def email_verification_required():
    """Page informant que la vérification email est requise"""
    return render_template('email_verification_required.html')

@app.route('/verify-email')
def verify_email():
    """Vérifier un token de vérification email - VERSION DEBUG AMÉLIORÉE"""
    token = request.args.get('token')
    
    print(f"🔍 DEBUG verify_email: Token reçu = {token[:8] if token else 'None'}...")
    
    if not token:
        print("❌ Token manquant dans la requête")
        flash('Token de vérification manquant.', 'danger')
        return redirect(url_for('email_verification_required'))
    
    print(f"🔍 Recherche du token dans la base de données...")
    
    # Vérifier le token
    email, error = verify_email_token(token)
    
    if error:
        print(f"❌ Erreur de vérification: {error}")
        flash(f'Erreur de vérification: {error}', 'danger')
        return redirect(url_for('email_verification_required'))
    
    print(f"✅ Token valide pour l'email: {email}")
    
    # **DATABASE-FIRST: Marquer l'email comme vérifié dans la base de données d'abord**
    from db_helpers import get_user_by_email, update_user_email_verification
    
    user_record = get_user_by_email(email)
    if user_record:
        print(f"✅ Utilisateur trouvé en base: {email}")
        
        # Mise à jour dans la base de données
        success = update_user_email_verification(email, True)
        if success:
            print(f"✅ Email vérifié dans la base de données pour: {email}")
        else:
            print(f"❌ Échec de vérification dans la base de données pour: {email}")
            
        # COMPATIBILITÉ: Mise à jour dans le dictionnaire pour fallback
        if email in users_db:
            users_db[email]['email_verified'] = True
            print(f"🔄 Email vérifié dans l'ancien dictionnaire pour: {email}")
        
        # Connecter automatiquement l'utilisateur après vérification
        user = user_record.to_dict()
        session['user_id'] = user['id']
        session['user_email'] = email
        session['user_first_name'] = user.get('first_name', '')
        
        print(f"🔐 Utilisateur connecté automatiquement: {email}")
        flash('Votre email a été vérifié avec succès! Vous êtes maintenant connecté.', 'success')
        return redirect(url_for('email_verification_success'))
    else:
        print(f"⚠️ Utilisateur non trouvé en base, vérification dictionnaire...")
        # Fallback: vérification dans l'ancien dictionnaire seulement
        if email in users_db:
            users_db[email]['email_verified'] = True
            
            user = users_db[email]
            session['user_id'] = user['id']
            session['user_email'] = email
            session['user_first_name'] = user.get('first_name', '')
            
            print(f"🔄 Email vérifié uniquement dans l'ancien dictionnaire pour: {email}")
            flash('Votre email a été vérifié avec succès! Vous êtes maintenant connecté.', 'success')
            return redirect(url_for('email_verification_success'))
        else:
            flash('Utilisateur non trouvé.', 'danger')
            return redirect(url_for('email_verification_required'))

@app.route('/email-verification-success')
def email_verification_success():
    """Page de succès après vérification email"""
    return render_template('email_verification_success.html')

@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Renvoyer l'email de vérification"""
    email = request.form.get('email')
    
    if not email:
        flash('Adresse email requise.', 'danger')
        return redirect(url_for('email_verification_required'))
    
    # **DATABASE-FIRST: Vérifier que l'utilisateur existe dans la base de données d'abord**
    from db_helpers import get_user_by_email
    user_record = get_user_by_email(email)
    user = None
    
    if user_record:
        user = user_record.to_dict()
        print(f"✅ Utilisateur trouvé dans la base de données pour renvoi vérification: {email}")
    else:
        # Fallback: chercher dans l'ancien dictionnaire
        user = users_db.get(email)
        if user:
            print(f"🔄 Utilisateur trouvé dans l'ancien dictionnaire pour renvoi vérification: {email}")
    
    if not user:
        flash('Aucun compte trouvé avec cette adresse email.', 'danger')
        return redirect(url_for('email_verification_required'))
    
    if user.get('email_verified', False):
        flash('Ce compte est déjà vérifié.', 'info')
        return redirect(url_for('login'))
    
    # Créer un nouveau token et renvoyer l'email
    token = create_verification_token(email)
    send_verification_email(email, token)
    
    flash('Un nouvel email de vérification a été envoyé.', 'success')
    return redirect(url_for('email_verification_required'))

# Routes pour la partie administration
@app.route('/admin/test-connection')
def admin_test_connection():
    """Route de test pour vérifier la connexion admin en production"""
    try:
        admin_count = Admin.query.count()
        admins = Admin.query.all()
        
        result = {
            'status': 'success',
            'admin_count': admin_count,
            'admins': []
        }
        
        for admin in admins:
            result['admins'].append({
                'id': admin.id,
                'email': admin.email,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'role': admin.role,
                'status': admin.status,
                'created_at': str(admin.created_at),
                'last_login': str(admin.last_login) if admin.last_login else None
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # Vérifier si l'admin est déjà connecté
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))  # Redirection directe si déjà connecté

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Récupérer l'administrateur et vérifier s'il existe
        admin = admins_db.get(email)
        employee = employees_db.get(email)
        
        # DATABASE-FIRST: Vérifier aussi dans la base de données Admin
        try:
            db_admin = Admin.query.filter_by(email=email, status='active').first()
        except Exception as e:
            print(f"Erreur requête Admin.query: {e}")
            db_admin = None
        
        # DATABASE-FIRST: Vérifier aussi dans la base de données Employee
        try:
            db_employee = Employee.query.filter_by(email=email, status='active').first()
        except Exception as e:
            print(f"Erreur requête Employee.query: {e}")
            db_employee = None
        
        user_found = False
        
        # Vérifier si c'est un administrateur (base de données d'abord)
        if db_admin and db_admin.check_password(password):
            # Connexion admin DB réussie
            session['admin_id'] = f"ADMIN_DB_{db_admin.id}"  # Préfixe ADMIN_DB_ pour différencier
            session['admin_email'] = email
            session['admin_name'] = f"{db_admin.first_name} {db_admin.last_name}"
            session['admin_role'] = db_admin.role
            session['user_type'] = 'admin'
            user_found = True
            
            # Mise à jour de la date de dernière connexion dans la base de données
            try:
                db_admin.last_login = datetime.utcnow()
                db.session.commit()
                print(f"✅ Connexion admin DB mise à jour pour {email}")
            except Exception as e:
                print(f"❌ Erreur mise à jour admin last_login: {e}")
                db.session.rollback()
            
            print(f"✅ Connexion administrateur DB réussie: {email} (ID: ADMIN_DB_{db_admin.id}, Rôle: {db_admin.role})")
            
        # Vérifier si c'est un administrateur (ancien système)
        elif admin and check_password_hash(admin['password_hash'], password):
            # Connexion admin réussie
            session['admin_id'] = f"ADMIN_{admin['id']}"  # Préfixe ADMIN_ pour différencier
            session['admin_email'] = email
            session['admin_name'] = f"{admin['first_name']} {admin['last_name']}"
            session['admin_role'] = admin['role']
            session['user_type'] = 'admin'
            user_found = True
            
            # Mise à jour de la date de dernière connexion
            admins_db[email]['last_login'] = datetime.now().strftime('%Y-%m-%d')
            
            print(f"✅ Connexion administrateur legacy réussie: {email} (ID: ADMIN_{admin['id']})")
            
        # Vérifier si c'est un employé (base de données d'abord)
        elif db_employee and db_employee.check_password(password):
            # Connexion employé DB réussie
            session['admin_id'] = f"EMP_{db_employee.id}"  # Préfixe EMP_ pour différencier
            session['admin_email'] = email
            session['admin_name'] = f"{db_employee.first_name} {db_employee.last_name}"
            session['admin_role'] = db_employee.role
            session['user_type'] = 'employee'
            user_found = True
            
            # Mise à jour de la date de dernière connexion dans la base de données
            try:
                db_employee.last_login = datetime.utcnow()
                db.session.commit()
                print(f"✅ Connexion employé DB mise à jour pour {email}")
            except Exception as e:
                print(f"❌ Erreur mise à jour last_login: {e}")
                db.session.rollback()
            
            # Ajouter aussi au dictionnaire en mémoire pour compatibilité session courante
            if email not in employees_db:
                employees_db[email] = db_employee.to_dict()
            else:
                employees_db[email]['last_login'] = datetime.now().strftime('%Y-%m-%d')
            
            print(f"✅ Connexion employé réussie: {email} (ID: EMP_{db_employee.id}, Rôle: {db_employee.role})")
                
        # Fallback: Vérifier si c'est un employé (ancien système)
        elif employee and check_password_hash(employee['password_hash'], password):
            # Connexion employé réussie
            session['admin_id'] = f"EMP_LEGACY_{employee['id']}"  # Préfixe EMP_LEGACY_ pour l'ancien système
            session['admin_email'] = email
            session['admin_name'] = f"{employee['first_name']} {employee['last_name']}"
            session['admin_role'] = employee['role']
            session['user_type'] = 'employee'
            user_found = True
            
            # Mise à jour de la date de dernière connexion
            employees_db[email]['last_login'] = datetime.now().strftime('%Y-%m-%d')
            
            print(f"✅ Connexion employé legacy réussie: {email} (ID: EMP_LEGACY_{employee['id']}, Rôle: {employee['role']})")
        
        if user_found:
            # Gérer la fonctionnalité "Se souvenir de moi" pour admin
            if remember:
                # Session permanente (31 jours)
                session.permanent = True
                print(f"[ADMIN LOGIN] Session permanente activée pour {email}")
            else:
                session.permanent = False
                print(f"[ADMIN LOGIN] Session temporaire pour {email}")
            
            print(f"Connexion admin/employé réussie pour: {email} - Type: {session['user_type']}, Remember: {remember}")
            flash('Vous êtes maintenant connecté.', 'success')
            
            # Redirection vers le tableau de bord approprié
            return redirect(url_for('admin_dashboard'))
        else:
            print(f"Échec connexion admin pour: {email} - Mot de passe incorrect ou admin inexistant")  # Log pour déboguer
            flash('Email ou mot de passe incorrect.', 'danger')
    
    # Empêcher la confusion avec d'autres sessions
    if 'user_id' in session or 'merchant_id' in session:
        # Sauvegarder temporairement les sessions pour les restaurer plus tard si nécessaire
        temp_session = dict(session)
        session.clear()
        session['prev_session'] = temp_session
    
    print("Affichage du formulaire de connexion admin")  # Log pour déboguer
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@permission_required(['super_admin', 'admin', 'manager', 'livreur'])
def admin_dashboard():
    """Tableau de bord admin - Version migrée database-first"""
    print(f"Accès au dashboard admin par: {session.get('admin_email')}")  # Log pour déboguer
    
    # Vérifier le rôle de l'utilisateur connecté
    user_role = get_user_role()
    
    # Si c'est un livreur, rediriger vers le dashboard livreur
    if user_role == 'livreur':
        return redirect(url_for('livreur_dashboard'))
    
    # **DATABASE-FIRST: Calculer toutes les statistiques depuis la base de données UNIQUEMENT**
    
    # Récupérer le taux de commission actuel depuis les paramètres
    site_settings = get_site_settings()
    commission_rate = site_settings['commission_rate'] / 100  # Convertir en décimal
    
    # 1. CALCUL DU REVENU ADMIN = COMMISSIONS DES MARCHANDS UNIQUEMENT
    total_commission_fees = 0
    admin_revenue = 0
    
    try:
        # Utiliser le nouveau système de calcul par catégorie
        total_commission_fees = calculate_admin_commission_revenue()
        admin_revenue = total_commission_fees
        
        # Compter les commandes pour le log
        merchant_orders_db = Order.query.filter(
            Order.merchant_id.isnot(None),
            Order.status.in_(['completed', 'delivered']),
            Order.payment_status == 'completed'
        ).all()
        
        print(f"✅ Commissions marchands: {total_commission_fees:.2f} KMF depuis {len(merchant_orders_db)} commandes DB")
        print(f"💰 REVENU ADMIN = COMMISSIONS: {admin_revenue:.2f} KMF")
        
    except Exception as e:
        print(f"❌ Erreur calcul revenus DB: {e}")
        total_commission_fees = 0
        admin_revenue = 0
    
    # Calcul du revenu total (dans ce cas = revenu admin puisque admin_revenue = commissions)
    total_revenue = admin_revenue
    print(f"💰 Revenu total: {total_revenue:.2f} KMF (100% commissions des marchands)")
    
    # 2. STATISTIQUES UTILISATEURS - Database-first
    try:
        total_users_db = User.query.count()
        print(f"✅ {total_users_db} utilisateurs récupérés depuis la DB")
    except Exception as e:
        total_users_db = 0
        print(f"❌ Erreur récupération utilisateurs DB: {e}")
    
    # Fallback utilisateurs
    total_users_dict = len(users_db)
    total_users = max(total_users_db, total_users_dict)  # Prendre le maximum pour éviter les pertes
    
    # 3. STATISTIQUES MARCHANDS - Database-first  
    try:
        total_merchants_db = Merchant.query.count()
        pending_merchants_db = Merchant.query.filter_by(store_verified=False).count()
        print(f"✅ {total_merchants_db} marchands ({pending_merchants_db} en attente) depuis la DB")
    except Exception as e:
        total_merchants_db = 0
        pending_merchants_db = 0
        print(f"❌ Erreur récupération marchands DB: {e}")
    
    # Fallback marchands
    total_merchants_dict = len(merchants_db)
    pending_merchants_dict = sum(1 for merchant in merchants_db.values() if not merchant.get('store_verified', False))
    
    total_merchants = max(total_merchants_db, total_merchants_dict)
    pending_merchants = max(pending_merchants_db, pending_merchants_dict)
    
    # 4. STATISTIQUES PRODUITS - Database-first
    try:
        total_products_db = Product.query.count()
        print(f"✅ {total_products_db} produits récupérés depuis la DB")
    except Exception as e:
        total_products_db = 0
        print(f"❌ Erreur récupération produits DB: {e}")
    
    # Fallback produits
    admin_products_count = len(globals().get('admin_created_products', []))
    total_products_dict = sum(len(merchant.get('products', [])) for merchant in merchants_db.values()) + admin_products_count
    total_products = max(total_products_db, total_products_dict)
    
    # 5. STATISTIQUES COMMANDES - Database-first
    try:
        from db_helpers import get_orders_count_safe
        total_orders_db = get_orders_count_safe()
        print(f"✅ {total_orders_db} commandes récupérées depuis la DB")
    except Exception as e:
        total_orders_db = 0
        print(f"❌ Erreur récupération commandes DB: {e}")
    
    # Fallback commandes
    merchant_orders_dict = sum(len(merchant.get('orders', [])) for merchant in merchants_db.values())
    total_orders = max(total_orders_db, merchant_orders_dict)
    
    # Statistiques consolidées
    stats = {
        'total_users': total_users,
        'total_merchants': total_merchants,
        'total_products': total_products,
        'pending_merchants': pending_merchants,
        'total_orders': total_orders,
        'total_commission_fees': int(total_commission_fees),  # Commissions marchands uniquement
        'commission_rate': commission_rate,
        'admin_revenue': int(admin_revenue),  # Revenus admin séparés
        'merchant_commissions': int(total_commission_fees),  # Commissions marchands
        'total_revenue': int(total_revenue)  # Revenu total (commissions + admin)
    }
    
    print(f"📊 Stats admin dashboard: {stats}")
    
    # 6. MARCHANDS RÉCENTS - Database-first
    recent_merchants = []
    
    try:
        # Récupérer les 5 marchands les plus récents depuis la DB
        recent_merchants_db = Merchant.query.order_by(Merchant.created_at.desc()).limit(5).all()
        
        for merchant_record in recent_merchants_db:
            recent_merchants.append({
                'id': merchant_record.id,
                'email': merchant_record.email,
                'name': merchant_record.store_name or 'Boutique sans nom',
                'date': merchant_record.created_at.strftime('%Y-%m-%d') if merchant_record.created_at else '',
                'verified': merchant_record.store_verified or False
            })
        
        print(f"✅ {len(recent_merchants)} marchands récents depuis la DB")
        
    except Exception as e:
        print(f"❌ Erreur récupération marchands récents DB: {e}")
    
    # Fallback marchands récents depuis dictionnaire
    if len(recent_merchants) < 5:
        dict_merchants = []
        for email, merchant in merchants_db.items():
            # Éviter les doublons avec la DB
            if not any(rm['email'] == email for rm in recent_merchants):
                dict_merchants.append({
                    'id': merchant['id'],
                    'email': email,
                    'name': merchant['store_name'],
                    'date': merchant['registration_date'],
                    'verified': merchant['store_verified']
                })
        
        # Trier et prendre ce qu'il faut pour compléter à 5
        dict_merchants.sort(key=lambda x: x['date'], reverse=True)
        needed = 5 - len(recent_merchants)
        recent_merchants.extend(dict_merchants[:needed])
        
        if dict_merchants:
            print(f"🔄 {min(needed, len(dict_merchants))} marchands récents ajoutés depuis dictionnaire")
    
    # 7. COMMANDES RÉCENTES - Database-ONLY (pas de fallback dictionnaire)
    all_orders = []
    
    try:
        # Récupérer UNIQUEMENT les 10 commandes les plus récentes depuis la DB
        from db_helpers import get_recent_orders_safe
        recent_orders_db = get_recent_orders_safe(10)
        
        for db_order in recent_orders_db:
            # Récupérer les infos du marchand
            merchant_name = "DOUKA KM (Admin)"
            if db_order.merchant_id:
                merchant_record = Merchant.query.get(db_order.merchant_id)
                merchant_name = merchant_record.store_name if merchant_record else "Marchand inconnu"
            
            # Formater la date de création
            created_at_str = ""
            if db_order.created_at:
                created_at_str = db_order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            
            order_dict = {
                'id': db_order.id,
                'order_number': db_order.order_number,
                'customer_name': db_order.customer_name or 'Client',
                'merchant_name': merchant_name,
                'total': float(db_order.total) if db_order.total else 0,
                'status': db_order.status or 'processing',
                'created_at': created_at_str,
                'date': created_at_str,  # Compatibilité template
                'source': 'database'
            }
            all_orders.append(order_dict)
        
        print(f"✅ {len(all_orders)} commandes récentes depuis la DB UNIQUEMENT")
        
    except Exception as e:
        print(f"❌ Erreur récupération commandes récentes DB: {e}")
        all_orders = []
    
    # Rendu final du template
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_merchants=recent_merchants,
                         recent_orders=all_orders,
                         admin_email=session.get('admin_email'))


@app.route('/admin/api/commission-stats')
@admin_required
def admin_commission_stats():
    """API endpoint pour récupérer les statistiques de commission et revenus admin en temps réel"""
    try:
        # Récupérer les paramètres actuels
        site_settings = get_site_settings()
        commission_rate = site_settings['commission_rate'] / 100
        
        # 1. Calculer les commissions marchands avec le nouveau système par catégorie
        total_commission_fees = calculate_admin_commission_revenue()
        
        # 2. Revenu admin = commissions des marchands (logique corrigée)
        admin_revenue = total_commission_fees
        
        # 3. Calcul du revenu total (dans ce cas = revenu admin puisque admin_revenue = commissions)
        total_revenue = admin_revenue
        
        return jsonify({
            'success': True,
            'total_commission_fees': int(total_commission_fees),
            'admin_revenue': int(admin_revenue),
            'total_revenue': int(total_revenue),
            'commission_rate': commission_rate,
            'formatted_total': f"{int(total_commission_fees):,}".replace(',', ' '),
            'formatted_admin_revenue': f"{int(admin_revenue):,}".replace(',', ' '),
            'formatted_total_revenue': f"{int(total_revenue):,}".replace(',', ' ')
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# À ajouter après les routes admin existantes (vers la ligne 3800)

@app.route('/admin/withdrawals')
@admin_required
def admin_withdrawals():
    """Page de gestion des demandes de retrait pour les administrateurs - Version migrée database-first"""
    # **DATABASE-FIRST: Récupérer toutes les demandes de retrait depuis la base de données d'abord**
    all_withdrawals = []
    
    try:
        # Récupérer toutes les demandes depuis la base de données
        db_withdrawals = WithdrawalRequest.query.order_by(WithdrawalRequest.requested_at.desc()).all()
        
        for withdrawal_request in db_withdrawals:
            withdrawal_dict = withdrawal_request.to_dict()
            
            # Récupérer les informations du marchand
            merchant_record = Merchant.query.get(withdrawal_request.merchant_id)
            if merchant_record:
                withdrawal_dict['merchant_name'] = merchant_record.store_name or 'Marchand inconnu'
                withdrawal_dict['merchant_email'] = merchant_record.email
            else:
                withdrawal_dict['merchant_name'] = 'Marchand supprimé'
                withdrawal_dict['merchant_email'] = 'N/A'
            
            all_withdrawals.append(withdrawal_dict)
        
        print(f"✅ {len(all_withdrawals)} demandes de retrait récupérées depuis la base de données")
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des demandes depuis la DB: {str(e)}")
    
    # Fallback: ajouter les demandes du dictionnaire non encore migrées
    fallback_count = 0
    for merchant_email, withdrawals in withdrawal_requests_db.items():
        merchant = merchants_db.get(merchant_email, {})
        for withdrawal in withdrawals:
            # Vérifier si cette demande n'est pas déjà dans all_withdrawals
            if not any(w.get('id') == withdrawal.get('id') for w in all_withdrawals):
                withdrawal_with_merchant = withdrawal.copy()
                withdrawal_with_merchant['merchant_name'] = merchant.get('store_name', 'Marchand inconnu')
                withdrawal_with_merchant['merchant_email'] = merchant_email
                all_withdrawals.append(withdrawal_with_merchant)
                fallback_count += 1
    
    if fallback_count > 0:
        print(f"🔄 {fallback_count} demandes ajoutées depuis le dictionnaire (fallback)")
    
    # Trier par date (plus récent en premier)
    all_withdrawals.sort(key=lambda x: x.get('requested_at', ''), reverse=True)
    
    # Filtrage par statut
    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        all_withdrawals = [w for w in all_withdrawals if w['status'] == status_filter]
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    
    withdrawals = all_withdrawals[start:end]
    total_withdrawals = len(all_withdrawals)
    
    pagination_info = {
        'current_page': page,
        'total_pages': (total_withdrawals + per_page - 1) // per_page,
        'total_items': total_withdrawals,
        'has_prev': page > 1,
        'has_next': end < total_withdrawals,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if end < total_withdrawals else None
    }
    
    # Statistiques
    stats = {
        'total': len(all_withdrawals),
        'pending': len([w for w in all_withdrawals if w['status'] == 'pending']),
        'approved': len([w for w in all_withdrawals if w['status'] == 'approved']),
        'processing': len([w for w in all_withdrawals if w['status'] == 'processing']),
        'completed': len([w for w in all_withdrawals if w['status'] == 'completed']),
        'rejected': len([w for w in all_withdrawals if w['status'] == 'rejected']),
        'total_amount': sum(w['amount'] for w in all_withdrawals if w['status'] == 'completed')
    }
    
    return render_template('admin/withdrawals.html',
                          withdrawals=withdrawals,
                          withdrawal_requests=withdrawals,
                          pagination=pagination_info,
                          status_filter=status_filter,
                          stats=stats)

@app.route('/admin/withdrawal/<request_id>/update', methods=['POST'])
@admin_required
def admin_update_withdrawal(request_id):
    """Mettre à jour le statut d'une demande de retrait - Version migrée vers base de données"""
    try:
        # DATABASE-FIRST: Chercher d'abord dans la base de données PostgreSQL
        from models import WithdrawalRequest, Merchant
        
        withdrawal_db = WithdrawalRequest.query.filter_by(request_id=request_id).first()
        withdrawal_request = None
        merchant_email = None
        use_database = False
        
        if withdrawal_db:
            # Utiliser la base de données
            use_database = True
            merchant_db = Merchant.query.get(withdrawal_db.merchant_id)
            merchant_email = merchant_db.email if merchant_db else 'unknown'
            
            # Ancien statut pour notifications
            old_status = withdrawal_db.status
            
            print(f"✅ Demande de retrait {request_id} trouvée en base de données")
        else:
            # Fallback: chercher dans le dictionnaire en mémoire
            for email, withdrawals in withdrawal_requests_db.items():
                for withdrawal in withdrawals:
                    if withdrawal['id'] == request_id:
                        withdrawal_request = withdrawal
                        merchant_email = email
                        break
                if withdrawal_request:
                    break
            
            if withdrawal_request:
                old_status = withdrawal_request['status']
                print(f"⚠️ Demande de retrait {request_id} trouvée en dictionnaire mémoire")
        
        if not withdrawal_db and not withdrawal_request:
            return jsonify({'success': False, 'message': 'Demande de retrait introuvable'})
        
        # Récupérer les nouveaux paramètres (JSON ou form data)
        if request.is_json:
            data = request.get_json()
            new_status = data.get('status')
            admin_notes = data.get('admin_notes', '')
            reference = data.get('reference', '')
        else:
            new_status = request.form.get('status')
            admin_notes = request.form.get('admin_notes', '')
            reference = request.form.get('reference', '')
        
        # Validation du statut
        valid_statuses = ['pending', 'approved', 'processing', 'completed', 'rejected']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Statut invalide'})
        
        # METTRE À JOUR EN BASE DE DONNÉES D'ABORD
        if use_database:
            try:
                withdrawal_db.status = new_status
                withdrawal_db.admin_notes = admin_notes
                withdrawal_db.reference = reference
                
                # Si le statut passe à complété ou rejeté, ajouter la date de traitement
                if new_status in ['completed', 'rejected'] and not withdrawal_db.processed_at:
                    withdrawal_db.processed_at = datetime.now()
                
                db.session.commit()
                print(f"✅ Demande de retrait {request_id} mise à jour en base de données")
                
                # Créer un objet compatible pour les notifications
                withdrawal_request = {
                    'id': withdrawal_db.request_id,
                    'amount': withdrawal_db.amount,
                    'method': withdrawal_db.method,
                    'status': new_status,
                    'notes': withdrawal_db.notes or '',
                    'admin_notes': admin_notes,
                    'reference': reference,
                    'requested_at': withdrawal_db.requested_at.strftime('%Y-%m-%d %H:%M:%S') if withdrawal_db.requested_at else None,
                    'processed_at': withdrawal_db.processed_at.strftime('%Y-%m-%d %H:%M:%S') if withdrawal_db.processed_at else None
                }
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erreur mise à jour BDD: {str(e)}")
                return jsonify({'success': False, 'message': f'Erreur de base de données: {str(e)}'})
        
        # METTRE À JOUR AUSSI LE DICTIONNAIRE EN MÉMOIRE pour compatibilité (si existe)
        elif withdrawal_request:
            # Mettre à jour la demande dans le dictionnaire
            withdrawal_request['status'] = new_status
            withdrawal_request['admin_notes'] = admin_notes
            withdrawal_request['reference'] = reference
            
            if new_status in ['completed', 'rejected']:
                withdrawal_request['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Envoyer une notification email au marchand si le statut a changé
        if old_status != new_status and merchant_email and withdrawal_request:
            try:
                print(f"🔄 Envoi notification: {merchant_email}, statut {old_status} → {new_status}")
                
                send_merchant_withdrawal_status_notification(
                    merchant_email, 
                    withdrawal_request, 
                    old_status, 
                    new_status
                )
                print(f"✅ Notification envoyée au marchand {merchant_email} pour le changement de statut de retrait")
                
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi de la notification de retrait: {str(e)}")
                # Ne pas faire échouer la mise à jour si l'email échoue
        
        return jsonify({
            'success': True,
            'message': f'Statut mis à jour vers "{new_status}" avec succès'
        })
        
    except Exception as e:
        print(f"❌ ERREUR DÉTAILLÉE lors de la mise à jour du retrait: {str(e)}")
        import traceback
        print(f"❌ TRACEBACK: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/admin/withdrawal/<request_id>/details')
@admin_required
def admin_withdrawal_details(request_id):
    """Récupérer les détails d'une demande de retrait - Version migrée vers base de données"""
    try:
        # DATABASE-FIRST: Chercher d'abord dans la base de données PostgreSQL
        from models import WithdrawalRequest, Merchant
        
        withdrawal_db = WithdrawalRequest.query.filter_by(request_id=request_id).first()
        withdrawal_request = None
        merchant_email = None
        merchant = None
        
        if withdrawal_db:
            # Utiliser les données de la base de données
            merchant_db = Merchant.query.get(withdrawal_db.merchant_id)
            
            if merchant_db:
                merchant_email = merchant_db.email
                merchant = {
                    'first_name': merchant_db.first_name or '',
                    'last_name': merchant_db.last_name or '',
                    'store_name': merchant_db.store_name or '',
                    'phone': merchant_db.phone or '',
                    'email': merchant_db.email
                }
                
                # Convertir en format attendu
                withdrawal_request = {
                    'id': withdrawal_db.request_id,
                    'amount': float(withdrawal_db.amount),
                    'method': withdrawal_db.method or 'bank_transfer',
                    'status': withdrawal_db.status,
                    'requested_at': withdrawal_db.requested_at.strftime('%Y-%m-%d %H:%M:%S') if withdrawal_db.requested_at else 'Non défini',
                    'processed_at': withdrawal_db.processed_at.strftime('%Y-%m-%d %H:%M:%S') if withdrawal_db.processed_at else None,
                    'notes': withdrawal_db.notes or '',
                    'admin_notes': withdrawal_db.admin_notes or '',
                    'reference': withdrawal_db.reference or ''
                }
                
                print(f"✅ Demande de retrait {request_id} récupérée depuis la base de données")
        
        # Fallback: chercher dans le dictionnaire en mémoire
        if not withdrawal_request:
            for email, withdrawals in withdrawal_requests_db.items():
                for withdrawal in withdrawals:
                    if withdrawal['id'] == request_id:
                        withdrawal_request = withdrawal
                        merchant_email = email
                        break
                if withdrawal_request:
                    break
            
            if withdrawal_request:
                # Récupérer les informations du marchand
                merchant = merchants_db.get(merchant_email, {})
                print(f"⚠️ Demande de retrait {request_id} récupérée depuis le dictionnaire en mémoire")
        
        if not withdrawal_request:
            return jsonify({'success': False, 'message': 'Demande de retrait introuvable'})
        
        # Déterminer la méthode de paiement (utiliser 'method' au lieu de 'payment_method')
        payment_method = withdrawal_request.get('method', 'bank_transfer')
        
        # Formatage des statuts
        status_labels = {
            'pending': 'En cours de préparation',
            'approved': 'Approuvée',
            'processing': 'En traitement', 
            'completed': 'Complété',
            'rejected': 'Rejeté',
            'cancelled': 'Annulé'
        }
        
        status_colors = {
            'pending': 'warning',
            'approved': 'success',
            'processing': 'info',
            'completed': 'primary', 
            'rejected': 'danger',
            'cancelled': 'secondary'
        }
        
        status_text = status_labels.get(withdrawal_request['status'], 'Inconnu')
        status_color = status_colors.get(withdrawal_request['status'], 'secondary')
        
        # Construire le HTML des détails
        html = f'''
        <div class="row">
            <div class="col-md-6">
                <h6 class="fw-bold">Informations de la demande</h6>
                <table class="table table-sm">
                    <tr>
                        <td><strong>ID:</strong></td>
                        <td>#{withdrawal_request['id']}</td>
                    </tr>
                    <tr>
                        <td><strong>Montant:</strong></td>
                        <td><span class="text-success fw-bold">{withdrawal_request['amount']:,.0f} KMF</span></td>
                    </tr>
                    <tr>
                        <td><strong>Date de demande:</strong></td>
                        <td>{withdrawal_request['requested_at']}</td>
                    </tr>
                    <tr>
                        <td><strong>Statut:</strong></td>
                        <td>
                            <span class="badge bg-{status_color}">
                                {status_text}
                            </span>
                        </td>
                    </tr>
        '''
        
        # Ajouter la date de traitement si disponible
        if withdrawal_request.get('processed_at'):
            html += f'''
                    <tr>
                        <td><strong>Date de traitement:</strong></td>
                        <td>{withdrawal_request['processed_at']}</td>
                    </tr>
            '''
        
        # Ajouter la référence si disponible
        if withdrawal_request.get('reference'):
            html += f'''
                    <tr>
                        <td><strong>Référence:</strong></td>
                        <td>{withdrawal_request['reference']}</td>
                    </tr>
            '''
        
        html += '''
                </table>
            </div>
            <div class="col-md-6">
                <h6 class="fw-bold">Informations du marchand</h6>
                <table class="table table-sm">
                    <tr>
                        <td><strong>Nom:</strong></td>
                        <td>{} {}</td>
                    </tr>
                    <tr>
                        <td><strong>Email:</strong></td>
                        <td>{}</td>
                    </tr>
                    <tr>
                        <td><strong>Boutique:</strong></td>
                        <td>{}</td>
                    </tr>
                    <tr>
                        <td><strong>Téléphone:</strong></td>
                        <td>{}</td>
                    </tr>
                </table>
            </div>
        </div>
        '''.format(
            merchant.get('first_name', ''),
            merchant.get('last_name', ''),
            merchant_email,
            merchant.get('store_name', 'Non défini'),
            merchant.get('phone', 'Non défini')
        )
        
        # Section détails de paiement
        html += f'''
        <div class="row mt-3">
            <div class="col-12">
                <h6 class="fw-bold">Détails de paiement</h6>
                <div class="card bg-light">
                    <div class="card-body">
                        <p><strong>Méthode:</strong> '''
        
        # Formatage de la méthode de paiement
        if payment_method == 'bank_transfer':
            html += 'Virement bancaire</p>'
            # Récupérer les informations bancaires du marchand
            bank_info = None
            
            # Si les données viennent de la base de données (withdrawal_db existe)
            if withdrawal_db:
                merchant_from_db = Merchant.query.get(withdrawal_db.merchant_id)
                if merchant_from_db:
                    bank_info = merchant_from_db.get_bank_info()
            else:
                # Fallback: chercher le marchand par email depuis le dictionnaire
                merchant_dict = merchants_db.get(merchant_email, {})
                bank_info = merchant_dict.get('bank_info', {})
            
            if bank_info:
                html += f'''
                        <p><strong>Banque:</strong> {bank_info.get('bank_name', 'Non spécifié')}</p>
                        <p><strong>Titulaire:</strong> {bank_info.get('account_holder', 'Non spécifié')}</p>
                        <p><strong>Numéro de compte:</strong> {bank_info.get('account_number', 'Non spécifié')}</p>
                '''
            else:
                html += '<p class="text-warning">Aucune information bancaire enregistrée</p>'
        elif payment_method == 'mobile_money':
            html += 'Mobile Money</p>'
            html += '<p><em>Détails de Mobile Money à ajouter</em></p>'
        elif payment_method == 'cash_pickup':
            html += 'Retrait en espèces</p>'
            html += '<p><em>Retrait en agence</em></p>'
        else:
            html += f'{payment_method.replace("_", " ").title()}</p>'
        
        html += '''
                    </div>
                </div>
            </div>
        </div>
        '''
        
        # Ajouter les notes du marchand si présentes
        if withdrawal_request.get('notes'):
            html += f'''
            <div class="row mt-3">
                <div class="col-12">
                    <h6 class="fw-bold">Notes du marchand</h6>
                    <div class="alert alert-secondary">
                        {withdrawal_request['notes']}
                    </div>
                </div>
            </div>
            '''
        
        # Ajouter les notes admin si présentes
        if withdrawal_request.get('admin_notes'):
            html += f'''
            <div class="row mt-3">
                <div class="col-12">
                    <h6 class="fw-bold">Notes administrateur</h6>
                    <div class="alert alert-info">
                        {withdrawal_request['admin_notes']}
                    </div>
                </div>
            </div>
            '''
        
        return jsonify({'success': True, 'html': html})
        
    except Exception as e:
        print(f"Erreur lors de la récupération des détails: {e}")
        print(traceback.format_exc())  # Pour plus de détails sur l'erreur
        return jsonify({'success': False, 'message': 'Une erreur est survenue'})
    
# Ajouter les routes manquantes pour la gestion des marchands
@app.route('/admin/merchants')
@admin_required
def admin_merchants():
    """Page d'administration pour la liste des marchands"""
    
    # DATABASE-FIRST: Récupérer tous les marchands depuis la base de données d'abord
    all_merchants = []
    merchant_records = Merchant.query.all()
    
    for merchant_record in merchant_records:
        merchant_dict = merchant_record.to_dict()
        merchant_email = merchant_record.email
        
        # Récupérer le nombre de commandes depuis la DB
        from db_helpers import get_merchant_orders
        db_orders = get_merchant_orders(merchant_record.id)
        orders_count = len(db_orders)
        
        # Calculer le solde dynamique pour chaque marchand
        balance_info = calculate_merchant_balance(merchant_email)
        
        # Récupérer le nombre de produits depuis la DB
        products_count = Product.query.filter_by(merchant_id=merchant_record.id).count()
        
        all_merchants.append({
            'id': merchant_record.id,  # Utiliser l'ID de la base de données
            'email': merchant_email,
            'store_name': merchant_dict.get('store_name', 'Boutique sans nom'),
            'first_name': merchant_dict.get('first_name', ''),
            'last_name': merchant_dict.get('last_name', ''),
            'phone': merchant_dict.get('phone', ''),
            'city': merchant_dict.get('store_city', ''),
            'region': merchant_dict.get('store_region', ''),
            'registration_date': merchant_dict.get('created_at', ''),
            'verified': merchant_dict.get('store_verified', False),
            'products_count': products_count,
            'orders_count': orders_count,
            'balance': balance_info['available_balance'],
            'total_earnings': balance_info['total_earnings'],
            'delivered_orders_count': balance_info['delivered_orders_count']
        })
        
        print(f"📊 Marchand chargé: ID {merchant_record.id} - {merchant_dict.get('store_name')} ({merchant_email})")
    
    # Fallback: Ajouter les marchands du dictionnaire qui ne sont pas encore en base de données
    for email, merchant in merchants_db.items():
        # Vérifier si ce marchand existe déjà dans la liste (par email)
        if not any(m['email'] == email for m in all_merchants):
            print(f"⚠️ Marchand uniquement en mémoire: {email} - ID dictionnaire: {merchant['id']}")
            
            # Calculer le solde dynamique
            balance_info = calculate_merchant_balance(email)
            
            all_merchants.append({
                'id': merchant['id'],  # ID du dictionnaire pour compatibilité
                'email': email,
                'store_name': merchant.get('store_name', 'Boutique sans nom'),
                'first_name': merchant.get('first_name', ''),
                'last_name': merchant.get('last_name', ''),
                'phone': merchant.get('phone', ''),
                'city': merchant.get('store_city', ''),
                'region': merchant.get('store_region', ''),
                'registration_date': merchant.get('registration_date', ''),
                'verified': merchant.get('store_verified', False),
                'products_count': len(merchant.get('products', [])),
                'orders_count': len(merchant.get('orders', [])),
                'balance': balance_info['available_balance'],
                'total_earnings': balance_info['total_earnings'],
                'delivered_orders_count': balance_info['delivered_orders_count']
            })
    
    # Trier les marchands par date d'inscription (plus récent en premier)
    all_merchants.sort(key=lambda x: x['registration_date'], reverse=True)
    
    # Compter les marchands en attente de vérification
    pending_count = sum(1 for m in all_merchants if not m['verified'])
    
    return render_template('admin/merchants.html', 
                          merchants=all_merchants,
                          pending_count=pending_count)

@app.route('/admin/merchants/<int:merchant_id>')
@admin_required
def admin_merchant_detail(merchant_id):
    """Page d'administration pour les détails d'un marchand spécifique"""
    
    # DATABASE-FIRST: Chercher le marchand directement dans la base de données
    merchant_record = Merchant.query.get(merchant_id)
    
    if not merchant_record:
        flash('Marchand non trouvé', 'danger')
        return redirect(url_for('admin_merchants'))
    
    # DATABASE-FIRST: Utiliser directement les données de la base de données
    merchant_email = merchant_record.email
    
    print(f"🔍 Admin - Détails du marchand ID {merchant_id}: {merchant_record.store_name} ({merchant_email})")
    
    # Calculer les données de notation du marchand (déjà migrées vers DB)
    avg_rating, total_reviews = calculate_merchant_average_rating(merchant_email)
    rating_distribution, _ = get_merchant_rating_distribution(merchant_email)

    # Calculer le solde dynamique du marchand (déjà migré vers DB)
    balance_info = calculate_merchant_balance(merchant_email)

    # DATABASE-FIRST: Charger les catégories depuis la base de données
    categories_records = Category.query.all()
    categories_mapping = {cat.id: cat.name for cat in categories_records}

    # DATABASE-FIRST: Charger les produits directement depuis la base de données
    products_from_db = Product.query.filter_by(merchant_id=merchant_id).all()
    products_sorted = []
    
    for product_record in products_from_db:
        product_dict = product_record.to_dict()
        product_dict['merchant_email'] = merchant_email  # Ajouter pour compatibilité
        
        # Enrichir avec le nom de catégorie
        category_id = product_dict.get('category_id')
        product_dict['category_name'] = categories_mapping.get(category_id, 'Non classé')
        
        products_sorted.append(product_dict)
    
    # Trier par date de création (plus récents en premier)
    products_sorted = sorted(products_sorted, key=lambda x: x.get('created_at', ''), reverse=True)
        
    print(f"📦 Produits chargés pour {merchant_record.store_name}: {len(products_sorted)} produits depuis la base de données")

    # DATABASE-FIRST: Récupérer les commandes directement avec l'instance merchant_record
    from db_helpers import get_merchant_orders
    
    # Récupérer les commandes depuis la DB
    db_orders = get_merchant_orders(merchant_record.id)
    
    # Convertir en format attendu par le template
    orders_list = []
    for db_order in db_orders:
        order_dict = {
            'id': db_order.id,
            'order_number': db_order.order_number,
            'customer_name': db_order.customer_name,
            'customer_email': db_order.customer_email,
            'total': db_order.total,
            'status': db_order.status,
            'status_text': db_order.status_text,
            'status_color': db_order.status_color,
            'payment_method': db_order.payment_method,
            'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        orders_list.append(order_dict)
    
    print(f"📋 Commandes chargées pour {merchant_record.store_name}: {len(orders_list)} commandes")

    # Préparer les données pour l'affichage en utilisant directement merchant_record
    merchant_data = {
        'id': merchant_record.id,
        'email': merchant_email,
        'first_name': merchant_record.first_name or '',
        'last_name': merchant_record.last_name or '',
        'phone': merchant_record.phone or '',
        'store_name': merchant_record.store_name or 'Boutique sans nom',
        'store_description': merchant_record.store_description or '',
        'store_address': merchant_record.store_address or '',
        'store_city': merchant_record.store_city or '',
        'store_region': merchant_record.store_region or '',
        'store_logo': merchant_record.store_logo or 'static/img/merchants/store_logo_default.png',
        'store_banner': merchant_record.store_banner or 'static/img/merchants/store_banner_default.jpg',
        'store_verified': merchant_record.store_verified,
        'registration_date': merchant_record.created_at.strftime('%Y-%m-%d') if merchant_record.created_at else '',
        'products': products_sorted,
        'orders': orders_list,
        'balance': balance_info['available_balance'],
        'total_earnings': balance_info['total_earnings'],
        'commission_fees': balance_info['commission_fees'],
        'delivered_orders_count': balance_info['delivered_orders_count'],
        'commission_rate': balance_info['commission_rate'],
        'bank_info': json.loads(merchant_record.bank_info) if merchant_record.bank_info else {},
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'rating_distribution': rating_distribution,
        'account_suspended': merchant_record.status == 'suspended',
        'status': merchant_record.status  # Ajouter le status direct pour le template
    }
    
    return render_template('admin/merchant_detail.html', merchant=merchant_data)

@app.route('/admin/merchants/<int:merchant_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_merchant(merchant_id):
    """Modifier les informations d'un marchand"""
    
    # DATABASE-FIRST: Chercher le marchand directement dans la base de données
    merchant_record = Merchant.query.get(merchant_id)
    
    if not merchant_record:
        flash('Marchand non trouvé', 'danger')
        return redirect(url_for('admin_merchants'))
    
    merchant_email = merchant_record.email
    target_merchant = merchant_record.to_dict()
    
    print(f"🔧 Admin - Édition du marchand ID {merchant_id}: {merchant_record.store_name} ({merchant_email})")
    
    if request.method == 'POST':
        try:
            # Mettre à jour les informations du marchand dans la base de données
            merchant_record.first_name = request.form.get('first_name', '').strip()
            merchant_record.last_name = request.form.get('last_name', '').strip()
            merchant_record.phone = request.form.get('phone', '').strip()
            merchant_record.store_name = request.form.get('store_name', '').strip()
            merchant_record.store_description = request.form.get('store_description', '').strip()
            merchant_record.store_address = request.form.get('store_address', '').strip()
            merchant_record.store_city = request.form.get('store_city', '').strip()
            merchant_record.store_region = request.form.get('store_region', '').strip()
            
            # Gérer la vérification du magasin
            store_verified = request.form.get('store_verified') == 'on'
            merchant_record.store_verified = store_verified
            
            # Informations bancaires
            bank_name = request.form.get('bank_name', '').strip()
            account_number = request.form.get('account_number', '').strip()
            account_holder = request.form.get('account_holder', '').strip()
            
            if bank_name or account_number or account_holder:
                bank_info = {
                    'bank_name': bank_name,
                    'account_number': account_number,
                    'account_holder': account_holder,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                merchant_record.bank_info = json.dumps(bank_info)
            
            merchant_record.updated_at = datetime.now()
            db.session.commit()
            
            # Mettre à jour aussi le dictionnaire mémoire pour compatibilité
            if merchant_email in merchants_db:
                merchants_db[merchant_email].update(merchant_record.to_dict())
            
            flash('Informations du marchand mises à jour avec succès', 'success')
            return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la mise à jour du marchand: {str(e)}")
            flash(f'Erreur lors de la mise à jour : {str(e)}', 'danger')
    
    # Préparer les données pour l'affichage
    merchant_data = {
        'id': merchant_record.id,
        'email': merchant_email,
        'first_name': target_merchant.get('first_name', ''),
        'last_name': target_merchant.get('last_name', ''),
        'phone': target_merchant.get('phone', ''),
        'store_name': target_merchant.get('store_name', ''),
        'store_description': target_merchant.get('store_description', ''),
        'store_address': target_merchant.get('store_address', ''),
        'store_city': target_merchant.get('store_city', ''),
        'store_region': target_merchant.get('store_region', ''),
        'store_verified': target_merchant.get('store_verified', False),
        'bank_info': target_merchant.get('bank_info', {})
    }
    
    return render_template('admin/merchant_edit.html', merchant=merchant_data)

@app.route('/admin/merchants/<int:merchant_id>/message', methods=['GET', 'POST'])
@admin_required
def admin_message_merchant(merchant_id):
    """Envoyer un message à un marchand"""
    
    # DATABASE-FIRST: Chercher le marchand directement dans la base de données
    merchant_record = Merchant.query.get(merchant_id)
    
    if not merchant_record:
        flash('Marchand non trouvé', 'danger')
        return redirect(url_for('admin_merchants'))
    
    merchant_email = merchant_record.email
    target_merchant = merchant_record.to_dict()
    
    print(f"✉️ Admin - Envoi message au marchand ID {merchant_id}: {merchant_record.store_name} ({merchant_email})")
    
    if request.method == 'POST':
        try:
            subject = request.form.get('subject', '').strip()
            message = request.form.get('message', '').strip()
            message_type = request.form.get('message_type', 'info')
            
            if not subject or not message:
                flash('Le sujet et le message sont obligatoires', 'warning')
                return render_template('admin/merchant_message.html', 
                                     merchant=target_merchant, 
                                     merchant_email=merchant_email)
            
            # Préparer l'email
            admin_email = session.get('admin_email', 'admin@doukakm.com')
            admin_info = employees_db.get(admin_email, {})
            admin_name = f"{admin_info.get('first_name', 'Admin')} {admin_info.get('last_name', 'DOUKA KM')}"
            
            # Envoyer l'email
            email_subject = f"[DOUKA KM Admin] {subject}"
            
            # Contenu HTML personnalisé selon le type de message
            type_colors = {
                'info': '#007bff',
                'warning': '#ffc107',
                'success': '#28a745',
                'error': '#dc3545'
            }
            
            type_labels = {
                'info': 'Information',
                'warning': 'Avertissement',
                'success': 'Félicitations',
                'error': 'Problème'
            }
            
            message_color = type_colors.get(message_type, '#007bff')
            message_label = type_labels.get(message_type, 'Message')
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: {message_color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                    .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>DOUKA KM - Administration</h2>
                        <p><strong>{message_label}:</strong> {subject}</p>
                    </div>
                    <div class="content">
                        <p>Bonjour {target_merchant.get('first_name', 'Marchand')},</p>
                        <div style="white-space: pre-line; margin: 20px 0;">{message}</div>
                        <p>Cordialement,<br>{admin_name}<br>Équipe DOUKA KM</p>
                    </div>
                    <div class="footer">
                        <p>Cet email a été envoyé depuis l'administration DOUKA KM.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
DOUKA KM - Administration
{message_label}: {subject}

Bonjour {target_merchant.get('first_name', 'Marchand')},

{message}

Cordialement,
{admin_name}
Équipe DOUKA KM
            """
            
            # Envoyer l'email
            success = send_email(merchant_email, email_subject, html_content, text_content)
            
            if success:
                flash(f'Message envoyé avec succès à {merchant_record.store_name}', 'success')
                print(f"✅ Message envoyé à {merchant_email}")
            else:
                flash('Erreur lors de l\'envoi de l\'email', 'danger')
                print(f"❌ Échec envoi email à {merchant_email}")
            
            return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
                
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi du message: {str(e)}")
            flash(f'Erreur lors de l\'envoi du message : {str(e)}', 'danger')
            
    return render_template('admin/merchant_message.html', 
                         merchant=merchant_record.to_dict(), 
                         merchant_email=merchant_email)


@app.route('/admin/merchants/<int:merchant_id>/suspend', methods=['POST'])
@admin_required
def admin_suspend_merchant(merchant_id):
    """Suspendre ou réactiver un compte marchand"""
    
    # DATABASE-FIRST: Chercher le marchand directement dans la base de données
    merchant_record = Merchant.query.get(merchant_id)
    
    if not merchant_record:
        flash('Marchand non trouvé', 'danger')
        return redirect(url_for('admin_merchants'))
    
    merchant_email = merchant_record.email
    
    print(f"🚫 Admin - Suspension/réactivation marchand ID {merchant_id}: {merchant_record.store_name} ({merchant_email})")
    
    try:
        action = request.form.get('action', 'suspend')
        reason = request.form.get('reason', '').strip()
        
        if action == 'suspend':
            # Suspendre le compte dans la base de données
            merchant_record.status = 'suspended'
            merchant_record.updated_at = datetime.now()
            
            # Mise à jour des informations de suspension dans les notifications JSON
            if not merchant_record.notifications:
                merchant_record.notifications = '{}'
            
            notifications_data = json.loads(merchant_record.notifications)
            notifications_data['account_suspended'] = True
            notifications_data['suspension_reason'] = reason
            notifications_data['suspension_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            notifications_data['suspended_by'] = session.get('admin_email', 'admin')
            
            merchant_record.notifications = json.dumps(notifications_data)
            
            # Sauvegarder les changements dans la base de données
            db.session.commit()
            
            # COMPATIBILITÉ: Mise à jour du dictionnaire pour fallback
            if merchant_email in merchants_db:
                merchants_db[merchant_email].update(merchant_record.to_dict())
            
            print(f"✅ Marchand ID {merchant_id} suspendu dans la base de données")
            
            # Envoyer un email de notification de suspension
            subject = "Suspension de votre compte marchand - DOUKA KM"
            html_content = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        padding: 0;
                        background-color: #f4f4f4;
                    }}
                    .email-container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        border-radius: 10px;
                        overflow: hidden;
                        box-shadow: 0 0 20px rgba(0,0,0,0.1);
                    }}
                    .email-header {{
                        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }}
                    .email-body {{
                        padding: 40px 30px;
                    }}
                    .warning-box {{
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                    .email-footer {{
                        background-color: #f8f9fa;
                        padding: 20px 30px;
                        text-align: center;
                        font-size: 14px;
                        color: #6c757d;
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="email-header">
                        <h1>⚠️ DOUKA KM - Suspension de compte</h1>
                    </div>
                    <div class="email-body">
                        <h2>Suspension de votre compte marchand</h2>
                        
                        <p>Bonjour {merchant_record.first_name} {merchant_record.last_name},</p>
                        
                        <p>Nous vous informons que votre compte marchand sur DOUKA KM a été temporairement suspendu.</p>
                        
                        <div class="warning-box">
                            <h4>⚠️ Raison de la suspension :</h4>
                            <p>{reason if reason else 'Suspension administrative'}</p>
                        </div>
                        
                        <p><strong>Conséquences de cette suspension :</strong></p>
                        <ul>
                            <li>Vos produits ne sont plus visibles sur la plateforme</li>
                            <li>Vous ne pouvez plus recevoir de nouvelles commandes</li>
                            <li>L'accès à votre espace marchand est restreint</li>
                        </ul>
                        
                        <p><strong>Que faire maintenant ?</strong></p>
                        <p>Si vous pensez que cette suspension est une erreur ou si vous souhaitez des clarifications, contactez-nous immédiatement :</p>
                        
                        <ul>
                            <li>📧 Email : ledouka.km@gmail.com</li>
                            <li>📞 Téléphone : +269 342 40 19</li>
                        </ul>
                        
                        <p>Nous restons à votre disposition pour résoudre cette situation.</p>
                        
                        <p>Cordialement,<br>L'équipe d'administration DOUKA KM</p>
                    </div>
                    <div class="email-footer">
                        <p><strong>DOUKA KM</strong></p>
                        <p>Administration - Marketplace des Comores</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
Suspension de votre compte marchand - DOUKA KM

Bonjour {merchant_record.first_name} {merchant_record.last_name},

Nous vous informons que votre compte marchand sur DOUKA KM a été temporairement suspendu.

Raison de la suspension : {reason if reason else 'Suspension administrative'}

Conséquences :
- Vos produits ne sont plus visibles sur la plateforme
- Vous ne pouvez plus recevoir de nouvelles commandes
- L'accès à votre espace marchand est restreint

Pour toute question, contactez-nous :
- Email : ledouka.km@gmail.com
- Téléphone : +269 342 40 19

Cordialement,
L'équipe d'administration DOUKA KM
            """
            
            send_email(merchant_email, subject, html_content, text_content)
            flash(f'Compte de {merchant_record.store_name} suspendu avec succès', 'warning')
            
        elif action == 'reactivate':
            # Réactiver le compte dans la base de données
            merchant_record.status = 'active'
            merchant_record.updated_at = datetime.now()
            
            # Mise à jour des informations de réactivation dans les notifications JSON
            if not merchant_record.notifications:
                merchant_record.notifications = '{}'
            
            notifications_data = json.loads(merchant_record.notifications)
            notifications_data['account_suspended'] = False
            notifications_data['suspension_reason'] = None
            notifications_data['suspension_date'] = None
            notifications_data['reactivation_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            notifications_data['reactivated_by'] = session.get('admin_email', 'admin')
            
            merchant_record.notifications = json.dumps(notifications_data)
            
            # Sauvegarder les changements dans la base de données
            db.session.commit()
            
            # COMPATIBILITÉ: Mise à jour du dictionnaire pour fallback
            if merchant_email in merchants_db:
                merchants_db[merchant_email].update(merchant_record.to_dict())
            
            print(f"✅ Marchand ID {merchant_id} réactivé dans la base de données")
            
            # Envoyer un email de notification de réactivation
            subject = "Réactivation de votre compte marchand - DOUKA KM"
            html_content = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        padding: 0;
                        background-color: #f4f4f4;
                    }}
                    .email-container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        border-radius: 10px;
                        overflow: hidden;
                        box-shadow: 0 0 20px rgba(0,0,0,0.1);
                    }}
                    .email-header {{
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }}
                    .email-body {{
                        padding: 40px 30px;
                    }}
                    .success-box {{
                        background-color: #d4edda;
                        border: 1px solid #c3e6cb;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                    .email-footer {{
                        background-color: #f8f9fa;
                        padding: 20px 30px;
                        text-align: center;
                        font-size: 14px;
                        color: #6c757d;
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="email-header">
                        <h1>✅ DOUKA KM - Réactivation de compte</h1>
                    </div>
                    <div class="email-body">
                        <h2>Réactivation de votre compte marchand</h2>
                        
                        <p>Bonjour {merchant_record.first_name} {merchant_record.last_name},</p>
                        
                        <div class="success-box">
                            <h4>✅ Bonne nouvelle !</h4>
                            <p>Votre compte marchand sur DOUKA KM a été réactivé avec succès.</p>
                        </div>
                        
                        <p><strong>Vous pouvez maintenant :</strong></p>
                        <ul>
                            <li>Accéder à votre espace marchand complet</li>
                            <li>Gérer vos produits et les rendre visibles</li>
                            <li>Recevoir de nouvelles commandes</li>
                            <li>Utiliser toutes les fonctionnalités de la plateforme</li>
                        </ul>
                        
                        <p>Nous vous remercions pour votre compréhension et nous excusons pour les désagréments occasionnés.</p>
                        
                        <p>N'hésitez pas à nous contacter si vous avez des questions :</p>
                        <ul>
                            <li>📧 Email : ledouka.km@gmail.com</li>
                            <li>📞 Téléphone : +269 342 40 19</li>
                        </ul>
                        
                        <p>Nous vous souhaitons beaucoup de succès dans vos ventes !</p>
                        
                        <p>Cordialement,<br>L'équipe d'administration DOUKA KM</p>
                    </div>
                    <div class="email-footer">
                        <p><strong>DOUKA KM</strong></p>
                        <p>Administration - Marketplace des Comores</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
Réactivation de votre compte marchand - DOUKA KM

Bonjour {merchant_record.first_name} {merchant_record.last_name},

Bonne nouvelle ! Votre compte marchand sur DOUKA KM a été réactivé avec succès.

Vous pouvez maintenant :
- Accéder à votre espace marchand complet
- Gérer vos produits et les rendre visibles
- Recevoir de nouvelles commandes
- Utiliser toutes les fonctionnalités de la plateforme

Pour toute question, contactez-nous :
- Email : ledouka.km@gmail.com
- Téléphone : +269 342 40 19

Cordialement,
L'équipe d'administration DOUKA KM
            """
            
            send_email(merchant_email, subject, html_content, text_content)
            flash(f'Compte de {merchant_record.store_name} réactivé avec succès', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la modification du statut du marchand: {str(e)}")
        flash(f'Erreur lors de la modification du statut du compte : {str(e)}', 'danger')
    
    return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))

@app.route('/admin/livreur-dashboard')
@permission_required(['livreur'])
def livreur_dashboard():
    """Dashboard spécialisé pour les livreurs - accès uniquement aux commandes - Version migrée vers base de données"""
    admin_email = session.get('admin_email')
    
    # DATABASE-FIRST: Récupérer l'employé depuis la base de données d'abord
    employee_data = None
    db_employee = Employee.query.filter_by(email=admin_email).first()
    
    if db_employee:
        employee_data = {
            'id': db_employee.id,
            'email': db_employee.email,
            'first_name': db_employee.first_name,
            'last_name': db_employee.last_name,
            'phone': db_employee.phone or '',
            'role': db_employee.role,
            'permissions': db_employee.get_permissions()
        }
    else:
        # Fallback: ancien dictionnaire
        employee_data = employees_db.get(admin_email, {})
    
    if not employee_data:
        flash('Employé introuvable.', 'danger')
        return redirect(url_for('admin_login'))
    
    # Récupérer les commandes assignées à ce livreur
    assigned_orders = get_livreur_assigned_orders(admin_email)
    
    # Récupérer les commandes disponibles (non assignées)
    available_orders = get_available_orders_for_livreur()
    
    # Compter les assignations actuelles de ce livreur
    current_assignments_count = get_livreur_assigned_orders_count(admin_email)
    can_take_more = can_livreur_take_order(admin_email)
    
    # Récupérer les commandes livrées par ce livreur pour les statistiques
    delivered_orders_count = 0
    try:
        from db_helpers import get_all_merchant_orders
        merchant_orders = get_all_merchant_orders()
        delivered_orders_count += len([o for o in merchant_orders 
                                     if o.delivery_employee_email == admin_email and o.status == 'delivered'])
        
        # Ajouter aussi les commandes admin livrées
        from db_helpers import get_all_admin_orders
        admin_orders = get_all_admin_orders()
        delivered_orders_count += len([o for o in admin_orders 
                                     if hasattr(o, 'delivery_employee_email') and 
                                     o.delivery_employee_email == admin_email and o.status == 'delivered'])
    except Exception as e:
        print(f"❌ Erreur lors du calcul des commandes livrées: {e}")
    
    # Statistiques pour le livreur
    stats = {
        'assigned_orders': len(assigned_orders),
        'available_orders': len(available_orders),
        'delivered_orders': delivered_orders_count,
        'assignments_remaining': 3 - current_assignments_count,
        'max_assignments': 3,
        'can_take_more': can_take_more
    }
    
    # Filtrer les commandes assignées par statut
    processing_orders = [o for o in assigned_orders if o.get('status') == 'processing']
    shipped_orders = [o for o in assigned_orders if o.get('status') == 'shipped']
    delivered_orders = [o for o in assigned_orders if o.get('status') == 'delivered']
    
    return render_template('admin/livreur_dashboard.html', 
                         employee=employee_data,
                         stats=stats,
                         assigned_orders=assigned_orders,
                         available_orders=available_orders[:10],  # 10 premières commandes disponibles
                         processing_orders=processing_orders,
                         shipped_orders=shipped_orders,
                         delivered_orders=delivered_orders,
                         current_assignments_count=current_assignments_count,
                         can_take_more=can_take_more)

@app.route('/admin/livreur-orders')
@permission_required(['livreur'])
def livreur_orders():
    """Page spécialisée pour les livreurs - gestion des commandes assignées et disponibles - Version migrée vers base de données"""
    admin_email = session.get('admin_email')
    
    # DATABASE-FIRST: Récupérer l'employé depuis la base de données d'abord
    employee_data = None
    db_employee = Employee.query.filter_by(email=admin_email).first()
    
    if db_employee:
        employee_data = {
            'id': db_employee.id,
            'email': db_employee.email,
            'first_name': db_employee.first_name,
            'last_name': db_employee.last_name,
            'phone': db_employee.phone or '',
            'role': db_employee.role,
            'permissions': db_employee.get_permissions()
        }
    else:
        # Fallback: ancien dictionnaire
        employee_data = employees_db.get(admin_email, {})
    
    if not employee_data:
        flash('Employé introuvable.', 'danger')
        return redirect(url_for('admin_login'))
    
    # Paramètres de filtrage
    view_type = request.args.get('view', 'assigned')  # 'assigned' ou 'available'
    status_filter = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    if view_type == 'assigned':
        # Commandes assignées à ce livreur
        orders = get_livreur_assigned_orders(admin_email)
        page_title = "Mes commandes assignées"
    else:
        # Commandes disponibles (non assignées)
        orders = get_available_orders_for_livreur()
        page_title = "Commandes disponibles"
    
    # Filtrer par statut si spécifié
    if status_filter:
        orders = [order for order in orders if order.get('status') == status_filter]
    
    # Filtrer par recherche si un terme est fourni
    if search:
        search_lower = search.lower()
        filtered_orders = []
        for order in orders:
            if (search_lower in order.get('customer_name', '').lower() or
                search_lower in order.get('order_number', '').lower() or
                search_lower in str(order.get('id', '')).lower()):
                filtered_orders.append(order)
        orders = filtered_orders
    
    # Trier par date (plus récent en premier)
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Informations sur les assignations du livreur
    current_assignments_count = get_livreur_assigned_orders_count(admin_email)
    can_take_more = can_livreur_take_order(admin_email)
    
    # Statistiques
    all_assigned = get_livreur_assigned_orders(admin_email)
    all_available = get_available_orders_for_livreur()
    
    stats = {
        'assigned_orders': len(all_assigned),
        'available_orders': len(all_available),
        'assignments_remaining': 3 - current_assignments_count,
        'current_assignments_count': current_assignments_count,
        'can_take_more': can_take_more
    }
    
    return render_template('admin/livreur_orders.html',
                         employee=employee_data,
                         orders=orders,
                         view_type=view_type,
                         page_title=page_title,
                         status_filter=status_filter,
                         search=search,
                         stats=stats,
                         current_assignments_count=current_assignments_count,
                         can_take_more=can_take_more)

@app.route('/admin/livreur-order/<order_id>')
@permission_required(['livreur'])
def livreur_order_detail(order_id):
    """Page de détails d'une commande pour les livreurs"""
    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        flash('ID de commande invalide', 'danger')
        return redirect(url_for('livreur_orders'))
    
    # **NOUVELLE VERSION: Rechercher la commande dans la base de données d'abord**
    order_data = None
    merchant_info = None
    
    # D'abord chercher dans les commandes des marchands via la DB
    from db_helpers import get_order_by_id, get_merchant_by_id
    db_order = get_order_by_id(order_id)
    
    if db_order and db_order.merchant_id:
        # Commande trouvée dans les marchands
        merchant_record = get_merchant_by_id(db_order.merchant_id)
        if merchant_record:
            # Récupérer l'adresse de livraison depuis le JSON
            shipping_address = db_order.get_shipping_address()
            
            order_data = {
                'id': db_order.id,
                'order_number': db_order.order_number,
                'customer_name': db_order.customer_name,
                'customer_email': db_order.customer_email,
                'customer_phone': db_order.customer_phone,
                'total': db_order.total,
                'shipping_fee': db_order.shipping_fee,
                'status': db_order.status,
                'status_text': db_order.status_text,
                'status_color': db_order.status_color,
                'payment_method': db_order.payment_method,
                'shipping_method': shipping_address.get('shipping_method', 'Standard'),
                'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'shipping_address': shipping_address,
                'source': 'merchant',
                'items': []
            }
            
            # Ajouter les items de la commande depuis la relation SQLAlchemy
            for item in db_order.items:
                order_data['items'].append({
                    'name': item.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'subtotal': item.subtotal,
                    'image': item.image or '/static/images/default.jpg',
                    'variant_details': item.variant_details or ''
                })
            
            merchant_info = {
                'email': merchant_record.email,
                'store_name': merchant_record.store_name,
                'store_address': merchant_record.store_address or '',
                'phone': merchant_record.phone or ''
            }
    
    # Fallback: rechercher dans l'ancien dictionnaire si pas trouvé en DB
    if not order_data:
        for merchant_email, merchant in merchants_db.items():
            for order in merchant.get('orders', []):
                if order.get('id') == order_id:
                    order_data = dict(order)
                    merchant_info = {
                        'email': merchant_email,
                        'store_name': merchant.get('store_name', 'Marchand'),
                        'store_address': merchant.get('store_address', ''),
                        'phone': merchant.get('phone', '')
                    }
                    order_data['source'] = 'merchant'
                    break
            if order_data:
                break
    
    # Si pas trouvé dans les marchands, chercher dans les commandes admin
    if not order_data:
        # **NOUVELLE VERSION: Rechercher dans la base de données admin**
        from db_helpers import get_admin_order_by_id
        admin_order = get_admin_order_by_id(order_id)
        
        if admin_order:
            order_data = {
                'id': admin_order.id,
                'order_number': admin_order.order_number,
                'customer_name': admin_order.customer_name,
                'customer_email': admin_order.customer_email,
                'customer_phone': admin_order.customer_phone,
                'total': admin_order.total,
                'shipping_fee': admin_order.shipping_fee,
                'status': admin_order.status,
                'status_text': admin_order.status_text,
                'created_at': admin_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'shipping_address': admin_order.get_shipping_address(),
                'items': []
            }
            
            # Ajouter les items de la commande
            for item in admin_order.items:
                order_data['items'].append({
                    'name': item.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'subtotal': item.price * item.quantity,
                    'image': item.image or '/static/images/default.jpg'
                })
            
            merchant_info = {
                'email': 'admin@doukakm.com',
                'store_name': 'DOUKA KM (Admin)',
                'store_address': 'Siège DOUKA KM',
                'phone': 'N/A'
            }
            order_data['source'] = 'admin'
    
    if not order_data:
        flash('Commande non trouvée', 'danger')
        return redirect(url_for('livreur_orders'))
    
    # Marquer les commandes livrées ou annulées comme étant en mode lecture seule
    order_data['is_readonly'] = order_data['status'] in ['delivered', 'cancelled']
    if order_data['status'] == 'delivered':
        flash('Cette commande a été livrée avec succès. Affichage en mode consultation.', 'info')
    elif order_data['status'] == 'cancelled':
        flash('Cette commande a été annulée. Affichage en mode consultation.', 'warning')
    
    # Enrichir les données pour l'affichage
    order_data['merchant_info'] = merchant_info
    
    # Vérifier si cette commande est assignée au livreur courant
    admin_email = session.get('admin_email')
    is_assigned, assigned_to = is_order_assigned(order_id, order_data['source'], 
                                               merchant_info['email'] if order_data['source'] == 'merchant' else None)
    order_data['is_assigned_to_me'] = is_assigned and assigned_to == admin_email
    order_data['is_assigned_to_other'] = is_assigned and assigned_to != admin_email
    order_data['assigned_to'] = assigned_to if is_assigned else None
    
    return render_template('admin/livreur_order_detail.html', 
                          order=order_data, 
                          merchant=merchant_info)

@app.route('/admin/livreur/assign-order', methods=['POST'])
@permission_required(['livreur'])
def livreur_assign_order():
    """Route pour assigner une commande à un livreur"""
    try:
        order_id = int(request.form.get('order_id'))
        order_type = request.form.get('order_type')  # 'merchant' ou 'admin'
        merchant_email = request.form.get('merchant_email') if order_type == 'merchant' else None
        
        livreur_email = session.get('admin_email')
        
        # **NOUVELLE VERSION: Vérifier dans la base de données uniquement**
        order_exists = False
        if order_type == 'merchant' and merchant_email:
            # Vérifier la commande marchand dans la base de données
            from db_helpers import get_order_by_id, get_merchant_by_email
            db_order = get_order_by_id(order_id)
            if db_order and db_order.status in ['processing', 'shipped']:
                # Vérifier que la commande appartient au bon marchand
                merchant_record = get_merchant_by_email(merchant_email)
                if merchant_record and db_order.merchant_id == merchant_record.id:
                    order_exists = True
        elif order_type == 'admin':
            # **NOUVELLE VERSION: Vérifier dans la base de données admin**
            from db_helpers import get_admin_order_by_id
            admin_order = get_admin_order_by_id(order_id)
            if admin_order and admin_order.status in ['processing', 'shipped']:
                order_exists = True
        
        if not order_exists:
            return jsonify({
                'success': False,
                'message': 'Commande non trouvée ou non assignable'
            })
        
        # Assigner la commande
        success, message = assign_order_to_livreur(order_id, order_type, livreur_email, merchant_email)
        
        return jsonify({
            'success': success,
            'message': message,
            'assignments_remaining': 3 - get_livreur_assigned_orders_count(livreur_email) if success else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de l\'assignation: {str(e)}'
        })

@app.route('/admin/livreur/unassign-order', methods=['POST'])
@permission_required(['livreur'])
def livreur_unassign_order():
    """Route pour désassigner une commande d'un livreur"""
    try:
        order_id = int(request.form.get('order_id'))
        order_type = request.form.get('order_type')  # 'merchant' ou 'admin'
        merchant_email = request.form.get('merchant_email') if order_type == 'merchant' else None
        
        livreur_email = session.get('admin_email')
        
        # Vérifier que la commande est bien assignée à ce livreur
        is_assigned, assigned_to = is_order_assigned(order_id, order_type, merchant_email)
        if not is_assigned or assigned_to != livreur_email:
            return jsonify({
                'success': False,
                'message': 'Cette commande n\'est pas assignée à vous'
            })
        
        # Désassigner la commande
        success = unassign_order_from_livreur(order_id, order_type, merchant_email)
        
        return jsonify({
            'success': success,
            'message': 'Commande désassignée avec succès' if success else 'Erreur lors de la désassignation',
            'assignments_remaining': 3 - get_livreur_assigned_orders_count(livreur_email) if success else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de la désassignation: {str(e)}'
        })

@app.route('/admin/livreur/history')
@permission_required(['livreur'])
def livreur_history():
    """Page d'historique des livraisons pour un livreur"""
    livreur_email = session.get('admin_email')
    
    if not livreur_email:
        flash('Session expirée', 'danger')
        return redirect(url_for('admin_login'))
    
    # Récupérer toutes les commandes livrées par ce livreur
    delivered_orders = []
    
    # 1. Chercher dans les commandes marchands
    from db_helpers import get_all_merchant_orders
    merchant_orders = get_all_merchant_orders()
    for order in merchant_orders:
        if (order.delivery_employee_email == livreur_email and 
            order.status in ['delivered', 'completed']):
            
            # Récupérer les informations du marchand
            from db_helpers import get_merchant_by_id
            merchant = get_merchant_by_id(order.merchant_id)
            
            order_info = {
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'total': order.total,
                'shipping_fee': order.shipping_fee,
                'status': order.status,
                'status_text': order.status_text or order.status,
                'status_color': order.status_color or 'success',
                'delivery_date': order.delivery_date,
                'assigned_at': order.assigned_at,
                'created_at': order.created_at,
                'merchant_name': merchant.store_name if merchant else 'Marchand',
                'source': 'merchant',
                'shipping_address': order.get_shipping_address()
            }
            delivered_orders.append(order_info)
    
    # 2. Chercher dans les commandes admin
    from db_helpers import get_all_admin_orders
    admin_orders = get_all_admin_orders()
    for order in admin_orders:
        if (hasattr(order, 'delivery_employee_email') and 
            order.delivery_employee_email == livreur_email and 
            order.status in ['delivered', 'completed']):
            
            order_info = {
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'total': order.total,
                'shipping_fee': order.shipping_fee or 0,
                'status': order.status,
                'status_text': order.status_text or order.status,
                'status_color': 'success',
                'delivery_date': order.delivery_date,
                'assigned_at': order.assigned_at,
                'created_at': order.created_at,
                'merchant_name': 'DOUKA KM (Admin)',
                'source': 'admin',
                'shipping_address': order.get_shipping_address()
            }
            delivered_orders.append(order_info)
    
    # Trier par date de livraison (plus récent en premier)
    delivered_orders.sort(key=lambda x: x['delivery_date'] or x['created_at'], reverse=True)
    
    # Calculer les statistiques
    total_deliveries = len(delivered_orders)
    total_revenue = sum(order['total'] for order in delivered_orders)
    total_shipping = sum(order['shipping_fee'] for order in delivered_orders)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    paginated_orders = delivered_orders[start:end]
    
    # Informations de pagination
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_deliveries,
        'has_prev': page > 1,
        'has_next': end < total_deliveries,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if end < total_deliveries else None
    }
    
    return render_template('admin/livreur_history.html',
                          orders=paginated_orders,
                          pagination=pagination_info,
                          stats={
                              'total_deliveries': total_deliveries,
                              'total_revenue': total_revenue,
                              'total_shipping': total_shipping
                          })

@app.route('/admin/orders')
@permission_required(['super_admin', 'admin', 'manager', 'livreur'])
def admin_orders():
    """Page d'administration pour toutes les commandes avec pagination et filtres"""
    
    # Paramètres de pagination et filtres
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    # Récupérer toutes les commandes de tous les marchands
    all_orders = []
    
    # **NOUVELLE VERSION: Ajouter les commandes des marchands depuis la DB**
    all_merchant_orders = get_all_merchant_orders()
    for db_order in all_merchant_orders:
        # Récupérer les informations du marchand
        merchant_info = get_merchant_by_id(db_order.merchant_id) if db_order.merchant_id else None
        
        # Récupérer l'adresse de livraison depuis le JSON
        shipping_address = db_order.get_shipping_address()
        
        order_dict = {
            'id': db_order.id,
            'order_number': db_order.order_number,
            'customer_name': db_order.customer_name,
            'customer_email': db_order.customer_email,
            'customer_phone': db_order.customer_phone,
            'total': db_order.total,
            'status': db_order.status,
            'status_text': db_order.status_text,
            'status_color': db_order.status_color,
            'payment_method': db_order.payment_method,
            'payment_status': db_order.payment_status or 'pending',
            'shipping_method': shipping_address.get('shipping_method', 'Standard'),
            'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'date': db_order.created_at.strftime('%d/%m/%Y'),
            'merchant_email': merchant_info.email if merchant_info else 'Unknown',
            'merchant_name': merchant_info.store_name if merchant_info else 'Boutique inconnue',
            'merchant_id': db_order.merchant_id,
            'merchant_verified': merchant_info.store_verified if merchant_info else False,
            'source': 'merchant'
        }
        all_orders.append(order_dict)
    
    # **NOUVELLE VERSION: Ajouter les commandes admin depuis la base de données**
    from db_helpers import get_admin_orders
    admin_orders = get_admin_orders()
    
    for admin_order in admin_orders:
        # Récupérer l'adresse de livraison depuis le JSON
        shipping_address = admin_order.get_shipping_address()
        
        # Convertir les objets Order en dictionnaires pour compatibility
        order_dict = {
            'id': admin_order.id,
            'order_number': admin_order.order_number,
            'customer_name': admin_order.customer_name,
            'customer_email': admin_order.customer_email,
            'customer_phone': admin_order.customer_phone,
            'total': admin_order.total,
            'status': admin_order.status,
            'status_text': admin_order.status_text,
            'status_color': admin_order.status_color,
            'payment_status': admin_order.payment_status or 'pending',
            'created_at': admin_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'date': admin_order.created_at.strftime('%d/%m/%Y'),
            'merchant_name': 'DOUKA KM (Admin)',
            'merchant_email': 'admin@doukakm.com',
            'merchant_verified': True,
            'source': 'admin',
            'payment_method': admin_order.payment_method or 'Non spécifié',
            'shipping_method': shipping_address.get('shipping_method', 'Standard'),
            'items': []
        }
        
        # Ajouter les items
        for item in admin_order.items:
            order_dict['items'].append({
                'name': item.name,
                'quantity': item.quantity,
                'price': item.price,
                'subtotal': item.price * item.quantity
            })
        
        all_orders.append(order_dict)
    
    # Filtrer par statut si spécifié
    if status_filter:
        all_orders = [order for order in all_orders if order.get('status') == status_filter]
    
    # Filtrer par recherche si un terme est fourni
    if search:
        search_lower = search.lower()
        all_orders = [
            order for order in all_orders 
            if (search_lower in order.get('order_number', '').lower() or
                search_lower in order.get('customer_name', '').lower() or
                search_lower in order.get('customer_email', '').lower() or
                search_lower in order.get('merchant_name', '').lower())
        ]
    
    # Trier par date de création (plus récentes en premier)
    all_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Pagination
    total_orders = len(all_orders)
    total_pages = (total_orders + per_page - 1) // per_page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    orders_paginated = all_orders[start_index:end_index]
    
    # Créer l'objet de pagination
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total_orders,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None
    }
    
    # Calculer les statistiques
    stats = {
        'total_orders': len(all_orders),
        'processing_orders': len([o for o in all_orders if o.get('status') == 'processing']),
        'shipped_orders': len([o for o in all_orders if o.get('status') == 'shipped']),
        'delivered_orders': len([o for o in all_orders if o.get('status') == 'delivered']),
        'cancelled_orders': len([o for o in all_orders if o.get('status') == 'cancelled']),
        'total_revenue': sum(o.get('total', 0) for o in all_orders if o.get('status') in ['shipped', 'delivered']),
        'pending_revenue': sum(o.get('total', 0) for o in all_orders if o.get('status') == 'processing'),
        'admin_orders': len([o for o in all_orders if o.get('source') == 'admin']),
        'merchant_orders': len([o for o in all_orders if o.get('source') == 'merchant'])
    }
    
    return render_template('admin/orders.html', 
                          orders=orders_paginated,
                          pagination=pagination,
                          stats=stats,
                          current_status_filter=status_filter,
                          current_search=search)

@app.route('/admin/orders/<order_id>')
@admin_required
def admin_order_detail(order_id):
    """Page de détail d'une commande spécifique côté admin"""
    
    # **NOUVELLE VERSION: Chercher d'abord dans la base de données**
    target_order = None
    merchant_info = None
    
    # D'abord chercher dans les commandes des marchands via la DB
    from db_helpers import get_order_by_id, get_merchant_by_id
    db_order = get_order_by_id(order_id)
    
    if db_order and db_order.merchant_id:
        # Commande trouvée dans les marchands
        merchant_record = get_merchant_by_id(db_order.merchant_id)
        if merchant_record:
            # Récupérer l'adresse de livraison depuis le JSON
            shipping_address = db_order.get_shipping_address()
            
            target_order = {
                'id': db_order.id,
                'order_number': db_order.order_number,
                'customer_name': db_order.customer_name,
                'customer_email': db_order.customer_email,
                'customer_phone': db_order.customer_phone,
                'total': db_order.total,
                'status': db_order.status,
                'status_text': db_order.status_text,
                'status_color': db_order.status_color,
                'payment_method': db_order.payment_method,
                'payment_status': db_order.payment_status or 'pending',
                'shipping_method': shipping_address.get('shipping_method', 'Standard'),
                'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'shipping_address': shipping_address,
                'source': 'merchant'
            }
            
            # Ajouter les items de la commande
            target_order['items'] = []
            subtotal = 0
            for item in db_order.items:
                item_subtotal = item.price * item.quantity
                subtotal += item_subtotal
                target_order['items'].append({
                    'name': item.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'subtotal': item_subtotal,
                    'image': item.image,
                    'variant_details': item.variant_details,
                    'options': item.get_options()  # Ajouter les options
                })
            target_order['subtotal'] = subtotal
            # Frais de livraison
            target_order['shipping_fee'] = db_order.shipping_fee or 0
            
            merchant_info = {
                'email': merchant_record.email,
                'name': merchant_record.store_name,
                'id': merchant_record.id,
                'verified': merchant_record.store_verified,
                'phone': merchant_record.phone or '',
                'address': merchant_record.store_address or '',
                'city': merchant_record.store_city or '',
                'region': merchant_record.store_region or ''
            }
    
    # Fallback: chercher dans l'ancien dictionnaire si pas trouvé en DB
    if not target_order:
        for merchant_email, merchant in merchants_db.items():
            for order in merchant.get('orders', []):
                if str(order.get('id')) == str(order_id):
                    target_order = dict(order)
                    merchant_info = {
                        'email': merchant_email,
                        'name': merchant.get('store_name', 'Boutique sans nom'),
                        'id': merchant.get('id'),
                        'verified': merchant.get('store_verified', False),
                        'phone': merchant.get('phone', ''),
                        'address': merchant.get('store_address', ''),
                        'city': merchant.get('store_city', ''),
                        'region': merchant.get('store_region', '')
                    }
                    break
            if target_order:
                break
    
    # **NOUVELLE VERSION: Si pas trouvée, chercher dans les commandes admin de la base de données**
    if not target_order:
        from db_helpers import get_admin_order_by_id
        admin_order = get_admin_order_by_id(order_id)
        
        if admin_order:
            target_order = {
                'id': admin_order.id,
                'order_number': admin_order.order_number,
                'customer_name': admin_order.customer_name,
                'customer_email': admin_order.customer_email,
                'customer_phone': admin_order.customer_phone,
                'total': admin_order.total,
                'status': admin_order.status,
                'status_text': admin_order.status_text,
                'payment_status': admin_order.payment_status or 'pending',
                'created_at': admin_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'date': admin_order.created_at.strftime('%d/%m/%Y'),
                'payment_method': admin_order.payment_method or 'Non spécifié',
                'shipping_method': getattr(admin_order, 'shipping_method', 'Standard'),
                'shipping_address': admin_order.get_shipping_address(),
                'items': [],
                'source': 'admin'
            }
            
            # Ajouter les items
            subtotal = 0
            for item in admin_order.items:
                item_subtotal = item.price * item.quantity
                subtotal += item_subtotal
                # Récupérer les options si la méthode existe, sinon None
                options = item.get_options() if hasattr(item, 'get_options') else getattr(item, 'options', None)
                target_order['items'].append({
                    'name': item.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'subtotal': item_subtotal,
                    'image': item.image or '/static/images/default.jpg',
                    'options': options
                })
            target_order['subtotal'] = subtotal
            # Frais de livraison
            target_order['shipping_fee'] = admin_order.shipping_fee or 0
            
            merchant_info = {
                'email': 'admin@douka-km.com',
                'name': 'Administration DOUKA KM',
                'id': 0,
                'verified': True,
                'phone': '',
                'address': '',
                'city': '',
                'region': ''
            }
    
    if not target_order:
        flash('Commande non trouvée', 'danger')
        return redirect(url_for('admin_orders'))
    
    # Enrichir la commande avec les informations du marchand
    target_order['merchant_info'] = merchant_info
    
    # Récupérer les informations du client
    customer_email = target_order.get('customer_email')
    customer_info = target_order.get('customer_info')  # Pour les commandes admin, c'est déjà là
    
    if not customer_info and customer_email and customer_email in users_db:
        customer = users_db[customer_email]
        customer_info = {
            'email': customer_email,
            'name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
            'phone': customer.get('phone', ''),
            'city': customer.get('city', ''),
            'region': customer.get('region', ''),
            'registration_date': customer.get('registration_date', '')
        }
    
    target_order['customer_info'] = customer_info
    
    # Chercher le livreur assigné à cette commande
    assigned_livreur_info = None
    current_order_obj = None
    
    # Récupérer l'objet Order de la base de données (qu'il soit marchand ou admin)
    if db_order:
        current_order_obj = db_order
    elif admin_order:
        current_order_obj = admin_order
    else:
        # Dernière tentative : récupérer directement par ID
        from db_helpers import get_order_by_id_safe
        current_order_obj = get_order_by_id_safe(order_id)
    
    # 1. Vérifier si les informations du livreur sont stockées dans la commande (historique permanent)
    if current_order_obj and current_order_obj.delivery_employee_email:
        assigned_livreur_info = {
            'email': current_order_obj.delivery_employee_email,
            'name': current_order_obj.delivery_employee_name or 'Livreur',
            'phone': current_order_obj.delivery_employee_phone or '',
            'assigned_at': current_order_obj.assigned_at.strftime('%Y-%m-%d %H:%M:%S') if current_order_obj.assigned_at else '',
            'is_employee': True,
            'is_from_history': True
        }
    
    # 2. Si pas d'historique permanent, chercher dans les assignations actuelles
    if not assigned_livreur_info:
        assigned_livreur_email = None
        order_type = 'merchant' if target_order.get('merchant_info', {}).get('email') != 'admin@douka-km.com' else 'admin'
        merchant_email = target_order.get('merchant_info', {}).get('email') if order_type == 'merchant' else None
        
        # Chercher dans les assignations en mémoire
        for livreur_email, assignments in livreur_assignments_db.items():
            for assignment in assignments:
                if (str(assignment['order_id']) == str(order_id) and assignment['order_type'] == order_type):
                    if order_type == 'merchant' and merchant_email:
                        if assignment.get('merchant_email') == merchant_email:
                            assigned_livreur_email = livreur_email
                            break
                    else:
                        assigned_livreur_email = livreur_email
                        break
            if assigned_livreur_email:
                break
            if assigned_livreur_email:
                break
        
        # 3. Récupérer les infos du livreur si trouvé dans les assignations actuelles
        if assigned_livreur_email:
            # D'abord chercher dans la table Employee (pour les employés livreurs)
            from models import Employee
            employee = Employee.query.filter_by(email=assigned_livreur_email, role='livreur').first()
            if employee:
                assigned_livreur_info = {
                    'email': assigned_livreur_email,
                    'name': f"{employee.first_name} {employee.last_name}".strip(),
                    'phone': employee.phone or '',
                    'address': '',  # Non disponible dans Employee
                    'city': '',     # Non disponible dans Employee  
                    'region': '',   # Non disponible dans Employee
                    'is_employee': True,
                    'is_active': employee.status == 'active',
                    'is_from_history': False
                }
            else:
                # Fallback vers users_db pour les utilisateurs classiques
                user = users_db.get(assigned_livreur_email)
                if user:
                    assigned_livreur_info = {
                        'email': assigned_livreur_email,
                        'name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                        'phone': user.get('phone', ''),
                        'region': user.get('region', ''),
                        'city': user.get('city', ''),
                        'address': user.get('address', ''),
                        'is_employee': False,
                        'is_from_history': False
                    }
                else:
                    assigned_livreur_info = {
                        'email': assigned_livreur_email,
                        'name': 'Livreur',
                        'is_employee': False,
                        'is_from_history': False
                    }
    return render_template('admin/order_detail.html', 
                          order=target_order,
                          assigned_livreur=assigned_livreur_info)

@app.route('/admin/orders/<order_id>/update-status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    """Met à jour le statut d'une commande depuis l'admin - VERSION SIMPLIFIÉE"""
    try:
        status = request.form.get('status')
        notes = request.form.get('notes', '')
        
        if not status:
            return jsonify({'success': False, 'message': 'Le statut est requis'})
        
        print(f"🔄 Admin met à jour commande {order_id} -> {status}")
        
        # **ÉTAPE 1: Chercher la commande dans la base de données d'abord (DATABASE-FIRST)**
        from db_helpers import get_order_by_id, update_order_status, get_admin_order_by_id, update_admin_order_status, get_user_order_by_id
        
        order_updated = False
        old_status = None
        customer_email = None
        
        # Chercher dans les commandes marchands
        db_order = get_order_by_id(order_id)
        if db_order:
            print(f"📦 Commande marchand trouvée: {order_id}")
            old_status = db_order.status
            customer_email = db_order.customer_email
            
            # Mettre à jour via db_helpers
            result = update_order_status(order_id, status, notes, 'Administrateur')
            if result:
                order_updated = True
                print(f"✅ Commande marchand {order_id} mise à jour: {old_status} -> {status}")
                
                # Désassignation automatique
                if status in ['delivered', 'cancelled']:
                    try:
                        from db_helpers import get_merchant_by_id
                        merchant_record = get_merchant_by_id(db_order.merchant_id) if db_order.merchant_id else None
                        merchant_email_for_unassign = merchant_record.email if merchant_record else None
                        unassign_order_from_livreur(order_id, 'merchant', merchant_email_for_unassign)
                        print(f"📤 Commande {order_id} désassignée du livreur")
                    except Exception as e:
                        print(f"⚠️ Erreur désassignation: {e}")
        
        # Si pas trouvée dans marchands, chercher dans commandes admin
        elif get_admin_order_by_id(order_id):
            print(f"🏛️ Commande admin trouvée: {order_id}")
            admin_order = get_admin_order_by_id(order_id)
            old_status = admin_order.status
            customer_email = admin_order.customer_email
            
            # Mettre à jour via db_helpers
            success, retrieved_old_status = update_admin_order_status(order_id, status)
            if success:
                order_updated = True
                print(f"✅ Commande admin {order_id} mise à jour: {retrieved_old_status} -> {status}")
                
                # Désassignation automatique
                if status in ['delivered', 'cancelled']:
                    try:
                        unassign_order_from_livreur(order_id, 'admin', None)
                        print(f"📤 Commande admin {order_id} désassignée du livreur")
                    except Exception as e:
                        print(f"⚠️ Erreur désassignation admin: {e}")
        
        # Si toujours pas trouvée, chercher dans les dictionnaires en mémoire (fallback)
        if not order_updated:
            print(f"🔍 Recherche fallback dans dictionnaires pour commande {order_id}")
            order_id_str = str(order_id)
            
            for merchant_email, merchant in merchants_db.items():
                for order in merchant.get('orders', []):
                    if str(order.get('id')) == order_id_str:
                        old_status = order.get('status')
                        customer_email = order.get('customer_email')
                        
                        # Mise à jour simple du dictionnaire
                        order['status'] = status
                        order['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Ajouter les notes si fournies
                        if notes:
                            if 'admin_notes' not in order:
                                order['admin_notes'] = []
                            order['admin_notes'].append({
                                'note': notes,
                                'admin_email': session.get('admin_email'),
                                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                        
                        order_updated = True
                        print(f"✅ Commande dictionnaire {order_id} mise à jour: {old_status} -> {status}")
                        break
                if order_updated:
                    break
        
        if not order_updated:
            print(f"❌ Commande {order_id} non trouvée")
            return jsonify({'success': False, 'message': f'Commande {order_id} non trouvée'})
        
        # **ÉTAPE 2: Envoyer l'email de notification (SÉPARÉ ET SÉCURISÉ)**
        email_sent = False
        if customer_email and status in ['processing', 'shipped', 'delivered', 'cancelled']:
            try:
                print(f"📧 Tentative d'envoi email à {customer_email} pour commande {order_id}")
                
                # Récupérer les données de commande pour l'email
                order_data = get_user_order_by_id(customer_email, order_id)
                if order_data:
                    email_success = send_order_status_email(customer_email, order_data, old_status, status)
                    if email_success:
                        email_sent = True
                        print(f"✅ Email de notification envoyé à {customer_email}")
                    else:
                        print(f"⚠️ Échec envoi email à {customer_email}")
                else:
                    print(f"⚠️ Données de commande non trouvées pour email à {customer_email}")
                    
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi de l'email à {customer_email}: {str(e)}")
        
        # **ÉTAPE 3: Retourner le succès avec informations sur l'email**
        status_text = {
            'processing': 'En cours de préparation',
            'shipped': 'Expédiée', 
            'delivered': 'Livrée',
            'cancelled': 'Annulée'
        }.get(status, status)
        
        message = f'Statut mis à jour vers "{status_text}"'
        if customer_email:
            if email_sent:
                message += f' et email envoyé à {customer_email}'
            else:
                message += f' mais échec envoi email à {customer_email}'
        
        return jsonify({
            'success': True, 
            'message': message,
            'email_sent': email_sent,
            'customer_email': customer_email
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Erreur dans admin_update_order_status: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erreur serveur: {str(e)}'})

@app.route('/admin/livreur/orders/<order_id>/update-status', methods=['POST'])
@permission_required(['livreur'])
def livreur_update_order_status(order_id):
    """Met à jour le statut d'une commande par un livreur (sans possibilité d'annulation)"""
    try:
        status = request.form.get('status')
        notes = request.form.get('notes', '')
        
        
        # Convertir order_id en string pour la comparaison
        order_id_str = str(order_id)
        
        if not status:
            return jsonify({'success': False, 'message': 'Le statut est requis'})
        
        # Statuts autorisés pour les livreurs (SANS annulation)
        allowed_statuses = ['processing', 'shipped', 'delivered']
        if status not in allowed_statuses:
            return jsonify({'success': False, 'message': 'Statut non autorisé pour les livreurs'})
        
        # Définir les mappings de statut
        status_colors = {
            'processing': 'primary',
            'shipped': 'info',
            'delivered': 'success'
        }
        status_texts = {
            'processing': 'En cours de préparation',
            'shipped': 'Expédiée',
            'delivered': 'Livrée'
        }
        payment_status_mapping = {
            'delivered': 'completed',
            'processing': 'pending',
            'shipped': 'pending'
        }
        
        # **NOUVELLE VERSION: Rechercher et mettre à jour la commande via la base de données d'abord**
        order_updated = False
        
        # D'abord chercher dans les commandes des marchands via la DB
        from db_helpers import get_order_by_id, update_order_status
        db_order = get_order_by_id(order_id)
        
        if db_order and db_order.merchant_id:
            # Commande de marchand trouvée dans la DB
            
            # Vérifier que le statut actuel permet la transition
            current_status = db_order.status
            
            # Logique de transition des statuts pour livreurs
            valid_transitions = {
                'processing': ['shipped'],
                'shipped': ['delivered']
            }
            
            if status != current_status and current_status in valid_transitions:
                if status not in valid_transitions[current_status]:
                    return jsonify({'success': False, 'message': f'Transition de statut non autorisée: {current_status} -> {status}'})
            
            # Mettre à jour le statut dans la base de données
            try:
                result = update_order_status(order_id, status, notes, 'Livreur')
                if result:
                    order_updated = True
                    
                    # **DÉSASSIGNATION AUTOMATIQUE: Si la commande est livrée, la désassigner du livreur**
                    if status == 'delivered':
                        from db_helpers import get_merchant_by_id
                        merchant_record = get_merchant_by_id(db_order.merchant_id) if db_order.merchant_id else None
                        merchant_email_for_unassign = merchant_record.email if merchant_record else None
                        
                        unassign_success = unassign_order_from_livreur(order_id, 'merchant', merchant_email_for_unassign)
                        if unassign_success:
                            print(f"✅ Commande marchand {order_id} désassignée automatiquement après livraison (DB)")
                        else:
                            print(f"⚠️ Échec désassignation automatique commande marchand {order_id}")
                    
                    # Envoyer notification email si nécessaire
                    customer_email = db_order.customer_email
                    if customer_email and status in ['shipped', 'delivered']:
                        try:
                            from db_helpers import get_user_order_by_id
                            order_data = get_user_order_by_id(customer_email, order_id)
                            if order_data:
                                send_order_status_email(customer_email, order_data, current_status, status)
                                print(f"Email de notification envoyé à {customer_email} pour commande {order_id} (livreur)")
                        except Exception as e:
                            print(f"Erreur lors de l'envoi de l'email: {e}")
            except Exception as e:
                print(f"Erreur lors de la mise à jour de la commande marchand: {e}")
        
        # Si pas trouvé en DB, fallback vers l'ancien dictionnaire
        if not order_updated:
            # Fallback: chercher dans l'ancien dictionnaire des marchands
            for merchant_email, merchant in merchants_db.items():
                for order in merchant.get('orders', []):
                    if str(order.get('id')) == order_id_str:
                        
                        # Capturer l'ancien statut avant modification
                        old_status = order.get('status', 'processing')
                        
                        # Vérifier que le statut actuel permet la transition
                        current_status = order.get('status', 'processing')
                        
                        # Logique de transition des statuts pour livreurs
                        valid_transitions = {
                            'processing': ['shipped'],
                            'shipped': ['delivered']
                        }
                        
                        if status != current_status and current_status in valid_transitions:
                            if status not in valid_transitions[current_status]:
                                return jsonify({'success': False, 'message': f'Transition de statut non autorisée: {current_status} -> {status}'})
                        
                        # Mettre à jour le statut
                        order['status'] = status
                        
                        # Ajouter les dates spécifiques selon le statut
                        current_date = datetime.now().strftime('%d/%m/%Y')
                        if status == 'processing' and 'processing_date' not in order:
                            order['processing_date'] = current_date
                        elif status == 'shipped' and 'shipping_date' not in order:
                            order['shipping_date'] = current_date
                        elif status == 'delivered' and 'delivery_date' not in order:
                            order['delivery_date'] = current_date
                        
                        # Ajouter les notes spécifiques livreur
                        if notes:
                            if 'livreur_notes' not in order:
                                order['livreur_notes'] = []
                            order['livreur_notes'].append({
                                'note': notes,
                                'livreur_email': session.get('admin_email'),
                                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                        
                        # Mettre à jour les informations de style pour le statut
                        order['status_color'] = status_colors.get(status, 'secondary')
                        order['status_text'] = status_texts.get(status, status)
                        order['payment_status'] = payment_status_mapping.get(status, 'pending')
                        
                        # Enregistrer la date de mise à jour et marquer comme mis à jour par livreur
                        order['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        order['livreur_updated'] = True
                        order['last_updated_by'] = 'livreur'
                        
                        # Mettre à jour la commande correspondante dans la base de données
                        customer_email = order.get('customer_email')
                        if customer_email:
                            # Convertir l'order_id_str en int pour la DB
                            order_id_int = int(order_id_str)
                            success, message = update_user_order_status(order_id_int, status)
                            if success:
                                print(f"✅ Commande {order_id_int} mise à jour en DB par livreur pour {customer_email}")
                            else:
                                print(f"⚠️ Erreur maj commande {order_id_int} en DB: {message}")
                                
                            # Envoyer email de notification au client
                            if status in ['shipped', 'delivered']:
                                try:
                                    order_data = get_user_order_by_id(customer_email, order_id_int)
                                    if order_data:
                                        send_order_status_email(customer_email, order_data, old_status, status)
                                        print(f"Email de notification envoyé à {customer_email} pour commande {order_id_str} (livreur)")
                                    else:
                                        print(f"⚠️ Commande {order_id_str} non trouvée pour email à {customer_email}")
                                except Exception as e:
                                    print(f"Erreur lors de l'envoi de l'email à {customer_email}: {str(e)}")
                        
                        order_updated = True
                        break
                if order_updated:
                    break
        
        # **NOUVELLE VERSION: Si pas trouvée dans les marchands, chercher dans la base de données admin**
        if not order_updated:
            from db_helpers import get_admin_order_by_id, update_admin_order_status
            
            # Chercher dans les commandes admin de la base de données
            admin_order = get_admin_order_by_id(order_id)
            if admin_order:
                
                # Vérifier que le statut actuel permet la transition
                current_status = admin_order.status
                
                # Logique de transition des statuts pour livreurs
                valid_transitions = {
                    'processing': ['shipped'],
                    'shipped': ['delivered']
                }
                
                if status != current_status and current_status in valid_transitions:
                    if status not in valid_transitions[current_status]:
                        return jsonify({'success': False, 'message': f'Transition de statut non autorisée: {current_status} -> {status}'})
                
                # Mettre à jour le statut dans la base de données
                status_text = status_texts.get(status, status)
                success, old_status = update_admin_order_status(order_id, status)
                
                if success:
                    
                    # **DÉSASSIGNATION AUTOMATIQUE: Si la commande admin est livrée, la désassigner du livreur**
                    if status == 'delivered':
                        unassign_success = unassign_order_from_livreur(order_id, 'admin', None)
                        if unassign_success:
                            print(f"✅ Commande admin {order_id} désassignée automatiquement après livraison (DB)")
                        else:
                            print(f"⚠️ Échec désassignation automatique commande admin {order_id}")
                    
                    # **GESTION DU STOCK POUR LES COMMANDES ADMIN LIVRÉES PAR LIVREUR**
                    if status == 'delivered' and admin_order.stock_reserved:
                        # Convertir les items pour la gestion du stock
                        reserved_items = []
                        for item in admin_order.items:
                            reserved_items.append({
                                'product_id': item.product_id,
                                'quantity': item.quantity,
                                'product_name': item.name
                            })
                        
                        print(f"Commande admin {order_id} livrée par livreur - Confirmation de la déduction du stock")
                        confirm_stock_deduction(reserved_items)
                        admin_order.stock_confirmed_at = datetime.now()
                        db.session.commit()
                    
                    order_updated = True
                else:
                    print(f"Échec de mise à jour du statut pour la commande admin {order_id}")
            else:
                print(f"Commande admin {order_id} non trouvée")
        
        if not order_updated:
            return jsonify({'success': False, 'message': 'Commande non trouvée'})
        
        # **NOUVELLE FONCTIONNALITÉ: Désassigner automatiquement la commande si elle est livrée**
        if status == 'delivered':
            try:
                order_id_int = int(order_id)
                # Déterminer le type de commande (merchant ou admin) et l'email du marchand
                is_merchant_order = False
                merchant_email_for_unassign = None
                
                # Vérifier si c'est une commande marchand
                for merchant_email, merchant in merchants_db.items():
                    for order in merchant.get('orders', []):
                        if order.get('id') == order_id_int:
                            is_merchant_order = True
                            merchant_email_for_unassign = merchant_email
                            break
                    if is_merchant_order:
                        break
                
                # Désassigner la commande
                order_type = 'merchant' if is_merchant_order else 'admin'
                unassign_success = unassign_order_from_livreur(order_id_int, order_type, merchant_email_for_unassign)
                
                if unassign_success:
                    print(f"Commande {order_id} désassignée automatiquement après livraison")
                else:
                    print(f"Impossible de désassigner la commande {order_id}")
                    
            except Exception as e:
                print(f"Erreur lors de la désassignation automatique: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Statut mis à jour avec succès par le livreur',
            'status': status,
            'status_text': status_texts.get(status, status),
            'status_color': status_colors.get(status, 'secondary')
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erreur serveur: {str(e)}'})

@app.route('/admin/merchants/<int:merchant_id>/verify', methods=['POST'])
@admin_required
def admin_verify_merchant(merchant_id):
    """Route pour vérifier un marchand"""
    try:
        # Récupérer le marchand depuis la base de données
        merchant_record = Merchant.query.get(merchant_id)
        
        if not merchant_record:
            flash('Marchand non trouvé', 'danger')
            return redirect(url_for('admin_merchants'))
        
        # Mettre à jour le statut de vérification dans la base de données
        merchant_record.store_verified = True
        db.session.commit()
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        if merchant_record.email in merchants_db:
            merchants_db[merchant_record.email]['store_verified'] = True
        
        flash(f"Le marchand {merchant_record.store_name} a été vérifié avec succès.", 'success')
        print(f"✅ Marchand {merchant_record.store_name} vérifié avec succès dans la base de données")
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la vérification du marchand: {str(e)}")
        flash('Erreur lors de la vérification du marchand', 'danger')
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))

@app.route('/admin/merchants/<int:merchant_id>/unverify', methods=['POST'])
@admin_required
def admin_unverify_merchant(merchant_id):
    """Route pour annuler la vérification d'un marchand"""
    try:
        # Récupérer le marchand depuis la base de données
        merchant_record = Merchant.query.get(merchant_id)
        
        if not merchant_record:
            flash('Marchand non trouvé', 'danger')
            return redirect(url_for('admin_merchants'))
        
        # Mettre à jour le statut de vérification dans la base de données
        merchant_record.store_verified = False
        db.session.commit()
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        if merchant_record.email in merchants_db:
            merchants_db[merchant_record.email]['store_verified'] = False
        
        flash(f"La vérification du marchand {merchant_record.store_name} a été annulée.", 'warning')
        print(f"⚠️ Vérification du marchand {merchant_record.store_name} annulée dans la base de données")
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de l'annulation de la vérification: {str(e)}")
        flash('Erreur lors de l\'annulation de la vérification', 'danger')
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))

@app.route('/admin/merchant/<int:merchant_id>/send_balance', methods=['POST'])
@admin_required
def admin_send_merchant_balance(merchant_id):
    """Route pour envoyer le solde disponible du marchand (retrait administratif) - Version base de données"""
    
    amount = request.form.get('amount', type=float)
    method = request.form.get('method', 'admin_payout').strip()
    reason = request.form.get('reason', '').strip()
    
    if not amount or amount <= 0:
        flash('Le montant doit être supérieur à 0 KMF', 'danger')
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
    
    if not reason:
        flash('La raison de l\'envoi est obligatoire', 'danger')
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
    
    # DATABASE-FIRST: Trouver le marchand dans la base de données
    merchant_record = Merchant.query.get(merchant_id)
    
    if not merchant_record:
        flash('Marchand non trouvé', 'danger')
        return redirect(url_for('admin_merchants'))
    
    merchant_email = merchant_record.email
    
    print(f"💰 Admin - Retrait administratif pour marchand ID {merchant_id}: {merchant_record.store_name} ({merchant_email})")
    
    # Vérifier le solde disponible du marchand
    balance_info = calculate_merchant_balance(merchant_email)
    available_balance = balance_info['available_balance']
    
    if amount > available_balance:
        flash(f'Montant trop élevé. Solde disponible du marchand: {available_balance:,.0f} KMF', 'danger')
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
    
    # Créer une demande de retrait automatique marquée comme "retrait admin"
    import uuid
    request_id = f"AR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    try:
        # DATABASE-FIRST: Créer la demande de retrait dans la base de données
        withdrawal_request = WithdrawalRequest(
            request_id=request_id,  # Utiliser request_id au lieu de id
            merchant_id=merchant_id,
            amount=float(amount),
            method=method,  # 'admin_payout' pour différencier
            status='completed',
            requested_at=datetime.now(),
            processed_at=datetime.now(),
            notes=f'Retrait administratif: {reason}',
            admin_notes=f'Versement effectué par {session.get("admin_email", "system")}',
            reference=f'ADMIN_PAYOUT_{request_id}'
            # Pas de withdrawal_type car ce champ n'existe pas dans le modèle
        )
        
        # Ajouter à la base de données
        db.session.add(withdrawal_request)
        db.session.commit()
        
        print(f"✅ Demande de retrait administratif créée dans la base de données: {request_id}")
        
        # COMPATIBILITÉ: Ajouter aussi à l'historique des dictionnaires pour fallback
        withdrawal_dict = {
            'id': request_id,
            'merchant_email': merchant_email,
            'amount': float(amount),
            'method': method,
            'status': 'completed',
            'requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'notes': f'Retrait administratif: {reason}',
            'admin_notes': f'Versement effectué par {session.get("admin_email", "system")}',
            'reference': f'ADMIN_PAYOUT_{request_id}',
            'type': 'admin_payout',
            'admin_email': session.get('admin_email', 'system')
        }
        
        if merchant_email not in withdrawal_requests_db:
            withdrawal_requests_db[merchant_email] = []
        
        withdrawal_requests_db[merchant_email].append(withdrawal_dict)
        
        flash(f'{amount:,.0f} KMF versés avec succès à {merchant_record.store_name} pour: {reason}', 'success')
        print(f"💰 ✅ Retrait administratif de {amount:,.0f} KMF effectué pour {merchant_record.store_name}")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors du retrait administratif: {e}")
        flash('Erreur lors du traitement du retrait administratif', 'danger')
    
    return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))

def delete_merchant_completely(merchant_id):
    """
    Supprime complètement un marchand et toutes ses données associées
    
    Args:
        merchant_id (int): ID du marchand à supprimer
    
    Returns:
        dict: Résultats de la suppression avec statistiques
    """
    deletion_stats = {
        'success': False,
        'merchant_deleted': False,
        'products_deleted': 0,
        'orders_deleted': 0,
        'reviews_deleted': 0,
        'withdrawals_deleted': 0,
        'cart_items_deleted': 0,
        'wishlist_items_deleted': 0,
        'order_items_deleted': 0,
        'errors': []
    }
    
    try:
        # Récupérer le marchand depuis la base de données
        merchant_record = Merchant.query.get(merchant_id)
        if not merchant_record:
            deletion_stats['errors'].append("Marchand non trouvé")
            return deletion_stats
        
        merchant_email = merchant_record.email
        store_name = merchant_record.store_name
        
        print(f"🗑️ Début de suppression complète du marchand: {store_name} ({merchant_email})")
        
        # Récupérer d'abord tous les IDs de produits du marchand
        product_ids = [p.id for p in Product.query.filter_by(merchant_id=merchant_id).all()]
        products_count = len(product_ids)
        
        print(f"📦 Produits à supprimer: {product_ids}")
        
        # Étape 1: Supprimer tous les OrderItems qui référencent les produits de ce marchand
        if product_ids:
            order_items_to_delete = OrderItem.query.filter(OrderItem.product_id.in_(product_ids)).all()
            for order_item in order_items_to_delete:
                print(f"🛒 Suppression OrderItem ID {order_item.id} (product_id: {order_item.product_id})")
                db.session.delete(order_item)
                deletion_stats['order_items_deleted'] += 1
            
            # Flush pour valider cette première étape
            db.session.flush()
            print(f"✅ {deletion_stats['order_items_deleted']} OrderItems supprimés")
        
        # Étape 2: Supprimer les avis des produits
        if product_ids:
            reviews_to_delete = Review.query.filter(Review.product_id.in_(product_ids)).all()
            for review in reviews_to_delete:
                db.session.delete(review)
                deletion_stats['reviews_deleted'] += 1
            print(f"✅ {deletion_stats['reviews_deleted']} avis supprimés")
        
        # Étape 3: Supprimer les items du panier
        if product_ids:
            cart_items_to_delete = CartItem.query.filter(CartItem.product_id.in_(product_ids)).all()
            for cart_item in cart_items_to_delete:
                db.session.delete(cart_item)
                deletion_stats['cart_items_deleted'] += 1
            print(f"✅ {deletion_stats['cart_items_deleted']} items panier supprimés")
        
        # Étape 4: Supprimer les items de la wishlist
        if product_ids:
            wishlist_items_to_delete = WishlistItem.query.filter(WishlistItem.product_id.in_(product_ids)).all()
            for wishlist_item in wishlist_items_to_delete:
                db.session.delete(wishlist_item)
                deletion_stats['wishlist_items_deleted'] += 1
            print(f"✅ {deletion_stats['wishlist_items_deleted']} items wishlist supprimés")
        
        # Étape 5: Maintenant supprimer les produits du marchand
        products_to_delete = Product.query.filter_by(merchant_id=merchant_id).all()
        for product in products_to_delete:
            db.session.delete(product)
        deletion_stats['products_deleted'] = len(products_to_delete)
        print(f"✅ {deletion_stats['products_deleted']} produits supprimés")
        
        # Étape 6: Supprimer les commandes vides du marchand (celles qui n'ont plus d'items)
        orders_to_delete = Order.query.filter_by(merchant_id=merchant_id).all()
        for order in orders_to_delete:
            # Vérifier s'il reste des items (il ne devrait plus y en avoir)
            remaining_items = OrderItem.query.filter_by(order_id=order.id).count()
            if remaining_items > 0:
                print(f"⚠️ Commande {order.id} a encore {remaining_items} items - suppression forcée")
                # Supprimer les items restants
                for item in OrderItem.query.filter_by(order_id=order.id).all():
                    db.session.delete(item)
            
            db.session.delete(order)
        deletion_stats['orders_deleted'] = len(orders_to_delete)
        print(f"✅ {deletion_stats['orders_deleted']} commandes supprimées")
        
        # Étape 7: Supprimer toutes les demandes de retrait du marchand
        withdrawals = WithdrawalRequest.query.filter_by(merchant_id=merchant_id).all()
        for withdrawal in withdrawals:
            db.session.delete(withdrawal)
        deletion_stats['withdrawals_deleted'] = len(withdrawals)
        print(f"✅ {deletion_stats['withdrawals_deleted']} demandes de retrait supprimées")
        
        # Étape 8: Supprimer le marchand lui-même
        db.session.delete(merchant_record)
        print(f"✅ Marchand {store_name} marqué pour suppression")
        
        # Étape 9: Commit final de toutes les suppressions
        db.session.commit()
        deletion_stats['merchant_deleted'] = True
        deletion_stats['success'] = True
        
        print(f"✅ Marchand {store_name} supprimé complètement:")
        print(f"   - Produits supprimés: {deletion_stats['products_deleted']}")
        print(f"   - Commandes supprimées: {deletion_stats['orders_deleted']}")
        print(f"   - OrderItems supprimés: {deletion_stats['order_items_deleted']}")
        print(f"   - Avis supprimés: {deletion_stats['reviews_deleted']}")
        print(f"   - Demandes de retrait supprimées: {deletion_stats['withdrawals_deleted']}")
        print(f"   - Items panier supprimés: {deletion_stats['cart_items_deleted']}")
        print(f"   - Items wishlist supprimés: {deletion_stats['wishlist_items_deleted']}")
        
        # 10. Nettoyer aussi les dictionnaires en mémoire (pour compatibilité)
        if merchant_email in merchants_db:
            del merchants_db[merchant_email]
        
        if merchant_email in withdrawal_requests_db:
            del withdrawal_requests_db[merchant_email]
        
        # Nettoyer les assignations de livreur
        for livreur_email, assignments in livreur_assignments_db.items():
            livreur_assignments_db[livreur_email] = [
                assignment for assignment in assignments 
                if not (assignment.get('order_type') == 'merchant' and 
                       assignment.get('merchant_email') == merchant_email)
            ]
        
        print(f"🧹 Nettoyage des dictionnaires en mémoire terminé")
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erreur lors de la suppression: {str(e)}"
        deletion_stats['errors'].append(error_msg)
        print(f"❌ {error_msg}")
    
    return deletion_stats

@app.route('/admin/merchants/<int:merchant_id>/delete', methods=['POST'])
@permission_required(['super_admin', 'admin'])
def admin_delete_merchant(merchant_id):
    """Route pour supprimer complètement un marchand et toutes ses données"""
    
    # Vérifications de sécurité
    confirmation = request.form.get('confirmation', '').strip()
    if confirmation != 'SUPPRIMER':
        flash('Vous devez taper "SUPPRIMER" pour confirmer la suppression', 'danger')
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))
    
    # Récupérer les informations du marchand avant suppression
    merchant_record = Merchant.query.get(merchant_id)
    if not merchant_record:
        flash('Marchand non trouvé', 'danger')
        return redirect(url_for('admin_merchants'))
    
    store_name = merchant_record.store_name
    merchant_email = merchant_record.email
    
    # Effectuer la suppression complète
    deletion_result = delete_merchant_completely(merchant_id)
    
    if deletion_result['success']:
        flash(f'Marchand "{store_name}" supprimé avec succès. '
              f'Produits supprimés: {deletion_result["products_deleted"]}, '
              f'Commandes supprimées: {deletion_result["orders_deleted"]}', 'success')
        
        # Log pour audit
        print(f"🗑️ SUPPRESSION MARCHAND par {session.get('admin_email', 'unknown')}: "
              f"{store_name} ({merchant_email}) - "
              f"Produits: {deletion_result['products_deleted']}, "
              f"Commandes: {deletion_result['orders_deleted']}")
        
        return redirect(url_for('admin_merchants'))
    else:
        error_messages = '; '.join(deletion_result['errors'])
        flash(f'Erreur lors de la suppression: {error_messages}', 'danger')
        return redirect(url_for('admin_merchant_detail', merchant_id=merchant_id))

@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    """Page d'édition d'un produit côté admin"""
    
    # Récupérer le produit depuis la base de données
    product_record = Product.query.get(product_id)
    
    if not product_record:
        flash('Produit non trouvé', 'danger')
        return redirect(url_for('admin_admin_products'))
    
    if request.method == 'POST':
        try:
            # Mettre à jour les informations dans la base de données
            product_record.name = request.form.get('name', product_record.name)
            product_record.description = request.form.get('description', product_record.description)
            product_record.price = float(request.form.get('price', product_record.price))
            product_record.stock = int(request.form.get('stock', product_record.stock))
            
            # Gestion des catégories
            category_id = request.form.get('category_id')
            if category_id:
                product_record.category_id = int(category_id)
            
            subcategory_id = request.form.get('subcategory_id')
            if subcategory_id:
                product_record.subcategory_id = int(subcategory_id)
            else:
                product_record.subcategory_id = None
            
            product_record.status = request.form.get('status', product_record.status)
            product_record.updated_at = datetime.now()
            
            # Gestion des images (URLs)
            image_urls = request.form.getlist('image_url[]')
            valid_image_urls = [url.strip() for url in image_urls if url.strip()]
            
            if valid_image_urls:
                product_record.main_image = valid_image_urls[0]
                product_record.images = json.dumps(valid_image_urls)
            
            db.session.commit()
            print(f"✅ Produit ID {product_id} mis à jour dans la base de données")
            
            # Si c'est un produit marchand, mettre à jour aussi dans le dictionnaire en mémoire
            if product_record.merchant_id:
                merchant_record = Merchant.query.get(product_record.merchant_id)
                if merchant_record and merchant_record.email in merchants_db:
                    # Mettre à jour le produit dans le dictionnaire du marchand
                    merchant_products = merchants_db[merchant_record.email].get('products', [])
                    for i, merchant_product in enumerate(merchant_products):
                        if merchant_product.get('id') == product_id:
                            # Mettre à jour avec les nouvelles données
                            merchants_db[merchant_record.email]['products'][i].update({
                                'name': product_record.name,
                                'description': product_record.description,
                                'price': product_record.price,
                                'stock': product_record.stock,
                                'category_id': product_record.category_id,
                                'subcategory_id': product_record.subcategory_id,
                                'status': product_record.status,
                                'updated_at': product_record.updated_at.strftime('%Y-%m-%d') if product_record.updated_at else None
                            })
                            print(f"✅ Produit mis à jour dans le dictionnaire marchand {merchant_record.email}")
                            break
            
            flash('Produit mis à jour avec succès.', 'success')
            
        except ValueError as e:
            db.session.rollback()
            flash('Erreur: Le prix et le stock doivent être des nombres valides.', 'danger')
            print(f"❌ Erreur de validation: {str(e)}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la mise à jour du produit: {str(e)}")
            flash(f'Erreur lors de la mise à jour du produit: {str(e)}', 'danger')
        
        return redirect(url_for('admin_admin_products'))
    
    # Convertir le produit en dictionnaire pour le template
    product = product_record.to_dict()
    
    # Préparer les catégories avec leurs sous-catégories pour le template
    categories_list = get_categories_with_subcategories()
    
    return render_template('admin/product_edit.html', product=product, categories=categories_list)

@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    """Supprimer un produit côté admin"""
    
    # Récupérer le produit depuis la base de données
    product_record = Product.query.get(product_id)
    
    if not product_record:
        flash('Produit non trouvé', 'danger')
        return redirect(url_for('admin_admin_products'))
    
    try:
        # Vérifier si le produit est référencé dans des commandes
        order_items = OrderItem.query.filter_by(product_id=product_id).all()
        
        if order_items:
            # Le produit est référencé dans des commandes, ne pas le supprimer
            orders_count = len(set(item.order_id for item in order_items))
            flash(f'Impossible de supprimer ce produit car il est référencé dans {orders_count} commande(s). '
                  f'Vous pouvez le désactiver en changeant son statut à "inactif".', 'warning')
            return redirect(url_for('admin_admin_products'))
        
        # Si c'est un produit marchand, le supprimer aussi du dictionnaire en mémoire
        if product_record.merchant_id:
            merchant_record = Merchant.query.get(product_record.merchant_id)
            if merchant_record and merchant_record.email in merchants_db:
                # Supprimer du dictionnaire du marchand
                merchant_products = merchants_db[merchant_record.email].get('products', [])
                merchants_db[merchant_record.email]['products'] = [
                    p for p in merchant_products if p.get('id') != product_id
                ]
                print(f"✅ Produit supprimé du dictionnaire marchand {merchant_record.email}")
        
        # Supprimer de la base de données
        db.session.delete(product_record)
        db.session.commit()
        print(f"✅ Produit ID {product_id} supprimé de la base de données")
        
        flash('Produit supprimé avec succès.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la suppression du produit: {str(e)}")
        flash(f'Erreur lors de la suppression du produit: {str(e)}', 'danger')
    
    return redirect(url_for('admin_admin_products'))

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_product_add():
    """Page d'ajout d'un nouveau produit par l'admin"""
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        price = request.form.get('price', 0)
        stock = request.form.get('stock', 0)
        status = request.form.get('status', 'active')
        
        # Gestion sécurisée des IDs de catégories
        try:
            category_id = int(request.form.get('category_id', 0) or 0)
            subcategory_id = int(request.form.get('subcategory_id', 0) or 0)
        except ValueError:
            categories_list = get_categories_with_subcategories()
            flash('Veuillez sélectionner une catégorie et une sous-catégorie valides.', 'danger')
            return render_template('admin/product_add.html', categories=categories_list)
        
        # Validation de base
        if not name or not description:
            categories_list = get_categories_with_subcategories()
            flash('Le nom et la description du produit sont obligatoires.', 'danger')
            return render_template('admin/product_add.html', categories=categories_list)
        
        try:
            price = int(float(price))
            stock = int(stock)
        except ValueError:
            categories_list = get_categories_with_subcategories()
            flash('Le prix et le stock doivent être des nombres.', 'danger')
            return render_template('admin/product_add.html', categories=categories_list)
        
        # Traitement des URLs d'images
        image_urls = request.form.getlist('image_url[]')
        valid_image_urls = [url.strip() for url in image_urls if url.strip()]
        
        if not valid_image_urls:
            categories_list = get_categories_with_subcategories()
            flash('Au moins une URL d\'image est requise.', 'danger')
            return render_template('admin/product_add.html', categories=categories_list)
        
        main_image = valid_image_urls[0]
        
        # Traitement des options du produit
        # Couleurs
        colors = []
        color_names = request.form.getlist('color_name[]')
        color_hex_codes = request.form.getlist('color_hex[]')  # Utiliser color_hex[] comme dans le template
        
        print(f"DEBUG Admin - Couleurs reçues: {color_names}")
        print(f"DEBUG Admin - Codes couleur reçus: {color_hex_codes}")
        
        for i in range(len(color_names)):
            if color_names[i] and color_names[i].strip():  # Vérifier que le nom n'est pas vide
                color_entry = {
                    'name': color_names[i].strip(),
                    'value': color_names[i].strip(),  # Garder le nom original pour la correspondance des prix
                    'hex': color_hex_codes[i] if i < len(color_hex_codes) else '#000000'
                }
                colors.append(color_entry)
                print(f"DEBUG Admin - Couleur ajoutée: {color_entry}")
        
        # Tailles
        sizes = []
        size_values = request.form.getlist('size_value[]')
        
        print(f"DEBUG Admin - Tailles reçues: {size_values}")
        
        for i in range(len(size_values)):
            if size_values[i] and size_values[i].strip():  # Vérifier que la valeur n'est pas vide
                size_entry = {
                    'value': size_values[i].strip(),
                    'label': size_values[i].strip()  # Utiliser la valeur comme label aussi
                }
                sizes.append(size_entry)
                print(f"DEBUG Admin - Taille ajoutée: {size_entry}")
        
        # Spécifications techniques
        specifications = {}
        spec_names = request.form.getlist('spec_name[]')
        spec_values = request.form.getlist('spec_value[]')
        
        for i in range(len(spec_names)):
            if spec_names[i] and i < len(spec_values) and spec_values[i]:
                specifications[spec_names[i]] = spec_values[i]
        
        # Combinaisons de prix
        price_combinations = []
        combination_colors = request.form.getlist('combination_color[]')
        combination_sizes = request.form.getlist('combination_size[]')
        combination_prices = request.form.getlist('combination_price[]')
        
        print("="*50)
        print("DEBUG COMBINAISONS PRIX - DONNÉES BRUTES REÇUES")
        print("="*50)
        print(f"Tous les champs du formulaire: {dict(request.form)}")
        print(f"Combinaisons couleurs brutes: {combination_colors}")
        print(f"Combinaisons tailles brutes: {combination_sizes}")
        print(f"Combinaisons prix brutes: {combination_prices}")
        print(f"Nombre de combinaisons trouvées: {len(combination_colors)}")
        print(f"Longueur des listes:")
        print(f"  - combination_colors: {len(combination_colors)}")
        print(f"  - combination_sizes: {len(combination_sizes)}")
        print(f"  - combination_prices: {len(combination_prices)}")
        
        # Vérifier tous les champs qui commencent par "combination_"
        combination_fields = {k: v for k, v in request.form.items() if k.startswith('combination_')}
        print(f"Tous les champs combination_*: {combination_fields}")
        print("="*50)
        
        for i in range(len(combination_colors)):
            print(f"DEBUG Admin - Traitement combinaison {i + 1}:")
            print(f"  - Couleur brute: '{combination_colors[i]}'")
            print(f"  - Taille brute: '{combination_sizes[i] if i < len(combination_sizes) else 'N/A'}'")
            print(f"  - Prix brut: '{combination_prices[i] if i < len(combination_prices) else 'N/A'}'")
            
            # Vérifier si on a un prix valide ET au moins une couleur OU une taille
            has_valid_price = i < len(combination_prices) and combination_prices[i] and combination_prices[i].strip()
            has_color = combination_colors[i] and combination_colors[i] != "Toutes les couleurs" and combination_colors[i].strip()
            has_size = (i < len(combination_sizes) and 
                       combination_sizes[i] and 
                       combination_sizes[i] != "Toutes les tailles" and 
                       combination_sizes[i].strip())
            
            print(f"  - Prix valide: {has_valid_price}")
            print(f"  - Couleur valide: {has_color}")
            print(f"  - Taille valide: {has_size}")
            
            if has_valid_price and (has_color or has_size):
                try:
                    combination_price = int(float(combination_prices[i]))
                    combination_data = {
                        'price': combination_price
                    }
                    
                    # Ajouter la couleur si elle est valide
                    if has_color:
                        combination_data['color'] = combination_colors[i].strip()
                        print(f"  - Couleur ajoutée: '{combination_data['color']}'")
                    
                    # Ajouter la taille si elle est valide
                    if has_size:
                        combination_data['size'] = combination_sizes[i].strip()
                        print(f"  - Taille ajoutée: '{combination_data['size']}'")
                    
                    print(f"DEBUG Admin - Combinaison créée finale: {combination_data}")
                    price_combinations.append(combination_data)
                except ValueError:
                    print(f"DEBUG Admin - Prix invalide ignoré: {combination_prices[i]}")
                    continue  # Ignorer les prix invalides
            else:
                print(f"  - Combinaison ignorée - Raisons:")
                print(f"    * Prix manquant/invalide: {not has_valid_price}")
                print(f"    * Ni couleur ni taille valide: {not (has_color or has_size)}")
        
        try:
            # Sauvegarder le produit dans la base de données
            product_record = Product(
                name=name,
                description=description,
                price=price,
                stock=stock,
                category_id=category_id if category_id > 0 else None,
                subcategory_id=subcategory_id if subcategory_id > 0 else None,
                image=main_image,  # Corriger le nom du champ
                images=json.dumps(valid_image_urls) if valid_image_urls else None,
                status=status,
                merchant_id=None,  # Produit admin - pas de marchand
                colors=json.dumps(colors) if colors else None,
                sizes=json.dumps(sizes) if sizes else None,
                specifications=json.dumps(specifications) if specifications else None,
                price_combinations=json.dumps(price_combinations) if price_combinations else None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.session.add(product_record)
            db.session.commit()
            
            # Récupérer l'ID généré par la base de données
            product_id = product_record.id
            
            print(f"✅ Produit admin ID {product_id} sauvegardé dans la base de données")
            print(f"DEBUG Admin - Produit créé avec les données suivantes:")
            print(f"  - ID: {product_id}")
            print(f"  - Nom: {name}")
            print(f"  - Couleurs finales: {colors}")
            print(f"  - Tailles finales: {sizes}")
            print(f"  - Combinaisons prix finales: {price_combinations}")
            print(f"  - Nombre de combinaisons: {len(price_combinations)}")
            
            # Vérification de cohérence : toutes les couleurs/tailles des combinaisons existent-elles ?
            color_values = [c['value'] for c in colors]
            size_values = [s['value'] for s in sizes]
            
            for i, combo in enumerate(price_combinations):
                print(f"  - Vérification combinaison {i + 1}: {combo}")
                if 'color' in combo and combo['color'] not in color_values:
                    print(f"    ⚠️  ATTENTION: Couleur '{combo['color']}' non trouvée dans les couleurs définies: {color_values}")
                if 'size' in combo and combo['size'] not in size_values:
                    print(f"    ⚠️  ATTENTION: Taille '{combo['size']}' non trouvée dans les tailles définies: {size_values}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la sauvegarde du produit admin: {str(e)}")
            flash(f'Erreur lors de la création du produit: {str(e)}', 'danger')
            return redirect(url_for('admin_product_add'))
        
        flash(f'Produit "{name}" ajouté avec succès.', 'success')
        return redirect(url_for('admin_admin_products'))
    
    # Préparer les catégories avec leurs sous-catégories pour le template
    categories_list = get_categories_with_subcategories()
    
    return render_template('admin/product_add.html', categories=categories_list)

def get_active_subcategories():
    """Retourne uniquement les sous-catégories actives"""
    return {sub_id: sub for sub_id, sub in admin_subcategories_db.items() if sub.get('active', True)}

def get_subcategories_by_category(category_id):
    """Retourne les sous-catégories actives d'une catégorie donnée"""
    return {sub_id: sub for sub_id, sub in admin_subcategories_db.items() 
            if sub.get('category_id') == category_id and sub.get('active', True)}

@app.route('/admin/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    """Page d'administration pour la gestion des catégories"""
    
    if request.method == 'POST':
        # Traiter l'ajout d'une nouvelle catégorie
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-tag').strip()
        
        # Validation
        if not name:
            flash('Le nom de la catégorie est obligatoire.', 'danger')
            return redirect(url_for('admin_categories'))
        
        if not description:
            flash('La description de la catégorie est obligatoire.', 'danger')
            return redirect(url_for('admin_categories'))
        
        # Vérifier si le nom existe déjà dans la base de données
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category:
            flash('Une catégorie avec ce nom existe déjà.', 'danger')
            return redirect(url_for('admin_categories'))
        
        try:
            # Créer la nouvelle catégorie dans la base de données
            new_category = Category(
                name=name,
                description=description,
                icon=icon,
                active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.session.add(new_category)
            db.session.commit()
            
            # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
            admin_categories_db[new_category.id] = new_category.to_dict()
            
            print(f"✅ Catégorie '{name}' créée avec ID {new_category.id} dans la base de données")
            flash(f'Catégorie "{name}" ajoutée avec succès.', 'success')
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la création de la catégorie: {str(e)}")
            flash(f'Erreur lors de la création de la catégorie: {str(e)}', 'danger')
        
        return redirect(url_for('admin_categories'))
    
    # **NOUVELLE VERSION: Récupérer les catégories depuis la base de données**
    categories_records = Category.query.order_by(Category.created_at.desc()).all()
    categories_list = []
    
    # Compter le nombre de produits par catégorie
    all_products = get_all_products()
    
    for category_record in categories_records:
        category_dict = category_record.to_dict()
        
        # Compter les produits dans cette catégorie
        category_dict['products_count'] = len([p for p in all_products if p.get('category_id') == category_record.id])
        
        # Compter le nombre de sous-catégories
        category_dict['subcategories_count'] = len([
            sub for sub in admin_subcategories_db.values() 
            if sub.get('category_id') == category_record.id
        ])
        
        categories_list.append(category_dict)
    
    # Statistiques générales
    stats = {
        'total_categories': len(categories_list),
        'active_categories': len([c for c in categories_list if c['active']]),
        'total_products': len(all_products),
        'products_with_category': len([p for p in all_products if p.get('category_id')])
    }
    
    return render_template('admin/categories.html', 
                          categories=categories_list,
                          stats=stats)

@app.route('/admin/categories/<int:category_id>')
@admin_required
def admin_category_detail(category_id):
    """Page de détail d'une catégorie spécifique"""
    
    # **NOUVELLE VERSION: Récupérer la catégorie depuis la base de données**
    category_record = Category.query.get(category_id)
    
    if not category_record:
        flash('Catégorie non trouvée', 'danger')
        return redirect(url_for('admin_categories'))
    
    category = category_record.to_dict()
    
    # Récupérer tous les produits de cette catégorie
    all_products = get_all_products()
    print(f"Total produits disponibles: {len(all_products)}")
    category_products = [p for p in all_products if p.get('category_id') == category_id]
    print(f"Produits trouvés pour catégorie {category_id}: {len(category_products)}")
    
    # Debug: afficher les IDs de catégories trouvés
    category_ids_found = list(set([p.get('category_id') for p in all_products if p.get('category_id')]))
    print(f"IDs de catégories trouvés dans les produits: {category_ids_found}")
    
    # Enrichir les produits avec les informations marchands
    for product in category_products:
        if product.get('source') == 'merchant' and product.get('merchant_email'):
            merchant_email = product['merchant_email']
            merchant = merchants_db.get(merchant_email, {})
            product['merchant_name'] = merchant.get('store_name', 'Marchand inconnu')
            product['merchant_verified'] = merchant.get('store_verified', False)
        else:
            product['merchant_name'] = 'DOUKA KM (Admin)'
            product['merchant_verified'] = True
    
    # Trier les produits par date de création (plus récents en premier)
    category_products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Statistiques de la catégorie
    category_stats = {
        'total_products': len(category_products),
        'admin_products': len([p for p in category_products if p.get('source') != 'merchant']),
        'merchant_products': len([p for p in category_products if p.get('source') == 'merchant']),
        'active_products': len([p for p in category_products if p.get('status') == 'active']),
        'average_price': sum(p.get('price', 0) for p in category_products) / len(category_products) if category_products else 0
    }
    
    return render_template('admin/category_detail.html', 
                          category=category,
                          products=category_products,
                          stats=category_stats)

@app.route('/admin/categories/<int:category_id>/edit', methods=['POST'])
@admin_required
def admin_category_edit(category_id):
    """Modifier une catégorie"""
    
    # **NOUVELLE VERSION: Vérifier dans la base de données**
    category_record = Category.query.get(category_id)
    
    if not category_record:
        return jsonify({'success': False, 'message': 'Catégorie non trouvée'})
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', '').strip()
        active = request.form.get('active') == 'true'
        
        # Validation
        if not name:
            return jsonify({'success': False, 'message': 'Le nom de la catégorie est obligatoire'})
        
        if not description:
            return jsonify({'success': False, 'message': 'La description de la catégorie est obligatoire'})
        
        # Vérifier si le nom existe déjà (sauf pour la catégorie actuelle)
        existing_category = Category.query.filter(
            Category.name.ilike(name),
            Category.id != category_id
        ).first()
        
        if existing_category:
            return jsonify({'success': False, 'message': 'Une catégorie avec ce nom existe déjà'})
        
        # Mettre à jour dans la base de données SQLite
        category_record.name = name
        category_record.description = description
        category_record.icon = icon
        category_record.active = active
        category_record.updated_at = datetime.now()
        db.session.commit()
        print(f"✅ Catégorie ID {category_id} mise à jour dans la base de données")
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        if category_id in admin_categories_db:
            admin_categories_db[category_id].update({
                'name': name,
                'description': description,
                'icon': icon,
                'active': active,
                'updated_at': category_record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if category_record.updated_at else None
            })
        else:
            # Si la catégorie n'existe pas dans le dictionnaire, l'ajouter
            admin_categories_db[category_id] = category_record.to_dict()
        
        return jsonify({'success': True, 'message': f'Catégorie "{name}" mise à jour avec succès'})
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la mise à jour de la catégorie: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de la mise à jour: {str(e)}'})

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def admin_category_delete(category_id):
    """Supprimer une catégorie"""
    
    # **NOUVELLE VERSION: Vérifier dans la base de données**
    category_record = Category.query.get(category_id)
    
    if not category_record:
        return jsonify({'success': False, 'message': 'Catégorie non trouvée'})
    
    try:
        # Vérifier s'il y a des produits dans cette catégorie
        all_products = get_all_products()
        products_in_category = [p for p in all_products if p.get('category_id') == category_id]
        
        if products_in_category:
            return jsonify({
                'success': False, 
                'message': f'Impossible de supprimer cette catégorie car elle contient {len(products_in_category)} produit(s). Veuillez d\'abord déplacer ou supprimer ces produits.'
            })
        
        # Supprimer de la base de données SQLite
        category_name = category_record.name
        db.session.delete(category_record)
        db.session.commit()
        print(f"✅ Catégorie ID {category_id} supprimée de la base de données")
        
        # Supprimer aussi du dictionnaire en mémoire pour compatibilité
        if category_id in admin_categories_db:
            del admin_categories_db[category_id]
        
        return jsonify({'success': True, 'message': f'Catégorie "{category_name}" supprimée avec succès'})
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la suppression de la catégorie: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'})

@app.route('/admin/categories/<int:category_id>/toggle-status', methods=['POST'])
@admin_required
def admin_category_toggle_status(category_id):
    """Activer/désactiver une catégorie"""
    
    # **NOUVELLE VERSION: Vérifier dans la base de données**
    category_record = Category.query.get(category_id)
    
    if not category_record:
        return jsonify({'success': False, 'message': 'Catégorie non trouvée'})
    
    try:
        # Basculer le statut active
        current_status = category_record.active
        new_status = not current_status
        
        # Mettre à jour dans la base de données SQLite
        category_record.active = new_status
        category_record.updated_at = datetime.now()
        db.session.commit()
        print(f"✅ Statut de la catégorie ID {category_id} mis à jour dans la base de données: {new_status}")
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        if category_id in admin_categories_db:
            admin_categories_db[category_id]['active'] = new_status
            admin_categories_db[category_id]['updated_at'] = category_record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if category_record.updated_at else None
        else:
            # Si la catégorie n'existe pas dans le dictionnaire, l'ajouter
            admin_categories_db[category_id] = category_record.to_dict()
        
        category_name = category_record.name
        status_text = 'activée' if new_status else 'désactivée'
        
        # Si on désactive la catégorie, vérifier s'il y a des produits
        if not new_status:
            all_products = get_all_products()
            products_in_category = [p for p in all_products if p.get('category_id') == category_id]
            
            if products_in_category:
                return jsonify({
                    'success': True, 
                    'message': f'Catégorie "{category_name}" {status_text}. Attention: {len(products_in_category)} produit(s) dans cette catégorie ne seront plus visibles publiquement.',
                    'status': new_status,
                    'status_text': 'Activé' if new_status else 'Désactivé',
                    'status_class': 'success' if new_status else 'danger',
                    'button_text': 'Désactiver' if new_status else 'Activer',
                    'button_class': 'btn-warning' if new_status else 'btn-success',
                    'products_warning': True,
                    'products_count': len(products_in_category)
                })
        
        return jsonify({
            'success': True, 
            'message': f'Catégorie "{category_name}" {status_text} avec succès.',
            'status': new_status,
            'status_text': 'Activé' if new_status else 'Désactivé',
            'status_class': 'success' if new_status else 'danger',
            'button_text': 'Désactiver' if new_status else 'Activer',
            'button_class': 'btn-warning' if new_status else 'btn-success',
            'products_warning': False
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors du changement de statut de la catégorie: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors du changement de statut: {str(e)}'})

@app.route('/admin/subcategories')
@admin_required
def admin_subcategories():
    """Page d'administration pour la gestion des sous-catégories"""
    
    # Récupérer toutes les sous-catégories directement depuis la base de données
    try:
        from db_helpers import get_all_subcategories_safe, get_all_categories_safe
        subcategories_list = get_all_subcategories_safe()
        categories_list = get_all_categories_safe()
        
        # Convertir en dictionnaires pour compatibilité
        subcategories = {}
        for subcat in subcategories_list:
            subcategories[subcat.id] = subcat.to_dict()
            
        categories_dict = {}
        for cat in categories_list:
            categories_dict[cat.id] = cat.to_dict()
            
        print(f"🔍 DEBUG: Trouvé {len(subcategories)} sous-catégories en base de données")
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des sous-catégories: {e}")
        # Fallback vers le dictionnaire en mémoire
        subcategories = admin_subcategories_db.copy()
        categories_dict = admin_categories_db.copy()
    
    # Enrichir avec les noms de catégories parentes
    for subcategory in subcategories.values():
        category_id = subcategory.get('category_id')
        if category_id in categories_dict:
            subcategory['category_name'] = categories_dict[category_id]['name']
        else:
            subcategory['category_name'] = 'Catégorie inconnue'
    
    # Compter le nombre de produits par sous-catégorie
    all_products = get_all_products()
    for subcategory in subcategories.values():
        subcategory['products_count'] = len([p for p in all_products if p.get('subcategory_id') == subcategory['id']])
    
    # Grouper les sous-catégories par catégorie
    categories_with_subcategories = {}
    
    for category_id, category in categories_dict.items():
        # Récupérer les sous-catégories de cette catégorie
        category_subcategories = [
            sub for sub in subcategories.values() 
            if sub.get('category_id') == category_id
        ]
        
        # Trier les sous-catégories par nom
        category_subcategories.sort(key=lambda x: x.get('name', ''))
        
        if category_subcategories:  # Seulement inclure les catégories qui ont des sous-catégories
            categories_with_subcategories[category_id] = {
                'category': category,
                'subcategories': category_subcategories,
                'subcategories_count': len(category_subcategories),
                'active_subcategories_count': len([s for s in category_subcategories if s.get('active', True)])
            }
    
    # Convertir en liste pour le template, triée par nom de catégorie
    categories_grouped = sorted(
        categories_with_subcategories.values(),
        key=lambda x: x['category']['name']
    )
    
    # Préparer les catégories pour le formulaire d'ajout
    categories_for_form = [
        {'id': cat_id, 'name': cat['name']} 
        for cat_id, cat in admin_categories_db.items() 
        if cat.get('active', True)
    ]
    
    # Statistiques générales
    total_subcategories = len(subcategories)
    stats = {
        'total_subcategories': total_subcategories,
        'active_subcategories': len([s for s in subcategories.values() if s['active']]),
        'total_products': len(all_products),
        'products_with_subcategory': len([p for p in all_products if p.get('subcategory_id')]),
        'categories_with_subcategories': len(categories_grouped)
    }
    
    return render_template('admin/subcategories.html', 
                          categories_grouped=categories_grouped,
                          categories=categories_for_form,
                          stats=stats)

@app.route('/admin/subcategories/add', methods=['POST'])
@admin_required
def admin_subcategory_add():
    """Ajouter une nouvelle sous-catégorie"""
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category_id = int(request.form.get('category_id', 0))
        
        # Validation
        if not name:
            return jsonify({'success': False, 'message': 'Le nom de la sous-catégorie est obligatoire'})
        
        if not description:
            return jsonify({'success': False, 'message': 'La description de la sous-catégorie est obligatoire'})
        
        if category_id not in admin_categories_db:
            return jsonify({'success': False, 'message': 'Catégorie parente invalide'})
        
        # Vérifier si le nom existe déjà dans la même catégorie
        for subcat in admin_subcategories_db.values():
            if (subcat['name'].lower() == name.lower() and 
                subcat['category_id'] == category_id):
                return jsonify({'success': False, 'message': f'Une sous-catégorie "{name}" existe déjà dans cette catégorie'})
        
        # Générer un nouvel ID
        new_id = max(admin_subcategories_db.keys()) + 1 if admin_subcategories_db else 1
        
        # Créer dans la base de données SQLite
        new_subcategory_record = Subcategory(
            name=name,
            description=description,
            category_id=category_id,
            active=True
        )
        db.session.add(new_subcategory_record)
        db.session.commit()
        
        # Utiliser l'ID généré par la base de données
        new_id = new_subcategory_record.id
        print(f"✅ Sous-catégorie ID {new_id} ajoutée à la base de données")
        
        # Créer la nouvelle sous-catégorie pour le dictionnaire en mémoire
        new_subcategory = {
            'id': new_id,
            'name': name,
            'description': description,
            'category_id': category_id,
            'active': True,
            'created_at': datetime.now().strftime('%Y-%m-%d'),
            'created_by': session.get('admin_email', 'admin')
        }
        
        # Ajouter au dictionnaire en mémoire
        admin_subcategories_db[new_id] = new_subcategory
        
        # Récupérer le nom de la catégorie parente pour la réponse
        category_name = admin_categories_db[category_id]['name']
        
        return jsonify({
            'success': True, 
            'message': f'Sous-catégorie "{name}" ajoutée avec succès dans "{category_name}"',
            'subcategory': {
                'id': new_id,
                'name': name,
                'description': description,
                'category_name': category_name,
                'active': True,
                'products_count': 0
            }
        })
        
    except ValueError:
        return jsonify({'success': False, 'message': 'ID de catégorie invalide'})
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de l'ajout de la sous-catégorie: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de l\'ajout: {str(e)}'})

@app.route('/admin/subcategories/<int:subcategory_id>/edit', methods=['POST'])
@admin_required
def admin_subcategory_edit(subcategory_id):
    """Modifier une sous-catégorie"""
    
    if subcategory_id not in admin_subcategories_db:
        return jsonify({'success': False, 'message': 'Sous-catégorie non trouvée'})
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category_id = int(request.form.get('category_id', 0))
        active = request.form.get('active') == 'true'
        
        # Validation
        if not name:
            return jsonify({'success': False, 'message': 'Le nom de la sous-catégorie est obligatoire'})
        
        if not description:
            return jsonify({'success': False, 'message': 'La description de la sous-catégorie est obligatoire'})
        
        if category_id not in admin_categories_db:
            return jsonify({'success': False, 'message': 'Catégorie parente invalide'})
        
        # Vérifier si le nom existe déjà dans la même catégorie (sauf pour la sous-catégorie actuelle)
        for sub_id, subcat in admin_subcategories_db.items():
            if (sub_id != subcategory_id and 
                subcat['name'].lower() == name.lower() and 
                subcat['category_id'] == category_id):
                return jsonify({'success': False, 'message': f'Une sous-catégorie "{name}" existe déjà dans cette catégorie'})
        
        # Mettre à jour dans la base de données SQLite
        subcategory_record = Subcategory.query.filter_by(id=subcategory_id).first()
        if subcategory_record:
            subcategory_record.name = name
            subcategory_record.description = description
            subcategory_record.category_id = category_id
            subcategory_record.active = active
            subcategory_record.updated_at = datetime.now()
            db.session.commit()
            print(f"✅ Sous-catégorie ID {subcategory_id} mise à jour dans la base de données")
        
        # Mettre à jour le dictionnaire en mémoire
        admin_subcategories_db[subcategory_id].update({
            'name': name,
            'description': description,
            'category_id': category_id,
            'active': active,
            'updated_at': datetime.now().strftime('%Y-%m-%d'),
            'updated_by': session.get('admin_email', 'admin')
        })
        
        return jsonify({'success': True, 'message': f'Sous-catégorie "{name}" mise à jour avec succès'})
        
    except ValueError:
        return jsonify({'success': False, 'message': 'ID de catégorie invalide'})
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la mise à jour de la sous-catégorie: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de la mise à jour: {str(e)}'})

@app.route('/admin/subcategories/<int:subcategory_id>/delete', methods=['POST'])
@admin_required
def admin_subcategory_delete(subcategory_id):
    """Supprimer une sous-catégorie"""
    
    if subcategory_id not in admin_subcategories_db:
        return jsonify({'success': False, 'message': 'Sous-catégorie non trouvée'})
    
    try:
        # Vérifier s'il y a des produits dans cette sous-catégorie
        all_products = get_all_products()
        products_in_subcategory = [p for p in all_products if p.get('subcategory_id') == subcategory_id]
        
        if products_in_subcategory:
            return jsonify({
                'success': False, 
                'message': f'Impossible de supprimer cette sous-catégorie car elle contient {len(products_in_subcategory)} produit(s). Veuillez d\'abord déplacer ou supprimer ces produits.'
            })
        
        # Supprimer de la base de données SQLite
        subcategory_record = Subcategory.query.filter_by(id=subcategory_id).first()
        if subcategory_record:
            db.session.delete(subcategory_record)
            db.session.commit()
            print(f"✅ Sous-catégorie ID {subcategory_id} supprimée de la base de données")
        
        # Supprimer du dictionnaire en mémoire
        subcategory_name = admin_subcategories_db[subcategory_id]['name']
        del admin_subcategories_db[subcategory_id]
        
        return jsonify({'success': True, 'message': f'Sous-catégorie "{subcategory_name}" supprimée avec succès'})
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la suppression de la sous-catégorie: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'})

@app.route('/admin/subcategories/<int:subcategory_id>/toggle-status', methods=['POST'])
@admin_required
def admin_subcategory_toggle_status(subcategory_id):
    """Activer/désactiver une sous-catégorie"""
    
    if subcategory_id not in admin_subcategories_db:
        return jsonify({'success': False, 'message': 'Sous-catégorie non trouvée'})
    
    try:
        # Basculer le statut active
        current_status = admin_subcategories_db[subcategory_id]['active']
        new_status = not current_status
        
        # Mettre à jour dans la base de données SQLite
        subcategory_record = Subcategory.query.filter_by(id=subcategory_id).first()
        if subcategory_record:
            subcategory_record.active = new_status
            subcategory_record.updated_at = datetime.now()
            db.session.commit()
            print(f"✅ Statut de la sous-catégorie ID {subcategory_id} mis à jour dans la base de données: {new_status}")
        
        # Mettre à jour le dictionnaire en mémoire
        admin_subcategories_db[subcategory_id]['active'] = new_status
        admin_subcategories_db[subcategory_id]['updated_at'] = datetime.now().strftime('%Y-%m-%d')
        admin_subcategories_db[subcategory_id]['updated_by'] = session.get('admin_email', 'admin')
        
        subcategory_name = admin_subcategories_db[subcategory_id]['name']
        status_text = 'activée' if new_status else 'désactivée'
        
        return jsonify({
            'success': True, 
            'message': f'Sous-catégorie "{subcategory_name}" {status_text} avec succès.',
            'status': new_status,
            'status_text': 'Activé' if new_status else 'Désactivé',
            'status_class': 'success' if new_status else 'danger',
            'button_text': 'Désactiver' if new_status else 'Activer',
            'button_class': 'btn-warning' if new_status else 'btn-success'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la mise à jour de la sous-catégorie: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de la modification du statut: {str(e)}'})

@app.route('/api/subcategories/<int:category_id>')
def api_get_subcategories_by_category(category_id):
    """API pour récupérer les sous-catégories d'une catégorie donnée"""
    
    print(f"DEBUG API: Requête pour catégorie {category_id}")
    
    try:
        # Utiliser directement la base de données au lieu de admin_subcategories_db
        subcategories = Subcategory.query.filter_by(category_id=category_id, active=True).all()
        
        print(f"DEBUG API: Sous-catégories trouvées pour catégorie {category_id}: {len(subcategories)}")
        
        subcategories_list = [
            {'id': subcat.id, 'name': subcat.name} 
            for subcat in subcategories
        ]
        
        for subcat in subcategories:
            print(f"DEBUG API:   - {subcat.name} (ID: {subcat.id})")
        
        result = {'subcategories': subcategories_list}
        print(f"DEBUG API: Réponse finale: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"DEBUG API: Erreur: {e}")
        return jsonify({'subcategories': [], 'error': str(e)}), 500

@app.route('/admin/products')
@admin_required
def admin_products():
    """Page d'administration pour la liste de tous les produits avec pagination"""
    
    # Paramètres de pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)  # 5 produits par page pour tester la pagination
    search = request.args.get('search', '', type=str)
    
    # Récupérer tous les produits (statiques + marchands)
    all_products = get_all_products()
    
    # Filtrer par recherche si un terme est fourni
    if search:
        search_lower = search.lower()
        all_products = [p for p in all_products 
                       if search_lower in p.get('name', '').lower() 
                       or search_lower in p.get('category_name', '').lower()]
    
    # Mapping des catégories depuis la base de données dynamique
    categories_mapping = {cat_id: cat['name'] for cat_id, cat in admin_categories_db.items()}
    
    # Enrichir les produits avec les noms de catégories
    for product in all_products:
        category_id = product.get('category_id')
        product['category_name'] = categories_mapping.get(category_id, 'Non classé')
        
        # Ajouter les informations du marchand si applicable
        if product.get('source') == 'merchant' and product.get('merchant_email'):
            merchant_email = product['merchant_email']
            merchant = merchants_db.get(merchant_email, {})
            product['merchant_name'] = merchant.get('store_name', 'Marchand inconnu')
            product['merchant_verified'] = merchant.get('store_verified', False)
        else:
            product['merchant_name'] = 'DOUKA KM (Admin)'
            product['merchant_verified'] = True
    
    # Trier les produits par date de création (plus récents en premier)
    all_products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Calcul de la pagination
    total_products = len(all_products)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    products_for_page = all_products[start_index:end_index]
    
    # Calcul des pages
    total_pages = (total_products + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    # Statistiques
    stats = {
        'total_products': total_products,
        'admin_products': len([p for p in all_products if p.get('source') != 'merchant']),
        'merchant_products': len([p for p in all_products if p.get('source') == 'merchant']),
        'active_products': len([p for p in all_products if p.get('status') == 'active'])
    }
    
    # Information de pagination
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_products,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': prev_page,
        'next_page': next_page,
        'start_index': start_index + 1,
        'end_index': min(end_index, total_products)
    }

    return render_template('admin/products.html', 
                          products=products_for_page,
                          stats=stats,
                          categories=categories_mapping,
                          pagination=pagination_info,
                          search=search)

@app.route('/admin/admin-products')
@admin_required
def admin_admin_products():
    """Page d'administration pour la liste des produits créés par l'admin uniquement"""
    
    # Paramètres de pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str)
    category_filter = request.args.get('category', '', type=str)
    status_filter = request.args.get('status', 'all', type=str)
    
    # **NOUVELLE VERSION: Récupérer uniquement les produits admin depuis la base de données**
    query = Product.query.filter(Product.merchant_id.is_(None))  # Produits admin n'ont pas de merchant_id
    
    # Filtrer par recherche si un terme est fourni
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%')
            )
        )
    
    # Filtrer par catégorie si spécifiée
    if category_filter:
        try:
            category_id = int(category_filter)
            query = query.filter(Product.category_id == category_id)
        except ValueError:
            pass
    
    # Filtrer par statut si spécifié
    if status_filter != 'all':
        query = query.filter(Product.status == status_filter)
    
    # Récupérer tous les produits admin avec filtres appliqués
    admin_products_db = query.order_by(Product.created_at.desc()).all()
    
    # Mapping des catégories depuis la base de données dynamique
    categories_mapping = {cat_id: cat['name'] for cat_id, cat in admin_categories_db.items()}
    
    # Convertir les produits en dictionnaires et enrichir avec informations supplémentaires
    admin_products = []
    for product_record in admin_products_db:
        product_dict = product_record.to_dict()
        product_dict['category_name'] = categories_mapping.get(product_record.category_id, 'Non classé')
        product_dict['merchant_name'] = 'DOUKA KM (Admin)'
        product_dict['merchant_verified'] = True
        product_dict['source'] = 'admin'
        admin_products.append(product_dict)
    
    # Calcul de la pagination
    total_products = len(admin_products)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    products_for_page = admin_products[start_index:end_index]
    
    # Calcul des pages
    total_pages = (total_products + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    # Statistiques des produits admin
    stats = {
        'total_products': total_products,
        'active_products': len([p for p in admin_products if p.get('status') == 'active']),
        'inactive_products': len([p for p in admin_products if p.get('status') == 'inactive']),
        'categories_used': len(set(p.get('category_id') for p in admin_products if p.get('category_id')))
    }
    
    # Information de pagination
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_products,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': prev_page,
        'next_page': next_page,
        'start_index': start_index + 1,
        'end_index': min(end_index, total_products)
    }

    return render_template('admin/admin_products.html', 
                          products=products_for_page,
                          stats=stats,
                          categories=categories_mapping,
                          pagination=pagination_info,
                          search=search,
                          category_filter=category_filter,
                          status_filter=status_filter)


@app.route('/admin/users')
@permission_required(['super_admin', 'admin'])
def admin_users():
    """Page d'administration pour la gestion des utilisateurs"""
    from datetime import datetime
    
    # Paramètres de pagination et filtres
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', 'all', type=str)
    
    # **DATABASE-FIRST: Récupérer tous les utilisateurs depuis la base de données d'abord**
    all_users = []
    
    try:
        # Récupérer tous les utilisateurs depuis la base de données
        user_records = User.query.all()
        
        for user_record in user_records:
            # Calculer les statistiques depuis la base de données
            user_stats = get_user_order_stats(user_record.email)
            
            user_info = {
                'id': user_record.id,
                'email': user_record.email,
                'first_name': user_record.first_name or '',
                'last_name': user_record.last_name or '',
                'phone': user_record.phone or '',
                'address': user_record.address or '',
                'city': user_record.city or '',
                'region': user_record.region or '',
                'created_at': user_record.created_at,  # Garder l'objet datetime pour le template
                'last_login': user_record.last_login,
                'is_active': user_record.is_active,
                'email_verified': user_record.email_verified,
                'orders_count': user_stats['total_orders'],
                'total_spent': user_stats['total_spent'],
                'wishlist_count': WishlistItem.query.filter_by(user_id=user_record.id).count(),
                'addresses_count': 1 if user_record.address else 0  # Pour l'instant, une seule adresse supportée
            }
            all_users.append(user_info)
        
        print(f"✅ {len(all_users)} utilisateurs récupérés depuis la base de données")
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des utilisateurs depuis la DB: {str(e)}")
    
    # Fallback: ajouter les utilisateurs du dictionnaire non encore migrés
    fallback_count = 0
    for email, user in users_db.items():
        # Vérifier si cet utilisateur n'est pas déjà dans all_users
        if not any(u['email'] == email for u in all_users):
            # Convertir la date string en objet datetime si possible
            created_at = None
            if user.get('registration_date'):
                try:
                    from datetime import datetime
                    created_at = datetime.strptime(user.get('registration_date'), '%Y-%m-%d')
                except:
                    created_at = None
            
            user_info = {
                'id': user.get('id'),
                'email': email,
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'phone': user.get('phone', ''),
                'address': user.get('address', ''),
                'city': user.get('city', ''),
                'region': user.get('region', ''),
                'created_at': created_at,  # Objet datetime pour compatibilité template
                'last_login': user.get('last_login', ''),
                'is_active': user.get('is_active', True),
                'email_verified': user.get('email_verified', False),
                'orders_count': get_user_orders_count(email),
                'wishlist_count': len(user.get('wishlist', [])),
                'addresses_count': len(user.get('addresses', [])),
            }
            # Calculer le total dépensé depuis la base de données
            user_stats = get_user_order_stats(email)
            user_info['total_spent'] = user_stats['total_spent']
            
            all_users.append(user_info)
            fallback_count += 1
    
    if fallback_count > 0:
        print(f"🔄 {fallback_count} utilisateurs ajoutés depuis le dictionnaire (fallback)")
    
    # Filtrer par recherche si un terme est fourni
    if search:
        search_lower = search.lower()
        all_users = [
            user for user in all_users 
            if (search_lower in user.get('email', '').lower() or
                search_lower in user.get('first_name', '').lower() or
                search_lower in user.get('last_name', '').lower() or
                search_lower in user.get('phone', '').lower())
        ]
    
    # Filtrer par statut
    if status_filter == 'active':
        all_users = [user for user in all_users if user.get('is_active', True)]
    elif status_filter == 'inactive':
        all_users = [user for user in all_users if not user.get('is_active', True)]
    
    # Trier par date d'inscription (plus récents en premier)
    all_users.sort(key=lambda x: x.get('created_at') or datetime.min, reverse=True)
    
    # Pagination
    total_users = len(all_users)
    total_pages = (total_users + per_page - 1) // per_page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    users_paginated = all_users[start_index:end_index]
    
    # Créer l'objet de pagination
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total_users,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None
    }
    
    # Calculer les statistiques
    stats = {
        'total_users': len(all_users),
        'active_users': len([u for u in all_users if u.get('is_active', True)]),
        'inactive_users': len([u for u in all_users if not u.get('is_active', True)]),
        'verified_emails': len([u for u in all_users if u.get('email_verified', False)]),
        'unverified_emails': len([u for u in all_users if not u.get('email_verified', False)]),
        'users_with_orders': len([u for u in all_users if u.get('orders_count', 0) > 0]),
        'total_revenue': sum(u.get('total_spent', 0) for u in all_users),
        'avg_orders_per_user': sum(u.get('orders_count', 0) for u in all_users) / len(all_users) if all_users else 0
    }
    
    return render_template('admin/users.html',
                          users=users_paginated,
                          pagination=pagination,
                          stats=stats,
                          current_search=search,
                          current_status_filter=status_filter)

@app.route('/admin/users/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    """Page de détail d'un utilisateur spécifique - Version migrée database-first"""
    
    # **DATABASE-FIRST: Chercher l'utilisateur dans la base de données d'abord**
    target_user_data = None
    user_email = None
    
    try:
        # Récupérer l'utilisateur depuis la base de données par ID
        user_record = User.query.filter_by(id=user_id).first()
        
        if user_record:
            user_email = user_record.email
            
            # Récupérer les statistiques et commandes depuis la base de données
            user_stats = get_user_order_stats(user_record.email)
            user_orders_db = Order.query.filter_by(customer_email=user_record.email).all()
            
            # Convertir les commandes DB en format dictionnaire
            user_orders = []
            for order in user_orders_db:
                # Convertir les items de la relation SQLAlchemy en liste
                items_list = []
                for item in order.items:
                    items_list.append({
                        'name': item.name,
                        'quantity': item.quantity,
                        'price': item.price,
                        'subtotal': item.subtotal,
                        'image': item.image or '/static/images/default.jpg',
                        'variant_details': item.variant_details or ''
                    })
                
                order_dict = {
                    'id': order.id,
                    'total': order.total,
                    'status': order.status,
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '',
                    'items': items_list,
                    'shipping_address': order.get_shipping_address(),
                    'payment_method': order.payment_method or '',
                    'tracking_number': getattr(order, 'tracking_number', '') or ''
                }
                
                # Ajouter les métadonnées de statut
                status_texts = {
                    'processing': 'En cours de préparation',
                    'shipped': 'Expédiée',
                    'delivered': 'Livrée',
                    'cancelled': 'Annulée'
                }
                order_dict['status_text'] = status_texts.get(order.status, 'En traitement')
                
                status_colors = {
                    'processing': 'primary',
                    'shipped': 'info',
                    'delivered': 'success',
                    'cancelled': 'danger'
                }
                order_dict['status_color'] = status_colors.get(order.status, 'secondary')
                
                user_orders.append(order_dict)
            
            # Récupérer les adresses depuis le dictionnaire utilisateur (fallback si pas en DB)
            user_addresses = []
            if user_record.email in users_db:
                user_addresses = users_db[user_record.email].get('addresses', [])
            # Note: Les adresses pourraient être stockées dans une table séparée à l'avenir
            
            target_user_data = {
                'id': user_record.id,
                'email': user_record.email,
                'first_name': user_record.first_name or '',
                'last_name': user_record.last_name or '',
                'phone': user_record.phone or '',
                'address': user_record.address or '',
                'city': user_record.city or '',
                'region': user_record.region or '',
                'registration_date': user_record.created_at.strftime('%Y-%m-%d') if user_record.created_at else '',
                'last_login': user_record.last_login.strftime('%Y-%m-%d %H:%M') if user_record.last_login else '',
                'is_active': user_record.is_active,
                'email_verified': user_record.email_verified,  # <-- Cette propriété est cruciale
                'orders': user_orders,
                'orders_count': len(user_orders),
                'total_spent': user_stats['total_spent'],
                'wishlist_count': WishlistItem.query.filter_by(user_id=user_record.id).count(),
                'addresses': user_addresses,  # Adresses depuis le dictionnaire
                'addresses_count': len(user_addresses)
            }
            
            print(f"✅ Utilisateur {user_email} récupéré depuis la base de données")
            
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de l'utilisateur depuis la DB: {str(e)}")
    
    # Fallback: chercher dans le dictionnaire si non trouvé en DB
    if not target_user_data:
        for email, user in users_db.items():
            if user.get('id') == user_id:
                target_user_data = user
                user_email = email
                
                # Récupérer les commandes de l'utilisateur
                user_orders = target_user_data.get('orders', [])
                
                # Enrichir les commandes avec des informations supplémentaires
                for order in user_orders:
                    if 'status_text' not in order:
                        status_texts = {
                            'processing': 'En cours de préparation',
                            'shipped': 'Expédiée',
                            'delivered': 'Livrée',
                            'cancelled': 'Annulée'
                        }
                        order['status_text'] = status_texts.get(order.get('status', 'processing'), 'En traitement')
                    
                    if 'status_color' not in order:
                        status_colors = {
                            'processing': 'primary',
                            'shipped': 'info',
                            'delivered': 'success',
                            'cancelled': 'danger'
                        }
                        order['status_color'] = status_colors.get(order.get('status', 'processing'), 'secondary')
                
                print(f"🔄 Utilisateur {user_email} récupéré depuis le dictionnaire (fallback)")
                break
    
    if not target_user_data:
        flash('Utilisateur non trouvé', 'danger')
        return redirect(url_for('admin_users'))
    
    # Récupérer les commandes de l'utilisateur
    user_orders = target_user_data.get('orders', [])
    
    # Enrichir les commandes avec des informations supplémentaires
    for order in user_orders:
        if 'status_text' not in order:
            status_texts = {
                'processing': 'En cours de préparation',
                'shipped': 'Expédiée',
                'delivered': 'Livrée',
                'cancelled': 'Annulée'
            }
            order['status_text'] = status_texts.get(order.get('status', 'processing'), 'En traitement')
        
        if 'status_color' not in order:
            status_colors = {
                'processing': 'primary',
                'shipped': 'info',
                'delivered': 'success',
                'cancelled': 'danger'
            }
            order['status_color'] = status_colors.get(order.get('status', 'processing'), 'secondary')
    
    # Trier les commandes par date (plus récentes en premier)
    user_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Préparer les données pour l'affichage
    user_data = {
        'id': target_user_data.get('id'),
        'email': user_email,
        'first_name': target_user_data.get('first_name', ''),
        'last_name': target_user_data.get('last_name', ''),
        'phone': target_user_data.get('phone', ''),
        'address': target_user_data.get('address', ''),
        'city': target_user_data.get('city', ''),
        'region': target_user_data.get('region', ''),
        'registration_date': target_user_data.get('registration_date', ''),
        'last_login': target_user_data.get('last_login', ''),
        'is_active': target_user_data.get('is_active', True),
        'orders': user_orders,
        'addresses': target_user_data.get('addresses', []),
        'wishlist': target_user_data.get('wishlist', []),
        'total_spent': target_user_data.get('total_spent', sum(order.get('total', 0) for order in user_orders if order.get('status') in ['delivered', 'shipped'])),
        'orders_count': target_user_data.get('orders_count', len(user_orders)),
        'completed_orders': len([o for o in user_orders if o.get('status') == 'delivered']),
        'pending_orders': len([o for o in user_orders if o.get('status') == 'processing']),
        'wishlist_count': target_user_data.get('wishlist_count', len(target_user_data.get('wishlist', []))),
        'addresses_count': target_user_data.get('addresses_count', len(target_user_data.get('addresses', [])))
    }
    
    return render_template('admin/user_detail.html', user=user_data)

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    """Activer/Désactiver un utilisateur - Version migrée database-first"""
    
    # **DATABASE-FIRST: Chercher l'utilisateur dans la base de données d'abord**
    try:
        user_record = User.query.filter_by(id=user_id).first()
        
        if user_record:
            # Basculer le statut actif/inactif dans la base de données
            current_status = user_record.is_active
            new_status = not current_status
            
            user_record.is_active = new_status
            db.session.commit()
            
            # Synchroniser avec le dictionnaire si l'utilisateur y existe
            if user_record.email in users_db:
                users_db[user_record.email]['is_active'] = new_status
            
            status_text = "activé" if new_status else "désactivé"
            print(f"✅ Utilisateur {user_record.email} {status_text} dans la base de données")
            
            return jsonify({
                'success': True, 
                'message': f'Utilisateur {status_text} avec succès',
                'new_status': new_status
            })
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour du statut utilisateur en DB: {str(e)}")
        db.session.rollback()
    
    # Fallback: chercher dans le dictionnaire
    target_user = None
    user_email = None
    
    for email, user in users_db.items():
        if user.get('id') == user_id:
            target_user = user
            user_email = email
            break
    
    if not target_user:
        return jsonify({'success': False, 'message': 'Utilisateur non trouvé'})
    
    try:
        # Basculer le statut actif/inactif dans le dictionnaire
        current_status = target_user.get('is_active', True)
        new_status = not current_status
        
        users_db[user_email]['is_active'] = new_status
        
        status_text = "activé" if new_status else "désactivé"
        print(f"🔄 Utilisateur {user_email} {status_text} dans le dictionnaire (fallback)")
        
        return jsonify({
            'success': True, 
            'message': f'Utilisateur {status_text} avec succès',
            'new_status': new_status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la mise à jour: {str(e)}'})

@app.route('/admin/users/<int:user_id>/verify-email', methods=['POST'])
@admin_required
def admin_verify_user_email(user_id):
    """Vérifier manuellement l'email d'un utilisateur - Version database-first"""
    
    # **DATABASE-FIRST: Chercher l'utilisateur dans la base de données d'abord**
    try:
        user_record = User.query.filter_by(id=user_id).first()
        
        if user_record:
            # Vérifier si l'email n'est pas déjà vérifié
            if user_record.email_verified:
                return jsonify({
                    'success': False, 
                    'message': 'L\'email de cet utilisateur est déjà vérifié'
                })
            
            # Marquer l'email comme vérifié dans la base de données
            user_record.email_verified = True
            db.session.commit()
            
            # Synchroniser avec le dictionnaire si l'utilisateur y existe
            if user_record.email in users_db:
                users_db[user_record.email]['email_verified'] = True
            
            print(f"✅ Email de l'utilisateur {user_record.email} vérifié par l'admin dans la base de données")
            
            return jsonify({
                'success': True, 
                'message': f'Email de {user_record.first_name} {user_record.last_name} vérifié avec succès'
            })
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification de l'email en DB: {str(e)}")
        db.session.rollback()
    
    # Fallback: chercher dans le dictionnaire
    target_user = None
    user_email = None
    
    for email, user in users_db.items():
        if user.get('id') == user_id:
            target_user = user
            user_email = email
            break
    
    if not target_user:
        return jsonify({'success': False, 'message': 'Utilisateur non trouvé'})
    
    try:
        # Vérifier si l'email n'est pas déjà vérifié
        if target_user.get('email_verified', False):
            return jsonify({
                'success': False, 
                'message': 'L\'email de cet utilisateur est déjà vérifié'
            })
        
        # Marquer l'email comme vérifié dans le dictionnaire
        users_db[user_email]['email_verified'] = True
        
        print(f"🔄 Email de l'utilisateur {user_email} vérifié par l'admin dans le dictionnaire (fallback)")
        
        return jsonify({
            'success': True, 
            'message': f'Email de {target_user["first_name"]} {target_user["last_name"]} vérifié avec succès'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la vérification: {str(e)}'})

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Supprimer un utilisateur (avec confirmation)"""
    
    print(f"🔍 Tentative de suppression utilisateur ID: {user_id} (type: {type(user_id)})")
    
    # S'assurer que la session est propre
    try:
        db.session.rollback()
    except Exception:
        pass
    
    # DATABASE-FIRST: Chercher l'utilisateur dans la base de données d'abord
    try:
        user_record = User.query.filter_by(id=user_id).first()
        print(f"🔍 Recherche en base pour ID {user_id}: {'Trouvé' if user_record else 'Non trouvé'}")
    except Exception as search_error:
        print(f"❌ Erreur lors de la recherche: {search_error}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur de recherche: {str(search_error)}'})
    
    target_user = None
    user_email = None
    
    if user_record:
        # Utilisateur trouvé dans la base de données
        user_email = user_record.email
        target_user = {
            'id': user_record.id,
            'first_name': user_record.first_name,
            'last_name': user_record.last_name,
            'email': user_record.email
        }
        print(f"✅ Utilisateur trouvé en base: {user_email}")
    else:
        # Fallback: chercher dans le dictionnaire en mémoire
        print("🔄 Recherche dans le dictionnaire en mémoire...")
        for email, user in users_db.items():
            if user.get('id') == user_id:
                target_user = user
                user_email = email
                print(f"✅ Utilisateur trouvé en mémoire: {user_email}")
                break
        
        if not target_user:
            print(f"❌ Utilisateur ID {user_id} non trouvé ni en base ni en mémoire")
            print(f"📊 Total utilisateurs en mémoire: {len(users_db)}")
            # Lister quelques IDs pour debug
            memory_ids = [user.get('id') for user in users_db.values() if user.get('id')][:5]
            print(f"📊 Quelques IDs en mémoire: {memory_ids}")
    
    if not target_user:
        return jsonify({'success': False, 'message': 'Utilisateur non trouvé'})
    
    try:
        # Vérifier s'il y a des commandes associées à cet utilisateur
        user_orders = target_user.get('orders', []) if user_email in users_db else []
        
        # Vérifier aussi les commandes dans la base de données
        user_db_orders = Order.query.filter_by(customer_email=user_email).all()
        
        total_orders = len(user_orders) + len(user_db_orders)
        
        if total_orders > 0:
            print(f"⚠️ Utilisateur {user_email} a {total_orders} commande(s) qui seront supprimées")
        
        # Supprimer l'utilisateur de la base de données
        if user_record:
            # Supprimer d'abord les éléments liés pour éviter les contraintes
            try:
                # Supprimer les éléments de wishlist
                WishlistItem.query.filter_by(user_id=user_id).delete()
                
                # Supprimer les tokens de vérification email (utiliser l'email, pas user_id)
                EmailVerificationToken.query.filter_by(email=user_email).delete()
                
                # Supprimer les tokens de réinitialisation de mot de passe (utiliser l'email, pas user_id)
                PasswordResetToken.query.filter_by(email=user_email).delete()
                
                # Supprimer TOUTES les commandes de l'utilisateur et leurs éléments associés
                user_orders_db = Order.query.filter_by(customer_email=user_email).all()
                
                print(f"🔄 Suppression des commandes pour l'utilisateur {user_email}")
                
                for order in user_orders_db:
                    print(f"   - Suppression commande #{order.id} (Status: {order.status})")
                    
                    # Supprimer tous les éléments de la commande (OrderItem)
                    order_items = OrderItem.query.filter_by(order_id=order.id).all()
                    for item in order_items:
                        print(f"     * Suppression item: {item.name} (x{item.quantity})")
                        db.session.delete(item)
                    
                    # Supprimer la commande elle-même
                    db.session.delete(order)
                
                # Supprimer également les adresses de l'utilisateur
                user_addresses = Address.query.filter_by(user_id=user_id).all()
                for address in user_addresses:
                    print(f"   - Suppression adresse: {address.name}")
                    db.session.delete(address)
                
                # Supprimer les éléments du panier
                user_carts = Cart.query.filter_by(user_id=user_id).all()
                for cart in user_carts:
                    # Supprimer les éléments du panier
                    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
                    for cart_item in cart_items:
                        db.session.delete(cart_item)
                    # Supprimer le panier lui-même
                    db.session.delete(cart)
                
                # Supprimer les avis/reviews de l'utilisateur
                user_reviews = Review.query.filter_by(user_id=user_id).all()
                for review in user_reviews:
                    print(f"   - Suppression avis pour produit #{review.product_id}")
                    db.session.delete(review)
                
                # Supprimer l'utilisateur lui-même
                db.session.delete(user_record)
                db.session.commit()
                
                orders_message = f" et {total_orders} commande(s)" if total_orders > 0 else ""
                print(f"✅ Utilisateur ID {user_id} supprimé de la base de données{orders_message}")
                
            except Exception as db_error:
                db.session.rollback()
                print(f"❌ Erreur lors de la suppression en base: {str(db_error)}")
                return jsonify({'success': False, 'message': f'Erreur base de données: {str(db_error)}'})
        
        # Supprimer l'utilisateur du dictionnaire en mémoire (si il y est)
        if user_email in users_db:
            user_name = f"{target_user.get('first_name', '')} {target_user.get('last_name', '')}"
            del users_db[user_email]
            print(f"✅ Utilisateur {user_email} supprimé du dictionnaire en mémoire")
        else:
            user_name = f"{target_user.get('first_name', '')} {target_user.get('last_name', '')}"
            print(f"✅ Utilisateur {user_email} supprimé (était uniquement en base de données)")
        
        orders_info = f" (avec {total_orders} commandes supprimées)" if total_orders > 0 else ""
        
        return jsonify({
            'success': True, 
            'message': f'Utilisateur "{user_name}" supprimé avec succès{orders_info}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'})

# Routes pour la gestion des codes promo
@app.route('/admin/promo-codes')
@admin_required
def admin_promo_codes():
    """Page d'administration pour la gestion des codes promo"""
    
    # Paramètres de pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', 'all', type=str)
    
    # **MIGRATION: Récupérer tous les codes promo depuis la base de données**
    db_codes = PromoCode.query.all()
    all_codes = [promo.to_dict() for promo in db_codes]
    
    # **COMPATIBILITÉ: Synchroniser avec le dictionnaire en mémoire pour les anciens codes**
    for code_data in all_codes:
        code = code_data['code']
        if code not in promo_codes_db:
            promo_codes_db[code] = code_data
    
    # Filtrer par recherche si un terme est fourni
    if search:
        search_lower = search.lower()
        all_codes = [
            code for code in all_codes
            if (search_lower in code.get('code', '').lower() or
                search_lower in code.get('name', '').lower() or
                search_lower in code.get('description', '').lower())
        ]
    
    # Filtrer par statut
    # Obtenir la date actuelle comme objet date pour les comparaisons SQL
    today = datetime.now().date()
    # Aussi comme string pour les comparaisons avec les données JSON
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if status_filter == 'active':
        all_codes = [
            code for code in all_codes
            if (code.get('active', False) and
                (not code.get('end_date') or code.get('end_date') >= today_str))
        ]
    elif status_filter == 'expired':
        all_codes = [
            code for code in all_codes
            if (code.get('end_date') and code.get('end_date') < today_str)
        ]
    elif status_filter == 'inactive':
        all_codes = [
            code for code in all_codes
            if not code.get('active', False)
        ]
    
    # Trier par date de création (plus récents en premier)
    all_codes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Pagination
    total_codes = len(all_codes)
    total_pages = (total_codes + per_page - 1) // per_page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    codes_paginated = all_codes[start_index:end_index]
    
    # Créer l'objet de pagination
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total_codes,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None
    }
    
    # **MIGRATION: Calculer les statistiques depuis la base de données**
    total_codes_db = PromoCode.query.count()
    active_codes_db = PromoCode.query.filter_by(active=True).count()
    expired_codes_db = PromoCode.query.filter(PromoCode.end_date < today).count()
    total_usage_db = db.session.query(db.func.sum(PromoCode.used_count)).scalar() or 0
    
    stats = {
        'total_codes': total_codes_db,
        'active_codes': active_codes_db,
        'expired_codes': expired_codes_db,
        'total_usage': total_usage_db,
        'avg_usage': total_usage_db / total_codes_db if total_codes_db > 0 else 0
    }
    
    from datetime import date
    
    return render_template('admin/promo_codes.html',
                          codes=codes_paginated,
                          pagination=pagination,
                          stats=stats,
                          current_search=search,
                          current_status_filter=status_filter,
                          today=date.today().strftime('%Y-%m-%d'))

@app.route('/admin/promo-codes/add', methods=['GET', 'POST'])
@admin_required
def admin_add_promo_code():
    """Ajouter un nouveau code promo"""
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            code = request.form.get('code', '').strip().upper()
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            type_discount = request.form.get('type', 'percentage')
            value = float(request.form.get('value', 0))
            min_amount = float(request.form.get('min_order_amount', 0))
            max_discount = request.form.get('max_discount', '')
            usage_limit = request.form.get('usage_limit', '')
            user_limit = request.form.get('user_limit', '')
            start_date = request.form.get('start_date', '')
            end_date = request.form.get('end_date', '')
            active = 'active' in request.form
            
            # Nouvelles données pour les restrictions
            applicable_to = request.form.get('applicable_to', 'all')
            applicable_categories = request.form.getlist('applicable_categories')
            applicable_subcategories = request.form.getlist('applicable_subcategories')
            applicable_products = request.form.getlist('applicable_products')
            applicable_merchants = request.form.getlist('applicable_merchants')
            
            # Validation
            if not code:
                flash('Le code promo est obligatoire.', 'danger')
                return redirect(request.url)
            
            # **MIGRATION: Vérifier dans la base de données d'abord**
            existing_promo = PromoCode.query.filter_by(code=code).first()
            if existing_promo or code in promo_codes_db:
                flash('Ce code promo existe déjà.', 'danger')
                return redirect(request.url)
            
            if not name:
                flash('Le nom du code promo est obligatoire.', 'danger')
                return redirect(request.url)
            
            if value <= 0:
                flash('La valeur de remise doit être positive.', 'danger')
                return redirect(request.url)
            
            if type_discount == 'percentage' and value > 100:
                flash('Le pourcentage de remise ne peut pas dépasser 100%.', 'danger')
                return redirect(request.url)
            
            # Validation des restrictions
            if applicable_to != 'all':
                if applicable_to == 'categories' and not applicable_categories:
                    flash('Veuillez sélectionner au moins une catégorie.', 'danger')
                    return redirect(request.url)
                elif applicable_to == 'subcategories' and not applicable_subcategories:
                    flash('Veuillez sélectionner au moins une sous-catégorie.', 'danger')
                    return redirect(request.url)
                elif applicable_to == 'products' and not applicable_products:
                    flash('Veuillez sélectionner au moins un produit.', 'danger')
                    return redirect(request.url)
                elif applicable_to == 'merchants' and not applicable_merchants:
                    flash('Veuillez sélectionner au moins un marchand.', 'danger')
                    return redirect(request.url)
            
            # **NOUVELLE VERSION: Créer le code promo en base de données**
            try:
                import json
                
                # Convertir les listes en chaînes JSON pour la base de données
                applicable_categories_json = json.dumps([int(cat_id) for cat_id in applicable_categories if cat_id.isdigit()])
                applicable_subcategories_json = json.dumps([int(sub_id) for sub_id in applicable_subcategories if sub_id.isdigit()])
                applicable_products_json = json.dumps([int(prod_id) for prod_id in applicable_products if prod_id.isdigit()])
                applicable_merchants_json = json.dumps(applicable_merchants)
                
                new_promo = PromoCode(
                    code=code,
                    name=name,
                    description=description,
                    type=type_discount,
                    value=value,
                    min_amount=min_amount,
                    max_discount=float(max_discount) if max_discount else None,
                    usage_limit=int(usage_limit) if usage_limit else None,
                    used_count=0,
                    user_limit=int(user_limit) if user_limit else None,
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
                    end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
                    active=active,
                    public_display=True,  # Par défaut, les codes sont publics
                    display_priority=0,
                    applicable_to=applicable_to,
                    applicable_categories=applicable_categories_json,
                    applicable_subcategories=applicable_subcategories_json,
                    applicable_products=applicable_products_json,
                    applicable_merchants=applicable_merchants_json,
                    used_by='{}',  # JSON vide pour les utilisations
                    created_at=datetime.utcnow(),
                    created_by=session.get('admin_email', 'admin')
                )
                
                db.session.add(new_promo)
                db.session.commit()
                
                # **COMPATIBILITÉ: Synchroniser avec le dictionnaire en mémoire**
                promo_dict = new_promo.to_dict()
                promo_codes_db[code] = promo_dict
                
                flash(f'Code promo "{code}" créé avec succès.', 'success')
                print(f"✅ Code promo {code} sauvegardé en base de données et en mémoire")
                return redirect(url_for('admin_promo_codes'))
                
            except Exception as db_error:
                db.session.rollback()
                print(f"❌ Erreur DB lors de création du code promo: {str(db_error)}")
                
                # **FALLBACK: Utiliser l'ancien système en cas d'erreur**
                # Générer un ID unique
                new_id = max([c.get('id', 0) for c in promo_codes_db.values()], default=0) + 1
                
                # Créer le nouveau code promo
                new_promo = {
                    'id': new_id,
                    'code': code,
                    'name': name,
                    'description': description,
                    'type': type_discount,
                    'value': value,
                    'min_amount': min_amount,
                    'max_discount': float(max_discount) if max_discount else None,
                    'usage_limit': int(usage_limit) if usage_limit else None,
                    'used_count': 0,
                    'user_limit': int(user_limit) if user_limit else None,
                    'start_date': start_date if start_date else None,
                    'end_date': end_date if end_date else None,
                    'active': active,
                    'public_display': True,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': session.get('admin_email', 'admin'),
                    'applicable_to': applicable_to,
                    'applicable_categories': [int(cat_id) for cat_id in applicable_categories if cat_id.isdigit()],
                    'applicable_subcategories': [int(sub_id) for sub_id in applicable_subcategories if sub_id.isdigit()],
                    'applicable_products': [int(prod_id) for prod_id in applicable_products if prod_id.isdigit()],
                    'applicable_merchants': applicable_merchants,
                    'used_by': {}
                }
                
                # Ajouter au dictionnaire en mémoire (fallback)
                promo_codes_db[code] = new_promo
                print(f"⚠️ Code promo {code} créé en mémoire (fallback)")
                
                flash(f'Code promo "{code}" créé avec succès.', 'success')
                return redirect(url_for('admin_promo_codes'))
            
        except ValueError:
            flash('Erreur dans les valeurs numériques. Veuillez vérifier vos saisies.', 'danger')
        except Exception as e:
            flash(f'Erreur lors de la création: {str(e)}', 'danger')
    
    # Préparer les données pour le formulaire
    categories = list(admin_categories_db.values())
    subcategories = list(admin_subcategories_db.values())
    
    # Enrichir les sous-catégories avec le nom de leur catégorie parente
    for subcategory in subcategories:
        category_id = subcategory.get('category_id')
        if category_id in admin_categories_db:
            subcategory['category_name'] = admin_categories_db[category_id]['name']
        else:
            subcategory['category_name'] = 'Non définie'
    
    all_products = get_all_products()
    merchants = list(merchants_db.values())
    
    return render_template('admin/promo_code_form.html', 
                          edit_mode=False,
                          categories=categories,
                          subcategories=subcategories,
                          products=all_products,
                          merchants=merchants)

@app.route('/admin/promo-codes/<code>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_promo_code(code):
    """Modifier un code promo existant"""
    
    # Chercher dans la base de données d'abord
    promo_record = PromoCode.query.filter_by(code=code).first()
    promo_in_memory = code in promo_codes_db
    if not promo_record and not promo_in_memory:
        flash('Code promo non trouvé.', 'danger')
        return redirect(url_for('admin_promo_codes'))
    # Utiliser l'objet en mémoire pour le formulaire, mais on mettra à jour les deux si besoin
    promo = promo_codes_db[code] if promo_in_memory else (promo_record.to_dict() if promo_record else {})
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            type_discount = request.form.get('type', 'percentage')
            value = float(request.form.get('value', 0))
            min_amount = float(request.form.get('min_order_amount', 0))
            max_discount = request.form.get('max_discount', '')
            usage_limit = request.form.get('usage_limit', '')
            user_limit = request.form.get('user_limit', '')
            start_date = request.form.get('start_date', '')
            end_date = request.form.get('end_date', '')
            # Conversion en date
            from datetime import datetime
            start_date_obj = None
            end_date_obj = None
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                except Exception:
                    start_date_obj = None
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                except Exception:
                    end_date_obj = None
            active = 'active' in request.form

            # Nouvelles données pour les restrictions
            applicable_to = request.form.get('applicable_to', 'all')
            applicable_categories = request.form.getlist('applicable_categories')
            applicable_subcategories = request.form.getlist('applicable_subcategories')
            applicable_products = request.form.getlist('applicable_products')
            applicable_merchants = request.form.getlist('applicable_merchants')

            # Validation
            if not name:
                flash('Le nom du code promo est obligatoire.', 'danger')
                return redirect(request.url)

            if value <= 0:
                flash('La valeur de remise doit être positive.', 'danger')
                return redirect(request.url)

            if type_discount == 'percentage' and value > 100:
                flash('Le pourcentage de remise ne peut pas dépasser 100%.', 'danger')
                return redirect(request.url)

            # Validation des restrictions
            if applicable_to != 'all':
                if applicable_to == 'categories' and not applicable_categories:
                    flash('Veuillez sélectionner au moins une catégorie.', 'danger')
                    return redirect(request.url)
                elif applicable_to == 'subcategories' and not applicable_subcategories:
                    flash('Veuillez sélectionner au moins une sous-catégorie.', 'danger')
                    return redirect(request.url)
                elif applicable_to == 'products' and not applicable_products:
                    flash('Veuillez sélectionner au moins un produit.', 'danger')
                    return redirect(request.url)
                elif applicable_to == 'merchants' and not applicable_merchants:
                    flash('Veuillez sélectionner au moins un marchand.', 'danger')
                    return redirect(request.url)

            # Mettre à jour le code promo en mémoire
            if promo_in_memory:
                promo.update({
                    'name': name,
                    'description': description,
                    'type': type_discount,
                    'value': value,
                    'min_amount': min_amount,
                    'max_discount': float(max_discount) if max_discount else None,
                    'usage_limit': int(usage_limit) if usage_limit else None,
                    'user_limit': int(user_limit) if user_limit else None,
                    'start_date': start_date if start_date else None,
                    'end_date': end_date if end_date else None,
                    'active': active,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': session.get('admin_email', 'admin'),
                    'applicable_to': applicable_to,
                    'applicable_categories': [int(cat_id) for cat_id in applicable_categories if cat_id.isdigit()],
                    'applicable_subcategories': [int(sub_id) for sub_id in applicable_subcategories if sub_id.isdigit()],
                    'applicable_products': [int(prod_id) for prod_id in applicable_products if prod_id.isdigit()],
                    'applicable_merchants': applicable_merchants
                })

            # Mettre à jour le code promo en base de données si présent
            if promo_record:
                promo_record.name = name
                promo_record.description = description
                promo_record.type = type_discount
                promo_record.value = value
                promo_record.min_order_amount = min_amount
                promo_record.max_discount = float(max_discount) if max_discount else None
                promo_record.usage_limit = int(usage_limit) if usage_limit else None
                promo_record.user_limit = int(user_limit) if user_limit else None
                promo_record.start_date = start_date_obj
                promo_record.end_date = end_date_obj
                promo_record.active = active
                promo_record.updated_at = datetime.now()
                promo_record.updated_by = session.get('admin_email', 'admin')
                promo_record.applicable_to = applicable_to
                promo_record.applicable_categories = ','.join([str(cat_id) for cat_id in applicable_categories if cat_id.isdigit()])
                promo_record.applicable_subcategories = ','.join([str(sub_id) for sub_id in applicable_subcategories if sub_id.isdigit()])
                promo_record.applicable_products = ','.join([str(prod_id) for prod_id in applicable_products if prod_id.isdigit()])
                promo_record.applicable_merchants = ','.join(applicable_merchants)
                db.session.commit()

            flash(f'Code promo "{code}" mis à jour avec succès.', 'success')
            return redirect(url_for('admin_promo_codes'))

        except ValueError:
            flash('Erreur dans les valeurs numériques. Veuillez vérifier vos saisies.', 'danger')
        except Exception as e:
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
    
    # Préparer les données pour le formulaire
    categories = list(admin_categories_db.values())
    subcategories = list(admin_subcategories_db.values())
    
    # Enrichir les sous-catégories avec le nom de leur catégorie parente
    for subcategory in subcategories:
        category_id = subcategory.get('category_id')
        if category_id in admin_categories_db:
            subcategory['category_name'] = admin_categories_db[category_id]['name']
        else:
            subcategory['category_name'] = 'Non définie'
    
    all_products = get_all_products()
    merchants = list(merchants_db.values())
    
    # Correction robustesse : forcer les champs à être des listes
    def ensure_list(val):
        if isinstance(val, list):
            return val
        if val is None:
            return []
        if isinstance(val, str):
            # Si c'est une string de type '1,2,3' ou '[1,2,3]'
            try:
                # Essayer de parser JSON
                import json
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                # Split par virgule si besoin
                return [int(x) if x.isdigit() else x for x in val.split(',') if x]
        if isinstance(val, int):
            return [val]
        return list(val) if hasattr(val, '__iter__') else [val]

    for key in ['applicable_categories', 'applicable_subcategories', 'applicable_products', 'applicable_merchants']:
        if key in promo:
            promo[key] = ensure_list(promo[key])

    return render_template('admin/promo_code_form.html', 
                          promo=promo, 
                          edit_mode=True,
                          categories=categories,
                          subcategories=subcategories,
                          products=all_products,
                          merchants=merchants)

@app.route('/admin/promo-codes/<code>/delete', methods=['POST'])
@admin_required
def admin_delete_promo_code(code):
    """Supprimer un code promo"""
    
    # **MIGRATION: Vérifier dans la base de données d'abord**
    promo_record = PromoCode.query.filter_by(code=code).first()
    promo_in_memory = code in promo_codes_db
    
    if not promo_record and not promo_in_memory:
        return jsonify({'success': False, 'message': 'Code promo non trouvé'})
    
    try:
        # Obtenir le nom pour le message
        if promo_record:
            promo_name = promo_record.name
        elif promo_in_memory:
            promo_name = promo_codes_db[code].get('name', code)
        else:
            promo_name = code
        
        # **NOUVEAU: Supprimer de la base de données en priorité**
        if promo_record:
            db.session.delete(promo_record)
            db.session.commit()
            print(f"✅ Code promo {code} supprimé de la base de données")
        
        # **COMPATIBILITÉ: Supprimer du dictionnaire en mémoire si présent**
        if promo_in_memory:
            del promo_codes_db[code]
            print(f"✅ Code promo {code} supprimé du dictionnaire en mémoire")
        
        return jsonify({
            'success': True,
            'message': f'Code promo "{promo_name}" supprimé avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la suppression du code promo: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'})

@app.route('/admin/promo-codes/<code>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_promo_code_status(code):
    """Activer/désactiver un code promo"""
    
    if code not in promo_codes_db:
        return jsonify({'success': False, 'message': 'Code promo non trouvé'})
    
    try:
        current_status = promo_codes_db[code].get('active', False)
        new_status = not current_status
        
        # Mettre à jour dans la base de données SQLite
        promo_record = PromoCode.query.filter_by(code=code).first()
        if promo_record:
            promo_record.active = new_status
            promo_record.updated_at = datetime.now()
            db.session.commit()
            print(f"✅ Statut du code promo {code} mis à jour dans la base de données: {new_status}")
        
        # Mettre à jour le dictionnaire en mémoire
        promo_codes_db[code]['active'] = new_status
        promo_codes_db[code]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        promo_codes_db[code]['updated_by'] = session.get('admin_email', 'admin')
        
        status_text = "activé" if new_status else "désactivé"
        promo_name = promo_codes_db[code].get('name', code)
        
        return jsonify({
            'success': True,
            'message': f'Code promo "{promo_name}" {status_text} avec succès',
            'new_status': new_status
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la mise à jour du code promo: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur lors de la modification: {str(e)}'})
        promo_codes_db[code]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        promo_codes_db[code]['updated_by'] = session.get('admin_email', 'admin')
        
        status_text = "activé" if new_status else "désactivé"
        promo_name = promo_codes_db[code].get('name', code)
        
        return jsonify({
            'success': True,
            'message': f'Code promo "{promo_name}" {status_text} avec succès',
            'new_status': new_status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de la modification: {str(e)}'})

@app.route('/api/validate-promo-code', methods=['POST'])
def api_validate_promo_code():
    """API pour valider un code promo côté client"""
    
    try:
        data = request.get_json()
        code = data.get('code', '').strip().upper()
        cart_total = float(data.get('cart_total', 0))
        cart_items = data.get('cart_items', [])  # Récupérer les articles du panier
        user_email = session.get('user_email')
        
        if not code:
            return jsonify({
                'valid': False,
                'error': 'Code promo requis',
                'discount': 0
            })
        
        # Passer les cart_items à la fonction de validation
        result = validate_promo_code(code, cart_total, user_email, cart_items)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': 'Erreur lors de la validation',
            'discount': 0
        })

@app.route('/admin/settings', methods=['GET', 'POST'])
@permission_required(['super_admin', 'admin'])
def admin_settings():
    """Page de paramètres et configuration du système"""
    
    if request.method == 'POST':
        # Traitement des mises à jour de paramètres
        action = request.form.get('action')
        
        if action == 'update_site_info':
            # Mise à jour des informations du site
            site_name = request.form.get('site_name', '').strip()
            site_description = request.form.get('site_description', '').strip()
            contact_email = request.form.get('contact_email', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            
            if site_name:
                # Sauvegarder dans la base de données
                success = True
                success &= update_site_setting('site_name', site_name, 'Nom du site')
                success &= update_site_setting('site_description', site_description, 'Description du site')
                success &= update_site_setting('contact_email', contact_email, 'Email de contact')
                success &= update_site_setting('contact_phone', contact_phone, 'Téléphone de contact')
                
                if success:
                    flash('Informations du site mises à jour avec succès.', 'success')
                else:
                    flash('Erreur lors de la mise à jour des informations du site.', 'danger')
            else:
                flash('Le nom du site est obligatoire.', 'danger')
        
        elif action == 'update_commission':
            # Mise à jour du taux de commission
            try:
                commission_rate = float(request.form.get('commission_rate', 0))
                if 0 <= commission_rate <= 100:
                    if update_site_setting('commission_rate', commission_rate, 'Taux de commission en pourcentage'):
                        flash(f'Taux de commission mis à jour à {commission_rate}%. Ce nouveau taux s\'appliquera uniquement aux prochaines commandes.', 'success')
                    else:
                        flash('Erreur lors de la mise à jour du taux de commission.', 'danger')
                else:
                    flash('Le taux de commission doit être entre 0 et 100%.', 'danger')
            except ValueError:
                flash('Taux de commission invalide.', 'danger')
        
        elif action == 'update_shipping':
            # Mise à jour des paramètres de livraison
            try:
                default_shipping_fee = float(request.form.get('default_shipping_fee', 0))
                free_shipping_threshold = float(request.form.get('free_shipping_threshold', 0))
                
                if default_shipping_fee >= 0 and free_shipping_threshold >= 0:
                    success = True
                    success &= update_site_setting('shipping_fee', default_shipping_fee, 'Frais de livraison par défaut')
                    success &= update_site_setting('default_shipping_fee', default_shipping_fee, 'Frais de livraison par défaut (compatibilité)')
                    success &= update_site_setting('free_shipping_threshold', free_shipping_threshold, 'Seuil pour livraison gratuite')
                    
                    if success:
                        flash('Paramètres de livraison mis à jour avec succès.', 'success')
                    else:
                        flash('Erreur lors de la mise à jour des paramètres de livraison.', 'danger')
                else:
                    flash('Les frais de livraison doivent être des montants positifs.', 'danger')
            except ValueError:
                flash('Paramètres de livraison invalides.', 'danger')
        
        elif action == 'update_shipping_rates':
            # Mise à jour des tarifs de livraison par région
            try:
                # Récupérer les paramètres généraux
                free_shipping_threshold = float(request.form.get('free_shipping_threshold', 50000))
                
                # Récupérer les tarifs par région
                shipping_rates = {}
                regions = ['grande-comore', 'anjouan', 'moheli', 'default']
                
                for region in regions:
                    standard_fee = float(request.form.get(f'{region}_standard', 0))
                    express_fee = float(request.form.get(f'{region}_express', 0))
                    
                    if standard_fee >= 0 and express_fee >= 0:
                        shipping_rates[region] = {
                            'standard': standard_fee,
                            'express': express_fee
                        }
                    else:
                        flash(f'Les frais de livraison pour {region} doivent être des montants positifs.', 'danger')
                        return redirect(url_for('admin_settings'))
                
                # Mettre à jour dans la base de données
                success = True
                success &= update_site_setting('shipping_rates', shipping_rates, 'Tarifs de livraison par région')
                success &= update_site_setting('free_shipping_threshold', free_shipping_threshold, 'Seuil pour livraison gratuite')
                success &= update_site_setting('shipping_fee', shipping_rates['default']['standard'], 'Frais de livraison standard (compatibilité)')
                success &= update_site_setting('default_shipping_fee', shipping_rates['default']['standard'], 'Frais de livraison par défaut (compatibilité)')
                
                # Mettre à jour la variable globale pour la compatibilité
                globals()['site_settings'].update({
                    'shipping_rates': shipping_rates,
                    'free_shipping_threshold': free_shipping_threshold,
                    'shipping_fee': shipping_rates['default']['standard'],
                    'default_shipping_fee': shipping_rates['default']['standard'],
                })
                
                if success:
                    flash('Tarifs de livraison par région mis à jour avec succès.', 'success')
                else:
                    flash('Erreur lors de la mise à jour des tarifs de livraison.', 'danger')
                
            except ValueError as e:
                flash(f'Erreur dans les tarifs de livraison: {str(e)}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
        
        elif action == 'update_shipping_price_ranges':
            # Mise à jour des tranches de prix de livraison
            try:
                # Récupérer l'état d'activation du système
                price_ranges_enabled = 'price_ranges_enabled' in request.form
                
                # Récupérer les paramètres généraux
                free_shipping_threshold = float(request.form.get('free_shipping_threshold_ranges', 50000))
                
                # Récupérer les tranches de prix
                ranges = []
                range_count = 0
                
                # Compter le nombre de tranches définies
                for key in request.form.keys():
                    if key.startswith('range_') and key.endswith('_min'):
                        range_count += 1
                
                for i in range(range_count):
                    min_price = request.form.get(f'range_{i}_min', '')
                    max_price = request.form.get(f'range_{i}_max', '')
                    standard_fee = request.form.get(f'range_{i}_standard', '')
                    express_fee = request.form.get(f'range_{i}_express', '')
                    
                    if min_price and standard_fee and express_fee:
                        try:
                            min_val = float(min_price)
                            max_val = float(max_price) if max_price else None  # None au lieu de float('inf')
                            standard_val = float(standard_fee)
                            express_val = float(express_fee)
                            
                            if min_val >= 0 and standard_val >= 0 and express_val >= 0:
                                ranges.append({
                                    'min': min_val,
                                    'max': max_val,
                                    'standard': standard_val,
                                    'express': express_val
                                })
                            else:
                                flash(f'Les valeurs de la tranche {i+1} doivent être positives.', 'danger')
                                return redirect(url_for('admin_settings'))
                        except ValueError:
                            flash(f'Erreur dans les valeurs de la tranche {i+1}.', 'danger')
                            return redirect(url_for('admin_settings'))
                
                # Trier les tranches par prix minimum
                ranges.sort(key=lambda x: x['min'])
                
                # Mettre à jour dans la base de données
                shipping_price_ranges_data = {
                    'enabled': price_ranges_enabled,
                    'ranges': ranges
                }
                
                success = True
                success &= update_site_setting('shipping_price_ranges', shipping_price_ranges_data, 'Tranches de prix de livraison')
                success &= update_site_setting('free_shipping_threshold', free_shipping_threshold, 'Seuil pour livraison gratuite')
                
                # Mettre à jour la variable globale pour la compatibilité
                globals()['site_settings'].update({
                    'shipping_price_ranges': shipping_price_ranges_data,
                    'free_shipping_threshold': free_shipping_threshold,
                })
                
                status_text = "activé" if price_ranges_enabled else "désactivé"
                if success:
                    flash(f'Système de tranches de prix {status_text} avec {len(ranges)} tranche(s) configurée(s).', 'success')
                else:
                    flash('Erreur lors de la mise à jour des tranches de prix.', 'danger')
                
            except ValueError as e:
                flash(f'Erreur dans la configuration des tranches de prix: {str(e)}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
        
        elif action == 'update_admin_profile':
            # Mise à jour du profil admin
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            
            if first_name and last_name:
                # Récupérer l'ID de l'admin depuis le dictionnaire employees_db
                admin_id = employees_db[admin_email].get('id')
                
                # Mettre à jour dans la base de données SQLite
                admin_record = Admin.query.filter_by(id=admin_id).first()
                if admin_record:
                    admin_record.first_name = first_name
                    admin_record.last_name = last_name
                    admin_record.phone = phone
                    admin_record.updated_at = datetime.now()
                    db.session.commit()
                    print(f"✅ Profil admin ID {admin_id} mis à jour dans la base de données")
                
                # Mettre à jour le dictionnaire en mémoire
                employees_db[admin_email].update({
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': phone,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                flash('Profil administrateur mis à jour avec succès.', 'success')
            else:
                flash('Le prénom et le nom sont obligatoires.', 'danger')
        
        elif action == 'update_logo':
            # Mise à jour du logo du site
            try:
                logo_file = request.files.get('logo_file')
                logo_alt_text = request.form.get('logo_alt_text', '').strip()
                
                if logo_file and logo_file.filename:
                    # Vérifier le type de fichier
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
                    file_extension = logo_file.filename.rsplit('.', 1)[1].lower() if '.' in logo_file.filename else ''
                    
                    if file_extension not in allowed_extensions:
                        flash('Format de fichier non supporté. Utilisez PNG, JPG, JPEG, GIF ou SVG.', 'danger')
                        return redirect(url_for('admin_settings'))
                    
                    # Créer le dossier uploads s'il n'existe pas
                    upload_folder = os.path.join('static', 'uploads', 'logos')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    # Générer un nom de fichier unique
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"logo_{timestamp}.{file_extension}"
                    file_path = os.path.join(upload_folder, filename)
                    
                    # Récupérer l'ancien logo depuis la base de données
                    old_logo_setting = SiteSettings.query.filter_by(key='logo_url').first()
                    if old_logo_setting and old_logo_setting.value:
                        old_logo_url = old_logo_setting.value
                        if old_logo_url.startswith('/static/uploads/logos/'):
                            old_logo_path = old_logo_url[1:]  # Enlever le '/' du début
                            if os.path.exists(old_logo_path):
                                try:
                                    os.remove(old_logo_path)
                                    print(f"✅ Ancien logo supprimé: {old_logo_path}")
                                except Exception as e:
                                    print(f"⚠️ Erreur lors de la suppression de l'ancien logo: {e}")
                    
                    # Sauvegarder le nouveau fichier
                    logo_file.save(file_path)
                    print(f"✅ Nouveau logo sauvegardé: {file_path}")
                    
                    # Mettre à jour dans la base de données
                    logo_url = f"/static/uploads/logos/{filename}"
                    success = True
                    success &= update_site_setting('logo_url', logo_url, 'URL du logo du site')
                    
                    # Récupérer le nom du site depuis la base de données pour le texte alternatif
                    current_site_settings = get_all_site_settings()
                    success &= update_site_setting('logo_alt_text', logo_alt_text or current_site_settings.get('site_name', 'DOUKA KM'), 'Texte alternatif du logo')
                    
                    if success:
                        flash('Logo mis à jour avec succès.', 'success')
                    else:
                        flash('Erreur lors de la sauvegarde du logo en base de données.', 'danger')
                else:
                    # Mise à jour seulement du texte alternatif
                    if logo_alt_text:
                        if update_site_setting('logo_alt_text', logo_alt_text, 'Texte alternatif du logo'):
                            flash('Texte alternatif du logo mis à jour.', 'success')
                        else:
                            flash('Erreur lors de la mise à jour du texte alternatif.', 'danger')
                    else:
                        flash('Aucun fichier sélectionné et aucun texte alternatif fourni.', 'warning')
                        
            except Exception as e:
                print(f"❌ Erreur lors de la mise à jour du logo: {str(e)}")
                flash(f'Erreur lors de la mise à jour du logo: {str(e)}', 'danger')
        
        elif action == 'remove_logo':
            # Suppression du logo
            try:
                # Récupérer l'URL du logo depuis la base de données
                old_logo_setting = SiteSettings.query.filter_by(key='logo_url').first()
                if old_logo_setting and old_logo_setting.value:
                    old_logo_url = old_logo_setting.value
                    if old_logo_url.startswith('/static/uploads/logos/'):
                        old_logo_path = old_logo_url[1:]  # Enlever le '/' du début
                        if os.path.exists(old_logo_path):
                            try:
                                os.remove(old_logo_path)
                                print(f"✅ Logo supprimé: {old_logo_path}")
                            except Exception as e:
                                print(f"⚠️ Erreur lors de la suppression du logo: {e}")
                
                # Supprimer les entrées de la base de données
                success = True
                logo_url_setting = SiteSettings.query.filter_by(key='logo_url').first()
                if logo_url_setting:
                    db.session.delete(logo_url_setting)
                
                logo_alt_setting = SiteSettings.query.filter_by(key='logo_alt_text').first()
                if logo_alt_setting:
                    db.session.delete(logo_alt_setting)
                
                db.session.commit()
                print("✅ Paramètres de logo supprimés de la base de données")
                
                # Mettre à jour la variable globale
                if 'logo_url' in globals()['site_settings']:
                    del globals()['site_settings']['logo_url']
                if 'logo_alt_text' in globals()['site_settings']:
                    del globals()['site_settings']['logo_alt_text']
                
                if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                    # Requête AJAX
                    return jsonify({'success': True, 'message': 'Logo supprimé avec succès.'})
                else:
                    flash('Logo supprimé avec succès.', 'success')
                    
            except Exception as e:
                db.session.rollback()
                error_msg = f'Erreur lors de la suppression du logo: {str(e)}'
                print(f"❌ {error_msg}")
                if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                    return jsonify({'success': False, 'message': error_msg})
                else:
                    flash(error_msg, 'danger')
        
        elif action == 'change_password':
            # Changement de mot de passe
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not all([current_password, new_password, confirm_password]):
                flash('Tous les champs du mot de passe sont obligatoires.', 'danger')
            elif new_password != confirm_password:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
            elif len(new_password) < 6:
                flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            else:
                # Récupérer l'admin depuis employees_db avec vérification du mot de passe
                admin_data = employees_db.get(admin_email)
                if not admin_data or 'password_hash' not in admin_data:
                    flash('Erreur: données administrateur introuvables.', 'danger')
                elif not check_password_hash(admin_data['password_hash'], current_password):
                    flash('Le mot de passe actuel est incorrect.', 'danger')
                else:
                    # Récupérer l'ID de l'admin
                    admin_id = admin_data.get('id')
                    
                    # Mettre à jour dans la base de données SQLite
                    admin_record = Admin.query.filter_by(id=admin_id).first()
                    if admin_record:
                        admin_record.password_hash = generate_password_hash(new_password)
                        admin_record.updated_at = datetime.now()
                        db.session.commit()
                        print(f"✅ Mot de passe admin ID {admin_id} mis à jour dans la base de données")
                    
                    # Mettre à jour le dictionnaire en mémoire
                    employees_db[admin_email]['password_hash'] = generate_password_hash(new_password)
                    employees_db[admin_email]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    flash('Mot de passe modifié avec succès.', 'success')
        
        return redirect(url_for('admin_settings'))
    
    # Récupérer les paramètres actuels depuis la base de données
    current_site_settings = get_all_site_settings()
    
    # **NOUVELLE VERSION: Statistiques incluant commandes DB + admin**
    total_users = len(users_db)
    total_merchants = len(merchants_db)
    total_products = len(get_all_products())
    
    # Calculer le total des commandes depuis la DB d'abord
    from db_helpers import get_all_merchant_orders, get_admin_orders_count
    all_db_orders = get_all_merchant_orders()
    admin_orders_count = get_admin_orders_count()
    
    # Fallback: ajouter les commandes des dictionnaires non migrées
    dictionary_orders_count = sum(len(merchant.get('orders', [])) for merchant in merchants_db.values())
    
    # Total des commandes = DB marchands + admin + dictionnaire fallback
    total_orders = len(all_db_orders) + admin_orders_count + dictionary_orders_count
    
    system_stats = {
        'total_users': total_users,
        'total_merchants': total_merchants,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_categories': len(admin_categories_db),
        'total_subcategories': len(admin_subcategories_db),
        'active_merchants': len([m for m in merchants_db.values() if m.get('store_verified', False)]),
        'pending_merchants': len([m for m in merchants_db.values() if not m.get('store_verified', False)])
    }
    
    return render_template('admin/settings.html',
                          site_settings=current_site_settings,
                          system_stats=system_stats)

@app.route('/admin/commission-rates', methods=['GET', 'POST'])
@permission_required(['super_admin', 'admin'])
def admin_commission_rates():
    """Gestion des taux de commission par catégorie"""
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_rates':
            try:
                # Récupérer toutes les catégories actives
                categories = Category.query.filter_by(active=True).all()
                
                for category in categories:
                    rate_input = request.form.get(f'rate_{category.id}')
                    if rate_input:
                        try:
                            rate_value = float(rate_input)
                            if 0 <= rate_value <= 100:
                                # Chercher un taux existant ou en créer un nouveau
                                existing_rate = CategoryCommissionRate.query.filter_by(category_id=category.id).first()
                                
                                if existing_rate:
                                    existing_rate.commission_rate = rate_value
                                    existing_rate.updated_at = datetime.utcnow()
                                else:
                                    new_rate = CategoryCommissionRate(
                                        category_id=category.id,
                                        commission_rate=rate_value,
                                        created_by=session.get('admin_email', 'Admin')
                                    )
                                    db.session.add(new_rate)
                            else:
                                flash(f'Le taux pour {category.name} doit être entre 0 et 100%', 'warning')
                                continue
                        except ValueError:
                            flash(f'Taux invalide pour {category.name}', 'warning')
                            continue
                
                db.session.commit()
                flash('Taux de commission mis à jour avec succès!', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
                
        elif action == 'reset_rate':
            category_id = request.form.get('category_id')
            try:
                rate = CategoryCommissionRate.query.filter_by(category_id=category_id).first()
                if rate:
                    db.session.delete(rate)
                    db.session.commit()
                    flash('Taux réinitialisé au taux par défaut', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la réinitialisation: {str(e)}', 'danger')
    
    # Récupérer les données pour l'affichage
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    
    # Récupérer les taux existants
    commission_rates = {}
    for rate in CategoryCommissionRate.query.all():
        commission_rates[rate.category_id] = rate
    
    # Récupérer le taux par défaut
    site_settings = get_site_settings()
    default_rate = site_settings.get('commission_rate', 15.0)
    
    # Préparer les données pour le template
    category_data = []
    for category in categories:
        current_rate = commission_rates.get(category.id)
        category_data.append({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'icon': category.icon or 'fas fa-folder',
            'current_rate': current_rate.commission_rate if current_rate else default_rate,
            'is_custom': current_rate is not None,
            'rate_object': current_rate
        })
    
    return render_template('admin/commission_rates.html',
                          categories=category_data,
                          default_rate=default_rate)

def format_delivery_time(days, hours):
    """Formater le temps de livraison en texte lisible"""
    if not days and not hours:
        return "Immédiat"
    
    parts = []
    if days:
        if days == 1:
            parts.append("1 jour")
        else:
            parts.append(f"{days} jours")
    
    if hours:
        if hours == 1:
            parts.append("1 heure")
        else:
            parts.append(f"{hours} heures")
    
    if len(parts) == 2:
        return f"{parts[0]} et {parts[1]}"
    elif len(parts) == 1:
        return parts[0]
    else:
        return "Délai non défini"

def get_shipping_rates_for_product(product):
    """Obtenir les tarifs de livraison pour un produit donné"""
    import json
    
    # Récupérer les paramètres de base
    site_settings = get_all_site_settings()
    default_shipping_fee = site_settings.get('shipping_fee', 1500)
    
    # Récupérer les tarifs personnalisés
    try:
        custom_rates_json = get_site_setting('custom_shipping_rates', '[]')
        custom_rates = json.loads(custom_rates_json) if custom_rates_json else []
    except:
        custom_rates = []
    
    # Valeurs par défaut
    standard_rate = default_shipping_fee
    express_rate = default_shipping_fee + 1000
    standard_delivery_time = format_delivery_time(3, 0)
    express_delivery_time = format_delivery_time(1, 0)
    
    # Rechercher un tarif spécifique pour ce produit
    product_category_id = product.get('category_id')
    product_subcategory_id = product.get('subcategory_id')
    
    # Chercher d'abord par sous-catégorie (plus spécifique)
    if product_subcategory_id:
        for rate in custom_rates:
            if (rate.get('rate_type') == 'subcategory' and 
                rate.get('subcategory_id') == product_subcategory_id and 
                rate.get('active', True)):
                standard_rate = rate['standard_rate']
                express_rate = rate['express_rate']
                standard_delivery_time = format_delivery_time(
                    rate.get('standard_delivery_days', 3),
                    rate.get('standard_delivery_hours', 0)
                )
                express_delivery_time = format_delivery_time(
                    rate.get('express_delivery_days', 1),
                    rate.get('express_delivery_hours', 0)
                )
                break
    
    # Sinon, chercher par catégorie
    if product_category_id and standard_rate == default_shipping_fee:
        for rate in custom_rates:
            if (rate.get('rate_type') == 'category' and 
                rate.get('category_id') == product_category_id and 
                rate.get('active', True)):
                standard_rate = rate['standard_rate']
                express_rate = rate['express_rate']
                standard_delivery_time = format_delivery_time(
                    rate.get('standard_delivery_days', 3),
                    rate.get('standard_delivery_hours', 0)
                )
                express_delivery_time = format_delivery_time(
                    rate.get('express_delivery_days', 1),
                    rate.get('express_delivery_hours', 0)
                )
                break
    
    return {
        'standard_rate': standard_rate,
        'express_rate': express_rate,
        'standard_delivery_time': standard_delivery_time,
        'express_delivery_time': express_delivery_time,
        'free_shipping_threshold': site_settings.get('free_shipping_threshold', 15000)
    }

def get_or_create_default_shipping_rate():
    """Obtenir ou créer le tarif de livraison par défaut"""
    import json
    
    # Récupérer les tarifs personnalisés
    try:
        custom_rates_json = get_site_setting('custom_shipping_rates', '[]')
        custom_rates = json.loads(custom_rates_json) if custom_rates_json else []
    except:
        custom_rates = []
    
    # Chercher le tarif par défaut existant
    default_rate = None
    for rate in custom_rates:
        if rate.get('rate_type') == 'default' and rate.get('is_system_default', False):
            default_rate = rate
            break
    
    # Si pas trouvé, créer le tarif par défaut
    if not default_rate:
        site_settings = get_all_site_settings()
        default_rate = {
            'id': 1,
            'name': 'Livraison Standard (Par défaut)',
            'rate_type': 'default',
            'category_id': None,
            'subcategory_id': None,
            'standard_rate': site_settings.get('shipping_fee', 1500),
            'express_rate': site_settings.get('shipping_fee', 1500) + 1000,
            'standard_delivery_days': 3,
            'standard_delivery_hours': 0,
            'express_delivery_days': 1,
            'express_delivery_hours': 0,
            'priority': 0,
            'active': True,
            'is_system_default': True,
            'created_at': str(datetime.now())
        }
        
        # Ajouter aux tarifs personnalisés et sauvegarder
        custom_rates.insert(0, default_rate)  # Mettre en premier
        rates_json = json.dumps(custom_rates)
        update_site_setting('custom_shipping_rates', rates_json)
    
    return default_rate

@app.route('/admin/shipping-rates', methods=['GET', 'POST'])
@permission_required(['super_admin', 'admin'])
def admin_shipping_rates():
    """Page de gestion des tarifs de livraison"""
    
    if request.method == 'POST':
        # Traitement des formulaires POST
        action = request.form.get('action')
        
        print(f"DEBUG: Action reçue = {action}")
        print(f"DEBUG: Données du formulaire = {dict(request.form)}")
        
        if action == 'create':
            # Ajouter un nouveau tarif dans la base de données
            try:
                from db_helpers import create_shipping_rate_safe
                
                # Récupérer les données du formulaire
                name = request.form.get('name', '').strip()
                rate_type = request.form.get('rate_type', '')
                category_id = request.form.get('category_id', '')
                subcategory_id = request.form.get('subcategory_id', '')
                standard_rate = float(request.form.get('standard_rate', 0))
                express_rate = float(request.form.get('express_rate', 0))
                priority = int(request.form.get('priority', 0))
                active = 'active' in request.form  # Correction pour checkbox
                
                print(f"DEBUG: Création tarif - type='{rate_type}', cat_id='{category_id}', sub_id='{subcategory_id}'")
                print(f"DEBUG: Tarifs - standard={standard_rate}, express={express_rate}, active={active}")
                
                # Validation des données
                if not name:
                    flash('Le nom du tarif est obligatoire', 'error')
                    return redirect(url_for('admin_shipping_rates'))
                
                if not rate_type:
                    flash('Le type de tarif est obligatoire', 'error')
                    return redirect(url_for('admin_shipping_rates'))
                
                if standard_rate <= 0:
                    flash('Le tarif standard doit être supérieur à 0', 'error')
                    return redirect(url_for('admin_shipping_rates'))
                
                if express_rate <= 0:
                    express_rate = standard_rate + 1000  # Valeur par défaut
                
                # Convertir les IDs en int si non vides
                category_id_int = int(category_id) if category_id and category_id.strip() else None
                subcategory_id_int = int(subcategory_id) if subcategory_id and subcategory_id.strip() else None
                
                # Vérifier qu'une catégorie est spécifiée pour les types 'category'
                if rate_type == 'category' and not category_id_int:
                    flash('Une catégorie doit être sélectionnée pour ce type de tarif', 'error')
                    return redirect(url_for('admin_shipping_rates'))
                
                # Vérifier qu'une sous-catégorie est spécifiée pour les types 'subcategory'
                if rate_type == 'subcategory' and not subcategory_id_int:
                    flash('Une sous-catégorie doit être sélectionnée pour ce type de tarif', 'error')
                    return redirect(url_for('admin_shipping_rates'))
                
                # Créer le nouveau tarif avec la fonction sécurisée
                new_rate = create_shipping_rate_safe(
                    name=name,
                    rate_type=rate_type,
                    category_id=category_id_int,
                    subcategory_id=subcategory_id_int,
                    standard_rate=standard_rate,
                    express_rate=express_rate,
                    priority=priority,
                    active=active
                )
                
                if new_rate:
                    print(f"DEBUG: Nouveau tarif créé avec ID: {new_rate.id}")
                    flash(f"Tarif '{name}' créé avec succès !", 'success')
                else:
                    flash('Erreur lors de la création du tarif', 'error')
                
            except ValueError as ve:
                print(f"DEBUG: Erreur de valeur = {ve}")
                flash('Erreur dans les valeurs saisies (vérifiez les montants)', 'error')
            except Exception as e:
                print(f"DEBUG: Erreur création tarif = {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erreur lors de la création du tarif : {str(e)}', 'error')
                
        elif action == 'update':
            # Mettre à jour un tarif existant depuis la base de données
            try:
                from db_helpers import update_shipping_rate_safe
                
                rate_id = int(request.form.get('rate_id', 0))
                name = request.form.get('name', '').strip()
                rate_type = request.form.get('rate_type', '').strip()
                standard_rate = float(request.form.get('standard_rate', 0))
                express_rate = float(request.form.get('express_rate', 0))
                priority = int(request.form.get('priority', 0))
                active = bool(request.form.get('active'))
                category_id = request.form.get('category_id', '').strip()
                subcategory_id = request.form.get('subcategory_id', '').strip()
                
                print(f"DEBUG: Mise à jour tarif ID={rate_id}, standard={standard_rate}")
                
                # Convertir les IDs en int si non vides
                category_id_int = int(category_id) if category_id else None
                subcategory_id_int = int(subcategory_id) if subcategory_id else None
                
                # Mettre à jour le tarif avec la fonction sécurisée
                updated_rate = update_shipping_rate_safe(
                    rate_id=rate_id,
                    name=name,
                    rate_type=rate_type,
                    category_id=category_id_int,
                    subcategory_id=subcategory_id_int,
                    standard_rate=standard_rate,
                    express_rate=express_rate,
                    priority=priority,
                    active=active
                )
                
                if updated_rate:
                    # Si c'est le tarif par défaut, mettre à jour aussi le paramètre site
                    if rate_type == 'default':
                        update_site_setting('shipping_fee', standard_rate)
                    
                    print(f"DEBUG: Tarif '{name}' (ID={rate_id}) mis à jour avec succès")
                    flash(f"Tarif '{name}' mis à jour avec succès !", 'success')
                else:
                    print(f"DEBUG: Tarif ID={rate_id} non trouvé en base de données")
                    flash('Tarif non trouvé', 'error')
                
            except Exception as e:
                print(f"DEBUG: Erreur mise à jour = {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erreur lors de la mise à jour : {str(e)}', 'error')
                
        elif action == 'delete':
            # Supprimer un tarif depuis la base de données
            try:
                from db_helpers import delete_shipping_rate_safe, get_shipping_rates_safe
                
                rate_id = int(request.form.get('rate_id', 0))
                print(f"DEBUG: Tentative suppression tarif ID={rate_id}")
                
                # Récupérer le tarif pour vérifier s'il existe et récupérer son nom
                rates = get_shipping_rates_safe()
                rate_to_delete = next((r for r in rates if r.id == rate_id), None)
                
                if rate_to_delete:
                    # Vérifier si c'est le tarif par défaut
                    if rate_to_delete.rate_type == 'default':
                        flash('Le tarif par défaut ne peut pas être supprimé, mais il peut être modifié', 'warning')
                        return redirect(url_for('admin_shipping_rates'))
                    
                    # Supprimer le tarif avec la fonction sécurisée
                    rate_name = rate_to_delete.name
                    if delete_shipping_rate_safe(rate_id):
                        print(f"DEBUG: Tarif '{rate_name}' (ID={rate_id}) supprimé avec succès")
                        flash(f"Tarif '{rate_name}' supprimé avec succès !", 'success')
                    else:
                        flash('Erreur lors de la suppression du tarif', 'error')
                else:
                    print(f"DEBUG: Tarif ID={rate_id} non trouvé en base de données")
                    flash('Tarif non trouvé', 'error')
                    
            except Exception as e:
                print(f"DEBUG: Erreur suppression = {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erreur lors de la suppression : {str(e)}', 'error')
                
        elif action == 'toggle_status':
            # Activer/désactiver un tarif depuis la base de données
            try:
                from models import ShippingRate, db
                
                rate_id = int(request.form.get('rate_id', 0))
                print(f"DEBUG: Basculement statut pour tarif ID={rate_id}")
                
                # Récupérer le tarif depuis la base de données
                rate = ShippingRate.query.get(rate_id)
                
                if rate:
                    # Vérifier si c'est le tarif par défaut
                    if rate.rate_type == 'default':
                        flash('Le tarif par défaut est toujours actif', 'info')
                        return redirect(url_for('admin_shipping_rates'))
                    
                    # Basculer le statut du tarif
                    rate.active = not rate.active
                    db.session.commit()
                    
                    new_status = 'activé' if rate.active else 'désactivé'
                    print(f"DEBUG: Tarif '{rate.name}' (ID={rate_id}) {new_status}")
                    flash(f"Tarif '{rate.name}' {new_status} avec succès", 'success')
                else:
                    print(f"DEBUG: Tarif ID={rate_id} non trouvé en base de données")
                    flash('Tarif non trouvé', 'error')
                    
            except Exception as e:
                print(f"DEBUG: Erreur changement statut = {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erreur lors du changement de statut : {str(e)}', 'error')
        
        else:
            print(f"DEBUG: Action non reconnue = {action}")
            flash('Action non reconnue', 'error')
        
        return redirect(url_for('admin_shipping_rates'))
    
    # GET request - afficher la page
    
    # Récupérer les paramètres de livraison actuels
    site_settings = get_all_site_settings()
    
    # **NOUVEAU : Récupérer les tarifs depuis la table ShippingRate**
    try:
        from models import ShippingRate, Category, Subcategory
        from db_helpers import get_shipping_rates_safe
        
        # Récupérer tous les tarifs (actifs et inactifs) depuis la base de données de manière sécurisée
        db_rates = get_shipping_rates_safe()
        
        # Créer une structure de données compatible avec le template
        shipping_rates = []
        
        for rate in db_rates:
            # Récupérer les noms des catégories
            category_name = rate.category.name if rate.category else None
            subcategory_name = rate.subcategory.name if rate.subcategory else None
            
            # Déterminer le type d'affichage
            if rate.rate_type == 'default':
                rate_type_display = 'Tarif par défaut'
            elif rate.rate_type == 'category':
                rate_type_display = f'Par catégorie: {category_name}'
            elif rate.rate_type == 'subcategory':
                rate_type_display = f'Par sous-catégorie: {subcategory_name}'
            else:
                rate_type_display = 'Tarif général'
            
            # Formatter les délais de livraison avec des valeurs par défaut sécurisées
            def format_delivery_time(days, hours=0):
                days = days or 0  # Convertir None en 0
                hours = hours or 0  # Convertir None en 0
                if days == 0 and hours == 0:
                    return "Livraison immédiate"
                elif days == 0:
                    return f"{hours}h"
                elif hours == 0:
                    return f"{days} jour{'s' if days > 1 else ''}"
                else:
                    return f"{days} jour{'s' if days > 1 else ''} {hours}h"
            
            # Utiliser des valeurs par défaut pour les colonnes manquantes
            standard_delivery_days = getattr(rate, 'standard_delivery_days', 3)
            standard_delivery_hours = getattr(rate, 'standard_delivery_hours', 0)
            express_delivery_days = getattr(rate, 'express_delivery_days', 1)
            express_delivery_hours = getattr(rate, 'express_delivery_hours', 0)
            
            shipping_rates.append({
                'id': rate.id,
                'name': rate.name,
                'rate_type': rate_type_display,
                'category_name': category_name,
                'subcategory_name': subcategory_name,
                'category_id': rate.category_id,
                'subcategory_id': rate.subcategory_id,
                'active': rate.active,
                'standard_rate': rate.standard_rate,
                'express_rate': rate.express_rate,
                'standard_delivery_formatted': format_delivery_time(standard_delivery_days, standard_delivery_hours),
                'express_delivery_formatted': format_delivery_time(express_delivery_days, express_delivery_hours),
                'standard_delivery_days': standard_delivery_days,
                'standard_delivery_hours': standard_delivery_hours,
                'express_delivery_days': express_delivery_days,
                'express_delivery_hours': express_delivery_hours,
                'priority': rate.priority,
                'free_threshold': site_settings.get('free_shipping_threshold', 15000),
                'description': f'Tarif personnalisé pour {rate_type_display.lower()}'
            })
            
        print(f"DEBUG: Affichage de {len(shipping_rates)} tarifs depuis la base de données")
        
    except Exception as e:
        print(f"Erreur lors du chargement des tarifs ShippingRate: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback vers l'ancien système en cas d'erreur
        shipping_rates = []
    
    return render_template('admin/shipping_rates.html',
                          shipping_rates=shipping_rates,
                          site_settings=site_settings,
                          categories=Category.query.filter_by(active=True).all(),
                          subcategories=Subcategory.query.filter_by(active=True).all())

@app.route('/admin/profile')
def admin_profile():
    """Page de profil de l'administrateur"""
    # Vérifier l'authentification admin
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    admin_id = session['admin_id']
    admin = employees_db.get(admin_id)
    
    if not admin:
        flash('Session administrative invalide', 'error')
        return redirect(url_for('admin_login'))
    
    return render_template('admin/profile.html', admin=admin)

@app.route('/admin/logout')
def admin_logout():
    """Déconnecte l'administrateur et redirige vers la page de connexion admin"""
    # Vérifier si nous avons une session utilisateur précédente à restaurer
    prev_session = None
    if 'prev_session' in session:
        prev_session = session.get('prev_session')
    
    # Vider la session actuelle
    session.clear()
    
    # Restaurer la session utilisateur précédente si elle existe
    if prev_session:
        for key, value in prev_session.items():
            # Ne pas restaurer les clés liées à l'administration
            if not key.startswith('admin_'):
                session[key] = value
    
    flash('Vous avez été déconnecté du panneau d\'administration.', 'info')
    return redirect(url_for('admin_login'))

# Routes pour la gestion des employés
@app.route('/admin/employees')
@permission_required(['super_admin', 'admin'])
def admin_employees():
    """Page de gestion des employés - Version migrée DATABASE-ONLY"""
    employees = []
    
    # **DATABASE-ONLY**: Récupérer uniquement les employés depuis la base de données
    try:
        # Récupérer les employés depuis la table Employee
        db_employees = Employee.query.all()
        for employee_record in db_employees:
            employees.append({
                'display_id': f'EMP_{employee_record.id}',
                'real_id': f'emp_{employee_record.id}',  # Préfixe pour différencier
                'source': 'database',
                'email': employee_record.email,
                'first_name': employee_record.first_name,
                'last_name': employee_record.last_name,
                'phone': employee_record.phone or '',
                'role': employee_record.role,
                'status': employee_record.status,
                'created_at': employee_record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': employee_record.last_login.strftime('%Y-%m-%d %H:%M:%S') if employee_record.last_login else 'Jamais',
                'permissions': employee_record.get_permissions()
            })
        
        # Récupérer aussi les administrateurs depuis la table Admin
        db_admins = Admin.query.all()
        for admin_record in db_admins:
            # Vérifier que cet admin n'existe pas déjà comme employé
            if not any(emp['email'] == admin_record.email for emp in employees):
                employees.append({
                    'display_id': f'ADMIN_{admin_record.id}',
                    'real_id': f'admin_{admin_record.id}',  # Préfixe pour différencier
                    'source': 'admin_db',
                    'email': admin_record.email,
                    'first_name': admin_record.first_name,
                    'last_name': admin_record.last_name,
                    'phone': admin_record.phone or '',
                    'role': admin_record.role,
                    'status': admin_record.status,  # Utiliser directement le status
                    'created_at': admin_record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_login': admin_record.last_login.strftime('%Y-%m-%d %H:%M:%S') if admin_record.last_login else 'Jamais',
                    'permissions': ['all'] if admin_record.role == 'super_admin' else [admin_record.role]
                })
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement des employés depuis la base de données: {str(e)}")
    
    # Trier par date de création (plus récent en premier)
    employees.sort(key=lambda x: x['created_at'], reverse=True)
    
    print(f"✅ Employés chargés depuis la base de données uniquement: {len(employees)}")
    
    return render_template('admin/employees.html', employees=employees)

@app.route('/admin/employees/add', methods=['GET', 'POST'])
@permission_required(['super_admin', 'admin'])
def admin_add_employee():
    """Ajouter un nouvel employé - Version migrée vers base de données"""
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        first_name = request.form.get('first_name').strip()
        last_name = request.form.get('last_name').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role')
        password = request.form.get('password')
        
        # Validation
        if not all([email, first_name, last_name, role, password]):
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('admin/employee_form.html', action='add')
        
        # Vérifier si l'email existe déjà dans la base de données
        existing_employee = Employee.query.filter_by(email=email).first()
        if existing_employee:
            flash('Cet email est déjà utilisé par un employé.', 'danger')
            return render_template('admin/employee_form.html', action='add')
        
        # Vérifier si l'email existe dans l'ancien système
        if email in employees_db or email in admins_db:
            flash('Cet email est déjà utilisé dans l\'ancien système.', 'danger')
            return render_template('admin/employee_form.html', action='add')
        
        # Vérifier le rôle
        if role not in ['livreur', 'manager', 'admin']:
            flash('Rôle invalide.', 'danger')
            return render_template('admin/employee_form.html', action='add')
        
        # Créer le nouvel employé dans la base de données
        try:
            new_employee = Employee(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                status='active'
            )
            new_employee.set_password(password)
            
            # Définir les permissions par défaut selon le rôle
            default_permissions = {
                'livreur': ['livreur'],
                'manager': ['manager', 'livreur'],
                'admin': ['admin', 'manager', 'livreur']
            }
            new_employee.set_permissions(default_permissions.get(role, [role]))
            
            db.session.add(new_employee)
            db.session.commit()
            
            # Ajouter aussi dans le dictionnaire en mémoire pour compatibilité avec l'ancienne session
            employee_id = str(new_employee.id)
            employees_db[email] = {
                'id': employee_id,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'role': role,
                'password_hash': new_employee.password_hash,
                'created_at': new_employee.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': session.get('admin_email'),
                'is_active': True,
                'permissions': new_employee.get_permissions()
            }
            
            flash(f'Employé {first_name} {last_name} ajouté avec succès dans la base de données.', 'success')
            return redirect(url_for('admin_employees'))
            
        except Exception as e:
            print(f"❌ Erreur lors de la création de l'employé: {e}")
            db.session.rollback()
            flash('Erreur lors de la création de l\'employé.', 'danger')
            return render_template('admin/employee_form.html', action='add')
    
    return render_template('admin/employee_form.html', action='add')

@app.route('/admin/employees/edit/<employee_id>', methods=['GET', 'POST'])
@permission_required(['super_admin', 'admin'])
def admin_edit_employee(employee_id):
    """Modifier un employé existant"""
    # Analyser l'employee_id pour déterminer la source et l'ID réel
    source = None
    real_id = None
    
    if employee_id.startswith('emp_'):
        source = 'database'
        try:
            real_id = int(employee_id.replace('emp_', ''))
        except (ValueError, TypeError):
            flash('ID employé invalide.', 'danger')
            return redirect(url_for('admin_employees'))
    elif employee_id.startswith('admin_'):
        source = 'admin_db'
        try:
            real_id = int(employee_id.replace('admin_', ''))
        except (ValueError, TypeError):
            flash('ID administrateur invalide.', 'danger')
            return redirect(url_for('admin_employees'))
    else:
        # Ancienne méthode - essayer de convertir directement
        try:
            real_id = int(employee_id)
            source = 'legacy'
        except (ValueError, TypeError):
            flash('ID employé invalide.', 'danger')
            return redirect(url_for('admin_employees'))
    
    # Trouver l'employé selon la source
    employee_data = None
    employee_email = None
    db_employee = None
    db_admin = None
    
    if source == 'database':
        # Chercher dans la table Employee
        db_employee = Employee.query.get(real_id)
        if db_employee:
            employee_data = {
                'id': db_employee.id,
                'first_name': db_employee.first_name,
                'last_name': db_employee.last_name,
                'phone': db_employee.phone or '',
                'role': db_employee.role,
                'is_active': db_employee.status == 'active',
                'permissions': db_employee.get_permissions()
            }
            employee_email = db_employee.email
    elif source == 'admin_db':
        # Chercher dans la table Admin
        db_admin = Admin.query.get(real_id)
        if db_admin:
            employee_data = {
                'id': db_admin.id,
                'first_name': db_admin.first_name,
                'last_name': db_admin.last_name,
                'phone': db_admin.phone or '',
                'role': db_admin.role,
                'is_active': db_admin.status == 'active',
                'permissions': ['all'] if db_admin.role == 'super_admin' else [db_admin.role]
            }
            employee_email = db_admin.email
    else:
        # Legacy - chercher dans les deux tables
        db_employee = Employee.query.get(real_id)
        if db_employee:
            employee_data = {
                'id': db_employee.id,
                'first_name': db_employee.first_name,
                'last_name': db_employee.last_name,
                'phone': db_employee.phone or '',
                'role': db_employee.role,
                'is_active': db_employee.status == 'active',
                'permissions': db_employee.get_permissions()
            }
            employee_email = db_employee.email
            source = 'database'
        else:
            db_admin = Admin.query.get(real_id)
            if db_admin:
                employee_data = {
                    'id': db_admin.id,
                    'first_name': db_admin.first_name,
                    'last_name': db_admin.last_name,
                    'phone': db_admin.phone or '',
                    'role': db_admin.role,
                    'is_active': db_admin.status == 'active',
                    'permissions': ['all'] if db_admin.role == 'super_admin' else [db_admin.role]
                }
                employee_email = db_admin.email
                source = 'admin_db'
            else:
                # Fallback: Chercher dans les dictionnaires
                for email, employee in employees_db.items():
                    if int(employee['id']) == real_id:
                        employee_data = employee
                        employee_email = email
                        source = 'legacy'
                        break
    
    if not employee_data:
        flash('Employé introuvable.', 'danger')
        return redirect(url_for('admin_employees'))
    
    if request.method == 'POST':
        first_name = request.form.get('first_name').strip()
        last_name = request.form.get('last_name').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role')
        new_password = request.form.get('password')
        is_active = 'is_active' in request.form
        
        # Validation
        if not all([first_name, last_name, role]):
            flash('Le prénom, nom et rôle sont obligatoires.', 'danger')
            return render_template('admin/employee_form.html', 
                                 employee=employee_data, 
                                 employee_email=employee_email,
                                 action='edit')
        
        # Vérifier le rôle
        if role not in ['livreur', 'manager', 'admin', 'super_admin']:
            flash('Rôle invalide.', 'danger')
            return render_template('admin/employee_form.html', 
                                 employee=employee_data, 
                                 employee_email=employee_email,
                                 action='edit')
        
        try:
            if source == 'database':
                # Mettre à jour dans la table Employee
                db_employee.first_name = first_name
                db_employee.last_name = last_name
                db_employee.phone = phone
                db_employee.role = role
                db_employee.status = 'active' if is_active else 'inactive'
                
                # Mettre à jour le mot de passe si fourni
                if new_password:
                    db_employee.set_password(new_password)
                
                # Définir les permissions par défaut selon le rôle
                default_permissions = {
                    'livreur': ['livreur'],
                    'manager': ['manager', 'livreur'],
                    'admin': ['admin', 'manager', 'livreur'],
                    'super_admin': ['super_admin', 'admin', 'manager', 'livreur']
                }
                db_employee.set_permissions(default_permissions.get(role, [role]))
                
                db.session.commit()
                
                # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité session courante
                if employee_email in employees_db:
                    employees_db[employee_email].update({
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone': phone,
                        'role': role,
                        'is_active': is_active,
                        'permissions': db_employee.get_permissions()
                    })
                
                print(f"✅ Employé DB {employee_email} mis à jour avec succès")
                
            elif source == 'admin_db':
                # Mettre à jour dans la table Admin
                db_admin.first_name = first_name
                db_admin.last_name = last_name
                db_admin.phone = phone
                db_admin.role = role
                db_admin.status = 'active' if is_active else 'inactive'
                
                # Mettre à jour le mot de passe si fourni
                if new_password:
                    db_admin.set_password(new_password)
                
                db.session.commit()
                
                print(f"✅ Administrateur DB {employee_email} mis à jour avec succès")
                
            else:
                # Mettre à jour les données en mémoire (legacy)
                employees_db[employee_email]['first_name'] = first_name
                employees_db[employee_email]['last_name'] = last_name
                employees_db[employee_email]['phone'] = phone
                employees_db[employee_email]['role'] = role
                employees_db[employee_email]['is_active'] = is_active
                
                # Mettre à jour le mot de passe si fourni
                if new_password:
                    from werkzeug.security import generate_password_hash
                    employees_db[employee_email]['password_hash'] = generate_password_hash(new_password)
                
                # Mettre à jour les métadonnées
                employees_db[employee_email]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                employees_db[employee_email]['updated_by'] = session.get('admin_email')
                
                print(f"✅ Employé legacy {employee_email} mis à jour avec succès")
            
            flash(f'Employé {first_name} {last_name} modifié avec succès.', 'success')
            return redirect(url_for('admin_employees'))
            
        except Exception as e:
            print(f"❌ Erreur lors de la modification de l'employé: {e}")
            if source == 'database':
                db.session.rollback()
            flash('Erreur lors de la modification de l\'employé.', 'danger')
    
    return render_template('admin/employee_form.html', 
                         employee=employee_data, 
                         employee_email=employee_email,
                         action='edit')

@app.route('/admin/employees/delete/<employee_id>', methods=['POST'])
@permission_required(['super_admin', 'admin'])
def admin_delete_employee(employee_id):
    """Supprimer un employé - Version DATABASE-ONLY"""
    try:
        employee_id = int(employee_id)
    except (ValueError, TypeError):
        flash('ID employé invalide.', 'danger')
        return redirect(url_for('admin_employees'))
    
    employee_deleted = False
    employee_name = "Employé"
    
    try:
        # **DATABASE-FIRST: Chercher dans la table Employee d'abord**
        db_employee = Employee.query.get(employee_id)
        if db_employee:
            employee_name = f"{db_employee.first_name} {db_employee.last_name}"
            employee_email = db_employee.email
            
            # Supprimer de la base de données
            db.session.delete(db_employee)
            db.session.commit()
            
            # Supprimer aussi du dictionnaire en mémoire si présent (pour compatibilité session)
            if employee_email in employees_db:
                del employees_db[employee_email]
            
            employee_deleted = True
            print(f"✅ Employé supprimé de la table Employee: {employee_email}")
        
        # Si pas trouvé dans Employee, chercher dans la table Admin
        if not employee_deleted:
            db_admin = Admin.query.get(employee_id)
            if db_admin:
                employee_name = f"{db_admin.first_name} {db_admin.last_name}"
                employee_email = db_admin.email
                
                # Supprimer de la base de données
                db.session.delete(db_admin)
                db.session.commit()
                
                # Supprimer aussi du dictionnaire en mémoire si présent
                if employee_email in employees_db:
                    del employees_db[employee_email]
                if employee_email in admins_db:
                    del admins_db[employee_email]
                
                employee_deleted = True
                print(f"✅ Admin supprimé de la table Admin: {employee_email}")
        
        if employee_deleted:
            flash(f'{employee_name} supprimé avec succès de la base de données.', 'success')
        else:
            flash('Employé introuvable dans la base de données.', 'danger')
            
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {str(e)}")
        db.session.rollback()
        flash('Erreur lors de la suppression de l\'employé.', 'danger')
    
    return redirect(url_for('admin_employees'))

@app.route('/admin/livreur-settings', methods=['GET', 'POST'])
@permission_required(['livreur'])
def livreur_settings():
    """Page de paramètres pour les livreurs - modification des informations personnelles - Version migrée vers base de données"""
    admin_email = session.get('admin_email')
    
    # DATABASE-FIRST: Récupérer l'employé depuis la base de données d'abord
    employee_data = None
    db_employee = Employee.query.filter_by(email=admin_email).first()
    source = None
    
    if db_employee:
        employee_data = {
            'id': db_employee.id,
            'email': db_employee.email,
            'first_name': db_employee.first_name,
            'last_name': db_employee.last_name,
            'phone': db_employee.phone or '',
            'role': db_employee.role,
            'permissions': db_employee.get_permissions()
        }
        source = 'database'
    else:
        # Fallback: ancien dictionnaire
        employee_data = employees_db.get(admin_email, {})
        source = 'legacy' if employee_data else None
    
    if not employee_data:
        flash('Profil introuvable.', 'danger')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        if not first_name or not last_name:
            flash('Le prénom et le nom sont obligatoires.', 'danger')
            return render_template('admin/livreur_settings.html', employee=employee_data)
        
        # Vérifier le mot de passe actuel si un nouveau mot de passe est fourni
        if new_password:
            if not current_password:
                flash('Veuillez saisir votre mot de passe actuel.', 'danger')
                return render_template('admin/livreur_settings.html', employee=employee_data)
            
            # Vérifier le mot de passe selon la source des données
            password_valid = False
            if source == 'database':
                password_valid = db_employee.check_password(current_password)
            else:
                password_valid = check_password_hash(employee_data['password_hash'], current_password)
            
            if not password_valid:
                flash('Mot de passe actuel incorrect.', 'danger')
                return render_template('admin/livreur_settings.html', employee=employee_data)
            
            if new_password != confirm_password:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
                return render_template('admin/livreur_settings.html', employee=employee_data)
            
            if len(new_password) < 6:
                flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'danger')
                return render_template('admin/livreur_settings.html', employee=employee_data)
        
        try:
            if source == 'database':
                # Mettre à jour dans la base de données
                db_employee.first_name = first_name
                db_employee.last_name = last_name
                db_employee.phone = phone
                
                # Mettre à jour le mot de passe si fourni
                if new_password:
                    db_employee.set_password(new_password)
                
                db.session.commit()
                
                # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité session courante
                if admin_email in employees_db:
                    employees_db[admin_email].update({
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone': phone,
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    if new_password:
                        employees_db[admin_email]['password_hash'] = generate_password_hash(new_password)
                
                print(f"✅ Profil livreur DB {admin_email} mis à jour avec succès")
                
            else:
                # Mettre à jour le dictionnaire en mémoire (legacy)
                employees_db[admin_email]['first_name'] = first_name
                employees_db[admin_email]['last_name'] = last_name
                employees_db[admin_email]['phone'] = phone
                
                # Mettre à jour le mot de passe si fourni
                if new_password:
                    employees_db[admin_email]['password_hash'] = generate_password_hash(new_password)
                
                # Mettre à jour la date de modification
                employees_db[admin_email]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"✅ Profil livreur legacy {admin_email} mis à jour avec succès")
            
            flash('Vos informations ont été mises à jour avec succès.', 'success')
            return redirect(url_for('livreur_settings'))
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du profil livreur: {e}")
            if source == 'database':
                db.session.rollback()
            flash('Erreur lors de la mise à jour de vos informations.', 'danger')
    
    return render_template('admin/livreur_settings.html', employee=employee_data)

# Routes pour la partie marchands
@app.route('/merchant/login', methods=['GET', 'POST'])
def merchant_login():
    """Page de connexion pour les marchands"""
    # Vérifier si le marchand est déjà connecté
    if 'merchant_id' in session:
        return redirect(url_for('merchant_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        print(f"Tentative de connexion marchand: {email}")  # Log pour déboguer
        
        # Récupérer le marchand directement depuis la base de données
        merchant_record = Merchant.query.filter_by(email=email).first()
        
        # Vérifier si le marchand existe et a un mot de passe valide
        if merchant_record and merchant_record.check_password(password):
            # Vérifier si le compte est suspendu AVANT la connexion
            if merchant_record.status == 'suspended':
                flash('Votre compte marchand a été suspendu. Contactez l\'administration pour plus d\'informations.', 'danger')
                return redirect(url_for('merchant_account_suspended'))
            
            # Connexion réussie
            session['merchant_id'] = merchant_record.id
            session['merchant_email'] = email
            session['merchant_name'] = merchant_record.store_name
            
            # Gérer la fonctionnalité "Se souvenir de moi" pour merchant
            if remember:
                # Session permanente (31 jours)
                session.permanent = True
                print(f"[MERCHANT LOGIN] Session permanente activée pour {email}")
            else:
                session.permanent = False
                print(f"[MERCHANT LOGIN] Session temporaire pour {email}")
            
            # Mise à jour de la dernière connexion (avec vérification)
            try:
                if email in merchants_db:
                    merchants_db[email]['last_login'] = datetime.now().strftime('%Y-%m-%d')
                    print(f"Dernière connexion mise à jour pour {email}")
                else:
                    print(f"Marchand {email} non trouvé dans merchants_db - création d'entrée")
                    # Créer une entrée basique si elle n'existe pas
                    merchants_db[email] = {
                        'last_login': datetime.now().strftime('%Y-%m-%d'),
                        'store_name': merchant_record.store_name,
                        'email': email
                    }
            except Exception as e:
                print(f"Erreur lors de la mise à jour de last_login: {e}")
            
            print(f"Connexion marchand réussie pour: {email}, Remember: {remember}")  # Log pour déboguer
            

            
            flash('Vous êtes maintenant connecté en tant que marchand.', 'success')
            
            # Redirection vers le tableau de bord marchand
            return redirect(url_for('merchant_dashboard'))
        else:
            print(f"Échec connexion marchand pour: {email}")  # Log pour déboguer
            flash('Email ou mot de passe incorrect.', 'danger')
    
    return render_template('merchant/login.html')

@app.route('/merchant/account-suspended')
def merchant_account_suspended():
    """Page d'information pour les comptes marchands suspendus"""
    return render_template('merchant/account_suspended.html')

@app.route('/merchant/forgot-password', methods=['GET', 'POST'])
def merchant_forgot_password():
    """Page de récupération de mot de passe pour les marchands"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Vérifier si le marchand existe
        merchant = merchants_db.get(email)
        if merchant:
            # Générer un token de réinitialisation
            token = secrets.token_urlsafe(32)
            
            # Sauvegarder le token avec une expiration (1 heure)
            password_reset_tokens_db[token] = {
                'email': email,
                'type': 'merchant',
                'expires': datetime.now() + timedelta(hours=1)
            }
            
            # Construire l'URL de réinitialisation
            reset_url = url_for('merchant_reset_password', token=token, _external=True)
            
            # Contenu de l'email
            subject = "Réinitialisation de votre mot de passe marchand - DOUKA KM"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #0d6efd, #6c757d); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .merchant-badge {{ background: #0d6efd; color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.9rem; display: inline-block; margin-bottom: 20px; }}
                    .btn {{ background: linear-gradient(135deg, #198754, #20c997); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; }}
                    .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 0.9rem; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏪 DOUKA KM - Espace Marchand</h1>
                        <p>Réinitialisation de mot de passe</p>
                    </div>
                    <div class="content">
                        <div class="merchant-badge">
                            🛍️ Compte Marchand
                        </div>
                        
                        <h2>Bonjour {merchant.get('store_name', 'Marchand')},</h2>
                        
                        <p>Nous avons reçu une demande de réinitialisation de mot de passe pour votre compte marchand DOUKA KM.</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_url}" class="btn">Réinitialiser mon mot de passe</a>
                        </div>
                        
                        <div class="warning">
                            <strong>⚠️ Important :</strong>
                            <ul>
                                <li>Ce lien expire dans <strong>1 heure</strong></li>
                                <li>Si vous n'avez pas fait cette demande, ignorez cet email</li>
                                <li>Ne partagez jamais ce lien avec quelqu'un d'autre</li>
                            </ul>
                        </div>
                        
                        <p>Si le bouton ne fonctionne pas, copiez et collez ce lien dans votre navigateur :</p>
                        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px; font-family: monospace;">
                            {reset_url}
                        </p>
                        
                        <hr style="margin: 30px 0; border: none; height: 1px; background: #dee2e6;">
                        
                        <p><strong>Informations de sécurité :</strong></p>
                        <ul>
                            <li>Utilisez un mot de passe fort (au moins 8 caractères)</li>
                            <li>Incluez des majuscules, minuscules, chiffres et symboles</li>
                            <li>Ne réutilisez pas vos anciens mots de passe</li>
                        </ul>
                    </div>
                    <div class="footer">
                        <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                        <p>© 2024 DOUKA KM - Votre marketplace de confiance</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            DOUKA KM - Réinitialisation de mot de passe marchand
            
            Bonjour {merchant.get('store_name', 'Marchand')},
            
            Nous avons reçu une demande de réinitialisation de mot de passe pour votre compte marchand DOUKA KM.
            
            Pour réinitialiser votre mot de passe, cliquez sur le lien suivant :
            {reset_url}
            
            IMPORTANT :
            - Ce lien expire dans 1 heure
            - Si vous n'avez pas fait cette demande, ignorez cet email
            - Ne partagez jamais ce lien avec quelqu'un d'autre
            
            Conseils de sécurité :
            - Utilisez un mot de passe fort (au moins 8 caractères)
            - Incluez des majuscules, minuscules, chiffres et symboles
            - Ne réutilisez pas vos anciens mots de passe
            
            © 2024 DOUKA KM - Votre marketplace de confiance
            """
            
            # Envoyer l'email
            try:
                if send_email(email, subject, text_content, html_content):
                    print(f"[MERCHANT RESET] Email envoyé avec succès à {email}")
                    flash('Un email de récupération a été envoyé à votre adresse email de marchand.', 'success')
                else:
                    print(f"[MERCHANT RESET] Erreur envoi email pour {email}")
                    flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer.', 'danger')
            except Exception as e:
                print(f"[MERCHANT RESET] Exception envoi email: {e}")
                flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer.', 'danger')
        else:
            # Ne pas révéler si l'email existe ou non pour la sécurité
            flash('Si cette adresse email correspond à un compte marchand, vous recevrez un email de récupération.', 'info')
        
        return render_template('merchant/forgot_password.html', success=True)
    
    return render_template('merchant/forgot_password.html')

@app.route('/merchant/reset-password/<token>', methods=['GET', 'POST'])
def merchant_reset_password(token):
    """Page de réinitialisation de mot de passe pour les marchands"""
    # Vérifier si le token existe et n'a pas expiré
    token_data = password_reset_tokens_db.get(token)
    if not token_data or token_data['expires'] < datetime.now() or token_data['type'] != 'merchant':
        flash('Le lien de réinitialisation est invalide ou a expiré.', 'danger')
        return redirect(url_for('merchant_forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation du mot de passe
        if not new_password or len(new_password) < 8:
            flash('Le mot de passe doit contenir au moins 8 caractères.', 'danger')
            return render_template('merchant/reset_password.html', token=token)
        
        if new_password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('merchant/reset_password.html', token=token)
        
        # Vérifications de sécurité supplémentaires
        if not re.search(r'[A-Z]', new_password):
            flash('Le mot de passe doit contenir au moins une lettre majuscule.', 'danger')
            return render_template('merchant/reset_password.html', token=token)
        
        if not re.search(r'[a-z]', new_password):
            flash('Le mot de passe doit contenir au moins une lettre minuscule.', 'danger')
            return render_template('merchant/reset_password.html', token=token)
        
        if not re.search(r'[0-9]', new_password):
            flash('Le mot de passe doit contenir au moins un chiffre.', 'danger')
            return render_template('merchant/reset_password.html', token=token)
        
        if not re.search(r'[^A-Za-z0-9]', new_password):
            flash('Le mot de passe doit contenir au moins un caractère spécial.', 'danger')
            return render_template('merchant/reset_password.html', token=token)
        
        # Mettre à jour le mot de passe
        email = token_data['email']
        merchant = merchants_db.get(email)
        
        if merchant:
            merchant['password_hash'] = generate_password_hash(new_password)
            
            # Supprimer le token utilisé
            del password_reset_tokens_db[token]
            
            # Envoyer un email de confirmation
            subject = "Mot de passe marchand modifié avec succès - DOUKA KM"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #198754, #20c997); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .success-badge {{ background: #198754; color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.9rem; display: inline-block; margin-bottom: 20px; }}
                    .security-tips {{ background: #e3f2fd; border: 1px solid #90caf9; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 0.9rem; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏪 DOUKA KM - Espace Marchand</h1>
                        <p>Mot de passe modifié avec succès</p>
                    </div>
                    <div class="content">
                        <div class="success-badge">
                            ✅ Sécurisé
                        </div>
                        
                        <h2>Bonjour {merchant.get('store_name', 'Marchand')},</h2>
                        
                        <p>Votre mot de passe marchand DOUKA KM a été modifié avec succès.</p>
                        
                        <div class="security-tips">
                            <strong>🔒 Conseils de sécurité :</strong>
                            <ul>
                                <li>Gardez votre nouveau mot de passe secret</li>
                                <li>Ne le partagez avec personne</li>
                                <li>Déconnectez-vous des appareils partagés</li>
                                <li>Surveillez votre compte régulièrement</li>
                            </ul>
                        </div>
                        
                        <p>Si vous n'avez pas effectué cette modification, contactez immédiatement notre support.</p>
                        
                        <p><strong>Date de modification :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                    </div>
                    <div class="footer">
                        <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                        <p>© 2024 DOUKA KM - Votre marketplace de confiance</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            DOUKA KM - Mot de passe marchand modifié avec succès
            
            Bonjour {merchant.get('store_name', 'Marchand')},
            
            Votre mot de passe marchand DOUKA KM a été modifié avec succès.
            
            Conseils de sécurité :
            - Gardez votre nouveau mot de passe secret
            - Ne le partagez avec personne
            - Déconnectez-vous des appareils partagés
            - Surveillez votre compte régulièrement
            
            Si vous n'avez pas effectué cette modification, contactez immédiatement notre support.
            
            Date de modification : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
            
            © 2024 DOUKA KM - Votre marketplace de confiance
            """
            
            try:
                send_email(email, subject, text_content, html_content)
                print(f"[MERCHANT RESET] Confirmation envoyée à {email}")
            except Exception as e:
                print(f"[MERCHANT RESET] Erreur confirmation email: {e}")
            
            flash('Votre mot de passe marchand a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('merchant_login'))
        else:
            flash('Erreur lors de la réinitialisation du mot de passe.', 'danger')
    
    return render_template('merchant/reset_password.html', token=token)

@app.route('/merchant/logout')
def merchant_logout():
    """Déconnecte le marchand et redirige vers la page de connexion marchand"""
    # Sauvegarder temporairement les infos non-marchand
    user_info = {}
    if 'user_id' in session:
        for key in ['user_id', 'user_email', 'user_first_name', 'cart']:
            if key in session:
                user_info[key] = session.get(key)
    
    # Supprimer uniquement les informations du marchand de la session
    keys_to_remove = [k for k in session if k.startswith('merchant_')]
    for key in keys_to_remove:
        session.pop(key, None)
    
    # Restaurer les informations utilisateur si nécessaire
    if user_info:
        for key, value in user_info.items():
            session[key] = value
    
    flash('Vous avez été déconnecté en tant que marchand.', 'info')
    return redirect(url_for('merchant_login'))

@app.route('/merchant/dashboard')
@merchant_required
def merchant_dashboard():
    """Tableau de bord principal pour les marchands - Version migrée vers la base de données"""
    merchant_email = session.get('merchant_email')
    
    # **MIGRATION COMPLÈTE: Récupérer le marchand depuis la base de données d'abord**
    from db_helpers import get_merchant_by_email, get_merchant_orders
    merchant_record = get_merchant_by_email(merchant_email)
    
    if not merchant_record:
        # Fallback vers l'ancien système
        merchant = merchants_db.get(merchant_email, {})
        if not merchant:
            flash('Erreur: Compte marchand introuvable.', 'danger')
            return redirect(url_for('merchant_logout'))
    
    # Récupérer les évaluations du marchand (fonction déjà migrée)
    merchant_reviews = get_merchant_reviews(merchant_email)
    avg_rating, total_reviews = calculate_merchant_average_rating(merchant_email)
    rating_distribution, _ = get_merchant_rating_distribution(merchant_email)
    
    # Récupérer les dernières évaluations (5 dernières)
    recent_reviews = merchant_reviews[:5]
    
    # Calculer le solde dynamique du marchand (fonction déjà migrée)
    balance_info = calculate_merchant_balance(merchant_email)
    
    # **MIGRATION COMPLÈTE: Statistiques depuis la base de données**
    if merchant_record:
        # Récupérer les commandes depuis la DB
        db_orders = get_merchant_orders(merchant_record.id)
        total_orders_count = len(db_orders)
        pending_orders_count = len([o for o in db_orders if o.status == 'processing'])
        
        # Récupérer les produits depuis la DB
        db_products = Product.query.filter_by(merchant_id=merchant_record.id).all()
        total_products_count = len(db_products)
        
        # Convertir les dernières commandes pour l'affichage
        recent_orders = []
        for db_order in sorted(db_orders, key=lambda x: x.created_at, reverse=True)[:5]:
            # Récupérer l'adresse de livraison depuis le JSON
            shipping_address = db_order.get_shipping_address()
            
            order_dict = {
                'id': db_order.id,
                'order_number': db_order.order_number,
                'customer_name': db_order.customer_name,
                'total': db_order.total,
                'status': db_order.status,
                'status_text': db_order.status_text,
                'status_color': db_order.status_color,
                'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_method': db_order.payment_method,
                'shipping_method': shipping_address.get('shipping_method', 'Standard')
            }
            recent_orders.append(order_dict)
        
        # Utiliser les données du marchand depuis la base de données
        merchant_data = merchant_record.to_dict()
    else:
        # Fallback: utiliser l'ancien système
        merchant = merchants_db.get(merchant_email, {})
        total_orders_count = len(merchant.get('orders', []))
        pending_orders_count = sum(1 for order in merchant.get('orders', []) if order.get('status') == 'processing')
        total_products_count = len(merchant.get('products', []))
        recent_orders = sorted(merchant.get('orders', []), 
                              key=lambda x: x.get('created_at', ''), 
                              reverse=True)[:5]
        merchant_data = merchant
    
    # Récupérer les statistiques du marchand
    stats = {
        'total_products': total_products_count,
        'total_orders': total_orders_count,
        'balance': balance_info['available_balance'],
        'total_earnings': balance_info['total_earnings'],
        'commission_fees': balance_info['commission_fees'],
        'delivered_orders_count': balance_info['delivered_orders_count'],
        'commission_rate': balance_info['commission_rate'],
        'pending_orders': pending_orders_count,
        'store_verified': merchant_data.get('store_verified', False),
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'rating_distribution': rating_distribution
    }
    
    # Calculer les taux de commission par catégorie pour ce marchand
    merchant_categories = []
    if merchant_record:
        # Récupérer les catégories des produits du marchand avec leurs taux
        categories_with_products = db.session.query(
            Category.id,
            Category.name,
            Category.description,
            db.func.count(Product.id).label('product_count')
        ).join(
            Product, Category.id == Product.category_id
        ).filter(
            Product.merchant_id == merchant_record.id
        ).group_by(
            Category.id, Category.name, Category.description
        ).all()
        
        # Récupérer les paramètres du site pour le taux par défaut
        site_settings = get_site_settings()
        default_rate = float(site_settings.get('commission_rate', 15.0))
        
        for category_data in categories_with_products:
            # Chercher le taux spécifique à cette catégorie
            custom_rate = CategoryCommissionRate.query.filter_by(category_id=category_data.id).first()
            commission_rate = custom_rate.commission_rate if custom_rate else default_rate
            
            merchant_categories.append({
                'id': category_data.id,
                'name': category_data.name,
                'description': category_data.description,
                'product_count': category_data.product_count,
                'commission_rate': commission_rate
            })
        
        # Trier par nom de catégorie
        merchant_categories.sort(key=lambda x: x['name'])
    
    return render_template('merchant/dashboard.html', 
                          merchant=merchant_data,
                          stats=stats,
                          recent_orders=recent_orders,
                          recent_reviews=recent_reviews,
                          merchant_categories=merchant_categories)

# À ajouter après la fonction calculate_merchant_balance (vers la ligne 450)

def get_merchant_withdrawal_requests(merchant_email):
    """
    Récupère toutes les demandes de retrait d'un marchand - Version migrée vers base de données
    
    Args:
        merchant_email (str): L'email du marchand
    
    Returns:
        list: Liste des demandes de retrait du marchand
    """
    try:
        # Récupérer le marchand depuis la base de données
        merchant_record = Merchant.query.filter_by(email=merchant_email).first()
        
        if not merchant_record:
            print(f"⚠️ Marchand non trouvé: {merchant_email}")
            # Fallback vers le dictionnaire en mémoire
            return withdrawal_requests_db.get(merchant_email, [])
        
        # Récupérer les demandes depuis la base de données
        withdrawal_requests = WithdrawalRequest.query.filter_by(merchant_id=merchant_record.id).order_by(WithdrawalRequest.requested_at.desc()).all()
        
        # Convertir en liste de dictionnaires pour compatibilité
        requests_list = []
        for request in withdrawal_requests:
            request_dict = request.to_dict()
            request_dict['merchant_email'] = merchant_email  # Ajouter pour compatibilité
            requests_list.append(request_dict)
        
        # Fusionner avec les demandes du dictionnaire en mémoire si nécessaires
        memory_requests = withdrawal_requests_db.get(merchant_email, [])
        if memory_requests:
            # Éviter les doublons basés sur l'ID ou la date
            existing_ids = {req['id'] for req in requests_list if 'id' in req}
            for memory_req in memory_requests:
                if memory_req.get('id') not in existing_ids:
                    requests_list.append(memory_req)
        
        return requests_list
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des demandes de retrait: {str(e)}")
        # Fallback vers le dictionnaire en mémoire
        return withdrawal_requests_db.get(merchant_email, [])

def add_withdrawal_request(merchant_email, amount, method='bank_transfer', notes=''):
    """
    Ajoute une nouvelle demande de retrait pour un marchand - Version migrée vers base de données
    
    Args:
        merchant_email (str): L'email du marchand
        amount (float): Montant à retirer
        method (str): Méthode de retrait
        notes (str): Notes optionnelles
    
    Returns:
        dict: Données de la demande créée
    """
    try:
        # Récupérer le marchand depuis la base de données
        merchant_record = Merchant.query.filter_by(email=merchant_email).first()
        
        if not merchant_record:
            print(f"❌ Marchand non trouvé: {merchant_email}")
            return None
        
        # Générer un ID de demande unique
        import uuid
        request_id = f"WR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        # Créer la demande de retrait dans la base de données
        withdrawal_request = WithdrawalRequest(
            request_id=request_id,
            merchant_id=merchant_record.id,
            amount=float(amount),
            method=method,
            status='pending',
            notes=notes
        )
        
        db.session.add(withdrawal_request)
        db.session.commit()
        
        # Convertir en dictionnaire pour compatibilité
        withdrawal_dict = withdrawal_request.to_dict()
        withdrawal_dict['merchant_email'] = merchant_email  # Ajouter pour compatibilité
        
        # Ajouter aussi au dictionnaire en mémoire pour la session courante (compatibilité)
        if merchant_email not in withdrawal_requests_db:
            withdrawal_requests_db[merchant_email] = []
        withdrawal_requests_db[merchant_email].append(withdrawal_dict)
        
        print(f"✅ Demande de retrait créée en base: ID {withdrawal_request.request_id} pour {merchant_email}")
        return withdrawal_dict
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de la demande de retrait: {str(e)}")
        db.session.rollback()
        
        # Fallback vers l'ancien système (en mémoire uniquement)
        import uuid
        request_id = f"WR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        withdrawal_request = {
            'id': request_id,
            'merchant_email': merchant_email,
            'amount': float(amount),
            'method': method,
            'status': 'pending',
            'requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'processed_at': None,
            'notes': notes,
            'admin_notes': '',
            'reference': ''
        }
        
        # Initialiser la liste si elle n'existe pas
        if merchant_email not in withdrawal_requests_db:
            withdrawal_requests_db[merchant_email] = []
        
        # Ajouter la demande
        withdrawal_requests_db[merchant_email].append(withdrawal_request)
        
        return withdrawal_request

# À ajouter après les routes marchands existantes (vers la ligne 4200)

@app.route('/merchant/payments')
@merchant_required
def merchant_payments():
    """Page de gestion des paiements et retraits pour un marchand - Version migrée"""
    merchant_email = session.get('merchant_email')
    
    # Récupérer le marchand depuis la base de données d'abord
    from db_helpers import get_merchant_by_email
    merchant_record = get_merchant_by_email(merchant_email)
    
    if not merchant_record:
        # Fallback vers l'ancien système
        merchant = merchants_db.get(merchant_email, {})
        if not merchant:
            flash('Erreur: Compte marchand introuvable.', 'danger')
            return redirect(url_for('merchant_logout'))
    
    # Calculer le solde dynamique du marchand (fonction déjà migrée)
    balance_info = calculate_merchant_balance(merchant_email)
    
    # Récupérer les demandes de retrait depuis la base de données
    if merchant_record:
        from db_helpers import get_merchant_withdrawal_requests as db_get_withdrawals
        db_withdrawals = db_get_withdrawals(merchant_record.id)
        
        # Convertir en format compatible avec l'ancien système
        withdrawal_requests = []
        for db_withdrawal in db_withdrawals:
            withdrawal_requests.append({
                'id': db_withdrawal.request_id,  # Utiliser request_id pour l'affichage
                'db_id': db_withdrawal.id,  # Garder l'ID de base pour les opérations
                'requested_at': db_withdrawal.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                'amount': db_withdrawal.amount,
                'method': db_withdrawal.method,
                'status': db_withdrawal.status,
                'notes': db_withdrawal.notes or '',
                'admin_notes': db_withdrawal.admin_notes or '',
                'reference': db_withdrawal.reference or '',
                'processed_at': db_withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S') if db_withdrawal.processed_at else None
            })
    else:
        # Fallback vers l'ancien système
        withdrawal_requests = get_merchant_withdrawal_requests(merchant_email)
    
    # Trier par date (plus récent en premier)
    withdrawal_requests = sorted(withdrawal_requests, 
                               key=lambda x: x.get('requested_at', ''), 
                               reverse=True)
    
    # Calculer le montant minimum pour un retrait
    min_withdrawal = 10000
    
    # Vérifier s'il y a des demandes en cours
    pending_statuses = ['pending', 'approved', 'processing']
    pending_requests = [req for req in withdrawal_requests if req['status'] in pending_statuses]
    has_pending_request = len(pending_requests) > 0
    pending_request_info = pending_requests[0] if pending_requests else None
    
    # Préparer les informations de balance pour l'affichage
    balance_display = {
        'current': balance_info['available_balance'],
        'pending': balance_info['pending_withdrawals'],
        'completed': balance_info['completed_withdrawals'],
        'total_withdrawals': balance_info['total_withdrawals'],
        'gross_balance': balance_info.get('net_earnings', balance_info['gross_balance']),
        'min_withdrawal': min_withdrawal,
        'next_payout_date': 'Traité sous 2-3 jours ouvrables',
        'has_pending_request': has_pending_request,
        'pending_request_info': pending_request_info
    }
    
    # Préparer les données du marchand pour l'affichage
    if merchant_record:
        merchant_display = merchant_record.to_dict()
        merchant_display['total_withdrawn'] = balance_info['completed_withdrawals']
        merchant_display['total_earnings'] = balance_info['total_earnings']
        merchant_display['commission_fees'] = balance_info['commission_fees']
        merchant_display['bank_info'] = merchant_record.get_bank_info()
    else:
        # Fallback vers l'ancien système
        merchant_display = merchants_db.get(merchant_email, {}).copy()
        merchant_display['total_withdrawn'] = balance_info['completed_withdrawals']
        merchant_display['total_earnings'] = balance_info['total_earnings']
        merchant_display['commission_fees'] = balance_info['commission_fees']
    
    # **MIGRATION COMPLÈTE: Générer les transactions depuis la base de données**
    transactions = []
    
    if merchant_record:
        # Ajouter les transactions des commandes depuis la DB
        from db_helpers import get_merchant_orders
        db_orders = get_merchant_orders(merchant_record.id)
        
        for db_order in db_orders:
            transaction = {
                'id': f"TXN{db_order.id}",
                'date': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'description': f"Commande #{db_order.order_number}",
                'amount': db_order.total - (db_order.shipping_fee or 0),  # Gains nets
                'status': 'completed' if db_order.status == 'delivered' else 'processing',
                'order_status': db_order.status,
                'customer_name': db_order.customer_name,
                'type': 'order'
            }
            transactions.append(transaction)
        
        # Ajouter les transactions de retrait depuis la DB
        for withdrawal in db_withdrawals:
            if withdrawal.status == 'completed':
                transaction = {
                    'id': f"WTH{withdrawal.id}",
                    'date': withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S') if withdrawal.processed_at else withdrawal.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'description': f"Retrait - {withdrawal.method}",
                    'amount': -withdrawal.amount,  # Négatif car c'est une sortie
                    'status': 'completed',
                    'withdrawal_status': withdrawal.status,
                    'reference': withdrawal.reference or '',
                    'type': 'withdrawal'
                }
                transactions.append(transaction)
    else:
        # Fallback: ajouter les transactions de l'ancien dictionnaire
        merchant = merchants_db.get(merchant_email, {})
        for order in merchant.get('orders', []):
            transaction = {
                'id': f"TXN{order.get('id', 'UNK')}",
                'date': order.get('created_at', order.get('date', '')),
                'description': f"Commande #{order.get('order_number', order.get('id', 'UNK'))}",
                'amount': order.get('total', 0) - order.get('shipping_fee', 0),
                'status': 'completed' if order.get('status') == 'delivered' else 'processing',
                'order_status': order.get('status', 'unknown'),
                'customer_name': order.get('customer_name', 'Client'),
                'type': 'order'
            }
            transactions.append(transaction)
        
        # Ajouter les transactions de retrait de l'ancien système
        for withdrawal in withdrawal_requests:
            if withdrawal.get('status') == 'completed':
                transaction = {
                    'id': f"WTH{withdrawal.get('id', 'UNK')}",
                    'date': withdrawal.get('processed_at', withdrawal.get('requested_at', '')),
                    'description': f"Retrait - {withdrawal.get('method', 'Méthode inconnue')}",
                    'amount': -withdrawal.get('amount', 0),
                    'status': 'completed',
                    'withdrawal_status': withdrawal.get('status'),
                    'reference': withdrawal.get('reference', ''),
                    'type': 'withdrawal'
                }
                transactions.append(transaction)
    
    # Trier les transactions par date (plus récent en premier)
    transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Limiter aux 10 dernières transactions pour l'affichage
    transactions = transactions[:10]
    
    return render_template('merchant/payments.html',
                          merchant=merchant_display,
                          balance_info=balance_display,
                          withdrawal_requests=withdrawal_requests,
                          transactions=transactions)

@app.route('/merchant/withdrawal/request', methods=['POST'])
@app.route('/merchant/request_withdrawal', methods=['POST'])
@merchant_required
def merchant_request_withdrawal():
    """Traiter une demande de retrait"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    if not merchant:
        return jsonify({'success': False, 'message': 'Compte marchand introuvable'})
    
    try:
        # Récupérer les données du formulaire
        amount = float(request.form.get('amount', 0))
        method = request.form.get('method', 'bank_transfer')
        notes = request.form.get('notes', '')
        
        # Vérifier s'il y a déjà une demande en cours
        existing_requests = get_merchant_withdrawal_requests(merchant_email)
        pending_statuses = ['pending', 'approved', 'processing']
        
        pending_requests = [req for req in existing_requests if req['status'] in pending_statuses]
        
        if pending_requests:
            pending_request = pending_requests[0]  # Prendre la première demande en cours
            status_labels = {
                'pending': 'en cours de préparation',
                'approved': 'approuvée',
                'processing': 'en traitement'
            }
            status_text = status_labels.get(pending_request['status'], pending_request['status'])
            return jsonify({
                'success': False, 
                'message': f'Vous avez déjà une demande de retrait {status_text} (ID: {pending_request["id"]}). Veuillez attendre qu\'elle soit complétée avant de faire une nouvelle demande.'
            })
        
        # Validation du montant
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Le montant doit être supérieur à 0'})
        
        # Vérifier le solde disponible
        balance_info = calculate_merchant_balance(merchant_email)
        available_balance = balance_info['available_balance']
        
        # Vérifier le montant minimum
        min_withdrawal = 10000
        if amount < min_withdrawal:
            return jsonify({'success': False, 'message': f'Le montant minimum de retrait est de {min_withdrawal:,.0f} KMF'})
        
        # Vérifier si le marchand a suffisamment de solde
        if amount > available_balance:
            return jsonify({'success': False, 'message': f'Solde insuffisant. Solde disponible: {available_balance:,.0f} KMF'})
        
        # Vérifier les informations bancaires
        bank_info = merchant.get('bank_info', {})
        if method == 'bank_transfer' and not all([
            bank_info.get('bank_name'),
            bank_info.get('account_number'),
            bank_info.get('account_holder')
        ]):
            return jsonify({'success': False, 'message': 'Veuillez d\'abord ajouter vos informations bancaires'})
        
        # Créer la demande de retrait
        withdrawal_request = add_withdrawal_request(merchant_email, amount, method, notes)
        
        return jsonify({
            'success': True,
            'message': f'Votre demande de retrait de {amount:,.0f} KMF a été soumise avec succès',
            'request_id': withdrawal_request['id']
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': 'Montant invalide'})
    except Exception as e:
        print(f"Erreur lors de la demande de retrait: {e}")
        return jsonify({'success': False, 'message': 'Une erreur est survenue lors de la soumission'})

@app.route('/merchant/withdrawal/<request_id>/cancel', methods=['POST'])
@merchant_required
def merchant_cancel_withdrawal(request_id):
    """Annuler une demande de retrait - Version migrée vers base de données"""
    merchant_email = session.get('merchant_email')
    
    try:
        # DATABASE-FIRST: Chercher dans la base de données d'abord
        from models import WithdrawalRequest, Merchant
        
        merchant_record = Merchant.query.filter_by(email=merchant_email).first()
        withdrawal_db = None
        
        if merchant_record:
            # Recherche robuste par request_id (insensible à la casse)
            request_id_clean = str(request_id).strip()
            
            # Chercher d'abord avec la casse exacte
            withdrawal_db = WithdrawalRequest.query.filter_by(
                merchant_id=merchant_record.id,
                request_id=request_id_clean
            ).first()
            
            # Si pas trouvé, chercher avec une requête insensible à la casse
            if not withdrawal_db:
                all_withdrawals = WithdrawalRequest.query.filter_by(merchant_id=merchant_record.id).all()
                for wd in all_withdrawals:
                    if wd.request_id.lower() == request_id_clean.lower():
                        withdrawal_db = wd
                        break
        
        if withdrawal_db:
            # Vérifier que la demande peut être annulée
            if withdrawal_db.status not in ['pending']:
                return jsonify({
                    'success': False, 
                    'message': 'Cette demande ne peut plus être annulée car elle est déjà en traitement ou terminée.'
                })
            
            # Mettre à jour dans la base de données
            withdrawal_db.status = 'cancelled'
            withdrawal_db.processed_at = datetime.utcnow()
            withdrawal_db.admin_notes = 'Demande annulée par le marchand'
            
            db.session.commit()
            
            # Mettre à jour aussi dans le dictionnaire pour la session courante
            merchant_requests = withdrawal_requests_db.get(merchant_email, [])
            for req in merchant_requests:
                if req.get('id') == withdrawal_db.request_id:
                    req['status'] = 'cancelled'
                    req['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    req['admin_notes'] = 'Demande annulée par le marchand'
                    break
            
            return jsonify({
                'success': True,
                'message': 'Demande de retrait annulée avec succès.',
                'redirect': url_for('merchant_payments')
            })
        
        # Fallback: chercher dans le dictionnaire en mémoire
        merchant_requests = withdrawal_requests_db.get(merchant_email, [])
        
        # Recherche robuste dans le dictionnaire
        request_index = None
        request_id_clean = str(request_id).strip()
        
        for i, req in enumerate(merchant_requests):
            req_id = str(req['id']).strip()
            if req_id == request_id_clean or req_id.lower() == request_id_clean.lower():
                request_index = i
                break
        
        if request_index is None:
            print(f"❌ Demande d'annulation introuvable pour ID: {request_id}")
            print(f"   IDs disponibles: {[req['id'] for req in merchant_requests]}")
            return jsonify({
                'success': False, 
                'message': 'Demande de retrait introuvable.'
            })
        
        # Vérifier que la demande peut être annulée
        current_request = merchant_requests[request_index]
        if current_request['status'] not in ['pending']:
            return jsonify({
                'success': False, 
                'message': 'Cette demande ne peut plus être annulée car elle est déjà en traitement ou terminée.'
            })
        
        # Mettre à jour le statut vers 'cancelled'
        withdrawal_requests_db[merchant_email][request_index]['status'] = 'cancelled'
        withdrawal_requests_db[merchant_email][request_index]['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        withdrawal_requests_db[merchant_email][request_index]['admin_notes'] = 'Demande annulée par le marchand'
        
        return jsonify({
            'success': True,
            'message': 'Demande de retrait annulée avec succès.',
            'redirect': url_for('merchant_payments')
        })
        
    except Exception as e:
        print(f"Erreur lors de l'annulation de la demande de retrait: {e}")
        return jsonify({
            'success': False, 
            'message': 'Une erreur est survenue lors de l\'annulation.'
        })

@app.route('/merchant/bank-info/update', methods=['POST'])
@merchant_required  
def merchant_update_bank_info():
    """Mettre à jour les informations bancaires du marchand"""
    merchant_email = session.get('merchant_email')
    
    try:
        # Récupérer les données du formulaire
        bank_name = request.form.get('bank_name', '').strip()
        account_holder = request.form.get('account_holder', '').strip()
        account_number = request.form.get('account_number', '').strip()
        
        # Validation des champs
        if not all([bank_name, account_holder, account_number]):
            return jsonify({'success': False, 'message': 'Tous les champs sont obligatoires'})
        
        # Préparer les informations bancaires
        bank_info = {
            'bank_name': bank_name,
            'account_holder': account_holder,
            'account_number': account_number,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # MISE À JOUR DATABASE-FIRST : Essayer d'abord dans la base de données
        merchant_record = Merchant.query.filter_by(email=merchant_email).first()
        if merchant_record:
            # Mettre à jour dans la base de données SQLite
            merchant_record.bank_info = json.dumps(bank_info)
            merchant_record.updated_at = datetime.now()
            db.session.commit()
            print(f"✅ Informations bancaires mises à jour dans la base de données pour {merchant_email}")
        else:
            print(f"⚠️ Marchand {merchant_email} introuvable dans la base de données")
        
        # Fallback : Mettre à jour aussi dans le dictionnaire mémoire pour compatibilité
        if merchant_email in merchants_db:
            merchants_db[merchant_email]['bank_info'] = bank_info
            print(f"✅ Informations bancaires mises à jour dans le dictionnaire mémoire pour {merchant_email}")
        else:
            print(f"⚠️ Marchand {merchant_email} introuvable dans le dictionnaire mémoire")
        
        return jsonify({
            'success': True,
            'message': 'Vos informations bancaires ont été mises à jour avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la mise à jour des informations bancaires: {e}")
        print(f"📍 Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Une erreur est survenue lors de la mise à jour'})

@app.route('/merchant/withdrawal/<request_id>')
@merchant_required
def merchant_withdrawal_detail(request_id):
    """Afficher les détails d'une demande de retrait - Version migrée vers base de données"""
    merchant_email = session.get('merchant_email')
    
    try:
        # DATABASE-FIRST: Chercher dans la base de données d'abord
        from models import WithdrawalRequest, Merchant
        
        merchant_record = Merchant.query.filter_by(email=merchant_email).first()
        withdrawal_request = None
        
        if merchant_record:
            # Recherche robuste par request_id (insensible à la casse)
            request_id_clean = str(request_id).strip()
            
            # Chercher d'abord avec la casse exacte
            withdrawal_db = WithdrawalRequest.query.filter_by(
                merchant_id=merchant_record.id,
                request_id=request_id_clean
            ).first()
            
            # Si pas trouvé, chercher avec une requête insensible à la casse
            if not withdrawal_db:
                all_withdrawals = WithdrawalRequest.query.filter_by(merchant_id=merchant_record.id).all()
                for wd in all_withdrawals:
                    if wd.request_id.lower() == request_id_clean.lower():
                        withdrawal_db = wd
                        break
            
            # Convertir en dictionnaire si trouvé
            if withdrawal_db:
                withdrawal_request = withdrawal_db.to_dict()
                withdrawal_request['merchant_email'] = merchant_email
                
                print(f"✅ Demande trouvée en base: {withdrawal_db.request_id}")
        
        # Fallback: chercher dans le dictionnaire en mémoire
        if not withdrawal_request:
            withdrawal_requests = withdrawal_requests_db.get(merchant_email, [])
            
            # Recherche robuste dans le dictionnaire
            request_id_clean = str(request_id).strip()
            
            for req in withdrawal_requests:
                req_id = str(req['id']).strip()
                if req_id == request_id_clean or req_id.lower() == request_id_clean.lower():
                    withdrawal_request = req
                    print(f"✅ Demande trouvée en mémoire: {req_id}")
                    break
        
        if not withdrawal_request:
            print(f"❌ Demande de retrait introuvable pour ID: {request_id}")
            
            # Debug: afficher les IDs disponibles
            if merchant_record:
                db_requests = WithdrawalRequest.query.filter_by(merchant_id=merchant_record.id).all()
                db_ids = [wr.request_id for wr in db_requests]
                print(f"   IDs en base: {db_ids}")
            
            memory_requests = withdrawal_requests_db.get(merchant_email, [])
            memory_ids = [req.get('id', 'N/A') for req in memory_requests]
            print(f"   IDs en mémoire: {memory_ids}")
            
            flash('Demande de retrait introuvable.', 'danger')
            return redirect(url_for('merchant_payments'))
        
        # Récupérer les informations du marchand
        if merchant_record:
            merchant = merchant_record.to_dict()
        else:
            merchant = merchants_db.get(merchant_email, {})
        
        return render_template('merchant/withdrawal_detail.html',
                              merchant=merchant,
                              withdrawal_request=withdrawal_request)
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des détails de retrait: {e}")
        flash('Une erreur est survenue lors de la récupération des détails.', 'danger')
        return redirect(url_for('merchant_payments'))

@app.route('/merchant/products')
@merchant_required
def merchant_products():
    """Page de gestion des produits pour un marchand - Version migrée vers la base de données avec pagination"""
    
    merchant_email = session.get('merchant_email')
    
    # Paramètres de pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)  # 10 produits par page par défaut
    search = request.args.get('search', '', type=str)
    
    # Limite la taille de la page pour éviter les abus
    per_page = min(per_page, 50)  # Maximum 50 produits par page
    
    # Récupérer le marchand depuis la base de données d'abord
    from db_helpers import get_merchant_by_email
    merchant_record = get_merchant_by_email(merchant_email)
    
    if not merchant_record:
        # Fallback vers l'ancien système
        merchant = merchants_db.get(merchant_email, {})
        if not merchant:
            flash('Erreur: Compte marchand introuvable.', 'danger')
            return redirect(url_for('merchant_logout'))
    
    # **MIGRATION COMPLÈTE: Récupérer les produits depuis la base de données avec pagination**
    if merchant_record:
        # Construire la requête de base
        query = Product.query.filter_by(merchant_id=merchant_record.id)
        
        # Ajouter la recherche si fournie
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                Product.name.ilike(search_pattern) | 
                Product.description.ilike(search_pattern)
            )
        
        # Ordonner par date de création (plus récent d'abord)
        query = query.order_by(Product.created_at.desc())
        
        # Appliquer la pagination
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Convertir les produits paginés en format compatible
        products = []
        for db_product in pagination.items:
            product_dict = db_product.to_dict()
            
            # Ajouter les informations du marchand pour compatibilité
            product_dict['merchant_email'] = merchant_email
            product_dict['source'] = 'database'
            
            # Calculer les statistiques des avis depuis la base de données
            from models import Review
            reviews = Review.query.filter_by(product_id=db_product.id).all()
            if reviews:
                total_rating = sum(review.rating for review in reviews)
                product_dict['rating'] = round(total_rating / len(reviews), 1)
                product_dict['reviews_count'] = len(reviews)
            else:
                product_dict['rating'] = 0
                product_dict['reviews_count'] = 0
            
            products.append(product_dict)
        
        # Utiliser les informations du marchand depuis la base de données
        merchant_data = merchant_record.to_dict()
        
        # Informations de pagination pour le template
        pagination_info = {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_prev': pagination.has_prev,
            'prev_num': pagination.prev_num,
            'has_next': pagination.has_next,
            'next_num': pagination.next_num,
            'items': products
        }
        
    else:
        # Fallback: utiliser l'ancien système avec pagination manuelle
        merchant = merchants_db.get(merchant_email, {})
        all_products = merchant.get('products', [])
        merchant_data = merchant
        
        # Filtrer par recherche si fournie
        if search:
            search_lower = search.lower()
            all_products = [
                p for p in all_products 
                if search_lower in p.get('name', '').lower() or 
                   search_lower in p.get('description', '').lower()
            ]
        
        # Fonction pour convertir la date en timestamp pour un tri cohérent
        def get_sort_timestamp(product):
            created_at = product.get('created_at', '1970-01-01')
            
            # Si c'est un objet datetime (depuis la DB)
            if isinstance(created_at, datetime):
                return created_at.timestamp()
            
            # Si c'est une chaîne (ancien système)
            try:
                if len(str(created_at)) > 10:  # Format: '2025-08-04 14:30:25'
                    return datetime.strptime(str(created_at), '%Y-%m-%d %H:%M:%S').timestamp()
                else:  # Format: '2025-08-04'
                    return datetime.strptime(str(created_at), '%Y-%m-%d').timestamp()
            except (ValueError, AttributeError):
                # Si le parsing échoue, retourner 0 (très ancien)
                return 0
        
        # Trier les produits par date de création (du plus récent au plus ancien)
        all_products = sorted(all_products, key=get_sort_timestamp, reverse=True)
        
        # Pagination manuelle
        total = len(all_products)
        start = (page - 1) * per_page
        end = start + per_page
        products = all_products[start:end]
        
        # Calculer les informations de pagination
        pages = (total + per_page - 1) // per_page  # Division arrondie vers le haut
        
        pagination_info = {
            'page': page,
            'pages': pages,
            'per_page': per_page,
            'total': total,
            'has_prev': page > 1,
            'prev_num': page - 1 if page > 1 else None,
            'has_next': page < pages,
            'next_num': page + 1 if page < pages else None,
            'items': products
        }
    
    return render_template('merchant/products.html', 
                          merchant=merchant_data,
                          products=products,
                          pagination=pagination_info,
                          search=search)

@app.route('/merchant/reviews')
@merchant_required
def merchant_reviews():
    """Page des évaluations reçues par le marchand"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    if not merchant:
        flash('Erreur: Compte marchand introuvable.', 'danger')
        return redirect(url_for('merchant_logout'))
    
    # Récupérer toutes les évaluations du marchand
    merchant_reviews = get_merchant_reviews(merchant_email)
    avg_rating, total_reviews = calculate_merchant_average_rating(merchant_email)
    rating_distribution, _ = get_merchant_rating_distribution(merchant_email)
    
    # Pagination (optionnelle, pour l'instant on affiche tout)
    reviews_per_page = 10
    page = request.args.get('page', 1, type=int)
    start_idx = (page - 1) * reviews_per_page
    end_idx = start_idx + reviews_per_page
    paginated_reviews = merchant_reviews[start_idx:end_idx]
    
    # Calculer les informations de pagination
    total_pages = (len(merchant_reviews) + reviews_per_page - 1) // reviews_per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('merchant/reviews.html',
                          merchant=merchant,
                          reviews=paginated_reviews,
                          avg_rating=avg_rating,
                          total_reviews=total_reviews,
                          rating_distribution=rating_distribution,
                          current_page=page,
                          total_pages=total_pages,
                          has_prev=has_prev,
                          has_next=has_next,
                          prev_num=page-1 if has_prev else None,
                          next_num=page+1 if has_next else None)

@app.route('/merchant/product/add', methods=['GET', 'POST'])
@merchant_required
def merchant_product_add():
    """Page d'ajout d'un nouveau produit"""
    merchant_email = session.get('merchant_email')
    
    # Récupérer le marchand depuis la base de données
    merchant_record = Merchant.query.filter_by(email=merchant_email).first()
    if not merchant_record:
        flash('Informations du marchand non trouvées', 'danger')
        return redirect(url_for('merchant_login'))
    
    # Vérifier si le marchand est vérifié dans la base de données
    if not merchant_record.store_verified:
        flash('Votre boutique doit être vérifiée par un administrateur avant de pouvoir ajouter des produits.', 'warning')
        return redirect(url_for('merchant_products'))
    
    # Fallback pour compatibilité avec le dictionnaire en mémoire
    merchant = merchants_db.get(merchant_email, {})
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        price = request.form.get('price', 0)
        stock = request.form.get('stock', 0)
        
        # Gestion sécurisée des IDs de catégories
        try:
            category_id = int(request.form.get('category_id', 0) or 0)
            subcategory_id = int(request.form.get('subcategory_id', 0) or 0)
        except ValueError:
            flash('Veuillez sélectionner une catégorie et une sous-catégorie valides.', 'danger')
            categories_list = [
                {'id': cat_id, 'name': cat['name']} 
                for cat_id, cat in admin_categories_db.items() 
                if cat.get('active', True)
            ]
            return render_template('merchant/product_add.html', merchant=merchant, categories=categories_list)
        
        # Validation de base
        if not name or not description:
            flash('Le nom et la description du produit sont obligatoires.', 'danger')
            categories_list = [
                {'id': cat_id, 'name': cat['name']} 
                for cat_id, cat in admin_categories_db.items() 
                if cat.get('active', True)
            ]
            return render_template('merchant/product_add.html', merchant=merchant, categories=categories_list)
        
        try:
            price = int(float(price))
            stock = int(stock)
        except ValueError:
            flash('Le prix et le stock doivent être des nombres.', 'danger')
            categories_list = [
                {'id': cat_id, 'name': cat['name']} 
                for cat_id, cat in admin_categories_db.items() 
                if cat.get('active', True)
            ]
            return render_template('merchant/product_add.html', merchant=merchant, categories=categories_list)
        
        # Générer un nouvel ID produit unique globalement
        # Les produits statiques utilisent IDs 1-100
        # Les produits marchands utilisent IDs 1000+
        all_products = get_all_products()
        merchant_products = [p for p in all_products if p.get('source') == 'merchant']
        
        if merchant_products:
            # Trouver le plus grand ID de produit marchand existant
            max_merchant_id = max(p['id'] for p in merchant_products)
            product_id = max_merchant_id + 1
        else:
            # Premier produit marchand - commencer à 1001
            product_id = 1001
        
        # Traitement des options du produit
        # Couleurs (sans price_modifier)
        colors = []
        color_names = request.form.getlist('color_name[]')
        color_hexs = request.form.getlist('color_hex[]')
        
        for i in range(len(color_names)):
            if color_names[i]:  # Vérifier que le nom n'est pas vide
                colors.append({
                    'name': color_names[i],
                    'value': color_names[i].lower().replace(' ', '_'),
                    'hex': color_hexs[i] if i < len(color_hexs) else '#000000'
                })
        
        # Tailles (sans price_modifier)
        sizes = []
        size_values = request.form.getlist('size_value[]')
        size_labels = request.form.getlist('size_label[]')
        size_labels = request.form.getlist('size_label[]')
        
        for i in range(len(size_values)):
            if size_values[i]:  # Vérifier que la valeur n'est pas vide
                sizes.append({
                    'value': size_values[i],
                    'label': size_labels[i] if i < len(size_labels) and size_labels[i] else size_values[i]
                })
        
        # Combinaisons de prix
        price_combinations = []
        combination_colors = request.form.getlist('combination_color[]')
        combination_sizes = request.form.getlist('combination_size[]')
        combination_prices = request.form.getlist('combination_price[]')
        
        for i in range(len(combination_prices)):
            if combination_prices[i]:  # Vérifier qu'un prix est défini
                try:
                    combination_price = int(float(combination_prices[i]))
                    combination = {
                        'price': combination_price
                    }
                    
                    # Ajouter la couleur si spécifiée
                    if i < len(combination_colors) and combination_colors[i]:
                        combination['color'] = combination_colors[i]
                    
                    # Ajouter la taille si spécifiée
                    if i < len(combination_sizes) and combination_sizes[i]:
                        combination['size'] = combination_sizes[i]
                    
                    # Au moins une option doit être spécifiée
                    if 'color' in combination or 'size' in combination:
                        price_combinations.append(combination)
                        
                except (ValueError, IndexError):
                    continue  # Ignorer les prix invalides
        
        # Traitement des URLs d'images
        image_urls = request.form.getlist('image_url[]')
        # Filtrer les URLs vides et valider qu'au moins une image est fournie
        valid_image_urls = [url.strip() for url in image_urls if url.strip()]
        
        if not valid_image_urls:
            flash('Au moins une URL d\'image est requise.', 'danger')
            categories_list = [
                {'id': cat_id, 'name': cat['name']} 
                for cat_id, cat in admin_categories_db.items() 
                if cat.get('active', True)
            ]
            return render_template('merchant/product_add.html', merchant=merchant, categories=categories_list)
        
        # La première image devient l'image principale
        main_image = valid_image_urls[0]
        
        # Spécifications
        specifications = {}
        spec_names = request.form.getlist('spec_name[]')
        spec_values = request.form.getlist('spec_value[]')
        
        for i in range(len(spec_names)):
            if spec_names[i] and i < len(spec_values) and spec_values[i]:
                specifications[spec_names[i]] = spec_values[i]
        
        # Créer le nouveau produit
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # SAUVEGARDER LE PRODUIT DANS LA BASE DE DONNÉES SQLITE
        try:
            # Trouver le marchand dans la base de données
            merchant_db = Merchant.query.filter_by(email=merchant_email).first()
            if not merchant_db:
                flash('Erreur: Marchand non trouvé dans la base de données.', 'danger')
                return redirect(url_for('merchant_products'))
            
            # Créer le nouveau produit dans la base de données
            new_product_db = Product(
                name=name,
                description=description,
                price=price,
                stock=stock,
                category_id=category_id,
                subcategory_id=subcategory_id,
                image=main_image,
                images=json.dumps(valid_image_urls),  # Convertir en JSON
                status='active',
                merchant_id=merchant_db.id,
                source='merchant',
                colors=json.dumps(colors) if colors else '[]',  # Convertir en JSON
                sizes=json.dumps(sizes) if sizes else '[]',  # Convertir en JSON
                specifications=json.dumps(specifications) if specifications else '{}',  # Convertir en JSON
                price_combinations=json.dumps(price_combinations) if price_combinations else '[]'  # Convertir en JSON
            )
            
            db.session.add(new_product_db)
            db.session.commit()
            
            print(f"✅ Produit '{name}' sauvegardé dans la base de données (ID: {new_product_db.id})")
            
            # Créer aussi l'objet pour le dictionnaire en mémoire (compatibilité)
            new_product_dict = {
                'id': new_product_db.id,  # Utiliser l'ID de la base de données
                'name': name,
                'description': description,
                'price': price,
                'stock': stock,
                'category_id': category_id,
                'subcategory_id': subcategory_id,
                'image': main_image,  # Image principale
                'images': valid_image_urls,  # Toutes les images
                'status': 'active',
                'created_at': now,
                'updated_at': now,
                'rating': 4.5,
                'reviews_count': 0,
                'source': 'merchant',
                'merchant_email': merchant_email
            }
            
            # Ajouter les options seulement si elles existent
            if colors:
                new_product_dict['colors'] = colors
            if sizes:
                new_product_dict['sizes'] = sizes
            if specifications:
                new_product_dict['specifications'] = specifications
            if price_combinations:
                new_product_dict['price_combinations'] = price_combinations
            
            # Ajouter le produit à la liste des produits du marchand EN MÉMOIRE aussi
            if 'products' not in merchant:
                merchants_db[merchant_email]['products'] = []
            
            # Insérer le nouveau produit au début de la liste pour qu'il soit en premier
            merchants_db[merchant_email]['products'].insert(0, new_product_dict)
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde du produit: {e}")
            db.session.rollback()
            flash('Erreur lors de la création du produit. Veuillez réessayer.', 'danger')
            return redirect(url_for('merchant_product_add'))
        
        flash('Produit ajouté avec succès.', 'success')
        return redirect(url_for('merchant_products'))
    
    # Préparer les catégories pour le template
    categories_list = get_categories_with_subcategories()
    
    return render_template('merchant/product_add.html', merchant=merchant, categories=categories_list)

@app.route('/merchant/register', methods=['GET', 'POST'])
def merchant_register():
    """Page d'inscription pour les nouveaux marchands"""
    # Rediriger si déjà connecté comme marchand
    if 'merchant_id' in session:
        return redirect(url_for('merchant_dashboard'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        store_name = request.form.get('store_name', '')
        store_description = request.form.get('store_description', '')
        store_address = request.form.get('store_address', '')
        store_city = request.form.get('store_city', '')
        store_region = request.form.get('store_region', '')
        store_logo = request.form.get('store_logo', '')
        store_banner = request.form.get('store_banner', '')
        latitude = request.form.get('latitude', '')
        longitude = request.form.get('longitude', '')
        bank_name = request.form.get('bank_name', '')
        account_holder = request.form.get('account_holder', '')
        account_number = request.form.get('account_number', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation des données
        errors = []
        
        if not all([first_name, last_name, phone, email, store_name, password, confirm_password]):
            errors.append('Tous les champs marqués * sont obligatoires.')
        
        if password != confirm_password:
            errors.append('Les mots de passe ne correspondent pas.')
        
        if email in merchants_db:
            errors.append('Cette adresse email est déjà utilisée.')
        
        # Validation des coordonnées GPS si fournies
        lat_value = None
        lon_value = None
        if latitude and longitude:
            try:
                lat_value = float(latitude)
                lon_value = float(longitude)
                if not (-90 <= lat_value <= 90) or not (-180 <= lon_value <= 180):
                    errors.append('Les coordonnées GPS doivent être valides (latitude: -90 à 90, longitude: -180 à 180).')
            except ValueError:
                errors.append('Les coordonnées GPS doivent être des nombres décimaux valides.')
        elif latitude or longitude:
            errors.append('Si vous fournissez des coordonnées GPS, veuillez remplir à la fois la latitude et la longitude.')
        
        # Si des erreurs sont trouvées, afficher et retourner le formulaire
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('merchant/register.html')
        
        # Créer un nouvel ID marchand unique
        merchant_id = max([m['id'] for m in merchants_db.values()], default=100) + 1
        
        # Créer l'entrée pour le nouveau marchand
        now = datetime.now()
        registration_date = now.strftime('%Y-%m-%d')
        
        # Préparer les informations bancaires
        bank_info_json = {}
        if bank_name and account_holder and account_number:
            bank_info_json = {
                'bank_name': bank_name,
                'account_holder': account_holder,
                'account_number': account_number,
                'updated_at': registration_date
            }
        
        # Créer le nouveau marchand dans la BASE DE DONNÉES
        new_merchant = Merchant(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            store_name=store_name,
            store_description=store_description or f"Boutique de {first_name} {last_name}",
            store_address=store_address or '',
            store_city=store_city or '',
            store_region=store_region or '',
            store_logo=store_logo if store_logo else 'static/img/merchants/store_logo_default.png',
            store_banner=store_banner if store_banner else 'static/img/merchants/store_banner_default.jpg',
            store_verified=False,
            balance=0,
            latitude=lat_value,
            longitude=lon_value
        )
        
        # Sérialiser les informations bancaires en JSON
        new_merchant.set_bank_info(bank_info_json)
        
        try:
            db.session.add(new_merchant)
            db.session.commit()
            print(f"✅ Marchand {email} sauvegardé dans la base de données")
            
            # **NOUVELLE FONCTIONNALITÉ: Envoyer notification à l'admin**
            try:
                send_admin_notification_new_merchant(new_merchant)
            except Exception as e:
                print(f"⚠️ Erreur notification admin pour nouveau marchand: {str(e)}")
                
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde marchand: {e}")
            db.session.rollback()
            flash('Erreur lors de la création du compte marchand. Veuillez réessayer.', 'danger')
            return render_template('merchant/register.html')
        
        # Mettre à jour AUSSI le dictionnaire en mémoire pour compatibilité
        merchants_db[email] = {
            'id': new_merchant.id,  # Utiliser l'ID généré par la base de données
            'password_hash': new_merchant.password_hash,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'store_name': store_name,
            'store_description': store_description or f"Boutique de {first_name} {last_name}",
            'store_address': store_address or '',
            'store_city': store_city or '',
            'store_region': store_region or '',
            'store_logo': store_logo if store_logo else 'static/img/merchants/store_logo_default.png',
            'store_banner': store_banner if store_banner else 'static/img/merchants/store_banner_default.jpg',
            'store_verified': False,  # Par défaut, non vérifié
            'registration_date': registration_date,
            'products': [],
            'orders': [],
            'balance': 0,
            'bank_info': bank_info_json,
            'latitude': lat_value,  # Coordonnées GPS
            'longitude': lon_value  # Coordonnées GPS
        }
        
        flash('Votre compte marchand a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('merchant_login'))
    
    # Passer les régions disponibles au template
    regions = [
        {'value': 'grande-comore', 'name': 'Grande Comore'},
        {'value': 'anjouan', 'name': 'Anjouan'},
        {'value': 'moheli', 'name': 'Mohéli'}
    ]
    
    return render_template('merchant/register.html', regions=regions)

@app.route('/merchant/product/edit/<int:product_id>', methods=['GET', 'POST'])
@merchant_required
def merchant_product_edit(product_id):
    """Page de modification d'un produit existant - Version migrée vers base de données"""
    merchant_email = session.get('merchant_email')
    
    # Récupérer le marchand depuis la base de données
    from db_helpers import get_merchant_by_email
    merchant_record = get_merchant_by_email(merchant_email)
    
    if not merchant_record:
        flash('Marchand non trouvé.', 'danger')
        return redirect(url_for('merchant_login'))
    
    # Vérifier si le marchand est vérifié
    if not merchant_record.store_verified:
        flash('Votre boutique doit être vérifiée par un administrateur avant de pouvoir modifier des produits.', 'warning')
        return redirect(url_for('merchant_products'))
    
    # **MIGRATION VERS BASE DE DONNÉES: Chercher le produit dans la base de données**
    product_db = Product.query.filter_by(id=product_id).first()
    
    if not product_db:
        flash('Produit non trouvé.', 'danger')
        return redirect(url_for('merchant_products'))
    
    # Vérifier que ce produit appartient bien à ce marchand
    if product_db.merchant_id != merchant_record.id:
        flash('Vous n\'êtes pas autorisé à modifier ce produit.', 'danger')
        return redirect(url_for('merchant_products'))
    
    # Convertir le produit en dictionnaire pour compatibilité avec le template
    product = product_db.to_dict()
    
    if request.method == 'POST':
        # Récupérer et valider les données du formulaire
        try:
            new_name = request.form.get('name', '').strip()
            new_description = request.form.get('description', '').strip()
            new_price = int(float(request.form.get('price', product['price'])))
            new_stock = int(request.form.get('stock', product['stock']))
            new_category_id = int(request.form.get('category_id', product['category_id']) or product['category_id'])
            
            # Gestion sécurisée de subcategory_id - peut être vide
            subcategory_value = request.form.get('subcategory_id', '')
            if subcategory_value:
                new_subcategory_id = int(subcategory_value)
            else:
                new_subcategory_id = None
                
            new_status = request.form.get('status', product['status'])
            
        except ValueError:
            flash('Le prix, le stock et les catégories doivent être des nombres valides.', 'danger')
            categories_list = get_categories_with_subcategories()
            merchant_data = merchant_record.to_dict()
            return render_template('merchant/product_edit.html', merchant=merchant_data, product=product, categories=categories_list)
        
        # Validation des données
        if not new_name:
            flash('Le nom du produit est obligatoire.', 'danger')
            categories_list = get_categories_with_subcategories()
            merchant_data = merchant_record.to_dict()
            return render_template('merchant/product_edit.html', merchant=merchant_data, product=product, categories=categories_list)
        
        if new_price <= 0:
            flash('Le prix doit être supérieur à zéro.', 'danger')
            categories_list = get_categories_with_subcategories()
            merchant_data = merchant_record.to_dict()
            return render_template('merchant/product_edit.html', merchant=merchant_data, product=product, categories=categories_list)
        
        # **SAUVEGARDER LES MODIFICATIONS DANS LA BASE DE DONNÉES**
        try:
            # Mettre à jour le produit dans la base de données
            product_db.name = new_name
            product_db.description = new_description
            product_db.price = new_price
            product_db.stock = new_stock
            product_db.category_id = new_category_id
            product_db.subcategory_id = new_subcategory_id
            product_db.status = new_status
            
            db.session.commit()
            print(f"✅ Produit {product_id} modifié avec succès dans la base de données")
            
            flash('Produit modifié avec succès !', 'success')
            return redirect(url_for('merchant_products'))
            
        except Exception as e:
            print(f"❌ Erreur lors de la modification du produit: {e}")
            db.session.rollback()
            flash('Erreur lors de la modification du produit.', 'danger')
    
    # Préparer les données pour le template
    categories_list = get_categories_with_subcategories()
    merchant_data = merchant_record.to_dict()
    
    return render_template('merchant/product_edit.html', merchant=merchant_data, product=product, categories=categories_list)

@app.route('/merchant/product/delete/<int:product_id>', methods=['POST'])
@merchant_required
def merchant_product_delete(product_id):
    """Supprimer un produit existant"""
    merchant_email = session.get('merchant_email')
    
    # Récupérer le marchand depuis la base de données
    merchant_record = Merchant.query.filter_by(email=merchant_email).first()
    if not merchant_record:
        flash('Informations du marchand non trouvées', 'danger')
        return redirect(url_for('merchant_login'))
    
    # Vérifier si le marchand est vérifié dans la base de données
    if not merchant_record.store_verified:
        flash('Votre boutique doit être vérifiée par un administrateur avant de pouvoir supprimer des produits.', 'warning')
        return redirect(url_for('merchant_products'))
    
    # Fallback pour compatibilité avec le dictionnaire en mémoire
    merchant = merchants_db.get(merchant_email, {})
    
    # VÉRIFIER D'ABORD SI LE PRODUIT EST RÉFÉRENCÉ DANS DES COMMANDES
    try:
        from models import OrderItem
        
        # Vérifier s'il y a des OrderItems qui référencent ce produit
        order_items_count = OrderItem.query.filter_by(product_id=product_id).count()
        
        if order_items_count > 0:
            flash(f'Impossible de supprimer ce produit car il est présent dans {order_items_count} commande(s). Pour préserver l\'historique des commandes, vous pouvez le désactiver à la place.', 'warning')
            return redirect(url_for('merchant_products'))
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des commandes: {e}")
        flash('Erreur lors de la vérification du produit.', 'danger')
        return redirect(url_for('merchant_products'))
    
    # SUPPRIMER LE PRODUIT DE LA BASE DE DONNÉES
    try:
        product_db = Product.query.get(product_id)
        if product_db:
            db.session.delete(product_db)
            db.session.commit()
            print(f"✅ Produit {product_id} supprimé de la base de données")
        else:
            print(f"⚠️ Produit {product_id} non trouvé dans la base de données")
            
    except Exception as e:
        print(f"❌ Erreur lors de la suppression du produit: {e}")
        db.session.rollback()
        flash('Erreur lors de la suppression du produit.', 'danger')
        return redirect(url_for('merchant_products'))
    
    # Trouver le produit à supprimer dans le dictionnaire en mémoire
    product_to_delete = None
    for i, p in enumerate(merchant.get('products', [])):
        if p.get('id') == product_id:
            product_to_delete = i
            break
    
    if product_to_delete is not None:
        # Supprimer le produit de la liste en mémoire
        del merchant['products'][product_to_delete]
        flash('Produit supprimé avec succès.', 'success')
    else:
        flash('Produit supprimé de la base de données mais non trouvé en mémoire.', 'success')
    
    return redirect(url_for('merchant_products'))

@app.route('/merchant/product/toggle/<int:product_id>', methods=['POST'])
@merchant_required
def merchant_product_toggle(product_id):
    """Activer/désactiver un produit"""
    merchant_email = session.get('merchant_email')
    
    # Récupérer le marchand depuis la base de données
    merchant_record = Merchant.query.filter_by(email=merchant_email).first()
    if not merchant_record:
        flash('Informations du marchand non trouvées', 'danger')
        return redirect(url_for('merchant_login'))
    
    # Vérifier si le marchand est vérifié dans la base de données
    if not merchant_record.store_verified:
        flash('Votre boutique doit être vérifiée par un administrateur avant de pouvoir modifier des produits.', 'warning')
        return redirect(url_for('merchant_products'))
    
    # Fallback pour compatibilité avec le dictionnaire en mémoire
    merchant = merchants_db.get(merchant_email, {})
    
    try:
        product_db = Product.query.get(product_id)
        if not product_db:
            flash('Produit non trouvé.', 'danger')
            return redirect(url_for('merchant_products'))
        
        # Vérifier que le produit appartient au marchand
        merchant_record = get_merchant_by_email(merchant_email)
        if not merchant_record or product_db.merchant_id != merchant_record.id:
            flash('Vous n\'êtes pas autorisé à modifier ce produit.', 'danger')
            return redirect(url_for('merchant_products'))
        
        # Basculer le statut
        if product_db.status == 'active':
            product_db.status = 'inactive'
            flash('Produit désactivé avec succès.', 'success')
        else:
            product_db.status = 'active'
            flash('Produit activé avec succès.', 'success')
        
        db.session.commit()
        print(f"✅ Statut du produit {product_id} changé vers {product_db.status}")
        
    except Exception as e:
        print(f"❌ Erreur lors du changement de statut: {e}")
        db.session.rollback()
        flash('Erreur lors de la modification du statut.', 'danger')
    
    return redirect(url_for('merchant_products'))

@app.route('/merchant/orders')
@merchant_required
def merchant_orders():
    """Page de gestion des commandes pour un marchand"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    # **NOUVELLE VERSION: Récupérer les commandes depuis la base de données**
    merchant_record = get_merchant_by_email(merchant_email)
    orders = []
    
    if merchant_record:
        # Récupérer les commandes depuis la DB
        db_orders = get_merchant_orders(merchant_record.id)
        
        # Convertir en format attendu par le template
        for db_order in db_orders:
            # Récupérer les items de la commande
            order_items = []
            for item in db_order.items:
                order_items.append({
                    'name': item.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'image': item.image,
                    'variant_details': item.variant_details,
                    'options': item.get_options()  # Ajouter les options
                })
            
            # Récupérer l'adresse de livraison depuis le JSON
            shipping_address = db_order.get_shipping_address()
            
            order_dict = {
                'id': db_order.id,
                'order_number': db_order.order_number,
                'customer_name': db_order.customer_name,
                'customer_email': db_order.customer_email,
                'customer_phone': db_order.customer_phone,
                'items': order_items,
                'total': db_order.total,
                'status': db_order.status,
                'status_text': db_order.status_text,
                'status_color': db_order.status_color,
                'payment_method': db_order.payment_method,
                'payment_status': db_order.payment_status or 'pending',
                'shipping_method': shipping_address.get('shipping_method', 'Standard'),  # Récupérer depuis l'adresse
                'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': db_order.updated_at.strftime('%Y-%m-%d %H:%M:%S') if db_order.updated_at else None,
                'shipping_address': shipping_address
            }
            orders.append(order_dict)
    else:
        # Fallback: utiliser l'ancienne méthode
        orders = merchant.get('orders', [])
        orders = sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True)
    
    return render_template('merchant/orders.html', 
                          merchant=merchant,
                          orders=orders)

@app.route('/merchant/order/<int:order_id>')
@merchant_required
def merchant_order_detail(order_id):
    """Page de détail d'une commande spécifique"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    # **NOUVELLE VERSION: Récupérer la commande depuis la base de données**
    from db_helpers import get_order_by_id, get_merchant_by_email
    
    # Récupérer la commande depuis la DB
    db_order = get_order_by_id(order_id)
    
    if not db_order:
        flash('Commande non trouvée.', 'danger')
        return redirect(url_for('merchant_orders'))
    
    # Vérifier que cette commande appartient à ce marchand
    merchant_record = get_merchant_by_email(merchant_email)
    if not merchant_record or db_order.merchant_id != merchant_record.id:
        flash('Commande non trouvée pour ce marchand.', 'danger')
        return redirect(url_for('merchant_orders'))
    
    # Convertir en format attendu par le template
    order_items = []
    for item in db_order.items:
        order_items.append({
            'name': item.name,
            'quantity': item.quantity,
            'price': item.price,
            'subtotal': item.subtotal,
            'image': item.image,
            'variant_details': item.variant_details,
            'options': item.get_options()  # Récupérer les options formatées
        })
    
    # Récupérer l'adresse de livraison depuis le JSON
    shipping_address = db_order.get_shipping_address()
    
    # Récupérer l'historique des statuts
    status_history = db_order.get_status_history()
    
    # Si pas d'historique, créer un historique basique avec le statut actuel
    if not status_history:
        status_history = [{
            'status': db_order.status,
            'status_text': db_order.status_text,
            'date': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'text': f"Commande {db_order.status_text}",
            'changed_by': 'Système'
        }]
    
    order_dict = {
        'id': db_order.id,
        'order_number': db_order.order_number,
        'customer_name': db_order.customer_name,
        'customer_email': db_order.customer_email,
        'customer_phone': db_order.customer_phone,
        'items': order_items,
        'products': order_items,  # Alias pour compatibilité template
        'total': db_order.total,
        'status': db_order.status,
        'status_text': db_order.status_text,
        'status_color': db_order.status_color,
        'payment_method': db_order.payment_method,
        'payment_status': db_order.payment_status or 'pending',
        'shipping_method': shipping_address.get('shipping_method', 'Standard'),
        'created_at': db_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': db_order.updated_at.strftime('%Y-%m-%d %H:%M:%S') if db_order.updated_at else None,
        'shipping_address': shipping_address,
        'notes': status_history  # Ajouter l'historique des statuts
    }
    
    return render_template('merchant/order_detail.html',
                          merchant=merchant,
                          order=order_dict)

@app.route('/merchant/test-simple')
def merchant_test_simple():
    """Route de test ultra simple sans authentification"""
    return "<h1>Test Simple - Ceci fonctionne</h1><p>Si vous voyez ceci, le routage fonctionne.</p>"





@app.route('/merchant/settings')
@merchant_required
def merchant_settings():
    """Page de paramètres du compte marchand"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    return render_template('merchant/settings.html', 
                          merchant=merchant)

@app.route('/merchant/profile', methods=['GET', 'POST'])
@merchant_required
def merchant_profile():
    """Page de profil du marchand et mise à jour des informations"""
    merchant_email = session.get('merchant_email')
    
    # DATABASE-FIRST: Récupérer les données depuis la base de données en priorité
    merchant_db = Merchant.query.filter_by(email=merchant_email).first()
    
    if merchant_db:
        # Utiliser les données de la base de données
        merchant = {
            'email': merchant_email,
            'first_name': merchant_db.first_name or '',
            'last_name': merchant_db.last_name or '',
            'phone': merchant_db.phone or '',
            'store_name': merchant_db.store_name or '',
            'store_description': merchant_db.store_description or '',
            'store_address': merchant_db.store_address or '',
            'store_city': merchant_db.store_city or '',
            'store_region': merchant_db.store_region or '',
            'store_logo': merchant_db.store_logo or 'static/img/merchants/store_logo_default.png',
            'store_banner': merchant_db.store_banner or 'static/img/merchants/store_banner_default.jpg',
            'store_verified': merchant_db.store_verified,
            'latitude': merchant_db.latitude,
            'longitude': merchant_db.longitude,
            'bank_info': json.loads(merchant_db.bank_info) if merchant_db.bank_info else {}
        }
        print(f"✅ Profil marchand {merchant_email} récupéré depuis la base de données")
    else:
        # Fallback vers le dictionnaire en mémoire
        merchant = merchants_db.get(merchant_email, {})
        print(f"⚠️ Profil marchand {merchant_email} récupéré depuis le dictionnaire en mémoire")
    
    # Calculer les statistiques d'évaluations
    merchant_reviews = get_merchant_reviews(merchant_email)
    avg_rating, total_reviews = calculate_merchant_average_rating(merchant_email)
    rating_distribution = get_merchant_rating_distribution(merchant_email)
    
    # Ajouter les stats d'évaluations au merchant
    merchant_stats = {
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'rating_distribution': rating_distribution
    }
    
    return render_template('merchant/profile.html', 
                          merchant=merchant,
                          merchant_stats=merchant_stats)



@app.route('/merchant/profile/update', methods=['POST'])
@merchant_required
def merchant_profile_update():
    """Mise à jour des informations de profil du marchand"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    # Récupérer les nouvelles valeurs
    new_first_name = request.form.get('first_name', merchant.get('first_name', ''))
    new_last_name = request.form.get('last_name', merchant.get('last_name', ''))
    new_phone = request.form.get('phone', merchant.get('phone', ''))
    new_store_name = request.form.get('store_name', merchant.get('store_name', ''))
    new_store_description = request.form.get('store_description', merchant.get('store_description', ''))
    new_store_address = request.form.get('store_address', merchant.get('store_address', ''))
    new_store_city = request.form.get('store_city', merchant.get('store_city', ''))
    new_store_region = request.form.get('store_region', merchant.get('store_region', ''))
    
    # Récupération et validation des coordonnées GPS
    new_latitude = merchant.get('latitude')
    new_longitude = merchant.get('longitude')
    
    try:
        latitude = request.form.get('latitude', '')
        longitude = request.form.get('longitude', '')
        
        if latitude and longitude:
            new_latitude = float(latitude)
            new_longitude = float(longitude)
        elif latitude or longitude:  # Si une seule coordonnée est fournie
            flash('Veuillez fournir à la fois la latitude et la longitude pour les coordonnées GPS.', 'warning')
            return redirect(url_for('merchant_profile'))
    except ValueError:
        flash('Les coordonnées GPS doivent être des nombres décimaux valides (ex: -11.7172, 43.2587).', 'danger')
        return redirect(url_for('merchant_profile'))
    
    # SAUVEGARDER LES MODIFICATIONS DANS LA BASE DE DONNÉES
    try:
        merchant_db = Merchant.query.filter_by(email=merchant_email).first()
        if merchant_db:
            merchant_db.first_name = new_first_name
            merchant_db.last_name = new_last_name
            merchant_db.phone = new_phone
            merchant_db.store_name = new_store_name
            merchant_db.store_description = new_store_description
            merchant_db.store_address = new_store_address
            merchant_db.store_city = new_store_city
            merchant_db.store_region = new_store_region
            merchant_db.latitude = new_latitude
            merchant_db.longitude = new_longitude
            merchant_db.updated_at = datetime.now()
            
            db.session.commit()
            print(f"✅ Profil marchand {merchant_email} mis à jour dans la base de données")
        else:
            print(f"⚠️ Marchand {merchant_email} non trouvé dans la base de données")
            
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour du profil marchand: {e}")
        db.session.rollback()
        flash('Erreur lors de la mise à jour du profil.', 'danger')
        return redirect(url_for('merchant_profile'))
    
    # Mise à jour des informations du profil en mémoire pour compatibilité
    merchant['first_name'] = new_first_name
    merchant['last_name'] = new_last_name
    merchant['phone'] = new_phone
    merchant['store_name'] = new_store_name
    merchant['store_description'] = new_store_description
    merchant['store_address'] = new_store_address
    merchant['store_city'] = new_store_city
    merchant['store_region'] = new_store_region
    merchant['latitude'] = new_latitude
    merchant['longitude'] = new_longitude
    
    # Enregistrer les modifications en mémoire
    merchants_db[merchant_email] = merchant
    
    flash('Profil mis à jour avec succès.', 'success')
    return redirect(url_for('merchant_profile'))

@app.route('/merchant/change-password', methods=['POST'])
@merchant_required
def merchant_change_password():
    """Route pour modifier le mot de passe du marchand"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    # Récupérer les données du formulaire
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Vérifier que tous les champs sont remplis
    if not current_password or not new_password or not confirm_password:
        flash('Tous les champs sont requis.', 'danger')
        return redirect(url_for('merchant_settings'))
    
    # Vérifier que les nouveaux mots de passe correspondent
    if new_password != confirm_password:
        flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
        return redirect(url_for('merchant_settings'))
    
    # Vérifier que le mot de passe actuel est correct
    if not check_password_hash(merchant['password_hash'], current_password):
        flash('Le mot de passe actuel est incorrect.', 'danger')
        return redirect(url_for('merchant_settings'))
    
    # Vérifier la longueur du nouveau mot de passe
    if len(new_password) < 6:
        flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
        return redirect(url_for('merchant_settings'))
    
    # Mettre à jour le mot de passe
    merchant['password_hash'] = generate_password_hash(new_password)
    merchants_db[merchant_email] = merchant
    
    flash('Mot de passe modifié avec succès.', 'success')
    return redirect(url_for('merchant_settings'))

@app.route('/merchant/update-logo', methods=['POST'])
@merchant_required
def merchant_update_logo():
    """Route pour mettre à jour le logo de la boutique"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    # Récupérer l'URL du logo depuis le formulaire
    logo_url = request.form.get('logo_url', '').strip()
    
    # Vérifier si une URL a été fournie
    if not logo_url:
        flash('Veuillez fournir une URL pour le logo.', 'danger')
        return redirect(url_for('merchant_profile'))
    
    # Validation basique de l'URL
    if not logo_url.startswith(('http://', 'https://')):
        flash('L\'URL doit commencer par http:// ou https://', 'danger')
        return redirect(url_for('merchant_profile'))
    
    # Vérifier que l'URL semble être une image
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')
    if not any(logo_url.lower().endswith(ext) for ext in allowed_extensions):
        # Si l'extension n'est pas visible, on accepte quand même (certains services comme Unsplash n'ont pas d'extension visible)
        print(f"URL sans extension image visible, mais on accepte: {logo_url}")
    
    try:
        # SAUVEGARDER DANS LA BASE DE DONNÉES D'ABORD
        merchant_db = Merchant.query.filter_by(email=merchant_email).first()
        if merchant_db:
            merchant_db.store_logo = logo_url
            merchant_db.updated_at = datetime.now()
            db.session.commit()
            print(f"✅ Logo mis à jour en base de données pour {merchant_email}: {logo_url}")
        else:
            print(f"⚠️ Marchand {merchant_email} non trouvé en base de données")
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        merchant['store_logo'] = logo_url
        merchants_db[merchant_email] = merchant
        
        flash('Logo mis à jour avec succès.', 'success')
        print(f"Logo mis à jour pour le marchand {merchant_email}: {logo_url}")
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la mise à jour du logo: {e}")
        flash('Erreur lors de la mise à jour du logo. Veuillez réessayer.', 'danger')
    
    return redirect(url_for('merchant_profile'))

@app.route('/merchant/update-banner', methods=['POST'])
@merchant_required
def merchant_update_banner():
    """Route pour mettre à jour la bannière de la boutique"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    # Récupérer l'URL de la bannière depuis le formulaire
    banner_url = request.form.get('banner_url', '').strip()
    
    # Vérifier si une URL a été fournie
    if not banner_url:
        flash('Veuillez fournir une URL pour la bannière.', 'danger')
        return redirect(url_for('merchant_profile'))
    
    # Validation basique de l'URL
    if not banner_url.startswith(('http://', 'https://')):
        flash('L\'URL doit commencer par http:// ou https://', 'danger')
        return redirect(url_for('merchant_profile'))
    
    # Vérifier que l'URL semble être une image
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')
    if not any(banner_url.lower().endswith(ext) for ext in allowed_extensions):
        # Si l'extension n'est pas visible, on accepte quand même (certains services comme Unsplash n'ont pas d'extension visible)
        print(f"URL sans extension image visible, mais on accepte: {banner_url}")
    
    try:
        # SAUVEGARDER DANS LA BASE DE DONNÉES D'ABORD
        merchant_db = Merchant.query.filter_by(email=merchant_email).first()
        if merchant_db:
            merchant_db.store_banner = banner_url
            merchant_db.updated_at = datetime.now()
            db.session.commit()
            print(f"✅ Bannière mise à jour en base de données pour {merchant_email}: {banner_url}")
        else:
            print(f"⚠️ Marchand {merchant_email} non trouvé en base de données")
        
        # Mettre à jour aussi le dictionnaire en mémoire pour compatibilité
        merchant['store_banner'] = banner_url
        merchants_db[merchant_email] = merchant
        
        flash('Bannière mise à jour avec succès.', 'success')
        print(f"Bannière mise à jour pour le marchand {merchant_email}: {banner_url}")
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la mise à jour de la bannière: {e}")
        flash('Erreur lors de la mise à jour de la bannière. Veuillez réessayer.', 'danger')
    
    return redirect(url_for('merchant_profile'))

@app.route('/merchant/update-notifications', methods=['POST'])
@merchant_required
def merchant_update_notifications():
    """Route pour mettre à jour les paramètres de notification du marchand"""
    merchant_email = session.get('merchant_email')
    merchant = merchants_db.get(merchant_email, {})
    
    # Récupérer les paramètres de notification depuis le formulaire
    email_orders = 'email_orders' in request.form
    email_messages = 'email_messages' in request.form
    email_payment_changes = 'email_payment_changes' in request.form
    sms_orders = 'sms_orders' in request.form
    
    # Initialiser les notifications si elles n'existent pas
    if 'notifications' not in merchant:
        merchant['notifications'] = {}
    
    # Mettre à jour les paramètres
    merchant['notifications']['email_orders'] = email_orders
    merchant['notifications']['email_messages'] = email_messages
    merchant['notifications']['email_payment_changes'] = email_payment_changes
    merchant['notifications']['sms_orders'] = sms_orders
    
    # Sauvegarder les modifications
    merchants_db[merchant_email] = merchant
    
    flash('Paramètres de notification mis à jour avec succès.', 'success')
    return redirect(url_for('merchant_settings'))

# Ajouter la route d'inscription des utilisateurs (manquante)
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription pour les nouveaux utilisateurs"""
    # Rediriger si déjà connecté
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        city = request.form.get('city', '')
        region = request.form.get('region', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation des données
        errors = []
        
        if not all([first_name, last_name, email, password, confirm_password]):
            errors.append('Tous les champs marqués * sont obligatoires.')
        
        if password != confirm_password:
            errors.append('Les mots de passe ne correspondent pas.')
        
        if email in users_db:
            errors.append('Cette adresse email est déjà utilisée.')
        
        # Si des erreurs sont trouvées, afficher et retourner le formulaire
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')
        
        # Créer un nouvel ID utilisateur unique
        user_id = max([u['id'] for u in users_db.values()], default=0) + 1
        
        # Créer le nouvel utilisateur dans la BASE DE DONNÉES
        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            phone=phone if phone else '',
            address=address if address else '',
            city=city if city else '',
            region=region if region else '',
            email_verified=False
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"✅ Utilisateur {email} sauvegardé dans la base de données")
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde utilisateur: {e}")
            db.session.rollback()
            flash('Erreur lors de la création du compte. Veuillez réessayer.', 'danger')
            return render_template('register.html')
        
        # Mettre à jour AUSSI le dictionnaire en mémoire pour compatibilité
        users_db[email] = {
            'id': new_user.id,  # Utiliser l'ID généré par la base de données
            'password_hash': new_user.password_hash,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone if phone else '',
            'address': address if address else '',
            'city': city if city else '',
            'region': region if region else '',
            'created_at': datetime.now().strftime('%Y-%m-%d'),
            'email_verified': False  # Compte non vérifié par défaut
        }
        
        # Créer un token de vérification
        token = create_verification_token(email)
        
        # Envoyer l'email de vérification
        send_verification_email(email, token)
        
        flash('Votre compte a été créé! Vérifiez votre email pour activer votre compte.', 'info')
        return redirect(url_for('email_verification_required'))
    
    # Passer les régions disponibles au template
    regions = [
        {'value': 'grande-comore', 'name': 'Grande Comore'},
        {'value': 'anjouan', 'name': 'Anjouan'},
        {'value': 'moheli', 'name': 'Mohéli'}
    ]
    
    return render_template('register.html', regions=regions)

# Routes pour la gestion des avis/évaluations
@app.route('/submit-review', methods=['POST'])
@login_required
def submit_review():
    """Soumettre un avis pour un produit"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        product_id = int(data.get('product_id'))
        rating = int(data.get('rating'))
        title = data.get('title', '').strip()
        comment = data.get('comment', '').strip()
        
        # Validation
        if not product_id or not rating or rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': 'Données invalides'}), 400
        
        # Récupérer les informations de l'utilisateur
        user_email = session.get('user_email')
        user = get_user_by_email(user_email)
        
        if not user:
            print(f"❌ Utilisateur non trouvé - Email: {user_email}")
            return jsonify({'success': False, 'message': 'Utilisateur non trouvé'}), 404
        
        user_name = f"{user['first_name']} {user['last_name'][0]}."
        
        # Ajouter l'avis
        review = add_review(
            product_id=product_id,
            user_id=user['id'],
            rating=rating,
            title=title,
            comment=comment,
            user_name=user_name
        )
        
        # Mettre à jour la note moyenne du produit
        avg_rating, reviews_count = calculate_average_rating(product_id)
        
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': 'Votre avis a été ajouté avec succès!',
                'review': review,
                'avg_rating': avg_rating,
                'reviews_count': reviews_count
            })
        else:
            flash('Votre avis a été ajouté avec succès!', 'success')
            return redirect(request.referrer or url_for('home'))
            
    except ValueError:
        message = 'Données invalides'
    except Exception as e:
        message = f'Erreur lors de l\'ajout de l\'avis: {str(e)}'
    
    if request.is_json:
        return jsonify({'success': False, 'message': message}), 500
    else:
        flash(message, 'danger')
        return redirect(request.referrer or url_for('home'))

@app.route('/submit-order-review', methods=['POST'])
@login_required
def submit_order_review():
    """Soumettre des avis pour plusieurs produits d'une commande"""
    try:
        data = request.get_json() if request.is_json else request.form
        order_id = data.get('order_id')
        reviews_data = data.get('reviews', [])
        
        if not order_id or not reviews_data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        # Récupérer les informations de l'utilisateur
        user_email = session.get('user_email')
        user = get_user_by_email(user_email)
        
        if not user:
            print(f"❌ Utilisateur non trouvé - Email: {user_email}")
            return jsonify({'success': False, 'message': 'Utilisateur non trouvé'}), 404
        
        user_name = f"{user['first_name']} {user['last_name'][0]}."
        added_reviews = []
        
        # Traiter chaque avis
        for review_data in reviews_data:
            try:
                product_id = int(review_data.get('product_id'))
                rating = int(review_data.get('rating'))
                comment = review_data.get('comment', '').strip()
                
                if rating >= 1 and rating <= 5:
                    review = add_review(
                        product_id=product_id,
                        user_id=user['id'],
                        rating=rating,
                        title=f"Avis sur commande #{order_id}",
                        comment=comment,
                        user_name=user_name
                    )
                    added_reviews.append(review)
            except (ValueError, TypeError):
                continue  # Ignorer les données invalides
        
        if added_reviews:
            message = f"{len(added_reviews)} avis ajouté(s) avec succès!"
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'reviews': added_reviews})
            else:
                flash(message, 'success')
        else:
            message = "Aucun avis valide n'a pu être ajouté"
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 400
            else:
                flash(message, 'warning')
        
        return redirect(request.referrer or url_for('orders')) if not request.is_json else None
        
    except Exception as e:
        message = f'Erreur lors de l\'ajout des avis: {str(e)}'
        if request.is_json:
            return jsonify({'success': False, 'message': message}), 500
        else:
            flash(message, 'danger')
            return redirect(request.referrer or url_for('orders'))

@app.route('/product-reviews/<int:product_id>')
def get_product_reviews_api(product_id):
    """API pour récupérer les avis d'un produit"""
    try:
        reviews = get_product_reviews(product_id)
        avg_rating, reviews_count = calculate_average_rating(product_id)
        
        return jsonify({
            'success': True,
            'reviews': reviews,
            'avg_rating': avg_rating,
            'reviews_count': reviews_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/add_to_cart', methods=['POST'])
def api_add_to_cart():
    """API pour ajouter un produit au panier avec des options et quantités"""
    try:
        # Gérer les données JSON ou FormData
        if request.is_json:
            # Données JSON
            data = request.get_json()
            if data is None:
                return jsonify({'error': 'Données JSON manquantes ou invalides'}), 400
            
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            options = data.get('options', {})
        else:
            # Données FormData
            product_id = request.form.get('product_id')
            quantity = int(request.form.get('quantity', 1))
            
            # Pour FormData, reconstruire les options depuis les paramètres
            options = {}
            
            # Si on n'a pas de product_id, chercher dans d'autres champs possibles
            if not product_id:
                # Chercher product_id dans d'autres champs possibles
                product_id = request.form.get('product_name', '')  # Fallback si nécessaire
        
        if not product_id:
            return jsonify({'error': 'ID du produit manquant'}), 400
        
        # Récupérer le produit - essayer comme produit standard
        product = None
        
        # Essayer de récupérer comme produit standard
        try:
            # Si l'ID est numérique, essayer directement
            if str(product_id).isdigit():
                product = get_product_by_id(int(product_id))
            else:
                # Pour les IDs complexes, essayer de récupérer quand même
                product = get_product_by_id(product_id)
        except (ValueError, TypeError):
            pass  # Ignorer les erreurs de conversion
        
        if not product:
            return jsonify({'error': 'Produit non trouvé'}), 404
        
        # ✅ NOUVEAU: Vérifier le stock avant d'ajouter au panier
        try:
            numeric_product_id = int(product_id) if str(product_id).isdigit() else product['id']
            stock_check = check_product_stock_availability(numeric_product_id, quantity)
            if not stock_check['available']:
                return jsonify({
                    'error': stock_check['message'],
                    'stock_error': True,
                    'available_stock': stock_check['current_stock'],
                    'requested_quantity': quantity
                }), 400
        except Exception as e:
            print(f"Erreur lors de la vérification du stock dans API: {e}")
            # En cas d'erreur, continuer sans bloquer (pour compatibilité)
            pass
        
        # Récupérer le panier de la session
        if 'cart' not in session:
            session['cart'] = []
        
        cart = session['cart']
        
        # Générer un ID unique pour cette combinaison produit + options
        import uuid
        cart_item_id = str(uuid.uuid4())
        
        # Calculer le prix avec les options
        base_price = product['price']
        options_price = 0
        
        # Traiter les options si le produit en a
        if 'options' in product and product['options']:
            for option_group in product['options']:
                option_group_name = option_group['name']
                if option_group_name in options:
                    selected_options = options[option_group_name]
                    
                    # Vérifier si c'est une sélection simple ou multiple
                    if option_group['type'] == 'single':
                        # Sélection simple
                        for option in option_group['options']:
                            if option['name'] == selected_options:
                                options_price += option.get('price', 0)
                                break
                    elif option_group['type'] == 'multiple':
                        # Sélection multiple
                        if isinstance(selected_options, list):
                            for selected_option in selected_options:
                                for option in option_group['options']:
                                    if option['name'] == selected_option:
                                        options_price += option.get('price', 0)
                                        break
        
        total_price = (base_price + options_price) * quantity
        
        # Créer l'article du panier
        cart_item = {
            'id': cart_item_id,
            'product_id': product_id,
            'unique_id': cart_item_id,  # ID unique pour cet article dans le panier
            'name': product['name'],
            'price': base_price,
            'quantity': quantity,
            'options': options,
            'options_price': options_price,
            'total_price': total_price,
            'image': product.get('image', ''),
            'category': product.get('category', ''),
            'restaurant': product.get('restaurant', 'Restaurant')
        }
        
        # Ajouter au panier
        cart.append(cart_item)
        session['cart'] = cart
        
        # Calculer le nombre total d'articles dans le panier
        total_items = sum(item['quantity'] for item in cart)
        
        return jsonify({
            'success': True,
            'message': 'Produit ajouté au panier',
            'cart_item': cart_item,
            'total_items': total_items
        })
    
    except ValueError as e:
        print(f"Erreur de valeur dans api_add_to_cart: {str(e)}")
        return jsonify({'error': f'Erreur de valeur: {str(e)}'}), 400
    except Exception as e:
        print(f"Erreur inattendue dans api_add_to_cart: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Erreur inattendue: {str(e)}'}), 500

@app.route('/admin/api/session-check', methods=['GET'])
def admin_session_check():
    """API pour vérifier si la session admin est valide"""
    if 'admin_id' not in session and 'admin_email' not in session:
        return jsonify({'valid': False, 'message': 'Session expirée'}), 401
    
    admin_email = session.get('admin_email')
    return jsonify({
        'valid': True, 
        'admin_email': admin_email,
        'message': 'Session valide'
    }), 200

# =============================================
# INITIALISATION POUR LA PRODUCTION
# =============================================

def migrate_database_schema():
    """Gère les migrations de schéma pour ajouter les colonnes manquantes avec gestion robuste des transactions"""
    try:
        print("🔄 Vérification et migration du schéma de base de données...")
        
        # S'assurer que la session est propre avant de commencer
        try:
            db.session.rollback()
        except Exception:
            pass
        
        # Liste des colonnes à vérifier/ajouter
        migrations = [
            {
                'table': 'orders',
                'column': 'shipping_method',
                'definition': 'VARCHAR(100) DEFAULT \'Standard\'',
                'description': 'Méthode de livraison'
            }
        ]
        
        for migration in migrations:
            table = migration['table']
            column = migration['column']
            definition = migration['definition']
            description = migration['description']
            
            try:
                # Tester si la colonne existe avec une requête simple
                test_query = f"SELECT {column} FROM {table} LIMIT 1"
                db.session.execute(db.text(test_query))
                print(f"✅ Colonne {table}.{column} existe déjà")
                
            except Exception as e:
                error_str = str(e).lower()
                if "does not exist" in error_str or "no such column" in error_str:
                    print(f"❌ Colonne {table}.{column} manquante, ajout en cours...")
                    
                    try:
                        # Nettoyer toute transaction en cours
                        db.session.rollback()
                        
                        # Ajouter la colonne avec une nouvelle transaction
                        alter_query = f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                        db.session.execute(db.text(alter_query))
                        db.session.commit()
                        
                        print(f"✅ Colonne {table}.{column} ajoutée avec succès ({description})")
                        
                    except Exception as add_error:
                        print(f"❌ Erreur lors de l'ajout de {column}: {add_error}")
                        # Rollback en cas d'erreur
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
                        
                        # Si c'est une erreur de transaction fermée, on continue
                        if "current transaction is aborted" in str(add_error):
                            print("⚠️ Transaction fermée, on continue sans cette migration")
                            continue
                        else:
                            raise add_error
                else:
                    print(f"⚠️ Erreur inattendue lors du test de {table}.{column}: {e}")
                    # Rollback et continuer
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
        
        print("✅ Migration du schéma terminée")
        
    except Exception as e:
        print(f"❌ Erreur générale lors de la migration: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass

def initialize_production_db():
    """Initialiser la base de données pour la production"""
    try:
        with app.app_context():
            print("🔄 Initialisation de la base de données pour la production...")
            
            # Créer toutes les tables
            db.create_all()
            print("✅ Tables de base de données créées")
            
            # **NOUVEAU: Gestion des migrations de schéma**
            migrate_database_schema()
            
            # **AMÉLIORATION: Debugging des variables d'environnement**
            print("🔍 Vérification des variables d'environnement admin...")
            admin_email = os.environ.get('ADMIN_EMAIL')
            admin_password = os.environ.get('ADMIN_PASSWORD') 
            admin_name = os.environ.get('ADMIN_NAME')
            
            print(f"   ADMIN_EMAIL: {'✅ Défini' if admin_email else '❌ Manquant'}")
            print(f"   ADMIN_PASSWORD: {'✅ Défini' if admin_password else '❌ Manquant'}")
            print(f"   ADMIN_NAME: {'✅ Défini' if admin_name else '❌ Manquant'}")
            
            if admin_email and admin_password and admin_name:
                print(f"🔄 Création/vérification du compte administrateur: {admin_email}")
                
                # Vérifier si l'admin existe déjà
                try:
                    existing_admin = Admin.query.filter_by(email=admin_email).first()
                    print(f"🔍 Recherche admin existant: {'Trouvé' if existing_admin else 'Non trouvé'}")
                except Exception as e:
                    print(f"⚠️ Erreur recherche admin: {e}")
                    existing_admin = None
                
                if not existing_admin:
                    print(f"🔄 Création du compte administrateur: {admin_email}")
                    
                    # Séparer le nom complet en prénom et nom de famille
                    name_parts = admin_name.split(' ', 1)
                    first_name = name_parts[0] if len(name_parts) > 0 else 'Admin'
                    last_name = name_parts[1] if len(name_parts) > 1 else 'DOUKA KM'
                    
                    print(f"   Prénom: {first_name}")
                    print(f"   Nom: {last_name}")
                    
                    # Créer le nouvel administrateur avec debug
                    try:
                        password_hash = generate_password_hash(admin_password)
                        print(f"   Hash mot de passe généré: {password_hash[:30]}...")
                        
                        new_admin = Admin(
                            email=admin_email,
                            first_name=first_name,
                            last_name=last_name,
                            password_hash=password_hash,
                            role='super_admin',
                            status='active'
                        )
                        
                        print("   Ajout de l'admin à la session...")
                        db.session.add(new_admin)
                        
                        print("   Commit en base de données...")
                        db.session.commit()
                        
                        print(f"✅ Compte administrateur créé avec succès!")
                        print(f"   Email: {admin_email}")
                        print(f"   Nom complet: {first_name} {last_name}")
                        print(f"   Rôle: super_admin")
                        print(f"   Mot de passe: {admin_password}")
                        
                        # Vérification finale
                        verify_admin = Admin.query.filter_by(email=admin_email).first()
                        if verify_admin:
                            print("✅ Vérification: Admin trouvé dans la base de données")
                            print(f"   ID: {verify_admin.id}")
                            print(f"   Statut: {verify_admin.status}")
                        else:
                            print("❌ Vérification: Admin NON trouvé après création!")
                            
                    except Exception as e:
                        db.session.rollback()
                        print(f"❌ Erreur lors de la création de l'administrateur: {e}")
                        print(f"   Type d'erreur: {type(e).__name__}")
                        import traceback
                        print(f"   Traceback: {traceback.format_exc()}")
                else:
                    print(f"ℹ️ Compte administrateur existe déjà: {admin_email}")
                    print(f"   ID: {existing_admin.id}")
                    print(f"   Statut: {existing_admin.status}")
                    print(f"   Rôle: {existing_admin.role}")
            else:
                print("⚠️ Variables d'environnement administrateur manquantes!")
                print(f"   ADMIN_EMAIL: {repr(admin_email)}")
                print(f"   ADMIN_PASSWORD: {'[DÉFINI]' if admin_password else '[MANQUANT]'}")
                print(f"   ADMIN_NAME: {repr(admin_name)}")
                
                # **FALLBACK: Créer l'admin avec des valeurs par défaut**
                print("🔄 Création d'un admin par défaut...")
                fallback_email = 'admin@doukakm.com'
                fallback_password = 'admin123!'
                fallback_name = 'Super Admin DOUKA KM'
                
                existing_admin = Admin.query.filter_by(email=fallback_email).first()
                if not existing_admin:
                    try:
                        new_admin = Admin(
                            email=fallback_email,
                            first_name='Super',
                            last_name='Admin DOUKA KM',
                            password_hash=generate_password_hash(fallback_password),
                            role='super_admin',
                            status='active'
                        )
                        db.session.add(new_admin)
                        db.session.commit()
                        print(f"✅ Admin par défaut créé: {fallback_email}")
                        print(f"   Mot de passe: {fallback_password}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"❌ Erreur création admin par défaut: {e}")
            
            # Initialiser les proxies de base de données
            initialize_db_proxies()
            
            # S'assurer que les répertoires nécessaires existent
            ensure_directories_exist()
            
            print("✅ Base de données initialisée avec succès pour la production!")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        raise

# Initialiser automatiquement en production
# DÉSACTIVÉ: L'initialisation se fait maintenant via init_render.py pour éviter les doubles appels
# if os.environ.get('RENDER'):
#     initialize_production_db()

# =============================================
# GESTION D'ERREURS
# =============================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# =============================================
# ROUTES DE MAINTENANCE ET DEBUG
# =============================================

@app.route('/admin/fix-logo-urgent')
def fix_logo_urgent():
    """Route d'urgence pour corriger les paramètres du logo manquant en production"""
    try:
        # Vérifier si logo_url existe
        logo_url_setting = SiteSettings.query.filter_by(key='logo_url').first()
        if not logo_url_setting:
            logo_url_setting = SiteSettings(
                key='logo_url',
                value='/static/img/logo.svg',
                description='URL du logo du site'
            )
            db.session.add(logo_url_setting)
        elif not logo_url_setting.value or logo_url_setting.value.strip() == '':
            logo_url_setting.value = '/static/img/logo.svg'
        
        # Vérifier si logo_alt_text existe
        logo_alt_setting = SiteSettings.query.filter_by(key='logo_alt_text').first()
        if not logo_alt_setting:
            logo_alt_setting = SiteSettings(
                key='logo_alt_text',
                value='DOUKA KM - Marketplace des Comores',
                description='Texte alternatif pour le logo'
            )
            db.session.add(logo_alt_setting)
        elif not logo_alt_setting.value or logo_alt_setting.value.strip() == '':
            logo_alt_setting.value = 'DOUKA KM - Marketplace des Comores'
        
        db.session.commit()
        
        # Vérifier le résultat
        updated_settings = get_all_site_settings()
        
        return jsonify({
            'success': True,
            'message': 'Logo corrigé avec succès!',
            'logo_url': updated_settings.get('logo_url'),
            'logo_alt_text': updated_settings.get('logo_alt_text'),
            'all_settings': {k: v for k, v in updated_settings.items() if 'logo' in k.lower()}
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Échec de la correction du logo'
        }), 500

@app.route('/debug/site-settings')
def debug_site_settings():
    """Route de debug pour vérifier les paramètres du site"""
    try:
        # Récupérer tous les paramètres de la base
        db_settings = {}
        settings_records = SiteSettings.query.all()
        for setting in settings_records:
            db_settings[setting.key] = setting.value
        
        # Récupérer les paramètres via la fonction
        computed_settings = get_all_site_settings()
        
        return jsonify({
            'database_settings': db_settings,
            'computed_settings': computed_settings,
            'logo_info': {
                'logo_url_in_db': db_settings.get('logo_url'),
                'logo_url_computed': computed_settings.get('logo_url'),
                'logo_alt_computed': computed_settings.get('logo_alt_text'),
                'static_path_exists': os.path.exists(os.path.join(app.static_folder, 'img', 'logo.png'))
            }
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Erreur lors du debug des paramètres'
        }), 500

@app.route('/static/img/<filename>')
def serve_static_image(filename):
    """Route explicite pour servir les images statiques sur Render.com"""
    try:
        # Chemin vers le dossier static/img
        img_folder = os.path.join(app.static_folder, 'img')
        
        # Vérifier si le fichier existe
        file_path = os.path.join(img_folder, filename)
        if os.path.exists(file_path):
            return send_from_directory(img_folder, filename)
        else:
            # Si le fichier n'existe pas, retourner une image par défaut ou 404
            return "Image not found", 404
            
    except Exception as e:
        print(f"Erreur lors du service de l'image {filename}: {e}")
        return "Error serving image", 500

@app.route('/logo')
def serve_logo():
    """Route directe pour servir le logo DOUKA KM"""
    try:
        # Chemin vers le logo
        img_folder = os.path.join(app.static_folder, 'img')
        logo_path = os.path.join(img_folder, 'logo.png')
        
        if os.path.exists(logo_path):
            return send_from_directory(img_folder, 'logo.png', mimetype='image/png')
        else:
            # Si le logo n'existe pas, retourner une image par défaut ou générer une réponse
            return "Logo not found", 404
            
    except Exception as e:
        print(f"Erreur lors du service du logo: {e}")
        return "Error serving logo", 500

@app.route('/debug/logo-test')
def debug_logo_test():
    """Route de debug pour tester l'accès au logo"""
    try:
        # Tester différents chemins pour le logo
        static_folder = app.static_folder or 'static'
        logo_path = os.path.join(static_folder, 'img', 'logo.png')
        
        # Vérifications
        results = {
            'static_folder': static_folder,
            'logo_path': logo_path,
            'logo_exists': os.path.exists(logo_path),
            'static_folder_exists': os.path.exists(static_folder),
            'img_folder_exists': os.path.exists(os.path.join(static_folder, 'img')),
            'current_directory': os.getcwd(),
            'app_static_folder': app.static_folder,
            'url_for_logo': url_for('static', filename='img/logo.svg'),
            'render_env': os.environ.get('RENDER', 'Not set'),
        }
        
        # Tenter de lire le fichier
        if os.path.exists(logo_path):
            try:
                file_size = os.path.getsize(logo_path)
                results['logo_size'] = f"{file_size} bytes"
            except Exception as e:
                results['logo_size_error'] = str(e)
        
        # Lister le contenu du dossier img
        img_dir = os.path.join(static_folder, 'img')
        if os.path.exists(img_dir):
            try:
                results['img_files'] = os.listdir(img_dir)
            except Exception as e:
                results['img_files_error'] = str(e)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Erreur lors du test du logo'
        }), 500

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(app.root_path, 'sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt', mimetype='text/plain')

@app.route('/manifest.json')
def manifest():
    return send_from_directory(app.static_folder, 'manifest.json', mimetype='application/json')

# =============================================
# LANCEMENT DE L'APPLICATION
# =============================================

# Bloc pour lancer l'application directement
if __name__ == '__main__':
    try:
        # S'assurer que les répertoires nécessaires existent avant de démarrer
        ensure_directories_exist()
        
        # Créer les tables si elles n'existent pas et initialiser les proxies
        with app.app_context():
            db.create_all()
            
            # **CORRECTION CRITIQUE: Créer l'admin aussi en développement**
            # Créer l'admin par défaut en développement
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@doukakm.com')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123!')
            admin_name = os.environ.get('ADMIN_NAME', 'Super Admin DOUKA KM')
            
            existing_admin = Admin.query.filter_by(email=admin_email).first()
            if not existing_admin:
                print(f"🔄 Création du compte administrateur pour le développement: {admin_email}")
                
                # Séparer le nom complet en prénom et nom de famille
                name_parts = admin_name.split(' ', 1)
                first_name = name_parts[0] if len(name_parts) > 0 else 'Admin'
                last_name = name_parts[1] if len(name_parts) > 1 else 'DOUKA KM'
                
                # Créer le nouvel administrateur
                new_admin = Admin(
                    email=admin_email,
                    first_name=first_name,
                    last_name=last_name,
                    password_hash=generate_password_hash(admin_password),
                    role='super_admin',
                    status='active'
                )
                
                try:
                    db.session.add(new_admin)
                    db.session.commit()
                    print(f"✅ Compte administrateur créé: {admin_email}")
                    print(f"   Nom: {first_name} {last_name}")
                    print(f"   Mot de passe: {admin_password}")
                    print(f"   Rôle: super_admin")
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Erreur création administrateur: {e}")
            else:
                print(f"ℹ️ Compte administrateur existe déjà: {admin_email}")
            
            initialize_db_proxies()
        
        print("🚀 Application DOUKA KM COMPLÈTE avec base de données SQLite démarrée!")
        print("📁 Base de données: douka_km.db")
        print("🌐 URL: http://localhost:5002")
        print("="*60)
        
        # Lancer le serveur Flask avec le mode debug activé sur le port 5003
        app.run(debug=True, host='0.0.0.0', port=5003)
        
    except Exception as e:
        print(f"❌ Erreur au démarrage de l'application: {e}")