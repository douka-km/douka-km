// Assurer que les liens du dropdown fonctionnent correctement
document.addEventListener('DOMContentLoaded', function() {
    // Sélectionner tous les éléments du dropdown qui sont des liens
    const dropdownLinks = document.querySelectorAll('.dropdown-menu .dropdown-item');
    
    // Ajouter un événement click à chaque lien
    dropdownLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Empêcher que l'événement soit capturé par d'autres gestionnaires
            e.stopPropagation();
            // Si le lien a un attribut href, naviguer vers cet URL
            if (this.getAttribute('href') && this.getAttribute('href') !== '#') {
                window.location.href = this.getAttribute('href');
            }
        });
    });
});
