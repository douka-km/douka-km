#!/bin/bash
set -e

echo "🔧 Configuration Python pour Render..."

# Vérifier la version Python
python --version
echo "📍 Utilisation de Python $(python --version)"

# Forcer l'utilisation de pip récent
echo "📦 Installation des dépendances avec versions stables..."
pip install --upgrade pip

# Installer les dépendances Flask/SQLAlchemy d'abord
echo "🔧 Installation Flask et SQLAlchemy..."
pip install Flask==2.3.3
pip install Flask-SQLAlchemy==2.5.1
pip install SQLAlchemy==1.4.53
pip install Werkzeug==2.3.7
pip install Jinja2==3.1.2
pip install MarkupSafe==2.1.3
pip install itsdangerous==2.1.2
pip install click==8.1.7
pip install gunicorn==21.2.0
pip install python-dotenv==1.0.0

# Installer psycopg avec stratégie de fallback
echo "🔧 Installation PostgreSQL adapter..."

# Tentative 1 : psycopg3 (recommandé pour Python 3.13)
if pip install --no-cache-dir "psycopg[binary]==3.1.19"; then
    echo "✅ psycopg3 installé avec succès"
# Tentative 2 : psycopg2-binary version récente
elif pip install --no-cache-dir --force-reinstall psycopg2-binary==2.9.10; then
    echo "✅ psycopg2-binary installé avec succès"
# Tentative 3 : compilation psycopg2 depuis les sources
else
    echo "⚡ Installation depuis les sources..."
    apt-get update && apt-get install -y libpq-dev gcc python3-dev
    pip install psycopg2==2.9.10
    echo "✅ psycopg2 compilé avec succès"
fi

echo "✅ Build terminé avec versions stables!"
