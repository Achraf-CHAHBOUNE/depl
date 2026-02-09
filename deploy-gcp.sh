#!/bin/bash

# ============================================================================
# GCP Deployment Script - One Command Deploy
# ============================================================================
# Usage: bash <(curl -sSL https://raw.githubusercontent.com/Achraf-CHAHBOUNE/depl/main/deploy-gcp.sh)
# Or: bash <(wget -qO- https://raw.githubusercontent.com/Achraf-CHAHBOUNE/depl/main/deploy-gcp.sh)
# ============================================================================

set -e

echo "=============================================="
echo "🚀 DGI Invoice Automation - GCP Deployment"
echo "=============================================="
echo ""

# ============================================================================
# Install curl if not present
# ============================================================================
if ! command -v curl &> /dev/null; then
    echo "📦 Installing curl..."
    sudo apt-get update -qq
    sudo apt-get install -y curl
    echo "   ✅ curl installed"
    echo ""
fi

# ============================================================================
# Check for API Key
# ============================================================================
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not found in environment"
    echo ""
    echo "Please enter your Anthropic API key:"
    echo "(Get it from: https://console.anthropic.com/)"
    read -r ANTHROPIC_API_KEY
    export ANTHROPIC_API_KEY
    echo ""
fi

# ============================================================================
# Get External IP
# ============================================================================
echo "📡 Detecting external IP address..."
EXTERNAL_IP=$(curl -s ifconfig.me)
echo "   External IP: $EXTERNAL_IP"
echo ""

# ============================================================================
# Update System
# ============================================================================
echo "📦 Step 1/8: Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
echo "   ✅ System updated"
echo ""

# ============================================================================
# Install Docker
# ============================================================================
echo "🐳 Step 2/8: Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "   ✅ Docker installed"
else
    echo "   ℹ️  Docker already installed"
fi
echo ""

# ============================================================================
# Install Docker Compose
# ============================================================================
echo "🐳 Step 3/8: Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "   ✅ Docker Compose installed"
else
    echo "   ℹ️  Docker Compose already installed"
fi
echo ""

# ============================================================================
# Install Git
# ============================================================================
echo "📥 Step 4/8: Installing Git..."
if ! command -v git &> /dev/null; then
    sudo apt-get install -y git
    echo "   ✅ Git installed"
else
    echo "   ℹ️  Git already installed"
fi
echo ""

# ============================================================================
# Clone Repository
# ============================================================================
echo "📂 Step 5/8: Cloning repository..."
cd /opt
if [ -d "invoice-automation" ]; then
    echo "   ℹ️  Repository already exists, pulling latest changes..."
    cd invoice-automation
    sudo git pull
else
    sudo git clone https://github.com/Achraf-CHAHBOUNE/depl.git invoice-automation
    cd invoice-automation
fi
sudo chown -R $USER:$USER /opt/invoice-automation
echo "   ✅ Repository ready"
echo ""

# ============================================================================
# Configure Environment Variables
# ============================================================================
echo "⚙️  Step 6/8: Configuring environment variables..."

# Create credentials directory if it doesn't exist
mkdir -p credentials

# Check for Google credentials
if [ ! -f "credentials/google-credentials.json" ]; then
    echo "⚠️  Google Cloud credentials not found"
    echo ""
    echo "Please paste your Google Cloud credentials JSON content:"
    echo "(Press Ctrl+D when done)"
    cat > credentials/google-credentials.json
    echo ""
    echo "   ✅ Google credentials saved"
fi

# Create .env file for deployment
cat > .env << EOF
# Deployment Configuration
VITE_API_URL=http://$EXTERNAL_IP:8000
ALLOWED_ORIGINS=http://$EXTERNAL_IP:8080,http://localhost:8080,http://localhost:5173
JWT_SECRET_KEY=change-this-in-production-$(openssl rand -hex 32)
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
EOF

echo "   ✅ Environment configured"
echo "   📝 VITE_API_URL=http://$EXTERNAL_IP:8000"
echo "   📝 ALLOWED_ORIGINS=http://$EXTERNAL_IP:8080"
echo ""

# ============================================================================
# Build and Start Services
# ============================================================================
echo "🏗️  Step 7/8: Building and starting services..."
echo "   This may take 5-10 minutes..."
docker-compose build
docker-compose up -d
echo "   ✅ Services started"
echo ""

