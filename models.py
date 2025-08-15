#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Models - Modèles de base de données pour DOUKA KM
Utilise SQLAlchemy pour la gestion de la base de données
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    """Modèle pour les utilisateurs clients"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(50), nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    orders = db.relationship('Order', backref='customer', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True)
    carts = db.relationship('Cart', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'password_hash': self.password_hash,  # Inclure le hash du mot de passe
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'region': self.region,
            'email_verified': self.email_verified,
            'is_active': self.is_active,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }

class Merchant(db.Model):
    """Modèle pour les marchands"""
    __tablename__ = 'merchants'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    
    # Informations de la boutique
    store_name = db.Column(db.String(200), nullable=False)
    store_description = db.Column(db.Text, nullable=True)
    store_address = db.Column(db.Text, nullable=True)
    store_city = db.Column(db.String(100), nullable=True)
    store_region = db.Column(db.String(50), nullable=True)
    store_logo = db.Column(db.String(500), default='static/img/merchants/store_logo_default.png')
    store_banner = db.Column(db.String(500), default='static/img/merchants/store_banner_default.jpg')
    store_verified = db.Column(db.Boolean, default=False)
    
    # Coordonnées GPS
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Informations bancaires (JSON)
    bank_info = db.Column(db.Text, nullable=True)  # Stocké en JSON
    
    # Paramètres de notification (JSON)
    notifications = db.Column(db.Text, nullable=True)  # Stocké en JSON
    
    # Balance et statistiques
    balance = db.Column(db.Float, default=0.0)
    
    # Statut du compte
    status = db.Column(db.String(20), default='active')  # active, inactive, suspended
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    products = db.relationship('Product', backref='merchant', lazy=True)
    orders = db.relationship('Order', backref='merchant', lazy=True)
    withdrawal_requests = db.relationship('WithdrawalRequest', backref='merchant', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_bank_info(self):
        if self.bank_info:
            return json.loads(self.bank_info)
        return {}
    
    def set_bank_info(self, bank_data):
        self.bank_info = json.dumps(bank_data)
    
    def get_notifications(self):
        if self.notifications:
            return json.loads(self.notifications)
        return {
            'email_orders': True,
            'email_messages': True,
            'email_payment_changes': True,
            'sms_orders': False
        }
    
    def set_notifications(self, notifications_data):
        self.notifications = json.dumps(notifications_data)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'store_name': self.store_name,
            'store_description': self.store_description,
            'store_address': self.store_address,
            'store_city': self.store_city,
            'store_region': self.store_region,
            'store_logo': self.store_logo,
            'store_banner': self.store_banner,
            'store_verified': self.store_verified,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'balance': self.balance,
            'status': self.status,  # Ajout du statut pour la suspension
            'bank_info': self.get_bank_info(),
            'notifications': self.get_notifications(),
            'registration_date': self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }

class Admin(db.Model):
    """Modèle pour les administrateurs"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(50), default='admin')  # super_admin, admin, manager, livreur
    phone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, inactive, suspended
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(120), nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'password_hash': self.password_hash,  # Inclure le hash du mot de passe
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'phone': self.phone,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }

