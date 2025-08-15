#!/usr/bin/env python3
"""
Script simple pour ajouter le paramètre logo_url via une route admin
"""

def add_logo_setting_to_app(app, db, SiteSettings):
    """Fonction pour ajouter le paramètre logo_url à l'application"""
    
    @app.route('/admin/fix-logo-settings', methods=['GET'])
    def fix_logo_settings():
        """Route temporaire pour corriger les paramètres du logo"""
        try:
            # Vérifier si le paramètre logo_url existe déjà
            existing_logo = SiteSettings.query.filter_by(key='logo_url').first()
            
            if existing_logo:
                return f"""
                <h2>✅ Logo Settings Status</h2>
                <p><strong>Logo URL existe déjà:</strong> {existing_logo.value}</p>
                <p><strong>Description:</strong> {existing_logo.description or 'N/A'}</p>
                <p><strong>Créé le:</strong> {existing_logo.created_at}</p>
                <p><strong>Modifié le:</strong> {existing_logo.updated_at}</p>
                <br>
                <a href="/admin/dashboard">← Retour au dashboard admin</a>
                """
            
            # Créer le paramètre logo_url par défaut
            logo_setting = SiteSettings(
                key='logo_url',
                value='/static/img/logo.png',
                description='URL du logo principal du site'
            )
            
            # Ajouter également le logo_alt_text
            logo_alt_setting = SiteSettings.query.filter_by(key='logo_alt_text').first()
            if not logo_alt_setting:
                logo_alt_setting = SiteSettings(
                    key='logo_alt_text',
                    value='DOUKA KM Logo',
                    description='Texte alternatif pour le logo'
                )
                db.session.add(logo_alt_setting)
            
            db.session.add(logo_setting)
            db.session.commit()
            
            return """
            <h2>✅ Logo Settings Fixed!</h2>
            <p><strong>Logo URL ajouté:</strong> """ + logo_setting.value + """</p>
            <p><strong>Description:</strong> """ + logo_setting.description + """</p>
            <p><strong>Logo Alt Text:</strong> """ + logo_alt_setting.value + """</p>
            <br>
            <p>🔄 Le logo devrait maintenant apparaître sur le site.</p>
            <p>⚠️ Supprimez cette route après utilisation pour des raisons de sécurité.</p>
            <br>
            <a href="/admin/dashboard">← Retour au dashboard admin</a>
            <script>
                setTimeout(function() {
                    window.location.href = '/admin/dashboard';
                }, 5000);
            </script>
            """
            
        except Exception as e:
            db.session.rollback()
            return f"""
            <h2>❌ Erreur lors de la correction</h2>
            <p><strong>Erreur:</strong> {str(e)}</p>
            <br>
            <a href="/admin/dashboard">← Retour au dashboard admin</a>
            """
    
    @app.route('/admin/check-logo-settings', methods=['GET'])
    def check_logo_settings():
        """Route pour vérifier l'état des paramètres du logo"""
        try:
            # Récupérer tous les paramètres
            all_settings = SiteSettings.query.all()
            settings_html = ""
            
            if all_settings:
                settings_html = "<ul>"
                for setting in all_settings:
                    settings_html += f"<li><strong>{setting.key}:</strong> {setting.value}</li>"
                settings_html += "</ul>"
            else:
                settings_html = "<p>Aucun paramètre trouvé dans la base de données</p>"
            
            # Vérifier spécifiquement le logo
            logo_setting = SiteSettings.query.filter_by(key='logo_url').first()
            logo_status = f"Logo URL: {logo_setting.value}" if logo_setting else "❌ Logo URL non trouvé"
            
            return f"""
            <h2>🔧 Logo Settings Status</h2>
            <p><strong>Status:</strong> {logo_status}</p>
            <p><strong>Nombre de paramètres:</strong> {len(all_settings)}</p>
            <br>
            <h3>Tous les paramètres:</h3>
            {settings_html}
            <br>
            <a href="/admin/dashboard">← Retour au dashboard admin</a>
            """
            
        except Exception as e:
            return f"""
            <h2>❌ Erreur lors de la vérification</h2>
            <p><strong>Erreur:</strong> {str(e)}</p>
            <br>
            <a href="/admin/dashboard">← Retour au dashboard admin</a>
            """

# Instructions d'utilisation
USAGE_INSTRUCTIONS = """
Pour utiliser ces routes, ajoutez ces lignes dans votre app_final_with_db.py :

# Importer la fonction
from fix_logo_route import add_logo_setting_to_app

# Après avoir créé l'app et configuré la DB, ajouter les routes
add_logo_setting_to_app(app, db, SiteSettings)

Ensuite, visitez :
- /admin/check-logo-settings pour vérifier l'état
- /admin/fix-logo-settings pour corriger le problème

⚠️ Supprimez ces routes après utilisation pour la sécurité !
"""

if __name__ == '__main__':
    print(USAGE_INSTRUCTIONS)