# ============================================================================
# Initialize Database
# ============================================================================
echo "🗄️  Step 8/8: Initializing database..."
sleep 10  # Wait for postgres to be ready

docker-compose exec -T postgres psql -U dgi_user -d dgi_compliance << 'EOSQL'
-- Drop existing tables
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS batches CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- USERS TABLE
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    company_name VARCHAR(255),
    company_ice VARCHAR(20),
    company_rc VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- BATCHES TABLE
CREATE TABLE batches (
    batch_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
    company_name VARCHAR(255) NOT NULL,
    company_ice VARCHAR(20) NOT NULL,
    company_rc VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    current_step TEXT,
    progress_percentage REAL DEFAULT 0.0,
    total_invoices INTEGER DEFAULT 0,
    total_payments INTEGER DEFAULT 0,
    alerts_count INTEGER DEFAULT 0,
    critical_alerts_count INTEGER DEFAULT 0,
    invoices_data JSONB DEFAULT '[]'::jsonb,
    payments_data JSONB DEFAULT '[]'::jsonb,
    matching_results JSONB DEFAULT '[]'::jsonb,
    legal_results JSONB DEFAULT '[]'::jsonb,
    dgi_declaration JSONB,
    requires_validation BOOLEAN DEFAULT FALSE,
    validated_by VARCHAR(50),
    validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exported_at TIMESTAMP,
    error_message TEXT,
    failed_documents JSONB DEFAULT '[]'::jsonb
);

-- DOCUMENTS TABLE
CREATE TABLE documents (
    document_id VARCHAR(50) PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    document_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    ocr_text TEXT,
    extracted_data JSONB,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT
);

-- AUDIT LOGS TABLE
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) REFERENCES batches(batch_id) ON DELETE CASCADE,
    user_id VARCHAR(50) REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(50),
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(50)
);

-- INDEXES
CREATE INDEX idx_batches_user_id ON batches(user_id);
CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_created_at ON batches(created_at DESC);
CREATE INDEX idx_documents_batch_id ON documents(batch_id);
CREATE INDEX idx_audit_logs_batch_id ON audit_logs(batch_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);

-- INSERT DEMO USERS (Password: demo123)
INSERT INTO users (user_id, email, password_hash, name, role, company_name, company_ice, company_rc) VALUES
('user-demo-001', 'demo@dgi.ma', '\$2b\$12\$k36Hq0ME8toXzSRiRBo/fu/M.dEzsEgP2FxCmPEmOPbP73Y7iv8lu', 'Mohamed Alami', 'admin', 'Entreprise ABC SARL', '001234567000089', 'RC12345'),
('user-demo-002', 'reviewer@dgi.ma', '\$2b\$12\$k36Hq0ME8toXzSRiRBo/fu/M.dEzsEgP2FxCmPEmOPbP73Y7iv8lu', 'Fatima Zahra', 'reviewer', 'Entreprise ABC SARL', '001234567000089', 'RC12345'),
('user-demo-003', 'accountant@dgi.ma', '\$2b\$12\$k36Hq0ME8toXzSRiRBo/fu/M.dEzsEgP2FxCmPEmOPbP73Y7iv8lu', 'Ahmed Bennani', 'user', 'Entreprise XYZ SARL', '002345678000090', 'RC67890');
EOSQL

echo "   ✅ Database initialized"
echo ""

# ============================================================================
# Display Summary
# ============================================================================
echo "=============================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=============================================="
echo ""
echo "🌐 Your application is now running at:"
echo ""
echo "   Frontend:    http://$EXTERNAL_IP:8080"
echo "   API Gateway: http://$EXTERNAL_IP:8000"
echo ""
echo "📝 Default credentials:"
echo "   Email:    demo@dgi.ma"
echo "   Password: demo123"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:     cd /opt/invoice-automation && docker-compose logs -f"
echo "   Restart:       cd /opt/invoice-automation && docker-compose restart"
echo "   Stop:          cd /opt/invoice-automation && docker-compose down"
echo "   Update code:   cd /opt/invoice-automation && git pull && docker-compose up -d --build"
echo ""
echo "💰 Cost: ~$27/month (covered by your $300 credit)"
echo ""
echo "=============================================="
