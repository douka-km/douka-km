# 🔄 Gestionnaire de Base de Données DOUKA KM

Ce guide vous explique comment basculer entre la base de données SQLite locale et la base PostgreSQL de Render.com.

## 🚀 Démarrage Rapide

### 1. Sauvegarde avant basculement
```bash
python backup_sqlite.py
```
Choisir l'option 1 pour créer une sauvegarde de votre base SQLite actuelle.

### 2. Basculement vers PostgreSQL Render
```bash
python switch_database.py
```
- Choisir l'option 2
- Coller votre URL PostgreSQL de Render

### 3. Redémarrer l'application
```bash
python app_final_with_db.py
```

## 📋 Étapes détaillées

### Récupérer l'URL PostgreSQL de Render

1. Aller sur [Render Dashboard](https://dashboard.render.com)
2. Se connecter à votre compte
3. Sélectionner votre service PostgreSQL
4. Copier l'**External Database URL** ou **Connection String**
   
   Format : `postgresql://username:password@hostname:port/database_name`

### Utilisation des scripts

#### `switch_database.py` - Gestionnaire principal
- **Option 1** : Basculer vers SQLite LOCAL (développement)
- **Option 2** : Basculer vers PostgreSQL RENDER (production)
- **Option 3** : Afficher la configuration actuelle

#### `backup_sqlite.py` - Gestionnaire de sauvegardes
- **Option 1** : Créer une sauvegarde avec timestamp
- **Option 2** : Lister toutes les sauvegardes disponibles

## ⚠️ Points Importants

### Sécurité
- ✅ Le fichier `.env` est exclu de Git (contient les URLs de base de données)
- ✅ Les sauvegardes SQLite sont exclues de Git
- ✅ Les mots de passe sont masqués dans l'affichage

### Différences SQLite vs PostgreSQL
- **SQLite** : Parfait pour le développement, données locales
- **PostgreSQL** : Base de production sur Render, données partagées

### Synchronisation des données
⚠️ **ATTENTION** : Les données entre SQLite et PostgreSQL ne sont PAS synchronisées automatiquement.

- Si vous ajoutez des données en local (SQLite), elles ne seront pas sur Render
- Si vous modifiez des données sur Render (PostgreSQL), elles ne seront pas en local

## 🔧 Dépendances

Les dépendances suivantes sont requises :
```bash
pip install psycopg2-binary  # Driver PostgreSQL
pip install python-dotenv   # Variables d'environnement
```

## 📁 Structure des fichiers

```
├── .env                    # Configuration actuelle (ignoré par Git)
├── .env.local             # Template de configuration
├── switch_database.py     # Script de basculement
├── backup_sqlite.py       # Script de sauvegarde
├── backups/               # Dossier des sauvegardes (ignoré par Git)
│   └── douka_km_backup_YYYYMMDD_HHMMSS.db
└── douka_km.db           # Base SQLite locale
```

## 🔄 Workflow recommandé

### Développement Local
1. Utiliser SQLite pour les tests et développement
2. Créer des sauvegardes régulières

### Tests en Production
1. Sauvegarder SQLite avant basculement
2. Basculer vers PostgreSQL Render
3. Tester les fonctionnalités
4. Revenir à SQLite si nécessaire

### Déploiement
1. Pousser le code vers GitHub
2. Render utilise automatiquement PostgreSQL en production

## 🆘 Dépannage

### Erreur de connexion PostgreSQL
- Vérifier que l'URL contient le bon username/password
- S'assurer que le serveur PostgreSQL de Render est accessible
- Vérifier que `psycopg2-binary` est installé

### Données manquantes après basculement
- Normal ! SQLite et PostgreSQL sont séparées
- Utiliser les sauvegardes pour revenir à l'état précédent

### Application ne démarre pas
- Vérifier le fichier `.env`
- Vérifier les logs d'erreur dans le terminal
- Essayer de revenir à SQLite
