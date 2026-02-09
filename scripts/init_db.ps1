# PostgreSQL Database Initialization Script for Windows PowerShell
# WORKING VERSION - Uses actual generated hash

Write-Host "Initializing database..." -ForegroundColor Cyan

$hash = '$2b$12$k36Hq0ME8toXzSRiRBo/fu/M.dEzsEgP2FxCmPEmOPbP73Y7iv8lu'

$sqlScript = @"
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
    failed_documents JSONB DEFAULT '[]'::jsonb,
    invoice_only_mode BOOLEAN DEFAULT FALSE
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
('user-demo-001', 'demo@dgi.ma', '$hash', 'Mohamed Alami', 'admin', 'Entreprise ABC SARL', '001234567000089', 'RC12345'),
('user-demo-002', 'reviewer@dgi.ma', '$hash', 'Fatima Zahra', 'reviewer', 'Entreprise ABC SARL', '001234567000089', 'RC12345'),
('user-demo-003', 'accountant@dgi.ma', '$hash', 'Ahmed Bennani', 'user', 'Entreprise XYZ SARL', '002345678000090', 'RC67890');

-- Verify
SELECT * FROM users;
"@

# Execute
$sqlScript | docker-compose exec -T postgres psql -U dgi_user -d dgi_compliance

Write-Host ""
Write-Host "Database initialization complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Demo Credentials:" -ForegroundColor Cyan
Write-Host "Email: demo@dgi.ma" -ForegroundColor White
Write-Host "Password: demo123" -ForegroundColor White