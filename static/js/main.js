// Main JavaScript file for DOUKA KM e-commerce platform

// Check logo loading at the beginning of the file
document.addEventListener('DOMContentLoaded', function() {
    // Logo visibility check
    const logo = document.querySelector('.navbar-logo');
    if (logo) {
        console.log('Logo element found in DOM');
        logo.onload = function() {
            console.log('Logo loaded successfully');
            // Make sure the logo is visible
            this.style.display = 'inline-block';
        };
        logo.onerror = function() {
            console.error('Logo failed to load. Check the image path and file.');
            // Provide fallback
            this.style.display = 'none';
        };
    } else {
        console.error('Logo element not found in DOM');
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Add event listeners for "Add to Cart" buttons
    const addToCartButtons = document.querySelectorAll('a[href^="/add-to-cart/"]');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const productId = this.getAttribute('href').split('/').pop();
            addToCart(productId);
        });
    });
    
    // Function to add product to cart via AJAX (will implement backend later)
    function addToCart(productId) {
        // This is just a placeholder for now
        console.log(`Product ${productId} added to cart`);
        
        // Show confirmation message
        const alertElement = document.createElement('div');
        alertElement.className = 'alert alert-success alert-dismissible fade show';
        alertElement.setAttribute('role', 'alert');
        alertElement.innerHTML = `
            Produit ajouté au panier avec succès!
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert at the top of the main content
        const mainContent = document.querySelector('main');
        mainContent.insertBefore(alertElement, mainContent.firstChild);
        
        // Auto dismiss after 3 seconds
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertElement);
            alert.close();
        }, 3000);
    }
});

// Remplace les gestionnaires d'événements sur les catégories pour utiliser le clic plutôt que le survol
document.addEventListener('DOMContentLoaded', function() {
    // Gestion du clic sur les catégories au lieu du survol
    const setupClickableCategories = function() {
        const categoryItems = document.querySelectorAll('.category-item');
        
        // Supprimer d'abord tous les écouteurs d'événements existants pour éviter les doublons
        categoryItems.forEach(item => {
            const newItem = item.cloneNode(true);
            item.parentNode.replaceChild(newItem, item);
        });
        
        // Récupérer les éléments fraîchement clonés
        const refreshedCategoryItems = document.querySelectorAll('.category-item');
        
        // Ajouter les nouveaux écouteurs d'événements
        refreshedCategoryItems.forEach(item => {
            // Fermer le menu au clic à l'extérieur
            document.addEventListener('click', function(e) {
                if (!item.contains(e.target)) {
                    const submenu = item.querySelector('.subcategory-menu');
                    if (submenu) {
                        submenu.style.display = 'none';
                        item.classList.remove('active');
                    }
                }
            });
            
            // Ouvrir/fermer le menu au clic sur l'élément de catégorie
            item.addEventListener('click', function(e) {
                // Ne pas réagir si on a cliqué sur un lien dans le sous-menu
                if (e.target.closest('.subcategory-menu a')) {
                    return;
                }
                
                const submenu = this.querySelector('.subcategory-menu');
                if (!submenu) return;
                
                e.preventDefault();
                e.stopPropagation();
                
                // Fermer tous les autres sous-menus
                refreshedCategoryItems.forEach(otherItem => {
                    if (otherItem !== item) {
                        const otherSubmenu = otherItem.querySelector('.subcategory-menu');
                        if (otherSubmenu) {
                            otherSubmenu.style.display = 'none';
                            otherItem.classList.remove('active');
                        }
                    }
                });
                
                // Basculer l'état actuel
                if (submenu.style.display === 'block') {
                    submenu.style.display = 'none';
                    this.classList.remove('active');
                } else {
                    submenu.style.display = 'block';
                    this.classList.add('active');
                }
            });
        });
    };
    
    // Exécuter l'initialisation
    setupClickableCategories();
});

// Remplacer la section fixStylesForSubmenus pour supprimer le comportement de survol
document.addEventListener('DOMContentLoaded', function() {
    // Appliquer un correctif de style pour garantir l'affichage des sous-menus
    const fixStylesForSubmenus = function() {
        // Corriger les conteneurs parents
        const categoryWrapper = document.querySelector('.category-wrapper');
        const categoryNav = document.querySelector('.category-nav');
        
        if (categoryWrapper && categoryNav) {
            // Les conteneurs doivent avoir overflow visible
            categoryWrapper.style.overflowY = 'visible';
            categoryNav.style.overflow = 'visible';
            
            // Appliquer en forçant via !important avec un style interne
            const styleEl = document.createElement('style');
            styleEl.textContent = `
                .category-wrapper, .category-nav {
                    overflow: visible !important;
                }
                
                .category-item {
                    position: relative !important;
                }
                
                .subcategory-menu {
                    position: absolute !important;
                    top: 100% !important;
                    z-index: 9999 !important;
                    width: 650px !important;
                    max-width: 90vw !important;
                    background: #ffffff !important;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
                    display: none !important;
                }
                
                /* Supprimer le comportement de survol */
                .category-item:hover .subcategory-menu {
                    display: none !important;
                }
                
                /* Ajouter le comportement de clic */
                .category-item.active .subcategory-menu {
                    display: block !important;
                }
            `;
            document.head.appendChild(styleEl);
        }
    };
    
    // Exécuter immédiatement
    fixStylesForSubmenus();
    
    // Configuration des interactions pour mobile
    const mobileSetup = function() {
        if (window.innerWidth <= 991) {
            // Pour mobile, ajouter des boutons toggle
            document.querySelectorAll('.category-item').forEach(item => {
                const link = item.querySelector('.category-link');
                const menu = item.querySelector('.subcategory-menu');
                
                if (link && menu) {
                    // Éviter les doublons
                    if (!item.querySelector('.mobile-toggle-btn')) {
                        const toggleBtn = document.createElement('span');
                        toggleBtn.className = 'mobile-toggle-btn';
                        toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
                        toggleBtn.style.cssText = 'position: absolute; right: 5px; top: 8px; padding: 5px;';
                        link.appendChild(toggleBtn);
                        
                        // Toggle au clic
                        toggleBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            
                            const isVisible = menu.style.display === 'block';
                            
                            // Cacher tous les sous-menus d'abord
                            document.querySelectorAll('.subcategory-menu').forEach(m => {
                                m.style.display = 'none';
                            });
                            
                            // Réinitialiser tous les icônes
                            document.querySelectorAll('.mobile-toggle-btn i').forEach(icon => {
                                icon.className = 'fas fa-chevron-down';
                            });
                            
                            // Afficher ou cacher selon l'état actuel
                            if (!isVisible) {
                                menu.style.display = 'block';
                                toggleBtn.querySelector('i').className = 'fas fa-chevron-up';
                            }
                        });
                        
                        // Empêcher la navigation au clic sur le lien principal sur mobile
                        link.addEventListener('click', function(e) {
                            if (e.target === link) {
                                e.preventDefault();
                            }
                        });
                    }
                }
            });
        }
    };
    
    // Exécuter la configuration pour mobile
    mobileSetup();
    window.addEventListener('resize', mobileSetup);
    
    // Vérifier et ajuster le positionnement des sous-menus
    function adjustMenuPositions() {
        document.querySelectorAll('.category-item').forEach(item => {
            const menu = item.querySelector('.subcategory-menu');
            if (menu && window.innerWidth > 991) {
                // Vérifier si le menu va déborder à droite
                const itemRect = item.getBoundingClientRect();
                const windowWidth = window.innerWidth;
                
                if (itemRect.left + 650 > windowWidth) {
                    menu.style.left = 'auto';
                    menu.style.right = '0';
                } else {
                    menu.style.left = '0';
                    menu.style.right = 'auto';
                }
            }
        });
    }
    
    // Ajuster les positions initialement et au redimensionnement
    adjustMenuPositions();
    window.addEventListener('resize', adjustMenuPositions);
});

// Modification du comportement mobile pour les catégories

document.addEventListener('DOMContentLoaded', function() {
    // Configuration des menus de catégories horizontaux
    const setupHorizontalCategoryMenu = function() {
        const categoryNav = document.querySelector('.category-nav');
        const categoryWrapper = document.querySelector('.category-wrapper');
        const categoryList = document.querySelector('.category-list');
        
        if (!categoryNav || !categoryWrapper || !categoryList) return;
        
        // Assurer une disposition horizontale
        categoryList.style.display = 'flex';
        categoryList.style.flexDirection = 'row';
        categoryList.style.flexWrap = 'nowrap';
        categoryList.style.justifyContent = 'space-between';
        
        // Correction cruciale: définir overflow-y à visible pour permettre l'affichage des sous-menus
        categoryWrapper.style.overflow = 'visible';
        categoryNav.style.overflow = 'visible';
        
        // Force les sous-menus à s'afficher correctement avec un z-index élevé
        document.querySelectorAll('.subcategory-menu').forEach(submenu => {
            // Position absolue avec un z-index élevé pour s'afficher par-dessus
            submenu.style.position = 'absolute';
            submenu.style.top = '100%';
            submenu.style.zIndex = '9999';
            
            // Adapter la largeur en fonction du nombre de sous-catégories
            const columnCount = submenu.querySelectorAll('.subcategory-group').length;
            if (columnCount > 3) {
                // Si beaucoup de sous-catégories, agrandir le menu
                submenu.style.width = '700px';
            } else {
                submenu.style.width = '650px';
            }
            
            submenu.style.maxWidth = '90vw';
            submenu.style.backgroundColor = '#ffffff';
            submenu.style.boxShadow = '0 5px 15px rgba(0,0,0,0.2)';
            submenu.style.borderRadius = '4px';
        });
        
        // Gestion spécifique selon la taille d'écran
        if (window.innerWidth <= 991) {
            // Pour les mobiles - permettre la navigation directe
            const categoryItems = document.querySelectorAll('.category-item');
            
            categoryItems.forEach(item => {
                item.style.flex = '0 0 auto';
                item.style.minWidth = '100px';
                item.style.textAlign = 'center';
                
                const link = item.querySelector('.category-link');
                const submenu = item.querySelector('.subcategory-menu');
                
                if (submenu) {
                    // Cacher complètement les sous-menus sur mobile
                    submenu.style.display = 'none';
                }
                
                if (link) {
                    // Simplifier l'affichage du lien pour mobile
                    link.style.padding = '10px 8px';
                    
                    // S'assurer que l'icône est au-dessus du texte
                    const icon = link.querySelector('i');
                    if (icon) {
                        icon.style.display = 'block';
                        icon.style.marginBottom = '5px';
                        icon.style.fontSize = '1.2rem';
                    }
                    
                    // Supprimer tous les écouteurs d'événements précédents
                    const newLink = link.cloneNode(true);
                    link.parentNode.replaceChild(newLink, link);
                }
                
                // Supprimer tous les boutons toggle existants
                const toggleButtons = item.querySelectorAll('.mobile-toggle, .mobile-toggle-btn');
                toggleButtons.forEach(btn => btn.remove());
            });
            
            // Permettre le défilement horizontal du menu de catégories sur mobile
            categoryWrapper.style.overflowX = 'auto';
            categoryWrapper.style.WebkitOverflowScrolling = 'touch';
        } else {
            // Pour les écrans plus larges
            const categoryItems = document.querySelectorAll('.category-item');
            const totalItems = categoryItems.length;
            
            categoryItems.forEach((item, index) => {
                // Distribuer les éléments uniformément et assurer la position relative
                item.style.flex = `0 0 ${Math.floor(100 / totalItems)}%`;
                item.style.position = 'relative'; // Important pour le positionnement des sous-menus
                
                const submenu = item.querySelector('.subcategory-menu');
                if (submenu) {
                    // Positionner correctement le sous-menu par rapport à son parent
                    submenu.style.position = 'absolute';
                    submenu.style.top = '100%';
                    submenu.style.display = 'none'; // Par défaut caché
                    
                    // Ajuster la position horizontale pour éviter les débordements
                    const itemRect = item.getBoundingClientRect();
                    const windowWidth = window.innerWidth;
                    
                    if (index >= Math.ceil(totalItems / 2) || itemRect.left + 650 > windowWidth) {
                        submenu.style.left = 'auto';
                        submenu.style.right = '0';
                    } else {
                        submenu.style.left = '0';
                        submenu.style.right = 'auto';
                    }
                }
            });
        }
    };
    
    // Exécuter l'initialisation et ajuster au redimensionnement
    setupHorizontalCategoryMenu();
    window.addEventListener('resize', setupHorizontalCategoryMenu);
});

// Simplification de la gestion mobile - remplacement du code existant
document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour gérer le comportement mobile
    const setupMobileCategoryBehavior = function() {
        if (window.innerWidth <= 991) {
            // Désactivation complète de l'affichage des sous-menus sur mobile
            const styleEl = document.createElement('style');
            styleEl.id = 'mobile-category-styles';
            styleEl.textContent = `
                @media (max-width: 991px) {
                    .subcategory-menu {
                        display: none !important;
                    }
                    
                    .category-item:hover .subcategory-menu {
                        display: none !important;
                    }
                    
                    .mobile-toggle, .mobile-toggle-btn {
                        display: none !important;
                    }
                    
                    .category-item {
                        flex: 0 0 auto !important;
                        min-width: 100px !important;
                        text-align: center !important;
                    }
                    
                    .category-link {
                        padding: 10px 8px !important;
                        text-decoration: none !important;
                    }
                    
                    .category-link i {
                        display: block !important;
                        margin: 0 auto 5px !important;
                        font-size: 1.2rem !important;
                    }
                    
                    .category-wrapper {
                        overflow-x: auto !important;
                        overflow-y: hidden !important;
                    }
                }
            `;
            
            // Supprimer l'ancien style s'il existe
            const oldStyle = document.getElementById('mobile-category-styles');
            if (oldStyle) {
                oldStyle.remove();
            }
            
            document.head.appendChild(styleEl);
            
            // S'assurer que tous les liens fonctionnent correctement
            document.querySelectorAll('.category-item .category-link').forEach(link => {
                // Clone le lien pour supprimer tous les écouteurs d'événements
                const newLink = link.cloneNode(true);
                link.parentNode.replaceChild(newLink, link);
            });
        }
    };
    
    // Exécuter au chargement et au redimensionnement
    setupMobileCategoryBehavior();
    window.addEventListener('resize', setupMobileCategoryBehavior);
});

// Mobile slide menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenu = document.getElementById('mobile-menu');
    const menuOverlay = document.getElementById('menu-overlay');
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const closeMenuBtn = document.getElementById('close-mobile-menu');
    
    if (mobileMenu && menuOverlay && mobileMenuBtn && closeMenuBtn) {
        const mobileMenuLinks = document.querySelectorAll('#mobile-menu .nav-link, #mobile-menu .btn');
        
        // Fonction pour ouvrir le menu
        function openMenu() {
            mobileMenu.classList.add('active');
            menuOverlay.classList.add('active');
            document.body.style.overflow = 'hidden'; // Empêche le défilement du body
        }
        
        // Fonction pour fermer le menu
        function closeMenu() {
            mobileMenu.classList.remove('active');
            menuOverlay.classList.remove('active');
            document.body.style.overflow = ''; // Rétablit le défilement
        }
        
        // Ouvrir le menu au clic sur le bouton hamburger
        mobileMenuBtn.addEventListener('click', openMenu);
        
        // Fermer le menu au clic sur le bouton de fermeture
        closeMenuBtn.addEventListener('click', closeMenu);
        
        // Fermer le menu au clic sur l'overlay
        menuOverlay.addEventListener('click', closeMenu);
        
        // Fermer le menu après clic sur un lien
        mobileMenuLinks.forEach(link => {
            link.addEventListener('click', closeMenu);
        });
        
        // Fermer le menu si l'écran est redimensionné vers une largeur desktop
        window.addEventListener('resize', function() {
            if (window.innerWidth >= 992) {
                closeMenu();
            }
        });
    }
});

// Correction du comportement des catégories sur mobile
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si on est sur mobile
    const isMobile = window.innerWidth <= 991;
    
    // Gérer les clics sur les catégories pour mobile
    const categoryLinks = document.querySelectorAll('.category-item .category-link');
    
    categoryLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (isMobile) {
                // Sur mobile, naviguer directement vers la page de catégorie
                const href = this.getAttribute('href');
                if (href && href !== '#') {
                    window.location.href = href;
                }
            }
        });
    });
    
    // Réappliquer cette logique si la fenêtre est redimensionnée
    window.addEventListener('resize', function() {
        const newIsMobile = window.innerWidth <= 991;
        if (newIsMobile !== isMobile) {
            // Recharger la page si le mode change entre desktop et mobile
            location.reload();
        }
    });
});

// Correction spécifique pour la navigation des catégories sur mobile
document.addEventListener('DOMContentLoaded', function() {
    // La fonction de correction pour la navigation mobile
    const fixMobileCategoryNavigation = function() {
        if (window.innerWidth <= 991) {
            document.querySelectorAll('.category-item').forEach(item => {
                // Rendre la catégorie entière cliquable
                const link = item.querySelector('.category-link');
                if (link) {
                    // S'assurer que le lien n'a pas d'écouteurs d'événements
                    const newLink = link.cloneNode(true);
                    if (link.parentNode) {
                        link.parentNode.replaceChild(newLink, link);
                    }
                    
                    // Assurer que les clics fonctionnent correctement
                    newLink.addEventListener('click', function(e) {
                        // Si c'est le lien principal (pas un élément enfant)
                        if (e.target === this || this.contains(e.target)) {
                            const href = this.getAttribute('href');
                            if (href && href !== '#') {
                                e.preventDefault();
                                window.location.href = href;
                                return false;
                            }
                        }
                    });
                }
                
                // Désactiver le comportement "onHover" des sous-menus sur mobile
                const submenu = item.querySelector('.subcategory-menu');
                if (submenu) {
                    submenu.style.display = 'none';
                }
            });
            
            // Styles pour rendre les catégories plus facilement cliquables
            const styleEl = document.createElement('style');
            styleEl.textContent = `
                @media (max-width: 991px) {
                    .category-link {
                        cursor: pointer !important;
                        display: block !important;
                        padding: 15px 10px !important;
                    }
                    
                    .category-item {
                        min-width: 100px !important;
                    }
                }
            `;
            document.head.appendChild(styleEl);
        }
    };
    
    // Exécuter la correction
    fixMobileCategoryNavigation();
    
    // S'assurer qu'elle s'applique aussi après un redimensionnement
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(fixMobileCategoryNavigation, 250);
    });
});

// Gestion des ajouts au panier
document.addEventListener('DOMContentLoaded', function() {
    // Attacher la fonction aux boutons "Ajouter au panier"
    document.querySelectorAll('a[href^="/add-to-cart/"]').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const productId = this.getAttribute('href').split('/').pop();
            const quantityInput = this.closest('.product-item')?.querySelector('.quantity-input');
            const quantity = quantityInput ? parseInt(quantityInput.value) : 1;
            
            addToCart(productId, quantity);
        });
    });
});

// Fonction pour afficher une notification d'ajout au panier
function showCartNotification(message) {
    // Créer la notification
    const notification = document.createElement('div');
    notification.className = 'alert alert-success alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Ajouter la notification au body
    document.body.appendChild(notification);
    
    // Supprimer automatiquement après 3 secondes
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// Fonction principale pour ajouter un produit au panier
function addToCart(productId, quantity = 1) {
    const formData = new FormData();
    formData.append('quantity', quantity);
    
    fetch(`/add-to-cart/${productId}`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mettre à jour le compteur du panier
            updateCartCount(data.cart_count);
            
            // Afficher la notification
            showCartNotification(`${data.product_name} ajouté au panier`);
        } else {
            showCartNotification(data.message || 'Erreur lors de l\'ajout au panier');
        }
    })
    .catch(error => {
        console.error('Erreur lors de l\'ajout au panier:', error);
        showCartNotification('Erreur lors de l\'ajout au panier');
    });
}

// Fonction pour mettre à jour le compteur du panier
function updateCartCount(count) {
    const cartCountElements = document.querySelectorAll('.cart-count');
    cartCountElements.forEach(element => {
        element.textContent = count;
    });
}

// Fonction pour mettre à jour TOUS les compteurs du panier, y compris en mobile
function updateAllCartCounters(count) {
    console.log('Mise à jour des compteurs du panier avec: ' + count);
    
    // Sélectionner tous les éléments avec la classe cart-count
    const cartCountElements = document.querySelectorAll('.cart-count');
    
    // Mettre à jour le contenu de chaque élément
    cartCountElements.forEach(element => {
        element.textContent = count;
        
        // S'assurer que l'élément est visible
        element.style.display = count > 0 ? 'inline-block' : 'none';
    });
}

// Ajouter les fonctions au window pour qu'elles soient disponibles globalement
window.addToCart = addToCart;
window.showCartNotification = showCartNotification;
window.updateCartCount = updateCartCount;
window.updateAllCartCounters = updateAllCartCounters;

// ========================================
// GESTION DES CODES PROMO PUBLICS
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    initPromoCodeFunctionality();
});

function initPromoCodeFunctionality() {
    // Gestion de la copie des codes promo
    const copyButtons = document.querySelectorAll('.copy-code-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const code = this.getAttribute('data-code');
            copyPromoCode(code);
        });
    });
    
    // Gestion de l'utilisation immédiate des codes promo
    const usePromoButtons = document.querySelectorAll('.use-promo-btn');
    usePromoButtons.forEach(button => {
        button.addEventListener('click', function() {
            const code = this.getAttribute('data-code');
            usePromoCode(code);
        });
    });
}

// Fonction pour copier un code promo dans le presse-papiers
function copyPromoCode(code) {
    // Méthode moderne pour copier dans le presse-papiers
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(code).then(() => {
            showCodeCopiedNotification(code);
        }).catch(err => {
            console.error('Erreur lors de la copie:', err);
            fallbackCopyTextToClipboard(code);
        });
    } else {
        // Fallback pour les navigateurs plus anciens
        fallbackCopyTextToClipboard(code);
    }
}

// Méthode de fallback pour copier du texte
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    
    // Éviter le défilement vers le haut de la page
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCodeCopiedNotification(text);
        } else {
            console.error('Échec de la copie');
        }
    } catch (err) {
        console.error('Erreur lors de la copie:', err);
    }
    
    document.body.removeChild(textArea);
}

// Afficher une notification de confirmation de copie
function showCodeCopiedNotification(code) {
    // Supprimer les notifications existantes
    const existingNotifications = document.querySelectorAll('.code-copied-notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Créer la nouvelle notification
    const notification = document.createElement('div');
    notification.className = 'code-copied-notification';
    notification.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        Code <strong>${code}</strong> copié !
    `;
    
    document.body.appendChild(notification);
    
    // Afficher avec animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // Masquer après 3 secondes
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 3000);
}

