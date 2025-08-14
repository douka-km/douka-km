#!/bin/bash
set -e

echo "🔧 Configuration Python pour Render..."

# Vérifier la version Python
python --version
echo "📍 Utilisation de Python $(python --version)"

# Forcer l'utilisation de pip récent
echo "📦 Installation des dépendances avec versions stables..."
pip install --upgrade pip

# Installer les versions compatibles manuellement
pip install Flask==2.3.3
pip install Flask-SQLAlchemy==2.5.1
pip install SQLAlchemy==1.4.53
pip install Werkzeug==2.3.7
pip install Jinja2==3.1.2
pip install MarkupSafe==2.1.3
pip install itsdangerous==2.1.2
pip install click==8.1.7
pip install gunicorn==21.2.0
pip install psycopg2-binary==2.9.9
pip install python-dotenv==1.0.0

echo "✅ Build terminé avec versions stables!"
