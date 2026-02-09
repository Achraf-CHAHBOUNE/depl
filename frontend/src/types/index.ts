// Invoice Intelligence - Core Types

// ============================================
// User & Auth Types
// ============================================

export type UserRole = 'admin' | 'reviewer' | 'viewer';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

// ============================================
// Draft Workflow Types (Primary Model)
// ============================================

export type DraftStatus = 'DRAFT' | 'VALIDATED';

export interface DraftData {
  // Supplier info
  supplier_name?: string;
  supplier_ice?: string;
  supplier_if?: string;              // N° IF (tax ID) - CRITICAL for DGI
  supplier_rc?: string;
  supplier_address?: string;
  
  // Invoice info
  invoice_number?: string;
  invoice_issue_date?: string;
  invoice_delivery_date?: string;
  invoice_amount_ttc?: number;
  nature_of_goods?: string;          // REQUIRED per DGI form
  
  // Payment info
  payment_date?: string;
  payment_amount_paid?: number;      // Renamed from payment_amount
  payment_amount_unpaid?: number;    // Auto-calculated unpaid portion
  payment_reference?: string;
  payment_mode?: 'virement' | 'cheque' | 'especes' | 'effet' | 'autre';  // REQUIRED
  
  // Delay configuration
  contractual_delay_days?: number;
  sector_delay_days?: number;
  agreed_payment_date?: string;
  
  // Periodic transactions
  is_periodic_transaction?: boolean;
  transaction_month?: number;
  transaction_year?: number;
  
  // Public establishment
  service_completion_date?: string;  // For établissements publics
  
  // Computed fields
  legal_due_date?: string;
  days_overdue?: number;
  months_delay_unpaid?: number;      // MUST auto-calculate
  months_delay_paid?: number;        // MUST auto-calculate
  penalty_amount?: number;
  
  // Litigation
  is_disputed?: boolean;
  litigation_amount?: number;
  judicial_recourse_date?: string;
  judgment_date?: string;
  penalty_suspension_months?: number;
  
  // Calculation breakdown (from intelligence service)
  calculation_breakdown?: CalculationBreakdown;
  
  // Field tracking
  missing_fields: string[];
  uncertain_fields: string[];
}

export interface Draft {
  id: string;
  user_id: string;
  company_name: string;
  company_ice: string;
  company_rc?: string;
  status: DraftStatus;
  data: DraftData;
  alerts: Alert[];
  created_at: string;
  updated_at: string;
  validated_at?: string;
  invoice_file_url?: string;
  bank_statement_file_url?: string;
}

// ============================================
// Batch Workflow Types (Primary Model)
// ============================================

export type BatchStatus =
  | 'created'
  | 'uploading'
  | 'ocr_processing'
  | 'extraction_done'
  | 'matching_done'
  | 'rules_calculated'
  | 'validation_pending'
  | 'validated'
  | 'exported'
  | 'failed';

export interface Batch {
  batch_id: string;
  user_id: string;
  company_name: string;
  company_ice: string;
  company_rc?: string;
  status: BatchStatus;
  current_step: string;
  progress_percentage: number;
  total_invoices: number;
  total_payments: number;
  alerts_count: number;
  critical_alerts_count: number;
  requires_validation: boolean;
  created_at: string;
  updated_at: string;
  validated_at?: string;
  exported_at?: string;
  error_message?: string;
}

// ============================================
// Invoice Types (Backend Structure)
// ============================================

export interface SupplierInfo {
  name?: string;
  ice?: string;
  rc?: string;
  address?: string;
}

export interface CustomerInfo {
  name?: string;
  ice?: string;
}

export interface InvoiceInfo {
  number?: string;
  issue_date?: string;
  delivery_date?: string;
  due_date?: string;
  contract_reference?: string;
  bl_reference?: string;
}

export interface AmountInfo {
  total_ht?: number;
  total_tva?: number;
  total_ttc?: number;
  currency?: string;
}

export interface LineItem {
  description: string;
  quantity?: number;
  unit_price_ht?: number;
  total_ht?: number;
  tva_rate?: number;
}

export interface InvoiceStruct {
  invoice_id: string;
  supplier: SupplierInfo;
  customer: CustomerInfo;
  invoice: InvoiceInfo;
  amounts: AmountInfo;
  line_items: LineItem[];
  missing_fields: string[];
  source_document?: string;
  ocr_confidence?: number;
}

// ============================================
// Payment Types
// ============================================

export interface PaymentStruct {
  payment_id: string;
  date: string;
  amount: number;
  reference?: string;
  bank_reference?: string;
  source_document?: string;
  is_manual: boolean;
}

// ============================================
// Matching Types
// ============================================

export interface PaymentMatch {
  payment_id: string;
  matched_amount: number;
  confidence_score: number;
  matching_reasons: string[];
}

export type PaymentStatus = 'PAID' | 'PARTIALLY_PAID' | 'UNPAID';

export interface MatchingResult {
  invoice_id: string;
  matches: PaymentMatch[];
  payment_status: PaymentStatus;
  total_paid: number;
  remaining_amount: number;
  payment_dates: string[];
  overall_confidence: number;
}

// ============================================
// Legal Calculation Types
// ============================================

