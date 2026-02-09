# DGI USE CASES - QUICK REFERENCE FOR WINDSURF

## 📸 CAS PRATIQUE #1: Délai Non Convenu Entre Les Parties (DEFAULT CASE)

**Scenario:** No contractual agreement between parties

**Example Data:**
- Invoice Date: 20 juillet 2023
- Legal Due Date: 18 septembre 2023 (60 days default)
- 1st day of delay: 19 septembre 2023

**3 Sub-cases:**

### Cas 1-1: Payment BEFORE Due Date
- Payment: 10/09/2023 (8 days early)
- **Result: NO PENALTY** ✅
- Status: Paid on time

### Cas 1-2: Payment 1 Month Late
- Payment: 25/09/2023
- Delay: 1 month
- **Penalty: 3%** (first month rate)

### Cas 1-3: Payment 2 Months Late
- Payment: 15/11/2023
- Delay: 2 months
- **Penalty: 3% + 0.85% = 3.85%**

**Form Fields Used:**
```
invoice_delivery_date: 2023-07-20
contractual_delay_days: NULL (use default 60)
payment_date: varies per case
```

---

## 📸 CAS PRATIQUE #2: Délai Convenu ≤ 120j (CONTRACTUAL DELAY)

**Scenario:** Contract specifies 80 days payment term

**Example Data:**
- Invoice Date: 20 juillet 2023
- Contractual Delay: 80 days
- Legal Due Date: 8 octobre 2023 (20/07 + 80 days)

**Form Fields Used:**
```
invoice_delivery_date: 2023-07-20
contractual_delay_days: 80  ← CUSTOM CONTRACT DELAY
agreed_payment_date: NULL
payment_date: to be filled
```

**Why Important:**
- Overrides 60-day default
- Must be ≤ 120 days (legal max)
- Must be in written contract

---

## 📸 CAS PRATIQUE #3: Délai Convenu ≤ 120j (SERVICE COMPLETION DATE)

**Scenario:** Service completion date different from invoice date

**Example Data:**
- Service Completion Date: 20/07/2023  ← START POINT
- Legal Due Date: 18/09/2023 (60 days from service completion)

**Form Fields Used:**
```
invoice_issue_date: (can be different)
service_completion_date: 2023-07-20  ← USE THIS AS ANCHOR
contractual_delay_days: NULL (60 days default)
```

**Why Important:**
- Common for construction/works projects
- Payment delay starts from COMPLETION not invoice
- Used especially for public establishments

---

## 📸 CAS PRATIQUE #4: Paiement Hors Délai (PAYMENT OUTSIDE PERIOD)

**Scenario:** Payment made before due date (early payment)

**Example Data:**
- Invoice Date: 20/07/2023
- Due Date: 18/09/2023 (60 days)
- Payment Date: 25/09/2023

**Form Fields Used:**
```
invoice_delivery_date: 2023-07-20
payment_date: 2023-09-25  ← PAID AFTER DUE
payment_amount_paid: (full amount)
```

**Penalty Calculation:**
- If paid before due date → NO PENALTY ✅
- If paid after due date → Calculate months

---

## 📸 CAS PRATIQUE #5: Paiement Hors Délai (LATE PAYMENT)

**Scenario:** Standard late payment case

**Example Data:**
- Invoice Date: 20/07/2023
- Due Date: 18/09/2023 (60 days default)
- Settlement Date EP: 18/10/2023
- Payment Date: 18/10/2023

**Timeline:**
- 60 days: No convention → default delay
- 1st month delay: 18/09 → 18/10
- Penalty: 3% + 0.85% = **3.85%**

**Form Fields Used:**
```
invoice_delivery_date: 2023-07-20
contractual_delay_days: NULL (use 60 default)
payment_date: 2023-10-18
```

---

## 📸 CAS PRATIQUE #6: Paiement Hors Délai + Convention (LONG DELAY WITH CONTRACT)

**Scenario:** Payment very late with contractual agreement

**Example Data:**
- Invoice Date: 20/07/2023
- Contractual Period: 120 days
- Convention Date: (agreement between parties)
- Settlement Deadline FR: (final deadline)

**Timeline Diagram Shows:**
- Initial 120 days (contractual agreement)
- 1st month of delay → 3%
- 2nd month of delay → +0.85%
- 3rd month of delay → +0.85%
- **Total: 3% + 0.85% + 0.85% = 4.70%**

**Key Point:**
- Even with 120-day contract, penalties apply AFTER that period
- Each month adds 0.85%

**Form Fields Used:**
```
invoice_delivery_date: 2023-07-20
contractual_delay_days: 120  ← MAX ALLOWED
payment_date: (much later)
```

---

## 🎯 QUICK MAPPING TO FORM FIELDS

### For Each Use Case, Fill:

**CASE 1 (Default 60 days):**
```javascript
{
  invoice_delivery_date: "2023-07-20",
  contractual_delay_days: null,  // Use default
  sector_delay_days: null,
  agreed_payment_date: null,
  service_completion_date: null,
  payment_date: "2023-09-25"  // Example
}
```