// Fonction pour utiliser immédiatement un code promo
function usePromoCode(code) {
    // Vérifier d'abord si l'utilisateur a des articles dans son panier
    fetch('/api/cart/count')
        .then(response => response.json())
        .then(data => {
            if (data.count === 0) {
                // Panier vide - rediriger vers les produits
                showPromoCodeGuide(code);
            } else {
                // Panier non vide - aller au checkout avec le code
                goToCheckoutWithPromo(code);
            }
        })
        .catch(error => {
            console.error('Erreur lors de la vérification du panier:', error);
            // En cas d'erreur, aller quand même au checkout
            goToCheckoutWithPromo(code);
        });
}

// Afficher un guide pour utiliser le code promo
function showPromoCodeGuide(code) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-info-circle me-2"></i>
                        Comment utiliser le code ${code}
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="text-center mb-3">
                        <div class="promo-code-display-modal">
                            <span class="badge bg-warning text-dark fs-6 px-3 py-2">${code}</span>
                        </div>
                    </div>
                    
                    <div class="steps">
                        <div class="step mb-3">
                            <div class="d-flex align-items-center">
                                <span class="step-number bg-primary text-white rounded-circle me-3">1</span>
                                <span>Ajoutez des produits à votre panier</span>
                            </div>
                        </div>
                        <div class="step mb-3">
                            <div class="d-flex align-items-center">
                                <span class="step-number bg-primary text-white rounded-circle me-3">2</span>
                                <span>Allez au checkout</span>
                            </div>
                        </div>
                        <div class="step mb-3">
                            <div class="d-flex align-items-center">
                                <span class="step-number bg-primary text-white rounded-circle me-3">3</span>
                                <span>Entrez le code <strong>${code}</strong></span>
                            </div>
                        </div>
                        <div class="step mb-3">
                            <div class="d-flex align-items-center">
                                <span class="step-number bg-success text-white rounded-circle me-3">4</span>
                                <span>Profitez de votre réduction !</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                        Fermer
                    </button>
                    <a href="/products" class="btn btn-primary">
                        <i class="fas fa-shopping-bag me-2"></i>
                        Voir les produits
                    </a>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
    
    // Supprimer le modal du DOM après fermeture
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
    
    // Copier automatiquement le code
    copyPromoCode(code);
}

// Aller au checkout avec le code promo pré-rempli
function goToCheckoutWithPromo(code) {
    // Stocker le code dans le sessionStorage pour le pré-remplir au checkout
    sessionStorage.setItem('promo_code_to_apply', code);
    
    // Rediriger vers le checkout
    window.location.href = '/checkout';
}

// CSS supplémentaire pour le modal
const modalStyles = `
    .step-number {
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.9rem;
    }
    
    .promo-code-display-modal {
        font-family: 'Courier New', monospace;
        font-size: 1.2rem;
        margin: 10px 0;
    }
`;

// Injecter les styles
if (!document.getElementById('promo-modal-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'promo-modal-styles';
    styleSheet.textContent = modalStyles;
    document.head.appendChild(styleSheet);
}

// Fonctions globales
window.copyPromoCode = copyPromoCode;
window.usePromoCode = usePromoCode;
