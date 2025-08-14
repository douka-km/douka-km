# DOUKA KM - E-commerce Platform

## 🚀 Déploiement sur Render.com

### Prérequis
- Compte GitHub avec le code du projet
- Compte sur [Render.com](https://render.com)

### Instructions de déploiement

1. **Préparer le repository GitHub**
   ```bash
   git add .
   git commit -m "Prêt pour déploiement Render.com"
   git push origin main
   ```

2. **Créer un Web Service sur Render**
   - Aller sur https://render.com/dashboard
   - Cliquer sur "New +" → "Web Service"
   - Connecter votre repository GitHub
   - Sélectionner la branche `main`

3. **Configuration du service**
   - **Name**: `douka-km`
   - **Environment**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     python init_render.py && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
     ```

4. **Variables d'environnement**
   Ajouter ces variables dans l'onglet "Environment":
   ```
   RENDER=1
   FLASK_ENV=production
   SECRET_KEY=(généré automatiquement par Render)
   ```

5. **Déploiement**
   - Cliquer sur "Create Web Service"
   - Attendre la fin du build (5-10 minutes)
   - L'URL de votre application sera affichée

### Test local avant déploiement

Exécuter le script de test :
```bash
python test_deployment.py
```

### Structure du projet

```
├── app.py                 # Point d'entrée pour Render
├── app_final_with_db.py   # Application principale Flask
├── models.py              # Modèles SQLAlchemy
├── db_helpers.py          # Fonctions d'aide pour la DB
├── email_config.py        # Configuration email
├── requirements.txt       # Dépendances Python
├── Procfile              # Configuration Heroku/Render
├── render.yaml           # Configuration Render (optionnel)
├── runtime.txt           # Version Python
├── init_render.py        # Script d'initialisation
├── test_deployment.py    # Test de déploiement
├── .env.example          # Variables d'environnement exemple
├── static/               # Fichiers statiques (CSS, JS, images)
└── templates/            # Templates Jinja2
```

### Fonctionnalités principales

- ✅ Système d'authentification multi-rôles (Admin, Merchant, User)
- ✅ Gestion des produits avec catégories
- ✅ Panier et commandes
- ✅ Dashboard administrateur
- ✅ Système de suspension/réactivation des marchands
- ✅ Gestion des stocks
- ✅ Interface responsive Bootstrap

### Base de données

- **Développement**: SQLite (locale)
- **Production**: SQLite avec disque persistant Render

### Support

En cas de problème lors du déploiement :
1. Vérifier les logs de build sur Render
2. S'assurer que toutes les dépendances sont dans `requirements.txt`
3. Vérifier que les variables d'environnement sont correctement définies

### URLs importantes après déploiement

- `/` - Page d'accueil
- `/admin/login` - Connexion administrateur  
- `/merchant/login` - Connexion marchand
- `/user/login` - Connexion utilisateur

---

**Développé avec Flask + SQLAlchemy + Bootstrap**

# douka-km