class Category(db.Model):
    """Modèle pour les catégories de produits"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), nullable=True)
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(120), nullable=True)
    
    # Relations
    subcategories = db.relationship('Subcategory', backref='category', lazy=True)
    products = db.relationship('Product', backref='category', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'active': self.active,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'created_by': self.created_by
        }

class Subcategory(db.Model):
    """Modèle pour les sous-catégories"""
    __tablename__ = 'subcategories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(120), nullable=True)
    
    # Relations
    products = db.relationship('Product', backref='subcategory', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
            'active': self.active,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'created_by': self.created_by
        }

class Product(db.Model):
    """Modèle pour les produits"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    
    # Relations avec les catégories
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.id'), nullable=True)
    
    # Images
    image = db.Column(db.String(500), nullable=True)
    images = db.Column(db.Text, nullable=True)  # JSON array des images
    
    # Propriétés du produit
    status = db.Column(db.String(20), default='active')  # active, inactive, out_of_stock
    source = db.Column(db.String(20), default='admin')  # admin, merchant, static
    
    # Relation avec le marchand (optionnel pour les produits admin)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchants.id'), nullable=True)
    
    # Options et variantes (stockées en JSON)
    colors = db.Column(db.Text, nullable=True)  # JSON
    sizes = db.Column(db.Text, nullable=True)  # JSON
    price_combinations = db.Column(db.Text, nullable=True)  # JSON
    specifications = db.Column(db.Text, nullable=True)  # JSON
    
    # Statistiques
    rating = db.Column(db.Float, default=0.0)
    reviews_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    reviews = db.relationship('Review', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='product', lazy=True)
    
    def get_images(self):
        if self.images:
            return json.loads(self.images)
        return [self.image] if self.image else []
    
    def set_images(self, images_list):
        self.images = json.dumps(images_list)
    
    def get_colors(self):
        if self.colors:
            return json.loads(self.colors)
        return []
    
    def set_colors(self, colors_list):
        self.colors = json.dumps(colors_list)
    
    def get_sizes(self):
        if self.sizes:
            return json.loads(self.sizes)
        return []
    
    def set_sizes(self, sizes_list):
        self.sizes = json.dumps(sizes_list)
    
    def get_price_combinations(self):
        if self.price_combinations:
            return json.loads(self.price_combinations)
        return []
    
    def set_price_combinations(self, combinations_list):
        self.price_combinations = json.dumps(combinations_list)
    
    def get_specifications(self):
        if self.specifications:
            return json.loads(self.specifications)
        return {}
    
    def set_specifications(self, specs_dict):
        self.specifications = json.dumps(specs_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'category_id': self.category_id,
            'subcategory_id': self.subcategory_id,
            'image': self.image,
            'images': self.get_images(),
            'status': self.status,
            'source': self.source,
            'merchant_id': self.merchant_id,
            'merchant_email': self.merchant.email if self.merchant else None,
            'colors': self.get_colors(),
            'sizes': self.get_sizes(),
            'price_combinations': self.get_price_combinations(),
            'specifications': self.get_specifications(),
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'in_stock': self.stock > 0,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d') if self.updated_at else None
        }

