import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# Configuration pour différents fournisseurs d'email
EMAIL_PROVIDERS = {
    'gmail': {
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': 587,
        'USE_TLS': True,
        'USE_SSL': False,
    },
    'outlook': {
        'SMTP_SERVER': 'smtp-mail.outlook.com',
        'SMTP_PORT': 587,
        'USE_TLS': True,
        'USE_SSL': False,
    },
    'yahoo': {
        'SMTP_SERVER': 'smtp.mail.yahoo.com',
        'SMTP_PORT': 587,
        'USE_TLS': True,
        'USE_SSL': False,
    }
}

# Configuration actuelle avec votre email
CURRENT_EMAIL_CONFIG = {
    'PROVIDER': 'gmail',
    'FROM_EMAIL': 'ledouka.km@gmail.com',
    'FROM_NAME': 'DOUKA-KM',
    'USERNAME': 'ledouka.km@gmail.com',
    'PASSWORD': 'eiwk xhhy qhhf vmjp',  # Votre mot de passe d'application
    'VERIFICATION_URL_BASE': os.environ.get('VERIFICATION_URL_BASE') or ('https://doukakm.com' if os.environ.get('RENDER') else 'http://localhost:5002')
}

# Debug: afficher la configuration au chargement
print(f"🔧 EMAIL_CONFIG DEBUG:")
print(f"   - RENDER env: {os.environ.get('RENDER')}")
print(f"   - VERIFICATION_URL_BASE env: {os.environ.get('VERIFICATION_URL_BASE')}")
print(f"   - Final URL: {CURRENT_EMAIL_CONFIG['VERIFICATION_URL_BASE']}")

def send_email(to_email, subject, html_content, text_content=None):
    """
    Envoie un email avec le contenu HTML et texte
    """
    try:
        provider_config = EMAIL_PROVIDERS[CURRENT_EMAIL_CONFIG['PROVIDER']]
        
        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{CURRENT_EMAIL_CONFIG['FROM_NAME']} <{CURRENT_EMAIL_CONFIG['FROM_EMAIL']}>"
        msg['To'] = to_email
        
        # Ajouter le contenu texte si fourni
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
        
        # Ajouter le contenu HTML
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Configurer le serveur SMTP
        server = smtplib.SMTP(provider_config['SMTP_SERVER'], provider_config['SMTP_PORT'])
        
        if provider_config['USE_TLS']:
            server.starttls()
        
        # Se connecter
        server.login(CURRENT_EMAIL_CONFIG['USERNAME'], CURRENT_EMAIL_CONFIG['PASSWORD'])
        
        # Envoyer l'email
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email envoyé avec succès à {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email à {to_email}: {str(e)}")
        return False

def test_email_connection():
    """
    Teste la connexion email
    """
    try:
        provider_config = EMAIL_PROVIDERS[CURRENT_EMAIL_CONFIG['PROVIDER']]
        server = smtplib.SMTP(provider_config['SMTP_SERVER'], provider_config['SMTP_PORT'])
        
        if provider_config['USE_TLS']:
            server.starttls()
        
        server.login(CURRENT_EMAIL_CONFIG['USERNAME'], CURRENT_EMAIL_CONFIG['PASSWORD'])
        server.quit()
        
        print("✅ Connexion email réussie!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de connexion email: {str(e)}")
        return False