# Guide de Déploiement - Application E-Commerce Flask sur Azure

## 📋 Table des Matières
1. [Prérequis](#prérequis)
2. [Préparation de l'application](#préparation-de-lapplication)
3. [Création des ressources Azure](#création-des-ressources-azure)
4. [Déploiement](#déploiement)
5. [Configuration et tests](#configuration-et-tests)

---

## 🔧 Prérequis

Avant de commencer, assurez-vous d'avoir :

- ✅ Un **compte Azure** actif ([créer un compte gratuit](https://azure.microsoft.com/free/))
- ✅ **Azure CLI** installé ([Installer Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli))
- ✅ **Git** installé
- ✅ **Python 3.7+** installé localement
- ✅ Les clés API **Stripe** pour les paiements
- ✅ Une base de données configurée (SQLite local ou Azure Database for PostgreSQL/MySQL)

---

## 📦 Préparation de l'Application

### Créer un fichier `.env` pour Azure

Créez un fichier `.env` à la racine du projet avec vos variables d'environnement :

```env
# Configuration Flask
FLASK_ENV=production
FLASK_APP=app.py
DEBUG=False

# Clés Stripe
STRIPE_PUBLIC_KEY=pk_test_votre_clé_publique
STRIPE_SECRET_KEY=sk_test_votre_clé_secrète

# Email (si utilisé)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=votre_email@gmail.com
MAIL_PASSWORD=votre_mot_de_passe

# Base de données (voir Étape 3 pour Azure)
DATABASE_URL=postgresql://user:password@server.postgres.database.azure.com/dbname

# Secret Flask
SECRET_KEY=votre_clé_secrète_très_longue_et_aléatoire
```

---

## ☁️ Création des Ressources Azure

### Déploiement avec Azure App Service

#### Étape 1 : Se connecter à Azure

```bash
az login
```

#### Étape 2 : Créer un groupe de ressources

```bash
az group create --name rg-ecommerce --location eastus
```

#### Étape 3 : Créer un plan App Service

```bash
az appservice plan create \
  --name plan-ecommerce \
  --resource-group rg-ecommerce \
  --sku B1 \
  --is-linux
```

#### Étape 4 : Créer l'application Web

```bash
az webapp create \
  --resource-group rg-ecommerce \
  --plan plan-ecommerce \
  --name app-ecommerce-fnuc \
  --runtime "python|3.9"
```

---

## 🚀 Déploiement

### Option 1 : Via ZIP (App Service)

#### Étape 1 : Préparer le projet pour le déploiement

```bash
# Créer un dossier de déploiement
mkdir deploy
cp -r app/ deploy/
cp app.py requirements.txt startup.sh .gitignore deploy/
cd deploy
```

#### Étape 2 : Configurer les variables d'environnement

```bash
az webapp config appsettings set \
  --resource-group rg-ecommerce \
  --name app-ecommerce-fnuc \
  --settings \
    FLASK_ENV=production \
    DEBUG=False \
    STRIPE_PUBLIC_KEY="votre_clé_publique" \
    STRIPE_SECRET_KEY="votre_clé_secrète" \
    SECRET_KEY="votre_clé_secrète_très_longue" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

#### Étape 3 : Configurer le démarrage de l'application

```bash
az webapp config set \
  --resource-group rg-ecommerce \
  --name app-ecommerce-fnuc \
  --startup-file "startup.sh"
```

#### Étape 4 : Déployer le code

Méthode A - Via Git :
```bash
az webapp deployment source config-local-git \
  --resource-group rg-ecommerce \
  --name app-ecommerce-fnuc

# Récupérez l'URL Git, puis ajoutez-la comme remote
git remote add azure <url-git-reçue>
git push azure main
```

Méthode B - Via ZIP :
```bash
zip -r deploy.zip deploy/*
az webapp deployment source config-zip \
  --resource-group rg-ecommerce \
  --name app-ecommerce-fnuc \
  --src-path deploy.zip
```

---

## ⚙️ Configuration et Tests

### Étape 1 : Vérifier l'état du déploiement

```bash
# Pour App Service
az webapp show \
  --resource-group rg-ecommerce \
  --name app-ecommerce-fnuc

# Pour Container Instances
az container show \
  --resource-group rg-ecommerce \
  --name app-ecommerce
```

### Étape 2 : Consulter les logs

```bash
# Pour App Service
az webapp log tail \
  --resource-group rg-ecommerce \
  --name app-ecommerce-fnuc

# Pour Container Instances
az container logs \
  --resource-group rg-ecommerce \
  --name app-ecommerce
```

### Étape 3 : Tester l'application

```bash
# Récupérez l'URL publique
az webapp show --resource-group rg-ecommerce --name app-ecommerce-fnuc --query defaultHostName

# Ouvrez un navigateur et accédez à : https://<nom-app>.azurewebsites.net
```

### Étape 4 : Configurer un domaine personnalisé (Optionnel)

```bash
# Ajouter un domaine personnalisé
az webapp config hostname add \
  --resource-group rg-ecommerce \
  --webapp-name app-ecommerce-fnuc \
  --hostname votre-domaine.com
```

---

## 🗄️ Base de Données

###  Utiliser SQLite avec Azure Storage

```bash
# Créer un compte de stockage
az storage account create \
  --resource-group rg-ecommerce \
  --name storageaccountecommerce \
  --location eastus

# Créer un partage de fichiers
az storage share create \
  --account-name storageaccountecommerce \
  --name app-storage
```

---

## 🔒 Sécurité

### Points importants à vérifier

1. **SSL/TLS** : Configuré automatiquement par Azure
   ```bash
   az webapp update \
     --resource-group rg-ecommerce \
     --name app-ecommerce-fnuc \
     --https-only true
   ```

2. **Firewall** : Limiter l'accès à la base de données
   ```bash
   az postgres server firewall-rule create \
     --resource-group rg-ecommerce \
     --server-name ecommerce-db-server \
     --name AllowAzureServices \
     --start-ip-address 0.0.0.0 \
     --end-ip-address 0.0.0.0
   ```

3. **Variables sensibles** : Utilisez Azure Key Vault
   ```bash
   az keyvault create \
     --resource-group rg-ecommerce \
     --name kv-ecommerce
   ```

---

## 📊 Monitoring et Logs

### Activer l'Application Insights

```bash
az monitor app-insights component create \
  --app app-ecommerce-insights \
  --location eastus \
  --resource-group rg-ecommerce

# Configurer l'App Service
az webapp config appsettings set \
  --resource-group rg-ecommerce \
  --name app-ecommerce-fnuc \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="votre_clé_instrumentation"
```

---


## 🧹 Nettoyage des ressources (Important pour éviter les coûts)

```bash
# Supprimer tout le groupe de ressources
az group delete --name rg-ecommerce --yes --no-wait
```

---

## 📚 Ressources supplémentaires

- [Documentation Azure App Service Python](https://learn.microsoft.com/azure/app-service/quickstart-python)
- [Guide Flask sur Azure](https://learn.microsoft.com/training/modules/deploy-flask-app-azure-app-service/)
- [Azure CLI Reference](https://learn.microsoft.com/cli/azure/reference-index)
- [Stripe Documentation](https://stripe.com/docs)

---

## ✅ Checklist de déploiement

- [ ] Fichier `.env` créé avec toutes les variables
- [ ] `requirements.txt` à jour
- [ ] Compte Azure créé et Azure CLI configuré
- [ ] Groupe de ressources créé
- [ ] App Service/Container créé et configuré
- [ ] Variables d'environnement définies
- [ ] Base de données configurée
- [ ] Domaine personnalisé configuré
- [ ] SSL/TLS activé
- [ ] Tests effectués
- [ ] Logs vérifié
