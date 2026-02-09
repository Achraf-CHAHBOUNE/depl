# 🚀 Guide de Déploiement Google Cloud Platform - DGI Invoice Automation

## 💰 Coût: ~$10-15/mois (Couvert par votre $300 crédit = 20+ mois gratuits!)

---

## ✅ **Pourquoi Google Cloud Platform?**

- ✅ **$300 crédit gratuit** (90 jours)
- ✅ **Infrastructure mondiale** de Google
- ✅ **Très performant** et fiable
- ✅ **Support Docker natif**
- ✅ **Vous avez déjà le crédit!**

---

## 🎯 **Déploiement Complet (15 minutes)**

### **Étape 1: Activer Google Cloud Platform (3 min)**

1. **Allez sur:** https://console.cloud.google.com

2. **Connectez-vous** avec votre compte Google

3. **Activez votre crédit gratuit:**
   - Cliquez sur "Activer" ou "Try for free"
   - Entrez vos informations de facturation (carte bancaire requise mais pas débitée)
   - Acceptez les conditions
   - **Vous recevez $300 de crédit!**

4. **Créez un nouveau projet:**
   - Nom: `dgi-invoice-automation`
   - Cliquez "Create"

---

### **Étape 2: Créer une VM Compute Engine (5 min)**

1. **Dans le menu de gauche:**
   - Cliquez sur **"Compute Engine"** → **"VM instances"**

2. **Cliquez "Create Instance"**

3. **Configuration de la VM:**

   **Nom:** `dgi-invoice-demo`

   **Région:** `europe-west1` (Belgique - proche du Maroc)
   
   **Zone:** `europe-west1-b`

   **Machine configuration:**
   - **Series:** E2
   - **Machine type:** `e2-medium` (2 vCPU, 4GB RAM)
   - **Coût:** ~$24/mois (couvert par crédit)

   **Boot disk:**
   - Cliquez "Change"
   - **Operating system:** Ubuntu
   - **Version:** Ubuntu 22.04 LTS
   - **Boot disk type:** Standard persistent disk
   - **Size:** 30 GB
   - Cliquez "Select"

   **Firewall:**
   - ✅ Cochez "Allow HTTP traffic"
   - ✅ Cochez "Allow HTTPS traffic"

4. **Cliquez "Create"**

5. **Attendez 1-2 minutes** - votre VM sera prête

---

### **Étape 3: Configurer le Firewall (2 min)**

**Important:** Ouvrir les ports pour votre application.

1. **Dans le menu de gauche:**
   - Cliquez **"VPC network"** → **"Firewall"**

2. **Cliquez "Create Firewall Rule"**

3. **Configuration:**
   - **Name:** `allow-invoice-app`
   - **Direction:** Ingress
   - **Targets:** All instances in the network
   - **Source IP ranges:** `0.0.0.0/0`
   - **Protocols and ports:**
     - ✅ Specified protocols and ports
     - **tcp:** `3000,8000,8001,8002,8004`

4. **Cliquez "Create"**

---

### **Étape 4: Se Connecter à la VM (1 min)**

1. **Retournez à "Compute Engine" → "VM instances"**

2. **Trouvez votre VM** `dgi-invoice-demo`

3. **Cliquez sur "SSH"** (bouton dans la colonne "Connect")

4. **Une fenêtre de terminal s'ouvre** dans votre navigateur

---

### **Étape 5: Déployer l'Application (5 min - Automatique)**

**Dans le terminal SSH, copiez-collez cette commande:**

```bash
curl -fsSL https://raw.githubusercontent.com/Achraf-CHAHBOUNE/invoice-intelligent/main/deploy-gcp.sh | bash
```

**Le script va automatiquement:**
- ✅ Installer Docker et Docker Compose
- ✅ Cloner votre code depuis GitHub
- ✅ Démarrer tous les services (frontend, backend, database)
- ✅ Configurer tout automatiquement

**Attendez 5 minutes** ☕

---

### **Étape 6: Obtenir l'IP Publique (1 min)**

1. **Retournez à "Compute Engine" → "VM instances"**

2. **Copiez l'adresse IP externe** de votre VM (colonne "External IP")
   - Exemple: `34.77.xxx.xxx`

---

### **Étape 7: Accéder à Votre Application**

**Ouvrez dans votre navigateur:**

```
http://VOTRE_IP_EXTERNE:3000
```

**Login:**
- Email: `demo@dgi.ma`
- Password: `demo123`

---

## 🎉 **C'est Prêt!**

Votre application est maintenant hébergée sur Google Cloud et accessible publiquement!

**Partagez cette URL avec vos clients:**
```
http://VOTRE_IP_EXTERNE:3000
```

---

## 🌐 **Ajouter un Nom de Domaine (Optionnel)**

### **Si vous avez un domaine (ex: demo.votresite.com):**

