# DGI Invoice Compliance System

Système automatisé de conformité fiscale pour la DGI (Direction Générale des Impôts) au Maroc.

## 🚀 Quick Deploy to GCP

**One command deployment:**

```bash
curl -sSL https://raw.githubusercontent.com/Achraf-CHAHBOUNE/depl/main/deploy-gcp.sh | bash
```

The script will:
- ✅ Install Docker & Docker Compose
- ✅ Clone repository
- ✅ Ask for your Anthropic API key
- ✅ Ask for Google Cloud credentials
- ✅ Configure everything automatically
- ✅ Start the application

**After ~10 minutes, access at:**
- Frontend: `http://YOUR_VM_IP:8080`
- Login: `demo@dgi.ma` / `demo123`

---

## 📋 Local Development

```bash
# Clone
git clone https://github.com/Achraf-CHAHBOUNE/depl.git
cd depl

# Configure .env
cp .env.example .env
# Edit .env with your API keys

# Add Google credentials
# Place google-credentials.json in ./credentials/

# Start
.\scripts\start.ps1  # Windows
./scripts/start.sh   # Linux/Mac

# Access
# http://localhost:8080
```

---

## 🔧 Features

- **OCR Intelligent**: Extraction automatique des données
- **Matching Automatique**: Rapprochement factures-paiements
- **Calcul des Pénalités**: Loi 69-21 (2.25% + 0.85%/mois)
- **Validation Manuelle**: Interface de révision
- **Export DGI**: Déclarations conformes

---

## 💰 GCP Cost

~$27/month (covered by $300 free credit)

---

## 📝 License

Propriétaire - Tous droits réservés
