/**
 * DOUKA KM - Sélecteur d'Icônes FontAwesome
 * Base de données complète d'icônes organisées par catégorie
 * 
 * @author DOUKA KM Team
 * @version 1.0.0
 */

const FontAwesomeIconDatabase = {
    
    // Icônes populaires et couramment utilisées
    popular: [
        'fas fa-box', 'fas fa-shopping-cart', 'fas fa-store', 'fas fa-tag', 'fas fa-tags',
        'fas fa-heart', 'fas fa-star', 'fas fa-user', 'fas fa-users', 'fas fa-home',
        'fas fa-phone', 'fas fa-envelope', 'fas fa-globe', 'fas fa-search', 'fas fa-cog',
        'fas fa-check', 'fas fa-times', 'fas fa-plus', 'fas fa-minus', 'fas fa-edit'
    ],
    
    // Commerce et business
    business: [
        'fas fa-store', 'fas fa-shopping-cart', 'fas fa-shopping-bag', 'fas fa-cash-register',
        'fas fa-credit-card', 'fas fa-money-bill-wave', 'fas fa-coins', 'fas fa-receipt',
        'fas fa-handshake', 'fas fa-chart-line', 'fas fa-briefcase', 'fas fa-building',
        'fas fa-warehouse', 'fas fa-truck', 'fas fa-shipping-fast', 'fas fa-clipboard-list',
        'fas fa-balance-scale', 'fas fa-calculator', 'fas fa-piggy-bank', 'fas fa-wallet',
        'fas fa-dollar-sign', 'fas fa-euro-sign', 'fas fa-yen-sign', 'fas fa-pound-sign'
    ],
    
    // Alimentation et restaurants
    food: [
        'fas fa-utensils', 'fas fa-hamburger', 'fas fa-pizza-slice', 'fas fa-coffee',
        'fas fa-wine-glass', 'fas fa-beer', 'fas fa-cookie-bite', 'fas fa-ice-cream',
        'fas fa-apple-alt', 'fas fa-carrot', 'fas fa-fish', 'fas fa-egg',
        'fas fa-bread-slice', 'fas fa-cheese', 'fas fa-birthday-cake', 'fas fa-seedling',
        'fas fa-lemon', 'fas fa-pepper-hot', 'fas fa-drumstick-bite', 'fas fa-bacon',
        'fas fa-cookie', 'fas fa-candy-cane', 'fas fa-glass-whiskey', 'fas fa-wine-bottle'
    ],
    
    // Mode et vêtements
    fashion: [
        'fas fa-tshirt', 'fas fa-hat-cowboy', 'fas fa-glasses', 'fas fa-gem',
        'fas fa-ring', 'fas fa-shoe-prints', 'fas fa-socks', 'fas fa-mitten',
        'fas fa-crown', 'fas fa-tie', 'fas fa-vest', 'fas fa-user-tie',
        'fas fa-shopping-bag', 'fas fa-tags', 'fas fa-palette', 'fas fa-cut',
        'fas fa-hat-wizard', 'fas fa-mask', 'fas fa-sunglasses', 'fas fa-watch',
        'fas fa-handbag', 'fas fa-high-heel', 'fas fa-boot', 'fas fa-diamond'
    ],
    
    // Technologie et électronique
    tech: [
        'fas fa-laptop', 'fas fa-mobile-alt', 'fas fa-tablet-alt', 'fas fa-desktop',
        'fas fa-keyboard', 'fas fa-mouse', 'fas fa-headphones', 'fas fa-microchip',
        'fas fa-wifi', 'fas fa-bluetooth', 'fas fa-camera', 'fas fa-video',
        'fas fa-gamepad', 'fas fa-tv', 'fas fa-plug', 'fas fa-battery-full',
        'fas fa-usb', 'fas fa-hard-drive', 'fas fa-memory', 'fas fa-sim-card',
        'fas fa-server', 'fas fa-router', 'fas fa-print', 'fas fa-scanner'
    ],
    
    // Général et divers
    general: [
        'fas fa-home', 'fas fa-car', 'fas fa-plane', 'fas fa-bicycle',
        'fas fa-book', 'fas fa-music', 'fas fa-film', 'fas fa-paint-brush',
        'fas fa-tools', 'fas fa-wrench', 'fas fa-hammer', 'fas fa-leaf',
        'fas fa-paw', 'fas fa-baby', 'fas fa-graduation-cap', 'fas fa-dumbbell',
        'fas fa-key', 'fas fa-lock', 'fas fa-unlock', 'fas fa-shield-alt',
        'fas fa-fire', 'fas fa-snowflake', 'fas fa-sun', 'fas fa-moon'
    ],
    
    // Beauté et cosmétiques
    beauty: [
        'fas fa-palette', 'fas fa-paint-brush', 'fas fa-cut', 'fas fa-spray-can',
        'fas fa-gem', 'fas fa-crown', 'fas fa-ring', 'fas fa-glasses',
        'fas fa-eye', 'fas fa-lips', 'fas fa-hand-sparkles', 'fas fa-star',
        'fas fa-heart', 'fas fa-kiss-wink-heart', 'fas fa-female', 'fas fa-mirror'
    ],
    
    // Sport et fitness
    sports: [
        'fas fa-dumbbell', 'fas fa-running', 'fas fa-swimmer', 'fas fa-bicycle',
        'fas fa-football-ball', 'fas fa-basketball-ball', 'fas fa-volleyball-ball', 'fas fa-table-tennis',
        'fas fa-golf-ball', 'fas fa-hockey-puck', 'fas fa-bowling-ball', 'fas fa-medal',
        'fas fa-trophy', 'fas fa-award', 'fas fa-stopwatch', 'fas fa-heartbeat'
    ],
    
    // Maison et jardin
    home: [
        'fas fa-home', 'fas fa-couch', 'fas fa-bed', 'fas fa-bath',
        'fas fa-toilet', 'fas fa-kitchen-set', 'fas fa-blender', 'fas fa-coffee-maker',
        'fas fa-seedling', 'fas fa-tree', 'fas fa-leaf', 'fas fa-flower',
        'fas fa-hammer', 'fas fa-wrench', 'fas fa-screwdriver', 'fas fa-paint-roller'
    ],
    
    // Livres et éducation
    books: [
        'fas fa-book', 'fas fa-book-open', 'fas fa-books', 'fas fa-bookmark',
        'fas fa-graduation-cap', 'fas fa-school', 'fas fa-university', 'fas fa-chalkboard',
        'fas fa-pencil-alt', 'fas fa-pen', 'fas fa-highlighter', 'fas fa-eraser',
        'fas fa-calculator', 'fas fa-globe', 'fas fa-map', 'fas fa-microscope'
    ],
    
    // Santé et médical
    health: [
        'fas fa-heartbeat', 'fas fa-heart', 'fas fa-plus-square', 'fas fa-user-md',
        'fas fa-stethoscope', 'fas fa-syringe', 'fas fa-pills', 'fas fa-thermometer',
        'fas fa-band-aid', 'fas fa-wheelchair', 'fas fa-tooth', 'fas fa-eye',
        'fas fa-brain', 'fas fa-lungs', 'fas fa-dna', 'fas fa-virus'
    ],
    
    // Automobile et transport
    auto: [
        'fas fa-car', 'fas fa-truck', 'fas fa-motorcycle', 'fas fa-bicycle',
        'fas fa-bus', 'fas fa-taxi', 'fas fa-ship', 'fas fa-plane',
        'fas fa-helicopter', 'fas fa-rocket', 'fas fa-train', 'fas fa-subway',
        'fas fa-gas-pump', 'fas fa-oil-can', 'fas fa-tire', 'fas fa-wrench'
    ],
    
    // Animaux et pets
    pets: [
        'fas fa-paw', 'fas fa-dog', 'fas fa-cat', 'fas fa-fish',
        'fas fa-bird', 'fas fa-horse', 'fas fa-frog', 'fas fa-spider',
        'fas fa-bone', 'fas fa-heart', 'fas fa-home', 'fas fa-utensils'
    ],
    
    // Musique et audio
    music: [
        'fas fa-music', 'fas fa-headphones', 'fas fa-microphone', 'fas fa-guitar',
        'fas fa-piano', 'fas fa-drums', 'fas fa-violin', 'fas fa-trumpet',
        'fas fa-volume-up', 'fas fa-volume-down', 'fas fa-play', 'fas fa-pause',
        'fas fa-stop', 'fas fa-forward', 'fas fa-backward', 'fas fa-record-vinyl'
    ],
    
    // Jeux et jouets
    toys: [
        'fas fa-gamepad', 'fas fa-puzzle-piece', 'fas fa-dice', 'fas fa-chess',
        'fas fa-robot', 'fas fa-rocket', 'fas fa-star', 'fas fa-magic',
        'fas fa-hat-wizard', 'fas fa-crown', 'fas fa-gift', 'fas fa-birthday-cake',
        'fas fa-balloon', 'fas fa-candy-cane', 'fas fa-teddy-bear', 'fas fa-kite'
    ],
    
    // Bébé et enfants
    baby: [
        'fas fa-baby', 'fas fa-baby-carriage', 'fas fa-bottle', 'fas fa-pacifier',
        'fas fa-diaper', 'fas fa-rattle', 'fas fa-teddy-bear', 'fas fa-blocks',
        'fas fa-heart', 'fas fa-moon', 'fas fa-star', 'fas fa-sun',
        'fas fa-rainbow', 'fas fa-cloud', 'fas fa-apple-alt', 'fas fa-milk'
    ]
};

