#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Helper Functions pour DOUKA KM
Fonctions utilitaires pour interagir avec la base de données SQLAlchemy
"""

from models import *
from sqlalchemy import func, and_, or_
import uuid
from datetime import datetime, timedelta
import json

# =============================================
# FONCTIONS UTILISATEURS
# =============================================

def get_user_by_email(email):
    """Récupérer un utilisateur par email"""
    return User.query.filter_by(email=email).first()

def get_user_by_id(user_id):
    """Récupérer un utilisateur par ID"""
    return User.query.get(user_id)

def create_user(email, password, first_name, last_name, phone=None, address=None, city=None, region=None):
    """Créer un nouveau compte utilisateur"""
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        address=address,
        city=city,
        region=region
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    return user

def get_user_orders(user_id):
    """Récupérer toutes les commandes d'un utilisateur"""
    return Order.query.filter_by(customer_id=user_id).order_by(Order.created_at.desc()).all()

def get_user_wishlist(user_id):
    """Récupérer la liste de souhaits d'un utilisateur"""
    return WishlistItem.query.filter_by(user_id=user_id).join(Product).filter(Product.status == 'active').all()

def update_user_email_verification(email, verified=True):
    """Mettre à jour le statut de vérification email d'un utilisateur"""
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ Utilisateur non trouvé pour l'email: {email}")
            return False
        
        user.email_verified = verified
        user.email_verified_at = datetime.utcnow() if verified else None
        
        db.session.commit()
        print(f"✅ Statut de vérification email mis à jour pour {email}: {verified}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour de la vérification email pour {email}: {str(e)}")
        db.session.rollback()
        return False

# =============================================
# FONCTIONS MARCHANDS
# =============================================

def get_merchant_by_email(email):
    """Récupérer un marchand par email"""
    return Merchant.query.filter_by(email=email).first()

def get_merchant_by_id(merchant_id):
    """Récupérer un marchand par ID"""
    return Merchant.query.get(merchant_id)

def get_merchant_by_email(email):
    """Récupérer un marchand par email"""
    return Merchant.query.filter_by(email=email).first()

def create_merchant(email, password, first_name, last_name, store_name, **kwargs):
    """Créer un nouveau compte marchand"""
    merchant = Merchant(
        email=email,
        first_name=first_name,
        last_name=last_name,
        store_name=store_name,
        **kwargs
    )
    merchant.set_password(password)
    
    db.session.add(merchant)
    db.session.commit()
    return merchant

def get_merchant_products(merchant_id):
    """Récupérer tous les produits d'un marchand"""
    return Product.query.filter_by(merchant_id=merchant_id).order_by(Product.created_at.desc()).all()

def get_merchant_orders(merchant_id):
    """Récupérer toutes les commandes d'un marchand"""
    return Order.query.filter_by(merchant_id=merchant_id).order_by(Order.created_at.desc()).all()

def calculate_merchant_balance(merchant_id):
    """Calculer le solde d'un marchand basé sur les commandes livrées"""
    # Récupérer toutes les commandes livrées du marchand
    delivered_orders = Order.query.filter_by(
        merchant_id=merchant_id,
        status='delivered',
        payment_status='completed'
    ).all()
    
    # Calculer les revenus bruts
    total_earnings = sum(order.total - order.shipping_fee for order in delivered_orders)
    
    # Calculer les commissions (5% par défaut)
    commission_rate = get_site_setting('commission_rate', 5.0)
    commission_fees = total_earnings * (float(commission_rate) / 100)
    
    # Calculer les retraits
    completed_withdrawals = WithdrawalRequest.query.filter_by(
        merchant_id=merchant_id,
        status='completed'
    ).all()
    
    total_withdrawals = sum(w.amount for w in completed_withdrawals)
    
    # Calculer les retraits en attente
    pending_withdrawals = WithdrawalRequest.query.filter_by(
        merchant_id=merchant_id,
        status__in=['pending', 'approved', 'processing']
    ).all()
    
    pending_amount = sum(w.amount for w in pending_withdrawals)
    
    # Solde disponible
    available_balance = total_earnings - commission_fees - total_withdrawals - pending_amount
    
    return {
        'total_earnings': total_earnings,
        'commission_fees': commission_fees,
        'commission_rate': commission_rate,
        'completed_withdrawals': total_withdrawals,
        'pending_withdrawals': pending_amount,
        'available_balance': max(0, available_balance),
        'delivered_orders_count': len(delivered_orders)
    }

# =============================================
# FONCTIONS ADMINISTRATEURS
# =============================================

