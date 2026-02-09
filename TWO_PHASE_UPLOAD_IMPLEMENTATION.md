# Two-Phase Upload Workflow - Implementation Summary

## ✅ Implementation Complete

This document summarizes the implementation of the two-phase upload workflow for the DGI Compliance System.

---

## 🎯 Overview

The system now supports **two upload workflows**:

### Workflow 1: Traditional (Both Files Together) - **PRESERVED**
1. Upload invoice + payment PDFs together
2. Process everything at once
3. Generate results

### Workflow 2: Two-Phase Upload - **NEW**
1. **Phase 1**: Upload invoice only → Extract data → Wait
2. **Phase 2**: Later upload payment → Complete matching & calculations

**Business Value**: Users can process invoices immediately when received, without waiting for month-end bank statements.

---

## 📦 Changes Made

### 1. Backend Models ✅

**File**: `backend/orchestrator-service/app/database/models.py`

Added new batch statuses:
- `INVOICES_OCR_PROCESSING` - OCR processing invoices only
- `INVOICES_EXTRACTED` - Invoices extracted, waiting for payment

Added field:
- `invoice_only_mode: Boolean` - Tracks if batch is in two-phase mode

**File**: `backend/orchestrator-service/app/models/batch.py`

Updated `BatchStatus` enum with same new statuses.

---

### 2. Workflow Orchestrator ✅

**File**: `backend/orchestrator-service/app/services/workflow_orchestrator.py`

#### New Method: `process_invoices_only()`
- **Purpose**: Phase 1 - Process invoices without payments
- **Flow**:
  1. OCR invoice documents
  2. Extract invoice data via Intelligence service
  3. Store in `batch.invoices_data`
  4. Set status to `INVOICES_EXTRACTED`
  5. Return batch (matching/calculations wait for Phase 2)

#### New Method: `process_payments_and_complete()`
- **Purpose**: Phase 2 - Add payments and complete workflow
- **Prerequisites**: `batch.status == INVOICES_EXTRACTED`
- **Flow**:
  1. Validate prerequisites (status, invoice data exists)
  2. OCR payment documents
  3. Extract payment data
  4. Match payments to invoices
  5. Calculate legal delays & penalties
  6. Set status to `VALIDATION_PENDING`

---

### 3. API Endpoints ✅

**File**: `backend/orchestrator-service/app/main.py`

#### New Endpoint: `POST /batches/{batch_id}/process/invoices`
- Triggers Phase 1 processing
- Validates invoice documents exist
- Runs `process_invoices_only()` in background

#### New Endpoint: `POST /batches/{batch_id}/process/complete`
- Triggers Phase 2 processing
- Validates status is `invoices_extracted`
- Validates payment documents exist
- Runs `process_payments_and_complete()` in background

#### Background Tasks Added:
- `process_invoices_only_background()` - Handles Phase 1
- `process_payments_complete_background()` - Handles Phase 2

---

### 4. API Gateway ✅

**File**: `backend/api-gateway/app/main.py`

Added proxy routes:
- `POST /api/batches/{batch_id}/process/invoices` → Orchestrator
- `POST /api/batches/{batch_id}/process/complete` → Orchestrator

---

### 5. Frontend API Client ✅

**File**: `frontend/src/lib/api.ts`

#### New Method: `draftAPI.createInvoiceOnly()`
```typescript
createInvoiceOnly: async (data: {
  company_name: string;
  company_ice: string;
  company_rc?: string;
  invoice_file: File;
})
```

**Flow**:
1. Create batch
2. Upload invoice
3. Call `/process/invoices`
4. Poll until status = `invoices_extracted`
5. Return draft with phase = `awaiting_payment`

#### New Method: `draftAPI.completeWithPayment()`
```typescript
completeWithPayment: async (batchId: string, payment_file: File)
```

**Flow**:
1. Upload payment file
2. Call `/process/complete`
3. Poll until status = `validation_pending` or `validated`
4. Return completion status

---

## 🔄 Workflow Comparison

### Traditional Workflow (Unchanged)
```
User uploads both files
    ↓
POST /batches/{id}/process
    ↓
OCR both → Extract both → Match → Calculate → Validate
    ↓
Status: validation_pending
```

### New Two-Phase Workflow
```
PHASE 1:
User uploads invoice only
    ↓
POST /batches/{id}/process/invoices
    ↓
OCR invoice → Extract invoice → STOP
    ↓
Status: invoices_extracted (WAITING)

[User waits for bank statement to arrive...]

PHASE 2:
User uploads payment
    ↓
POST /batches/{id}/process/complete
    ↓
OCR payment → Extract payment → Match → Calculate → Validate
    ↓
Status: validation_pending
```

---

## 🎨 Frontend UI Updates (Recommended)

The following UI updates are recommended but not yet implemented:

### DraftCreate.tsx
```typescript
// Add state for workflow mode
const [uploadMode, setUploadMode] = useState<'both' | 'invoice-only'>('both');

// Conditional rendering
{uploadMode === 'both' ? (
  // Show both invoice + payment upload
) : (
  // Show invoice-only upload with message:
  // "You can add the bank statement later"
)}

// Submit button logic
if (invoiceFile && !paymentFile) {
  // Call createInvoiceOnly()
} else if (invoiceFile && paymentFile) {
  // Call create() - existing workflow
}
```