/**
 * Suggestions intelligentes d'icônes basées sur le nom de la catégorie
 */
const IconSuggestions = {
    
    // Mapping des mots-clés vers les icônes appropriées
    keywordMapping: {
        // Commerce et vente
        'commerce': 'fas fa-store',
        'vente': 'fas fa-shopping-cart',
        'magasin': 'fas fa-store-alt',
        'boutique': 'fas fa-shopping-bag',
        'achat': 'fas fa-credit-card',
        'paiement': 'fas fa-money-bill-wave',
        
        // Électronique
        'électronique': 'fas fa-microchip',
        'electronique': 'fas fa-microchip',
        'tech': 'fas fa-laptop',
        'technologie': 'fas fa-laptop',
        'ordinateur': 'fas fa-desktop',
        'téléphone': 'fas fa-mobile-alt',
        'smartphone': 'fas fa-mobile-alt',
        
        // Mode et vêtements
        'mode': 'fas fa-tshirt',
        'vêtement': 'fas fa-tshirt',
        'vetement': 'fas fa-tshirt',
        'fashion': 'fas fa-tshirt',
        'chaussure': 'fas fa-shoe-prints',
        'accessoire': 'fas fa-gem',
        
        // Alimentation
        'alimentation': 'fas fa-utensils',
        'nourriture': 'fas fa-hamburger',
        'food': 'fas fa-utensils',
        'restaurant': 'fas fa-utensils',
        'cuisine': 'fas fa-utensils',
        'boisson': 'fas fa-coffee',
        
        // Santé et beauté
        'santé': 'fas fa-heartbeat',
        'sante': 'fas fa-heartbeat',
        'health': 'fas fa-heartbeat',
        'beauté': 'fas fa-palette',
        'beaute': 'fas fa-palette',
        'beauty': 'fas fa-palette',
        'cosmétique': 'fas fa-palette',
        
        // Maison et jardin
        'maison': 'fas fa-home',
        'home': 'fas fa-home',
        'jardin': 'fas fa-seedling',
        'garden': 'fas fa-seedling',
        'décoration': 'fas fa-paint-brush',
        'meuble': 'fas fa-couch',
        
        // Sport
        'sport': 'fas fa-dumbbell',
        'fitness': 'fas fa-dumbbell',
        'gym': 'fas fa-dumbbell',
        'course': 'fas fa-running',
        
        // Bébé et enfants
        'bébé': 'fas fa-baby',
        'bebe': 'fas fa-baby',
        'baby': 'fas fa-baby',
        'enfant': 'fas fa-baby',
        'kids': 'fas fa-baby',
        
        // Automobile
        'auto': 'fas fa-car',
        'automobile': 'fas fa-car',
        'voiture': 'fas fa-car',
        'moto': 'fas fa-motorcycle',
        
        // Animaux
        'animal': 'fas fa-paw',
        'pet': 'fas fa-paw',
        'chien': 'fas fa-dog',
        'chat': 'fas fa-cat',
        
        // Livres et éducation
        'livre': 'fas fa-book',
        'book': 'fas fa-book',
        'éducation': 'fas fa-graduation-cap',
        'education': 'fas fa-graduation-cap',
        'école': 'fas fa-school',
        
        // Artisanat
        'artisanat': 'fas fa-palette',
        'art': 'fas fa-paint-brush',
        'craft': 'fas fa-palette',
        'traditionnel': 'fas fa-palette',
        'local': 'fas fa-map-marker-alt'
    },
    
    /**
     * Suggère une icône basée sur le nom de la catégorie
     * @param {string} categoryName - Nom de la catégorie
     * @returns {string} - Classe CSS de l'icône suggérée
     */
    suggest: function(categoryName) {
        if (!categoryName) return 'fas fa-box';
        
        const name = categoryName.toLowerCase().trim();
        
        // Recherche exacte
        if (this.keywordMapping[name]) {
            return this.keywordMapping[name];
        }
        
        // Recherche par mots-clés partiels
        for (const keyword in this.keywordMapping) {
            if (name.includes(keyword) || keyword.includes(name)) {
                return this.keywordMapping[keyword];
            }
        }
        
        // Icône par défaut
        return 'fas fa-box';
    },
    
    /**
     * Retourne plusieurs suggestions d'icônes pour une catégorie
     * @param {string} categoryName - Nom de la catégorie
     * @returns {Array} - Array d'icônes suggérées
     */
    getMultipleSuggestions: function(categoryName) {
        const suggestions = [];
        const name = categoryName.toLowerCase().trim();
        
        // Ajouter l'icône principale suggérée
        suggestions.push(this.suggest(categoryName));
        
        // Ajouter des icônes relatives
        Object.keys(this.keywordMapping).forEach(keyword => {
            if (name.includes(keyword) || keyword.includes(name)) {
                const icon = this.keywordMapping[keyword];
                if (!suggestions.includes(icon)) {
                    suggestions.push(icon);
                }
            }
        });
        
        // Limiter à 6 suggestions maximum
        return suggestions.slice(0, 6);
    }
};

// Export pour utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        FontAwesomeIconDatabase,
        IconSuggestions
    };
}