def get_admin_by_email(email):
    """Récupérer un administrateur par email"""
    return Admin.query.filter_by(email=email).first()

def get_admin_by_id(admin_id):
    """Récupérer un administrateur par ID"""
    return Admin.query.get(admin_id)

def create_admin(email, password, first_name, last_name, role='admin', **kwargs):
    """Créer un nouveau compte administrateur"""
    admin = Admin(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        **kwargs
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    return admin

# =============================================
# FONCTIONS PRODUITS
# =============================================

def get_product_by_id(product_id):
    """Récupérer un produit par ID"""
    return Product.query.get(product_id)

def get_all_products(status='active'):
    """Récupérer tous les produits actifs"""
    query = Product.query
    if status:
        query = query.filter_by(status=status)
    return query.order_by(Product.created_at.desc()).all()

def get_products_by_category(category_id, limit=None):
    """Récupérer les produits d'une catégorie"""
    query = Product.query.filter_by(category_id=category_id, status='active')
    if limit:
        query = query.limit(limit)
    return query.all()

def get_featured_products(limit=12):
    """Récupérer les produits mis en avant"""
    # Mélange de produits récents et bien notés
    recent_products = Product.query.filter_by(status='active').order_by(Product.created_at.desc()).limit(6).all()
    top_rated = Product.query.filter_by(status='active').order_by(Product.rating.desc()).limit(6).all()
    
    # Combiner et dédupliquer
    featured = list({p.id: p for p in recent_products + top_rated}.values())
    return featured[:limit]

def search_products(query, category_id=None, min_price=None, max_price=None, limit=None):
    """Rechercher des produits"""
    search = Product.query.filter_by(status='active')
    
    if query:
        search = search.filter(
            or_(
                Product.name.contains(query),
                Product.description.contains(query)
            )
        )
    
    if category_id:
        search = search.filter_by(category_id=category_id)
    
    if min_price:
        search = search.filter(Product.price >= min_price)
    
    if max_price:
        search = search.filter(Product.price <= max_price)
    
    if limit:
        search = search.limit(limit)
    
    return search.all()

def create_product(name, price, description=None, stock=0, merchant_id=None, **kwargs):
    """Créer un nouveau produit"""
    product = Product(
        name=name,
        price=price,
        description=description,
        stock=stock,
        merchant_id=merchant_id,
        **kwargs
    )
    
    db.session.add(product)
    db.session.commit()
    return product

# =============================================
# FONCTIONS COMMANDES
# =============================================

def generate_order_number():
    """Générer un numéro de commande unique avec gestion des collisions"""
    from sqlalchemy import func
    import random
    
    prefix = datetime.now().strftime("ORD-%Y")
    today = datetime.now().date()
    
    max_attempts = 100
    for attempt in range(max_attempts):
        # Compter les commandes existantes avec ce préfixe aujourd'hui
        existing_count = Order.query.filter(
            func.date(Order.created_at) == today
        ).count()
        
        # Générer un numéro basé sur le count + un petit offset aléatoire pour éviter les collisions
        count = existing_count + 1 + attempt
        order_number = f"{prefix}-{count:04d}"
        
        # Vérifier que ce numéro n'existe pas déjà
        existing_order = Order.query.filter_by(order_number=order_number).first()
        if not existing_order:
            return order_number
    
    # Si après 100 tentatives on n'a pas trouvé de numéro unique, utiliser un timestamp
    import time
    timestamp = int(time.time() % 10000)  # Derniers 4 chiffres du timestamp
    return f"{prefix}-{timestamp:04d}"

def create_order(customer_id, merchant_id, items_data, shipping_address=None, **kwargs):
    """Créer une nouvelle commande"""
    order_number = generate_order_number()
    
    # Calculer le total
    subtotal = sum(item['price'] * item['quantity'] for item in items_data)
    shipping_fee = kwargs.get('shipping_fee', 0)
    discount = kwargs.get('discount', 0)
    total = subtotal + shipping_fee - discount
    
    # Récupérer les informations client
    customer = get_user_by_id(customer_id)
    
    # Exclure les paramètres déjà utilisés et filtrer les paramètres valides pour éviter les conflits
    valid_order_fields = [
        'status', 'payment_status', 'payment_method', 'shipping_method',
        'promo_code_used', 'processing_date', 'shipping_date', 
        'delivery_date', 'cancelled_at'
    ]
    order_kwargs = {k: v for k, v in kwargs.items() 
                   if k not in ['shipping_fee', 'discount', 'total'] 
                   and k in valid_order_fields}
    
    order = Order(
        order_number=order_number,
        customer_id=customer_id,
        merchant_id=merchant_id,
        customer_name=f"{customer.first_name} {customer.last_name}" if customer else None,
        customer_email=customer.email if customer else None,
        customer_phone=customer.phone if customer else None,
        total=total,
        shipping_fee=shipping_fee,
        discount=discount,
        **order_kwargs
    )
    
    if shipping_address:
        order.set_shipping_address(shipping_address)
    
    db.session.add(order)
    db.session.flush()  # Pour obtenir l'ID de la commande
    
    # Ajouter les articles de la commande
    for item_data in items_data:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data['product_id'],
            name=item_data['name'],
            price=item_data['price'],
            quantity=item_data['quantity'],
            subtotal=item_data['price'] * item_data['quantity'],
            image=item_data.get('image'),
            variant_details=item_data.get('variant_details')
        )
        
        if 'options' in item_data:
            order_item.set_options(item_data['options'])
        
        db.session.add(order_item)
    
    db.session.commit()
    return order