**CASE 2 (Contractual 80 days):**
```javascript
{
  invoice_delivery_date: "2023-07-20",
  contractual_delay_days: 80,  // ← CUSTOM
  sector_delay_days: null,
  agreed_payment_date: null,
  service_completion_date: null,
  payment_date: "2023-10-08"
}
```

**CASE 3 (Service Completion):**
```javascript
{
  invoice_issue_date: "2023-07-15",
  invoice_delivery_date: "2023-07-20",
  service_completion_date: "2023-07-20",  // ← USE THIS
  contractual_delay_days: null,
  payment_date: "2023-09-25"
}
```

**CASE 4 (Early Payment):**
```javascript
{
  invoice_delivery_date: "2023-07-20",
  payment_date: "2023-09-10",  // Before due date
  // Penalty = 0 (paid early)
}
```

**CASE 5 (1 Month Late):**
```javascript
{
  invoice_delivery_date: "2023-07-20",
  payment_date: "2023-10-18",  // 1 month late
  // Penalty = 3.85%
}
```

**CASE 6 (Max Contract + Multiple Months Late):**
```javascript
{
  invoice_delivery_date: "2023-07-20",
  contractual_delay_days: 120,  // MAX
  payment_date: "2024-01-20",  // 3 months after contract end
  // Penalty = 4.70%
}
```

---

## 💡 WINDSURF INSTRUCTIONS

When implementing the form, ensure:

1. **Default Behavior (Case 1):**
   - If `contractual_delay_days` is empty → use 60 days
   - Calculate due_date = delivery_date + 60 days

2. **Contractual Delay (Case 2):**
   - If `contractual_delay_days` is filled → use that value
   - MUST validate ≤ 120 days
   - Calculate due_date = delivery_date + contractual_delay_days

3. **Service Completion (Case 3):**
   - If `service_completion_date` is filled → use it as anchor instead of delivery_date
   - Calculate due_date = service_completion_date + delay

4. **Early Payment (Case 4):**
   - If payment_date < due_date → penalty = 0
   - Show "Payé à temps" status

5. **Late Payment (Cases 5-6):**
   - Calculate months using calendar method
   - Apply 3% + 0.85% per additional month

---

## 🔢 PENALTY CALCULATION EXAMPLES

### Example 1: Case 1-2 (1 Month Late)
```
Invoice: 20/07/2023
Due: 18/09/2023 (60 days)
Paid: 25/09/2023

Calculation:
- Month transitions: 0 (same month Sept)
- Day penalty: 1 (25 > 18)
- Total: 1 month
- Penalty: 3%
```

### Example 2: Case 1-3 (2 Months Late)
```
Invoice: 20/07/2023
Due: 18/09/2023
Paid: 15/11/2023

Calculation:
- Sept 18 → Oct 18: 1 month
- Oct 18 → Nov 15: 1 month (15 < 18, no extra day)
- Total: 2 months
- Penalty: 3% + 0.85% = 3.85%
```

### Example 3: Case 6 (3 Months Late with 120-day contract)
```
Invoice: 20/07/2023
Contract: 120 days
Due: 17/11/2023 (20/07 + 120)
Paid: 17/02/2024

Calculation:
- Nov 17 → Dec 17: 1 month
- Dec 17 → Jan 17: 1 month  
- Jan 17 → Feb 17: 1 month
- Total: 3 months
- Penalty: 3% + 2×0.85% = 4.70%
```

---

## ✅ VALIDATION RULES

Based on these cases:

1. **Contractual Delay Validation:**
   ```javascript
   if (contractual_delay_days > 120) {
     ERROR: "Délai contractuel ne peut dépasser 120 jours"
   }
   ```

2. **Service Completion Validation:**
   ```javascript
   if (service_completion_date < invoice_delivery_date) {
     ERROR: "Service fait ne peut être avant livraison"
   }
   ```

3. **Payment Date Validation:**
   ```javascript
   if (payment_date < invoice_issue_date) {
     ERROR: "Date de paiement ne peut être avant émission"
   }
   ```

4. **Penalty Calculation:**
   ```javascript
   // Always use calendar months (not 30-day periods)
   months = calculate_calendar_months(due_date, payment_date)
   penalty_rate = 0.03 + max(0, months - 1) * 0.0085
   ```

---

## 🎓 SUMMARY FOR WINDSURF

**6 Main Scenarios to Handle:**

| Case | Delay Type | Anchor Date | Special Field |
|------|------------|-------------|---------------|
| 1 | Default 60 | delivery_date | - |
| 2 | Contractual 80 | delivery_date | contractual_delay_days |
| 3 | Default 60 | **service_completion_date** | service_completion_date |
| 4 | Early payment | delivery_date | payment_date < due |
| 5 | Late 1 month | delivery_date | - |
| 6 | Late 3 months + contract | delivery_date | contractual_delay_days |

**All cases use CALENDAR MONTH calculation** - this is CRITICAL and already correct in backend.

**Your form MUST support:**
- ✅ Default 60-day delay (empty contractual_delay)
- ✅ Custom contractual delay (max 120)
- ✅ Service completion date (for works/services)
- ✅ All payment scenarios (early, on-time, late)

That's it! These 6 images cover ALL the DGI use cases.