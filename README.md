# DGI Invoice Compliance System

Système automatisé de conformité fiscale pour la DGI (Direction Générale des Impôts) au Maroc.

## 🚀 Fonctionnalités

- **OCR Intelligent**: Extraction automatique des données de factures et relevés bancaires
- **Matching Automatique**: Rapprochement intelligent factures-paiements
- **Calcul des Pénalités**: Calcul automatique selon la loi 69-21 (taux de base 2.25% + 0.85%/mois)
- **Validation Manuelle**: Interface de révision et correction
- **Export DGI**: Génération de déclarations conformes

## 📋 Prérequis

- Docker & Docker Compose
- Clé API Anthropic (Claude)
- Credentials Google Cloud (pour OCR)

## 🔧 Installation Locale

1. **Cloner le repository**
```bash
git clone <your-repo-url>
cd invoice-automation
```

2. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos clés API
```

3. **Ajouter les credentials Google Cloud**
```bash
# Placer votre fichier google-credentials.json dans ./credentials/
```

4. **Démarrer les services**
```bash
# Windows
.\scripts\start.ps1

# Linux/Mac
./scripts/start.sh
```

5. **Accéder à l'application**
- Frontend: http://localhost:8080
- API Gateway: http://localhost:8000
- Credentials: demo@dgi.ma / demo123

## 🌐 Déploiement GCP

### Prérequis GCP
- VM Ubuntu 20.04+ avec au moins 4GB RAM
- Docker et Docker Compose installés
- Ports ouverts: 80, 443, 8000, 8080

### Déploiement Automatique
```bash
# Sur votre VM GCP
git clone <your-repo-url>
cd invoice-automation
chmod +x deploy-gcp.sh
./deploy-gcp.sh
```

### Configuration DNS (Optionnel)
Pointer votre domaine vers l'IP de la VM pour accès HTTPS.

## 📁 Structure du Projet

```
invoice-automation/
├── backend/
│   ├── api-gateway/          # Point d'entrée API
│   ├── orchestrator-service/ # Orchestration des workflows
│   ├── intelligence-service/ # Extraction & règles métier
│   └── ocr-service/          # OCR Google Vision
├── frontend/                 # Interface React + TypeScript
├── shared/                   # Volumes partagés
├── scripts/                  # Scripts de démarrage
└── docker-compose.yml        # Configuration Docker
```

## 🔑 Variables d'Environnement

### Obligatoires
- `ANTHROPIC_API_KEY`: Clé API Claude
- `GOOGLE_APPLICATION_CREDENTIALS`: Chemin vers credentials GCP

### Optionnelles
- `PENALTY_BASE_RATE`: Taux de pénalité de base (défaut: 2.25%)
- `PENALTY_MONTHLY_INCREMENT`: Incrément mensuel (défaut: 0.85%)
- `JWT_SECRET_KEY`: Secret pour JWT (généré auto)

## 🛠️ Développement

### Backend
```bash
cd backend/<service-name>
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📊 Architecture

- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Backend**: Python FastAPI (microservices)
- **Database**: PostgreSQL
- **OCR**: Google Cloud Vision API
- **AI**: Anthropic Claude (extraction structurée)

## 🔒 Sécurité

- Authentification JWT
- Variables d'environnement pour secrets
- CORS configuré
- Validation des données côté backend

## 📝 License

Propriétaire - Tous droits réservés

## 👥 Support

Pour toute question ou problème, contactez l'équipe de développement.