def update_order_status(order_id, new_status, admin_notes=None, changed_by='Marchand'):
    """Mettre à jour le statut d'une commande avec historique"""
    order = Order.query.get(order_id)
    if not order:
        return None
    
    old_status = order.status
    
    # Si le statut n'a pas changé, ne rien faire
    if old_status == new_status:
        return {
            'order': order,
            'old_status': old_status,
            'new_status': new_status
        }
    
    # Mettre à jour le statut
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    # Mettre à jour les dates spécifiques selon le statut
    if new_status == 'processing':
        order.processing_date = datetime.utcnow()
    elif new_status == 'shipped':
        order.shipping_date = datetime.utcnow()
    elif new_status == 'delivered':
        order.delivery_date = datetime.utcnow()
        order.payment_status = 'completed'
    elif new_status == 'cancelled':
        order.cancelled_at = datetime.utcnow()
        
        # **NOUVELLE FONCTIONNALITÉ: Remettre le stock lors de l'annulation par admin/marchand**
        try:
            import json
            order_items = json.loads(order.items) if isinstance(order.items, str) else (order.items or [])
            
            # Importer la fonction de remise en stock
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from app_final_with_db import release_stock
            
            # Remettre le stock
            release_stock(order_items)
            print(f"✅ Stock remis suite à l'annulation de la commande {order_id} par {changed_by}")
            
        except Exception as stock_error:
            print(f"⚠️ Erreur lors de la remise en stock pour commande {order_id}: {stock_error}")
            # Continuer même si la remise en stock échoue
    
    # Ajouter le changement à l'historique des statuts
    order.add_status_change(new_status, admin_notes, changed_by)
    
    db.session.commit()
    
    return {
        'order': order,
        'old_status': old_status,
        'new_status': new_status
    }

def get_order_by_id(order_id):
    """Récupérer une commande par son ID"""
    return Order.query.get(order_id)

def get_order_by_number(order_number):
    """Récupérer une commande par son numéro"""
    return Order.query.filter_by(order_number=order_number).first()

def get_all_orders(limit=None, status=None):
    """Récupérer toutes les commandes avec filtres optionnels"""
    query = Order.query.order_by(Order.created_at.desc())
    
    if status:
        query = query.filter_by(status=status)
    
    if limit:
        query = query.limit(limit)
    
    return query.all()

def get_orders_by_customer_email(customer_email):
    """Récupérer les commandes d'un client par email"""
    return Order.query.filter_by(customer_email=customer_email).order_by(Order.created_at.desc()).all()

def get_pending_merchant_orders(merchant_id):
    """Récupérer les commandes en attente d'un marchand"""
    return Order.query.filter_by(
        merchant_id=merchant_id, 
        status='pending'
    ).order_by(Order.created_at.desc()).all()

def create_complete_order(customer_id, merchant_id, cart_items, shipping_address, **kwargs):
    """Créer une commande complète avec tous les articles"""
    try:
        # Préparer les données des articles
        items_data = []
        for item in cart_items:
            items_data.append({
                'product_id': item.get('product_id', item.get('id')),
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'image': item.get('image', ''),
                'variant_details': item.get('variant_details', ''),
                'options': item.get('options', {})
            })
        
        # Enrichir l'adresse de livraison avec la méthode de livraison
        if shipping_address and 'shipping_method' in kwargs:
            shipping_address_with_method = dict(shipping_address)
            shipping_address_with_method['shipping_method'] = kwargs.get('shipping_method')
        else:
            shipping_address_with_method = shipping_address
        
        # Créer la commande
        order = create_order(
            customer_id=customer_id,
            merchant_id=merchant_id,
            items_data=items_data,
            shipping_address=shipping_address_with_method,
            **kwargs
        )
        
        return order
        
    except Exception as e:
        print(f"Erreur lors de la création de la commande: {str(e)}")
        db.session.rollback()
        return None