1. **Réserver une IP statique (pour qu'elle ne change pas):**
   - Menu: **"VPC network"** → **"IP addresses"**
   - Cliquez **"Reserve External Static Address"**
   - **Name:** `invoice-app-ip`
   - **Attached to:** Sélectionnez votre VM
   - Cliquez **"Reserve"**

2. **Dans votre DNS provider:**
   - Créez un enregistrement A: `demo` → `VOTRE_IP_STATIQUE`

3. **Installer Nginx + SSL (HTTPS gratuit):**

Connectez-vous en SSH et exécutez:

```bash
# Installer Nginx et Certbot
sudo apt install nginx certbot python3-certbot-nginx -y

# Créer configuration Nginx
sudo nano /etc/nginx/sites-available/invoice-automation
```

Collez cette configuration:

```nginx
server {
    listen 80;
    server_name demo.votresite.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activer la configuration
sudo ln -s /etc/nginx/sites-available/invoice-automation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Installer SSL gratuit (HTTPS)
sudo certbot --nginx -d demo.votresite.com

# Renouvellement automatique SSL
sudo systemctl enable certbot.timer
```

**Maintenant accessible sur:** `https://demo.votresite.com` 🎉

---

## 🔧 **Commandes Utiles**

### **Se connecter en SSH:**
```bash
gcloud compute ssh dgi-invoice-demo --zone=europe-west1-b
```

### **Voir les logs:**
```bash
cd /opt/invoice-automation
docker-compose logs -f
```

### **Redémarrer l'application:**
```bash
cd /opt/invoice-automation
docker-compose restart
```

### **Arrêter l'application:**
```bash
cd /opt/invoice-automation
docker-compose down
```

### **Mettre à jour le code:**
```bash
cd /opt/invoice-automation
git pull
docker-compose up -d --build
```

### **Voir l'état des services:**
```bash
cd /opt/invoice-automation
docker-compose ps
```

---

## 💰 **Estimation des Coûts**

### **Configuration Recommandée:**
- **VM e2-medium:** ~$24/mois
- **Stockage 30GB:** ~$2/mois
- **Trafic réseau:** ~$1-2/mois
- **Total:** ~$27/mois

### **Avec votre crédit $300:**
- **11+ mois gratuits!**
- Parfait pour démos et premiers clients

### **Optimisation (si besoin):**
- **VM e2-small** (1 vCPU, 2GB): ~$13/mois = 23 mois gratuits
- **Arrêter la VM** quand pas utilisée: Économisez 100%

---

## 📊 **Surveillance des Coûts**

1. **Menu:** **"Billing"** → **"Cost table"**
2. Voyez votre consommation en temps réel
3. Configurez des alertes de budget

---

## 🔒 **Sécurité Importante**

### **1. Changer les mots de passe par défaut:**

```bash
cd /opt/invoice-automation
nano docker-compose.yml
# Changez POSTGRES_PASSWORD
docker-compose up -d --force-recreate postgres
```

### **2. Configurer un pare-feu plus strict:**

Dans GCP Firewall, limitez l'accès SSH:
- Source IP ranges: `VOTRE_IP_FIXE/32` (au lieu de `0.0.0.0/0`)

### **3. Activer les backups automatiques:**

```bash
# Créer un snapshot du disque chaque jour
gcloud compute disks snapshot dgi-invoice-demo \
    --zone=europe-west1-b \
    --snapshot-names=invoice-backup-$(date +%Y%m%d)
```

---

## 🚀 **Optimisations Avancées (Optionnel)**

### **1. Utiliser Cloud SQL au lieu de PostgreSQL local:**
- Plus fiable
- Backups automatiques
- ~$10/mois supplémentaire

### **2. Utiliser Cloud Storage pour les uploads:**
- Stockage illimité
- ~$0.02/GB/mois

### **3. Utiliser Load Balancer + Auto-scaling:**
- Pour production avec beaucoup de trafic
- ~$20/mois supplémentaire

---

## ⚠️ **Arrêter la VM (Économiser le Crédit)**

**Si vous n'utilisez pas l'app temporairement:**

1. **Menu:** **"Compute Engine"** → **"VM instances"**
2. **Sélectionnez** votre VM
3. **Cliquez** "Stop"
4. **Coût pendant l'arrêt:** ~$2/mois (stockage seulement)

**Pour redémarrer:**
1. Cliquez "Start"
2. Attendez 1 minute
3. L'application redémarre automatiquement

---

## 📞 **Support et Dépannage**

### **Problème: Services ne démarrent pas**
```bash
cd /opt/invoice-automation
docker-compose logs -f
# Vérifiez les erreurs
```

### **Problème: Impossible d'accéder à l'IP**
- Vérifiez que le firewall est configuré (Étape 3)
- Vérifiez que les services tournent: `docker-compose ps`

### **Problème: Manque de mémoire**
- Augmentez la taille de la VM à `e2-standard-2` (8GB RAM)

---

## 🎯 **Résumé: Pourquoi Google Cloud?**

| Avantage | Détail |
|----------|--------|
| **Crédit gratuit** | $300 = 11+ mois gratuits |
| **Infrastructure** | Même infra que Gmail, YouTube |
| **Performance** | Très rapide, fiable |
| **Scalabilité** | Facile d'augmenter les ressources |
| **Support** | Documentation excellente |
| **Vous l'avez déjà!** | Crédit activé ✅ |

---

## ✅ **Checklist de Déploiement**

- [ ] Activer Google Cloud Platform
- [ ] Créer projet `dgi-invoice-automation`
- [ ] Créer VM `e2-medium` Ubuntu 22.04
- [ ] Configurer firewall (ports 3000, 8000)
- [ ] Se connecter en SSH
- [ ] Exécuter script de déploiement
- [ ] Tester l'application sur `http://IP:3000`
- [ ] (Optionnel) Configurer domaine + SSL

---

**Temps total: 15 minutes**
**Coût: GRATUIT (couvert par crédit $300)**

**Bonne chance avec votre démo! 🚀**