class Order(db.Model):
    """Modèle pour les commandes"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # Relations avec client et marchand
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchants.id'), nullable=True)
    
    # Informations de la commande
    total = db.Column(db.Float, nullable=False)
    shipping_fee = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    
    # Statuts
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, processing, shipped, delivered, cancelled
    payment_status = db.Column(db.String(50), default='pending')  # pending, completed, failed
    payment_method = db.Column(db.String(100), nullable=True)  # cash, mvola, holo, bank_transfer, etc.
    
    # Adresse de livraison (JSON)
    shipping_address = db.Column(db.Text, nullable=True)
    
    # Informations client
    customer_name = db.Column(db.String(200), nullable=True)
    customer_email = db.Column(db.String(120), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    
    # Code promo utilisé
    promo_code_used = db.Column(db.String(50), nullable=True)
    
    # Dates importantes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processing_date = db.Column(db.DateTime, nullable=True)
    shipping_date = db.Column(db.DateTime, nullable=True)
    delivery_date = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    # Gestion de stock
    stock_reserved = db.Column(db.Boolean, default=False, nullable=False)
    stock_released_at = db.Column(db.DateTime, nullable=True)
    stock_confirmed_at = db.Column(db.DateTime, nullable=True)
    
    # Historique des statuts (JSON)
    status_history = db.Column(db.Text, nullable=True)
    
    # Relations
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def get_shipping_address(self):
        if self.shipping_address:
            return json.loads(self.shipping_address)
        return {}
    
    def set_shipping_address(self, address_dict):
        self.shipping_address = json.dumps(address_dict)
    
    def get_status_history(self):
        """Retourne l'historique des statuts"""
        if self.status_history:
            try:
                return json.loads(self.status_history)
            except:
                return []
        return []
    
    def add_status_change(self, new_status, notes=None, changed_by=None):
        """Ajoute un changement de statut à l'historique"""
        from datetime import datetime
        
        status_map = {
            'pending': 'En cours de préparation',
            'confirmed': 'Confirmée',
            'processing': 'En cours de préparation',
            'shipped': 'Expédiée',
            'delivered': 'Livrée',
            'cancelled': 'Annulée',
            'refunded': 'Remboursée'
        }
        
        # Récupérer l'historique actuel
        history = self.get_status_history()
        
        # Créer l'entrée d'historique
        history_entry = {
            'status': new_status,
            'status_text': status_map.get(new_status, new_status.title()),
            'date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'text': notes or f"Commande {status_map.get(new_status, new_status)}",
            'changed_by': changed_by or 'Système'
        }
        
        # Ajouter au début de la liste (plus récent en premier)
        history.insert(0, history_entry)
        
        # Limiter l'historique à 20 entrées maximum
        if len(history) > 20:
            history = history[:20]
        
        # Sauvegarder l'historique mis à jour
        self.status_history = json.dumps(history)
        
        return history_entry
    
    @property
    def status_text(self):
        """Retourne le texte correspondant au statut"""
        status_map = {
            'pending': 'En cours de préparation',
            'confirmed': 'Confirmée',
            'processing': 'En cours de préparation',
            'shipped': 'Expédiée',
            'delivered': 'Livrée',
            'cancelled': 'Annulée',
            'refunded': 'Remboursée'
        }
        return status_map.get(self.status, self.status.title())
    
    @property
    def status_color(self):
        """Retourne la couleur correspondant au statut"""
        color_map = {
            'pending': 'warning',
            'confirmed': 'info',
            'processing': 'primary',
            'shipped': 'info',
            'delivered': 'success',
            'cancelled': 'danger',
            'refunded': 'secondary'
        }
        return color_map.get(self.status, 'secondary')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'merchant_id': self.merchant_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'total': self.total,
            'shipping_fee': self.shipping_fee,
            'discount': self.discount,
            'status': self.status,
            'status_text': self.status_text,
            'status_color': self.status_color,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'shipping_address': self.get_shipping_address(),
            'promo_code_used': self.promo_code_used,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'processing_date': self.processing_date.strftime('%Y-%m-%d %H:%M:%S') if self.processing_date else None,
            'shipping_date': self.shipping_date.strftime('%Y-%m-%d %H:%M:%S') if self.shipping_date else None,
            'delivery_date': self.delivery_date.strftime('%Y-%m-%d %H:%M:%S') if self.delivery_date else None,
            'cancelled_at': self.cancelled_at.strftime('%Y-%m-%d %H:%M:%S') if self.cancelled_at else None,
            'stock_reserved': self.stock_reserved,
            'stock_released_at': self.stock_released_at.strftime('%Y-%m-%d %H:%M:%S') if self.stock_released_at else None,
            'stock_confirmed_at': self.stock_confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if self.stock_confirmed_at else None,
            'items': [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    """Modèle pour les articles d'une commande"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    # Options sélectionnées (JSON)
    options = db.Column(db.Text, nullable=True)
    variant_details = db.Column(db.String(500), nullable=True)
    
    # Image du produit au moment de la commande
    image = db.Column(db.String(500), nullable=True)
    
    def get_options(self):
        if self.options:
            return json.loads(self.options)
        return {}
    
    def set_options(self, options_dict):
        self.options = json.dumps(options_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity,
            'subtotal': self.subtotal,
            'options': self.get_options(),
            'variant_details': self.variant_details,
            'image': self.image
        }

class Review(db.Model):
    """Modèle pour les avis clients"""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(200), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    verified_purchase = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name[0]}." if self.user else "Utilisateur",
            'rating': self.rating,
            'title': self.title,
            'comment': self.comment,
            'verified_purchase': self.verified_purchase,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class PromoCode(db.Model):
    """Modèle pour les codes promo"""
    __tablename__ = 'promo_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    type = db.Column(db.String(20), nullable=False)  # percentage, fixed
    value = db.Column(db.Float, nullable=False)
    min_amount = db.Column(db.Float, default=0)
    max_discount = db.Column(db.Float, nullable=True)
    
    usage_limit = db.Column(db.Integer, nullable=True)
    used_count = db.Column(db.Integer, default=0)
    user_limit = db.Column(db.Integer, default=1)
    
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    
    active = db.Column(db.Boolean, default=True)
    public_display = db.Column(db.Boolean, default=False)
    display_priority = db.Column(db.Integer, default=0)
    
    # Applicabilité
    applicable_to = db.Column(db.String(50), default='all')  # all, categories, subcategories, products, merchants
    applicable_categories = db.Column(db.Text, nullable=True)  # JSON
    applicable_subcategories = db.Column(db.Text, nullable=True)  # JSON
    applicable_products = db.Column(db.Text, nullable=True)  # JSON
    applicable_merchants = db.Column(db.Text, nullable=True)  # JSON
    
    used_by = db.Column(db.Text, nullable=True)  # JSON: {user_email: count}
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(120), nullable=True)
    
    def get_applicable_categories(self):
        if self.applicable_categories:
            return json.loads(self.applicable_categories)
        return []
    
    def get_applicable_subcategories(self):
        if self.applicable_subcategories:
            return json.loads(self.applicable_subcategories)
        return []
    
    def get_applicable_products(self):
        if self.applicable_products:
            return json.loads(self.applicable_products)
        return []
    
    def get_applicable_merchants(self):
        if self.applicable_merchants:
            return json.loads(self.applicable_merchants)
        return []
    
    def get_used_by(self):
        if self.used_by:
            return json.loads(self.used_by)
        return {}
    
    def set_used_by(self, used_by_dict):
        self.used_by = json.dumps(used_by_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'value': self.value,
            'min_amount': self.min_amount,
            'max_discount': self.max_discount,
            'usage_limit': self.usage_limit,
            'used_count': self.used_count,
            'user_limit': self.user_limit,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'active': self.active,
            'public_display': self.public_display,
            'display_priority': self.display_priority,
            'applicable_to': self.applicable_to,
            'applicable_categories': self.get_applicable_categories(),
            'applicable_subcategories': self.get_applicable_subcategories(),
            'applicable_products': self.get_applicable_products(),
            'applicable_merchants': self.get_applicable_merchants(),
            'used_by': self.get_used_by(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'created_by': self.created_by
        }

class WithdrawalRequest(db.Model):
    """Modèle pour les demandes de retrait des marchands"""
    __tablename__ = 'withdrawal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(50), unique=True, nullable=False)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchants.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), default='bank_transfer')  # bank_transfer, mobile_money, cash_pickup
    status = db.Column(db.String(50), default='pending')  # pending, approved, processing, completed, rejected, cancelled
    
    notes = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    reference = db.Column(db.String(100), nullable=True)
    
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.request_id,
            'merchant_id': self.merchant_id,
            'merchant_email': self.merchant.email if self.merchant else None,
            'amount': self.amount,
            'method': self.method,
            'status': self.status,
            'notes': self.notes,
            'admin_notes': self.admin_notes,
            'reference': self.reference,
            'requested_at': self.requested_at.strftime('%Y-%m-%d %H:%M:%S') if self.requested_at else None,
            'processed_at': self.processed_at.strftime('%Y-%m-%d %H:%M:%S') if self.processed_at else None
        }

class Cart(db.Model):
    """Modèle pour le panier persistant des utilisateurs"""
    __tablename__ = 'carts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(255), nullable=True)  # Pour les utilisateurs non connectés
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

class CartItem(db.Model):
    """Modèle pour les articles du panier"""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    # ID unique pour différencier les mêmes produits avec options différentes
    unique_product_id = db.Column(db.String(100), nullable=False)
    original_product_id = db.Column(db.Integer, nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    # Options sélectionnées (JSON) - couleur, taille, etc.
    options = db.Column(db.Text, nullable=True)
    
    # Prix modifié selon les options
    modified_price = db.Column(db.Float, nullable=True)
    
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_options(self):
        if self.options:
            try:
                return json.loads(self.options)
            except:
                return {}
        return {}
    
    def set_options(self, options_dict):
        if options_dict:
            self.options = json.dumps(options_dict)
        else:
            self.options = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'cart_id': self.cart_id,
            'product_id': self.unique_product_id,  # Pour compatibilité avec le système existant
            'original_product_id': self.original_product_id,
            'unique_id': self.unique_product_id,
            'quantity': self.quantity,
            'options': self.get_options(),
            'modified_price': self.modified_price,
            'is_food': False,
            'added_at': self.added_at.strftime('%Y-%m-%d %H:%M:%S') if self.added_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

class WishlistItem(db.Model):
    """Modèle pour les articles de liste de souhaits"""
    __tablename__ = 'wishlist_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Contrainte d'unicité pour éviter les doublons
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),)

class EmailVerificationToken(db.Model):
    """Modèle pour les tokens de vérification email"""
    __tablename__ = 'email_verification_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordResetToken(db.Model):
    """Modèle pour les tokens de réinitialisation de mot de passe"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # user, merchant, admin
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Employee(db.Model):
    """Modèle pour les employés/administrateurs"""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Informations personnelles
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    
    # Rôle et permissions
    role = db.Column(db.String(50), nullable=False)  # super_admin, admin, manager, livreur
    permissions = db.Column(db.Text, nullable=True)  # JSON string pour permissions spécifiques
    status = db.Column(db.String(20), default='active')  # active, inactive, suspended
    
    # Dates importantes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Définir le mot de passe avec hachage"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Vérifier le mot de passe"""
        return check_password_hash(self.password_hash, password)
    
    def get_permissions(self):
        """Récupérer les permissions depuis JSON"""
        if self.permissions:
            try:
                return json.loads(self.permissions)
            except:
                return []
        return []
    
    def set_permissions(self, permissions_list):
        """Définir les permissions en JSON"""
        self.permissions = json.dumps(permissions_list)
    
    def has_permission(self, permission):
        """Vérifier si l'employé a une permission spécifique"""
        permissions = self.get_permissions()
        return permission in permissions or self.role in ['super_admin', 'admin']
    
    def to_dict(self):
        """Convertir en dictionnaire pour compatibilité avec l'ancien système"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'role': self.role,
            'permissions': self.get_permissions(),
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }

class SiteSettings(db.Model):
    """Modèle pour les paramètres globaux du site"""
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