# =============================================
# FONCTIONS AVIS/REVIEWS
# =============================================

def add_review(product_id, user_id, rating, title=None, comment=None):
    """Ajouter un avis pour un produit"""
    review = Review(
        product_id=product_id,
        user_id=user_id,
        rating=rating,
        title=title,
        comment=comment
    )
    
    db.session.add(review)
    
    # Mettre à jour les statistiques du produit
    product = get_product_by_id(product_id)
    if product:
        # Recalculer la note moyenne
        avg_rating = db.session.query(func.avg(Review.rating)).filter_by(product_id=product_id).scalar()
        reviews_count = Review.query.filter_by(product_id=product_id).count()
        
        product.rating = round(avg_rating, 1) if avg_rating else 0
        product.reviews_count = reviews_count
    
    db.session.commit()
    return review

def get_product_reviews(product_id, limit=None):
    """Récupérer les avis d'un produit"""
    query = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc())
    if limit:
        query = query.limit(limit)
    return query.all()

# =============================================
# FONCTIONS GESTION COMMANDES ADMINISTRATIVES 
# =============================================

def get_admin_orders():
    """Récupérer toutes les commandes admin (produits statiques/admin)"""
    return Order.query.filter(Order.merchant_id.is_(None)).order_by(Order.created_at.desc()).all()

def get_admin_orders_count():
    """Récupérer le nombre total de commandes admin"""
    return Order.query.filter(Order.merchant_id.is_(None)).count()

def get_admin_order_by_id_and_email(order_id, customer_email):
    """Récupérer une commande admin spécifique par ID et email client"""
    return Order.query.filter(
        Order.id == order_id,
        Order.customer_email == customer_email,
        Order.merchant_id.is_(None)
    ).first()

def get_admin_orders_by_status(status):
    """Récupérer les commandes admin par statut"""
    return Order.query.filter(
        Order.status == status,
        Order.merchant_id.is_(None)
    ).order_by(Order.created_at.desc()).all()

def update_admin_order_status(order_id, status):
    """Mettre à jour le statut d'une commande admin avec historique"""
    order = Order.query.filter(
        Order.id == order_id,
        Order.merchant_id.is_(None)
    ).first()
    
    if order:
        old_status = order.status
        order.status = status
        order.updated_at = datetime.utcnow()
        
        # Mettre à jour les dates selon le statut
        now = datetime.utcnow()
        if status == 'processing' and not order.processing_date:
            order.processing_date = now
        elif status == 'shipped' and not order.shipping_date:
            order.shipping_date = now
        elif status == 'delivered' and not order.delivery_date:
            order.delivery_date = now
            order.payment_status = 'completed'
        elif status == 'cancelled' and not order.cancelled_at:
            order.cancelled_at = now
            
        # Ajouter le changement à l'historique des statuts
        order.add_status_change(status, None, 'Livreur')
        
        db.session.commit()
        print(f"✅ Statut commande admin {order_id} mis à jour: {old_status} → {status}")
        return True, old_status
    return False, None

def get_admin_order_by_id(order_id):
    """Récupérer une commande admin par son ID"""
    return Order.query.filter(
        Order.id == order_id,
        Order.merchant_id.is_(None)
    ).first()

def get_admin_orders_for_delivery():
    """Récupérer les commandes admin disponibles pour livraison"""
    return Order.query.filter(
        Order.merchant_id.is_(None),
        Order.status.in_(['processing', 'shipped'])
    ).order_by(Order.created_at.desc()).all()

def get_admin_orders_by_status_list(status_list):
    """Récupérer les commandes admin par liste de statuts"""
    return Order.query.filter(
        Order.merchant_id.is_(None),
        Order.status.in_(status_list)
    ).order_by(Order.created_at.desc()).all()

def get_recent_admin_orders(limit=5):
    """Récupérer les commandes admin récentes pour le dashboard"""
    return Order.query.filter(
        Order.merchant_id.is_(None)
    ).order_by(Order.created_at.desc()).limit(limit).all()

def calculate_admin_orders_total():
    """Calculer le total des commandes admin"""
    result = db.session.query(func.sum(Order.total)).filter(
        Order.merchant_id.is_(None),
        Order.status != 'cancelled'
    ).scalar()
    return result or 0

# =============================================
# FONCTIONS CODES PROMO
# =============================================

def get_promo_code(code):
    """Récupérer un code promo par son code"""
    return PromoCode.query.filter_by(code=code, active=True).first()