### DraftsList.tsx
```typescript
// Show badge for invoice-only drafts
{draft.status === 'invoices_extracted' && (
  <Badge variant="warning">
    En attente paiement
  </Badge>
)}

// Add "Upload Payment" button for these drafts
{draft.status === 'invoices_extracted' && (
  <Button onClick={() => handleUploadPayment(draft.id)}>
    Ajouter relevé bancaire
  </Button>
)}
```

---

## 🧪 Testing Checklist

### ✅ Backend Tests

**Existing Workflow (Regression)**:
- [ ] Upload both files together
- [ ] Processing completes successfully
- [ ] Matching produces results
- [ ] Legal calculations are correct
- [ ] CSV export works

**New Workflow (Phase 1)**:
- [ ] Upload invoice only
- [ ] Status becomes `invoices_extracted`
- [ ] Invoice data is stored
- [ ] No matching/legal calculations yet

**New Workflow (Phase 2)**:
- [ ] Upload payment to invoice-only batch
- [ ] Status transitions correctly
- [ ] Matching executes
- [ ] Legal calculations produce same results as traditional workflow
- [ ] CSV export identical to traditional workflow

**Edge Cases**:
- [ ] Try to complete without payment → Should fail with 400
- [ ] Try to complete when status != invoices_extracted → Should fail
- [ ] Upload payment to already-completed batch → Should fail

### 🔧 Manual Testing Commands

```bash
# Test Phase 1: Invoice Only
curl -X POST http://localhost:8000/api/batches \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"company_name":"Test","company_ice":"123"}'

# Upload invoice
curl -X POST http://localhost:8000/api/batches/{batch_id}/upload/invoices \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@invoice.pdf"

# Process invoices only
curl -X POST http://localhost:8000/api/batches/{batch_id}/process/invoices \
  -H "Authorization: Bearer $TOKEN"

# Check status (should be invoices_extracted)
curl http://localhost:8000/api/batches/{batch_id} \
  -H "Authorization: Bearer $TOKEN"

# Test Phase 2: Complete with Payment
curl -X POST http://localhost:8000/api/batches/{batch_id}/upload/payments \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@payment.pdf"

# Complete processing
curl -X POST http://localhost:8000/api/batches/{batch_id}/process/complete \
  -H "Authorization: Bearer $TOKEN"

# Check final status (should be validation_pending)
curl http://localhost:8000/api/batches/{batch_id} \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🗄️ Database Migration

If using the `invoice_only_mode` flag, run this migration:

```sql
ALTER TABLE batches 
ADD COLUMN invoice_only_mode BOOLEAN DEFAULT FALSE;
```

---

## 📊 Status Flow Diagram

```
CREATED
  ↓
UPLOADING
  ↓
┌─────────────────────────────────────┐
│  DECISION: Both files or Invoice?   │
└─────────────────────────────────────┘
         ↓                    ↓
    BOTH FILES          INVOICE ONLY
         ↓                    ↓
  OCR_PROCESSING    INVOICES_OCR_PROCESSING
         ↓                    ↓
  EXTRACTION_DONE   INVOICES_EXTRACTED ← WAIT HERE
         ↓                    ↓
         │            (User uploads payment)
         │                    ↓
         │            OCR_PROCESSING
         │                    ↓
         └────────→  EXTRACTION_DONE
                            ↓
                     MATCHING_DONE
                            ↓
                    RULES_CALCULATED
                            ↓
                   VALIDATION_PENDING
                            ↓
                        VALIDATED
                            ↓
                        EXPORTED
```

---

## 🚨 Critical Notes

### DO NOT BREAK:
1. **Existing workflow** - Traditional upload must still work
2. **DGI penalty calculations** - Formula must remain identical
3. **Matching logic** - Confidence scoring unchanged
4. **Database schema** - Backwards compatible

### Backwards Compatibility:
- All existing API endpoints unchanged
- Existing batches continue to work
- No breaking changes to frontend contracts

---

## 📝 Next Steps (Optional Enhancements)

1. **Frontend UI**: Implement conditional upload interface
2. **Batch List**: Show "awaiting payment" badge
3. **Notifications**: Email user when ready for payment upload
4. **Analytics**: Track how many users use two-phase workflow
5. **Bulk Operations**: Support multiple invoices in Phase 1

---

## 🎉 Success Criteria

✅ **Backend Implementation Complete**:
- New statuses added
- Workflow methods implemented
- API endpoints created
- Background tasks configured

✅ **API Gateway Updated**:
- Proxy routes added

✅ **Frontend API Client Ready**:
- `createInvoiceOnly()` method
- `completeWithPayment()` method

⏳ **Pending**:
- Frontend UI updates (optional)
- End-to-end testing
- User documentation

---

## 📞 Support

For issues or questions:
1. Check backend logs: `docker logs orchestrator-service`
2. Check database: `SELECT * FROM batches WHERE status = 'invoices_extracted';`
3. Test endpoints with Postman/curl
4. Review this document for workflow details

---

**Implementation Date**: 2026-02-06  
**Status**: Backend Complete, Frontend API Ready, UI Updates Pending  
**Backwards Compatible**: Yes ✅
