# 🚀 GCP VM Deployment Guide

Complete guide to deploy the DGI Invoice Compliance System on Google Cloud Platform.

## 📋 Prerequisites

### 1. GCP VM Requirements
- **OS**: Ubuntu 20.04 LTS or later
- **Machine Type**: e2-medium (2 vCPU, 4GB RAM) minimum
- **Disk**: 20GB SSD
- **Firewall**: Allow ports 80, 443, 8000, 8080

### 2. Required Credentials
- **Anthropic API Key**: Get from https://console.anthropic.com/
- **Google Cloud Credentials**: JSON file for Vision API

---

## 🔧 Step-by-Step Deployment

### Step 1: Create GCP VM Instance

1. Go to [GCP Console](https://console.cloud.google.com/)
2. Navigate to **Compute Engine > VM Instances**
3. Click **CREATE INSTANCE**
4. Configure:
   - **Name**: `dgi-invoice-system`
   - **Region**: Choose closest to Morocco (e.g., `europe-west1`)
   - **Machine type**: `e2-medium` (2 vCPU, 4GB RAM)
   - **Boot disk**: Ubuntu 20.04 LTS, 20GB SSD
   - **Firewall**: ✅ Allow HTTP, ✅ Allow HTTPS

5. Click **CREATE**

### Step 2: Configure Firewall Rules

1. Go to **VPC Network > Firewall**
2. Click **CREATE FIREWALL RULE**
3. Configure:
   - **Name**: `allow-dgi-ports`
   - **Direction**: Ingress
   - **Targets**: All instances in network
   - **Source IP ranges**: `0.0.0.0/0`
   - **Protocols and ports**: `tcp:8000,8080`
4. Click **CREATE**

### Step 3: Connect to VM

```bash
# From GCP Console, click SSH button
# Or use gcloud CLI:
gcloud compute ssh dgi-invoice-system --zone=europe-west1-b
```

### Step 4: Prepare Credentials

**On your local machine:**

1. **Get your Anthropic API Key**
   - Go to https://console.anthropic.com/
   - Copy your API key

2. **Upload Google Credentials to VM**
   ```bash
   # From your local machine
   gcloud compute scp ./credentials/google-credentials.json dgi-invoice-system:~/google-credentials.json --zone=europe-west1-b
   ```

### Step 5: Run Deployment Script

**On the VM:**

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Clone repository
cd /opt
sudo git clone https://github.com/Achraf-CHAHBOUNE/depl.git invoice-automation
cd invoice-automation

# Create credentials directory
sudo mkdir -p credentials
sudo mv ~/google-credentials.json credentials/

# Make script executable
sudo chmod +x deploy-gcp.sh

# Run deployment
sudo -E ./deploy-gcp.sh
```

**The script will:**
- ✅ Install Docker & Docker Compose
- ✅ Configure environment variables
- ✅ Build all services
- ✅ Initialize database
- ✅ Start the application

**Deployment takes ~10 minutes**

### Step 6: Access Your Application

After deployment completes, you'll see:

```
============================================
✅ DEPLOYMENT COMPLETE!
============================================

🌐 Your application is now running at:

   Frontend:    http://YOUR_VM_IP:8080
   API Gateway: http://YOUR_VM_IP:8000

📝 Default credentials:
   Email:    demo@dgi.ma
   Password: demo123
============================================
```

**Replace `YOUR_VM_IP` with your VM's external IP**

---

## 🔍 Verify Deployment

### Check Services Status
```bash
cd /opt/invoice-automation
docker-compose ps
```

All services should show "Up" status.

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f intelligence-service
```

### Test API
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

---

## 🛠️ Common Issues & Solutions

### Issue 1: Services not starting
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart
```

### Issue 2: Port already in use
```bash
# Find process using port
sudo lsof -i :8080

# Kill process
sudo kill -9 <PID>

# Restart
docker-compose up -d
```

### Issue 3: Out of memory
```bash
# Check memory
free -h

# Upgrade VM to e2-standard-2 (2 vCPU, 8GB RAM)
```

### Issue 4: Can't access from browser
- Check firewall rules allow ports 8000, 8080
- Verify VM external IP is correct
- Try accessing from incognito mode

---

## 🔄 Update Application

```bash
cd /opt/invoice-automation
sudo git pull
docker-compose up -d --build
```

---

## 🛑 Stop/Start Services

### Stop
```bash
cd /opt/invoice-automation
docker-compose down
```

### Start
```bash
cd /opt/invoice-automation
docker-compose up -d
```

### Restart
```bash
cd /opt/invoice-automation
docker-compose restart
```

---

## 💰 Cost Estimation

**Monthly costs (with $300 free credit):**
- VM e2-medium: ~$27/month
- Storage 20GB: ~$2/month
- Network egress: ~$5/month
- **Total**: ~$34/month (covered by free credit)

---

## 🔒 Security Recommendations

1. **Change default password** after first login
2. **Set up HTTPS** with Let's Encrypt (optional)
3. **Restrict firewall** to specific IPs if possible
4. **Rotate API keys** regularly
5. **Enable Cloud Armor** for DDoS protection (optional)

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Verify all services are running: `docker-compose ps`
3. Review this guide carefully

---

## ✅ Deployment Checklist

- [ ] GCP VM created (e2-medium, Ubuntu 20.04)
- [ ] Firewall rules configured (ports 8000, 8080)
- [ ] Anthropic API key obtained
- [ ] Google credentials uploaded to VM
- [ ] Repository cloned to `/opt/invoice-automation`
- [ ] `deploy-gcp.sh` executed successfully
- [ ] All services showing "Up" status
- [ ] Application accessible at `http://VM_IP:8080`
- [ ] Login successful with demo credentials
- [ ] Test invoice upload works

---

**🎉 Your DGI Invoice Compliance System is now live!**
