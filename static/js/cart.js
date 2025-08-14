/**
 * Fonctions utilitaires pour la gestion du panier
 */

// Fonction globale pour ajouter un produit au panier
function addToCart(productId, quantity = 1, options = {}) {
    // Validation des entrées
    productId = parseInt(productId) || 0;
    quantity = parseInt(quantity) || 1;
    
    if (productId <= 0) {
        console.error("ID de produit invalide:", productId);
        return;
    }
    
    console.log(`Ajout au panier: ID=${productId}, Qté=${quantity}, Options=`, options);
    
    // Préparation des données pour l'envoi
    let formData = new URLSearchParams();
    formData.append('quantity', quantity);
    
    if (Object.keys(options).length > 0) {
        formData.append('options', JSON.stringify(options));
    }
    
    // Envoi de la requête AJAX
    return fetch(`/add-to-cart/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) throw new Error('Erreur réseau');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Mise à jour du compteur du panier directement avec la valeur retournée
            if (typeof data.cart_count !== 'undefined') {
                updateCartCount(data.cart_count);
            } else {
                // Fallback si pas de cart_count dans la réponse
                updateCartCount();
            }
            
            // Affichage d'une notification
            if (window.showCartNotification) {
                let message = `${data.product_name || 'Produit'} ajouté au panier`;
                
                // Inclure les détails des options dans la notification si disponibles
                if (options && Object.keys(options).length > 0) {
                    const optionString = Object.entries(options)
                        .map(([key, value]) => `${key.charAt(0).toUpperCase() + key.slice(1)}: ${value}`)
                        .join(', ');
                        
                    message += ` (${optionString})`;
                }
                
                showCartNotification(message);
            }
        }
        return data;
    });
}

// Fonction pour mettre à jour l'affichage du compteur du panier
function updateCartCount(count) {
    if (typeof count !== 'undefined') {
        // Mise à jour directe avec la valeur fournie
        document.querySelectorAll('.cart-count').forEach(element => {
            // Masquer complètement le badge si le panier est vide
            if (count === 0 || count === null || count === undefined) {
                element.style.display = 'none';
            } else {
                element.textContent = count;
                element.style.display = '';
            }
        });
        console.log(`🛒 Compteur mis à jour directement: ${count === 0 ? 'masqué (panier vide)' : count}`);
    } else {
        // Si aucune valeur n'est fournie, recharger via l'API
        fetch('/get-cart-count', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            const apiCount = data.cart_count !== undefined ? data.cart_count : data.count;
            if (typeof apiCount !== 'undefined') {
                document.querySelectorAll('.cart-count').forEach(element => {
                    // Masquer complètement le badge si le panier est vide
                    if (apiCount === 0 || apiCount === null || apiCount === undefined) {
                        element.style.display = 'none';
                    } else {
                        element.textContent = apiCount;
                        element.style.display = '';
                    }
                });
                console.log(`🛒 Compteur rechargé via API: ${apiCount === 0 ? 'masqué (panier vide)' : apiCount}`);
            }
        })
        .catch(error => {
            console.warn('Erreur lors du rechargement du compteur:', error);
        });
    }
}

// Fonction pour afficher une notification
function showCartNotification(message, type = 'success') {
    // Utiliser le système de notification toast de Bootstrap si disponible
    const toast = document.getElementById('cartToast');
    if (toast) {
        const toastBody = toast.querySelector('.toast-body');
        if (toastBody) {
            toastBody.textContent = message;
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            return;
        }
    }
    
    // Si le toast Bootstrap n'est pas disponible, créer une notification personnalisée
    const notification = document.createElement('div');
    notification.className = `toast show ${type === 'error' ? 'bg-danger' : 'bg-success'} text-white`;
    notification.style.position = 'fixed';
    notification.style.bottom = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '250px';
    notification.style.padding = '15px';
    notification.style.borderRadius = '4px';
    notification.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="me-3">
                <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : 'fa-check-circle'} fa-lg"></i>
            </div>
            <div>${message}</div>
        </div>
    `;
    
    // Ajouter la notification au corps de la page
    document.body.appendChild(notification);
    
    // Supprimer la notification après 3 secondes
    setTimeout(() => {
        notification.style.transition = 'opacity 0.5s ease';
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}

// Rendre les fonctions disponibles globalement
window.addToCart = addToCart;
window.updateCartCount = updateCartCount;
window.showCartNotification = showCartNotification;