def validate_promo_code(code, user_email, cart_items):
    """Valider un code promo"""
    promo = get_promo_code(code)
    if not promo:
        return {'valid': False, 'message': 'Code promo invalide'}
    
    # Vérifier les dates
    today = datetime.now().date()
    if promo.start_date and today < promo.start_date:
        return {'valid': False, 'message': 'Ce code promo n\'est pas encore actif'}
    
    if promo.end_date and today > promo.end_date:
        return {'valid': False, 'message': 'Ce code promo a expiré'}
    
    # Vérifier l'usage global
    if promo.usage_limit and promo.used_count >= promo.usage_limit:
        return {'valid': False, 'message': 'Ce code promo a atteint sa limite d\'utilisation'}
    
    # Vérifier l'usage par utilisateur
    used_by = promo.get_used_by()
    user_usage = used_by.get(user_email, 0)
    if user_usage >= promo.user_limit:
        return {'valid': False, 'message': 'Vous avez déjà utilisé ce code promo'}
    
    # Calculer le montant du panier applicable
    cart_total = sum(item.get('total_price', item['price'] * item['quantity']) for item in cart_items)
    
    # Vérifier le montant minimum
    if cart_total < promo.min_amount:
        return {
            'valid': False, 
            'message': f'Montant minimum de {promo.min_amount:,.0f} KMF requis'
        }
    
    # Calculer la réduction
    if promo.type == 'percentage':
        discount = cart_total * (promo.value / 100)
        if promo.max_discount:
            discount = min(discount, promo.max_discount)
    else:  # fixed
        discount = promo.value
    
    discount = min(discount, cart_total)  # La réduction ne peut pas dépasser le total
    
    return {
        'valid': True,
        'discount': discount,
        'message': f'Code promo appliqué! Réduction de {discount:,.0f} KMF'
    }

def use_promo_code(code, user_email):
    """Marquer un code promo comme utilisé"""
    promo = get_promo_code(code)
    if not promo:
        return False
    
    # Incrémenter le compteur global
    promo.used_count += 1
    
    # Incrémenter le compteur par utilisateur
    used_by = promo.get_used_by()
    used_by[user_email] = used_by.get(user_email, 0) + 1
    promo.set_used_by(used_by)
    
    db.session.commit()
    return True

# =============================================
# FONCTIONS CATÉGORIES
# =============================================

def get_all_categories(active_only=True):
    """Récupérer toutes les catégories"""
    query = Category.query
    if active_only:
        query = query.filter_by(active=True)
    return query.order_by(Category.name).all()

def get_category_by_id(category_id):
    """Récupérer une catégorie par ID"""
    return Category.query.get(category_id)

def get_subcategories_by_category(category_id):
    """Récupérer les sous-catégories d'une catégorie"""
    return Subcategory.query.filter_by(category_id=category_id, active=True).order_by(Subcategory.name).all()

def get_all_subcategories(active_only=True):
    """Récupérer toutes les sous-catégories"""
    query = Subcategory.query
    if active_only:
        query = query.filter_by(active=True)
    return query.order_by(Subcategory.name).all()

# =============================================
# FONCTIONS PARAMÈTRES DU SITE
# =============================================

def get_site_setting(key, default=None):
    """Récupérer un paramètre du site"""
    setting = SiteSettings.query.filter_by(key=key).first()
    if setting:
        try:
            # Essayer de convertir en nombre si possible
            if setting.value.isdigit():
                return int(setting.value)
            elif '.' in setting.value and setting.value.replace('.', '').isdigit():
                return float(setting.value)
            elif setting.value.lower() in ('true', 'false'):
                return setting.value.lower() == 'true'
            else:
                return setting.value
        except:
            return setting.value
    return default

def set_site_setting(key, value, description=None):
    """Définir un paramètre du site"""
    setting = SiteSettings.query.filter_by(key=key).first()
    
    if setting:
        setting.value = str(value)
        setting.updated_at = datetime.utcnow()
        if description:
            setting.description = description
    else:
        setting = SiteSettings(
            key=key,
            value=str(value),
            description=description
        )
        db.session.add(setting)
    
    db.session.commit()
    return setting

def get_all_site_settings():
    """Récupérer tous les paramètres du site"""
    settings = SiteSettings.query.all()
    return {s.key: s.value for s in settings}

def get_all_users():
    """Récupérer tous les utilisateurs"""
    return User.query.all()

def get_all_merchants():
    """Récupérer tous les marchands"""
    return Merchant.query.all()

def get_all_admins():
    """Récupérer tous les administrateurs"""
    return Admin.query.all()