export type LegalStatus = 'NORMAL' | 'DISPUTED' | 'CREDIT_NOTE' | 'PROCEDURE_690';

export type AlertSeverity = 'CRITICAL' | 'ERROR' | 'WARNING' | 'INFO';

export interface Alert {
  code: string;
  severity: AlertSeverity;
  message: string;
  field?: string;
}

export interface CalculationBreakdown {
  base_rate_percent: number;
  monthly_increment_percent: number;
  months_breakdown: Array<{
    month: number;
    rate: number;
    is_applied: boolean;
  }>;
  calculation_steps: {
    step1_delay: {
      label: string;
      formula: string;
      due_date?: string;
      payment_date?: string;
      days_overdue?: number;
      months_of_delay?: number;
    };
    step2_rate: {
      label: string;
      formula: string;
      base_rate?: number;
      months?: number;
      increment?: number;
      penalty_rate?: number;
    };
    step3_amount: {
      label: string;
      formula: string;
      unpaid_amount?: number;
      penalty_rate?: number;
      base_penalty?: number;
    };
    step4_status: {
      label: string;
      formula: string;
      legal_status?: string;
      penalty_suspended?: boolean;
      final_penalty?: number;
    };
  };
}

export interface LegalResult {
  invoice_id: string;
  legal_start_date?: string;
  legal_due_date?: string;
  contractual_delay_days?: number;
  applied_legal_delay_days: number;
  actual_payment_date?: string;
  days_overdue: number;
  months_of_delay: number;
  months_delay_unpaid?: number;
  months_delay_paid?: number;
  penalty_rate: number;
  penalty_amount: number;
  penalty_suspended: boolean;
  legal_status: LegalStatus;
  invoice_amount_ttc: number;
  paid_amount: number;
  unpaid_amount: number;
  alerts: Alert[];
  computation_notes: string[];
  calculation_breakdown?: CalculationBreakdown;
  requires_manual_review: boolean;
}

// ============================================
// Batch Results (Combined Response)
// ============================================

export interface BatchResults {
  batch_id: string;
  invoices: InvoiceStruct[];
  payments: PaymentStruct[];
  matching_results: MatchingResult[];
  legal_results: LegalResult[];
  alerts_count: number;
  critical_alerts_count: number;
  requires_validation: boolean;
  summary: {
    total_invoices: number;
    total_payments: number;
    total_amount_ttc: number;
    total_paid: number;
    total_unpaid: number;
    total_penalties: number;
    invoices_needing_review: number;
  };
}

// ============================================
// Validation Types
// ============================================

export interface InvoiceUpdate {
  invoice_id: string;
  delivery_date?: string;
  issue_date?: string;
  supplier_name?: string;
  amount_ttc?: number;
  is_disputed?: boolean;
  contractual_delay_days?: number;
  notes?: string;
}

export interface ValidationSubmission {
  batch_id: string;
  user_id: string;
  invoice_updates: InvoiceUpdate[];
  delivery_dates_confirmed: boolean;
  amounts_confirmed: boolean;
}

// ============================================
// Settings Types
// ============================================

export interface CompanySettings {
  name: string;
  ice: string;
  rc: string;
  address: string;
}

export interface RulesConfig {
  PENALTY_BASE_RATE: number;
  PENALTY_MONTHLY_INCREMENT: number;
  AMOUNT_TOLERANCE: number;
  MIN_CONFIDENCE_SCORE: number;
  DEFAULT_LEGAL_DELAY_DAYS: number;
}

export interface Holiday {
  id: string;
  date: string;
  name: string;
}

// ============================================
// Dashboard Types
// ============================================

export interface DashboardStats {
  totalBatches: number;
  batchesInProgress: number;
  batchesValidated: number;
  batchesExported: number;
  totalInvoicesProcessed: number;
  totalPenaltiesCalculated: number;
}

export interface ActivityLog {
  id: string;
  action: string;
  entityType: string;
  entityId: string;
  performedBy: string;
  performedAt: string;
  details?: string;
}

// ============================================
// Legacy Types (for backwards compatibility)
// ============================================

export type DocumentType = 'invoice' | 'payment';

export type DocumentStatus =
  | 'UPLOADED'
  | 'OCR_DONE'
  | 'EXTRACTION_DONE'
  | 'MATCHED'
  | 'RULES_COMPUTED'
  | 'NEEDS_REVIEW'
  | 'VALIDATED';

export interface Document {
  id: string;
  filename: string;
  type: DocumentType;
  status: DocumentStatus;
  uploadedAt: string;
  ocrText?: string;
  fileSize?: number;
}

// Legacy DraftStatus kept for backwards compatibility
export type LegacyDraftStatus = 'DRAFT' | 'NEEDS_REVIEW' | 'READY_TO_VALIDATE' | 'VALIDATED';

export interface AuditEntry {
  id: string;
  action: string;
  performedBy: string;
  performedAt: string;
  details?: string;
}

export type RecordStatus = 'VALIDATED' | 'INVALIDATED';

export interface Declaration {
  id: string;
  period: string;
  companyId: string;
  batchIds: string[];
  createdAt: string;
  createdBy: string;
  status: 'DRAFT' | 'FINALIZED';
  totals: {
    totalTTC: number;
    totalPenalties: number;
    recordCount: number;
  };
}