def get_all_promo_codes():
    """Récupérer tous les codes promo"""
    return PromoCode.query.all()

def get_user_wishlist(user_id):
    """Récupérer la liste d'envies d'un utilisateur"""
    wishlist_items = WishlistItem.query.filter_by(user_id=user_id).all()
    items_data = []
    for item in wishlist_items:
        product = get_product_by_id(item.product_id)
        if product:
            items_data.append({
                'id': item.id,
                'product': product.to_dict(),
                'added_at': item.created_at
            })
    return items_data

# =============================================
# FONCTIONS RETRAITS
# =============================================

def create_withdrawal_request(merchant_id, amount, method='bank_transfer', notes=''):
    """Créer une demande de retrait"""
    request_id = f"WR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    withdrawal = WithdrawalRequest(
        request_id=request_id,
        merchant_id=merchant_id,
        amount=amount,
        method=method,
        notes=notes
    )
    
    db.session.add(withdrawal)
    db.session.commit()
    return withdrawal

def get_merchant_withdrawal_requests(merchant_id):
    """Récupérer les demandes de retrait d'un marchand"""
    return WithdrawalRequest.query.filter_by(merchant_id=merchant_id).order_by(WithdrawalRequest.requested_at.desc()).all()

def update_withdrawal_status(request_id, new_status, admin_notes=None, reference=None):
    """Mettre à jour le statut d'une demande de retrait"""
    withdrawal = WithdrawalRequest.query.filter_by(request_id=request_id).first()
    if not withdrawal:
        return None
    
    old_status = withdrawal.status
    withdrawal.status = new_status
    withdrawal.processed_at = datetime.utcnow()
    
    if admin_notes:
        withdrawal.admin_notes = admin_notes
    
    if reference:
        withdrawal.reference = reference
    
    db.session.commit()
    
    return {
        'withdrawal': withdrawal,
        'old_status': old_status,
        'new_status': new_status
    }

# =============================================
# FONCTIONS STATISTIQUES
# =============================================

def get_dashboard_stats():
    """Récupérer les statistiques pour le tableau de bord"""
    return {
        'total_users': User.query.count(),
        'total_merchants': Merchant.query.count(),
        'total_products': Product.query.filter_by(status='active').count(),
        'total_orders': Order.query.count(),
        'total_categories': Category.query.filter_by(active=True).count(),
        'total_subcategories': Subcategory.query.filter_by(active=True).count(),
        'verified_merchants': Merchant.query.filter_by(store_verified=True).count(),
        'pending_merchants': Merchant.query.filter_by(store_verified=False).count(),
        'recent_orders': Order.query.order_by(Order.created_at.desc()).limit(5).all(),
        'top_products': Product.query.filter_by(status='active').order_by(Product.rating.desc()).limit(5).all()
    }

# =============================================
# FONCTIONS HELPER POUR LES COMMANDES UTILISATEUR
# =============================================

def get_user_orders(user_email):
    """Récupère toutes les commandes d'un utilisateur depuis la base de données ET les dictionnaires en mémoire"""
    try:
        orders_list = []
        
        # 1. D'abord récupérer les commandes depuis la base de données
        user = User.query.filter_by(email=user_email).first()
        if user:
            # Récupérer toutes les commandes de cet utilisateur depuis la DB
            db_orders = Order.query.filter_by(customer_id=user.id).order_by(Order.created_at.desc()).all()
            
            # Convertir en dictionnaires pour compatibilité avec l'ancien système
            for order in db_orders:
                order_dict = order.to_dict()
                
                # Ajouter les items de la commande
                order_items = OrderItem.query.filter_by(order_id=order.id).all()
                order_dict['items'] = []
                
                for item in order_items:
                    item_dict = item.to_dict()
                    
                    # Récupérer les détails du produit
                    product = Product.query.get(item.product_id)
                    if product:
                        item_dict['name'] = product.name
                        item_dict['image'] = product.image
                        
                    # Utiliser variant_details directement s'il existe
                    item_dict['variant_details'] = item.variant_details or ''
                        
                    order_dict['items'].append(item_dict)
                
                # Ajouter des champs de compatibilité et calculés
                order_dict['products'] = order_dict['items']  # Alias pour compatibilité
                
                # Calculer le subtotal (total - frais de livraison + réduction)
                # Le subtotal représente le total des articles avant frais et réductions
                shipping_fee = order_dict.get('shipping_fee', 0) or 0
                discount = order_dict.get('discount', 0) or 0
                total = order_dict.get('total', 0) or 0
                order_dict['subtotal'] = total - shipping_fee + discount
                
                orders_list.append(order_dict)
        
        # 2. Ensuite récupérer les commandes depuis le dictionnaire en mémoire (anciennes commandes)
        try:
            import app_final_with_db as app_module
            users_db = getattr(app_module, 'users_db', {})
            if user_email in users_db and 'orders' in users_db[user_email]:
                memory_orders = users_db[user_email]['orders']
                orders_list.extend(memory_orders)
        except ImportError:
            pass  # Ignorer si l'import échoue
        
        # 3. Trier toutes les commandes par date (plus récentes en premier)
        orders_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return orders_list
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des commandes pour {user_email}: {e}")
        return []

def get_user_order_by_id(user_email, order_id):
    """Récupère une commande spécifique d'un utilisateur"""
    try:
        # Récupérer l'utilisateur
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return None
            
        # Récupérer la commande spécifique
        order = Order.query.filter_by(id=order_id, customer_id=user.id).first()
        if not order:
            return None
            
        # Convertir en dictionnaire
        order_dict = order.to_dict()
        
        # Ajouter les items
        order_items = OrderItem.query.filter_by(order_id=order.id).all()
        order_dict['items'] = []
        
        for item in order_items:
            item_dict = item.to_dict()
            
            # Récupérer les détails du produit
            product = Product.query.get(item.product_id)
            if product:
                item_dict['name'] = product.name
                item_dict['image'] = product.image
                
            # Utiliser variant_details directement s'il existe
            item_dict['variant_details'] = item.variant_details or ''
                
            order_dict['items'].append(item_dict)
        
        # Ajouter des champs de compatibilité et calculés
        order_dict['products'] = order_dict['items']  # Alias pour compatibilité
        
        # Calculer le subtotal (total - frais de livraison + réduction)
        shipping_fee = order_dict.get('shipping_fee', 0) or 0
        discount = order_dict.get('discount', 0) or 0
        total = order_dict.get('total', 0) or 0
        order_dict['subtotal'] = total - shipping_fee + discount
        
        return order_dict
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération de la commande {order_id} pour {user_email}: {e}")
        return None

def get_user_orders_count(user_email):
    """Compte le nombre total de commandes d'un utilisateur"""
    try:
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return 0
        return Order.query.filter_by(customer_id=user.id).count()
    except Exception as e:
        print(f"⚠️ Erreur lors du comptage des commandes pour {user_email}: {e}")
        return 0

def get_user_order_stats(user_email):
    """Récupère les statistiques des commandes d'un utilisateur"""
    try:
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return {
                'total_orders': 0,
                'total_spent': 0,
                'pending_orders': 0,
                'completed_orders': 0,
                'cancelled_orders': 0
            }
        
        orders = Order.query.filter_by(customer_id=user.id).all()
        
        total_orders = len(orders)
        # Exclure les commandes annulées du total dépensé
        total_spent = sum(order.total for order in orders if order.status != 'cancelled')
        pending_orders = sum(1 for order in orders if order.status in ['pending', 'processing'])
        completed_orders = sum(1 for order in orders if order.status == 'delivered')
        cancelled_orders = sum(1 for order in orders if order.status == 'cancelled')
        
        return {
            'total_orders': total_orders,
            'total_spent': total_spent,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders
        }
        
    except Exception as e:
        print(f"⚠️ Erreur lors du calcul des statistiques pour {user_email}: {e}")
        return {
            'total_orders': 0,
            'total_spent': 0,
            'pending_orders': 0,
            'completed_orders': 0,
            'cancelled_orders': 0
        }

def cancel_user_order(user_email, order_id):
    """Annule une commande spécifique d'un utilisateur"""
    try:
        # Récupérer l'utilisateur
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return False, "Utilisateur non trouvé"
            
        # Récupérer la commande
        order = Order.query.filter_by(id=order_id, customer_id=user.id).first()
        if not order:
            return False, "Commande non trouvée"
            
        # NOUVELLE RÈGLE MÉTIER STRICTE: Seulement Processing + Paiement à la livraison/Cash peut être annulé
        current_status = order.status
        payment_method = (order.payment_method or '').lower()
        
        print(f"🔍 DEBUG cancel_user_order: Status = '{current_status}', Payment = '{payment_method}'")
        
        # RÈGLE UNIQUE: Seulement Processing + (Paiement à la livraison OU Cash) peut être annulé
        if current_status == 'processing' and ('paiement à la livraison' in payment_method or 'cash' in payment_method):
            print("✅ Annulation autorisée: Processing + (Paiement à la livraison OU Cash)")
            # La commande peut être annulée - continuer
        else:
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
                # Processing mais pas paiement à la livraison/cash
                return False, f'Cette commande ne peut pas être annulée car vous avez choisi le paiement par {order.payment_method}. Veuillez contacter le service client.'
            else:
                return False, f'Cette commande ne peut plus être annulée (statut: {current_status})'
        
        # Annuler la commande
        order.status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        # **NOUVELLE FONCTIONNALITÉ: Remettre le stock lors de l'annulation**
        try:
            import json
            order_items = json.loads(order.items) if isinstance(order.items, str) else (order.items or [])
            
            # Importer la fonction de remise en stock
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from app_final_with_db import release_stock
            
            # Remettre le stock
            release_stock(order_items)
            print(f"✅ Stock remis suite à l'annulation de la commande {order_id}")
            
        except Exception as stock_error:
            print(f"⚠️ Erreur lors de la remise en stock pour commande {order_id}: {stock_error}")
            # Continuer même si la remise en stock échoue
        
        db.session.commit()
        
        print(f"✅ Commande {order_id} annulée avec succès pour {user_email}")
        return True, "Commande annulée avec succès"
        
    except Exception as e:
        print(f"⚠️ Erreur lors de l'annulation de la commande {order_id} pour {user_email}: {e}")
        db.session.rollback()
        return False, f"Erreur lors de l'annulation: {str(e)}"

def update_user_order_status(order_id, new_status, notes=None):
    """Met à jour le statut d'une commande utilisateur dans la base de données avec historique"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return False, "Commande non trouvée"
            
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # Mettre à jour les dates spécifiques selon le statut
        if new_status == 'processing' and not order.processing_date:
            order.processing_date = datetime.utcnow()
        elif new_status == 'shipped' and not order.shipping_date:
            order.shipping_date = datetime.utcnow()
        elif new_status == 'delivered' and not order.delivery_date:
            order.delivery_date = datetime.utcnow()
            order.payment_status = 'completed'
        elif new_status == 'cancelled' and not order.cancelled_at:
            order.cancelled_at = datetime.utcnow()
        
        # Ajouter le changement à l'historique des statuts
        order.add_status_change(new_status, notes, 'Livreur')
            
        db.session.commit()
        
        print(f"✅ Statut de la commande {order_id} mis à jour: {old_status} → {new_status}")
        return True, f"Statut mis à jour avec succès"
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la mise à jour du statut de la commande {order_id}: {e}")
        db.session.rollback()
        return False, f"Erreur lors de la mise à jour: {str(e)}"
def get_all_merchant_orders():
    """Récupérer toutes les commandes de tous les marchands"""
    try:
        return Order.query.filter(Order.merchant_id.is_not(None)).order_by(Order.created_at.desc()).all()
    except Exception as e:
        if "does not exist" in str(e) or "UndefinedColumn" in str(e):
            print(f"⚠️ Erreur de schéma détectée dans get_all_merchant_orders: {e}")
            print("🔄 Tentative de récupération des commandes avec schéma partiel...")
            try:
                # Utiliser une requête SQL brute pour éviter les colonnes manquantes
                from sqlalchemy import text
                result = db.session.execute(text("""
                    SELECT id, order_number, customer_id, merchant_id, total, 
                           status, payment_status, customer_name, customer_email, 
                           customer_phone, created_at
                    FROM orders 
                    WHERE merchant_id IS NOT NULL 
                    ORDER BY created_at DESC
                """))
                
                # Convertir en objets Order partiels
                orders = []
                for row in result:
                    order = Order()
                    order.id = row[0]
                    order.order_number = row[1]
                    order.customer_id = row[2]
                    order.merchant_id = row[3]
                    order.total = row[4]
                    order.status = row[5]
                    order.payment_status = row[6]
                    order.customer_name = row[7]
                    order.customer_email = row[8]
                    order.customer_phone = row[9]
                    order.created_at = row[10]
                    orders.append(order)
                
                print(f"✅ Récupéré {len(orders)} commandes avec schéma partiel")
                return orders
                
            except Exception as fallback_error:
                print(f"❌ Erreur lors du fallback: {fallback_error}")
                return []
        else:
            print(f"❌ Erreur inattendue dans get_all_merchant_orders: {e}")
            return []

def get_merchant_orders(merchant_id):
    """Récupérer toutes les commandes d'un marchand spécifique"""
    return Order.query.filter_by(merchant_id=merchant_id).order_by(Order.created_at.desc()).all()

def get_merchant_by_id(merchant_id):
    """Récupérer un marchand par son ID"""
    return Merchant.query.get(merchant_id)
