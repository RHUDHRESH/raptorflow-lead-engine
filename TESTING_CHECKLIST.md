# PHASE B Testing Checklist

**Print this out or reference while testing**

---

## Pre-Test Checklist

- [ ] Python 3.9+ installed
- [ ] Ollama installed (run `ollama --version`)
- [ ] Gemma 3 1B model pulled (`ollama pull gemma3:1b`)
- [ ] Gemma 3 4B model pulled (`ollama pull gemma3:4b`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Tesseract OCR installed (Windows: https://github.com/UB-Mannheim/tesseract/wiki)
- [ ] Backend dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] `.env` file exists in `backend/` directory
- [ ] Ollama listening on `localhost:11434` (check with `curl http://localhost:11434`)

---

## Service Startup Checklist

### Terminal 1: Ollama
```bash
ollama serve
```
- [ ] Command started without error
- [ ] Message shows "Listening on 127.0.0.1:11434"
- [ ] Keep running (don't close)

### Terminal 2: Backend
```bash
cd backend
python main.py
```
- [ ] No errors during startup
- [ ] Sees "🚀 Initializing Raptorflow Lead Engine..."
- [ ] Sees "✅ System ready!"
- [ ] Sees "Uvicorn running on http://127.0.0.1:8000"
- [ ] Keep running (don't close)

### Terminal 3: Frontend
```bash
npm run dev
```
- [ ] No build errors
- [ ] Shows "✓ Ready in X.Xs"
- [ ] Listening on http://localhost:3000
- [ ] Keep running (don't close)

### Terminal 4: Tests
- [ ] Use for running curl commands or manual API calls
- [ ] Can open new terminals as needed

---

## Workflow 1: Stack Verification

**Objective**: Ensure all 3 services are running and communicate

### Test 1A: Backend Health
```bash
curl http://localhost:8000/
```
- [ ] Returns JSON with `"status": "ok"`
- [ ] Response time < 1 second
- [ ] No error messages

### Test 1B: Frontend Loads
- [ ] Navigate to http://localhost:3000/dashboard
- [ ] Page loads without errors
- [ ] Dashboard visible with "Lead Pipeline" title
- [ ] No red error messages on page

### Test 1C: Browser Network
- [ ] Open DevTools (F12)
- [ ] Go to Network tab
- [ ] Refresh page
- [ ] [ ] No 500 errors
- [ ] [ ] No CORS errors
- [ ] [ ] No "Connection refused" messages

**Workflow 1 Result**: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

## Workflow 2: Signal Classification

**Objective**: Test the 1B classifier with realistic and edge case signals

### Test 2A: Create ICP Profile
- [ ] Navigate to ICP Profiles section
- [ ] Click "New Profile"
- [ ] Name: "Micro D2C Brands"
- [ ] Size: Check "1" and "2-5"
- [ ] Industry: Check "d2c" and "ecommerce"
- [ ] Pain keywords: Add "marketing", "growth"
- [ ] Click Save
- [ ] Profile appears in list

### Test 2B: Strong Signal (Expected: Red Hot, score 75+)
```
Signal: "Hiring: Growth Marketer. We are a 3-person D2C skincare brand,
launched 6 months ago. Currently spending $500/month on ads with 2% ROAS.
Our founder is doing all marketing but burning out. Need someone to help
with TikTok and email strategy. Location: India."
Company: SkinGlow D2C
```

- [ ] Classification completes in < 10 seconds
- [ ] Score returned: 75+ (RED HOT)
- [ ] ICP match: true
- [ ] Pain tags include "marketing_pain" or "founder_burnout"
- [ ] Lead created with ID shown

### Test 2C: Weak Signal (Expected: Parked, score 20-30)
```
Signal: "We are growing our enterprise SaaS team in California.
Just funded Series C, hiring 50 engineers."
Company: EnterpriseCorp
```

- [ ] Classification completes
- [ ] Score returned: < 40 (PARKED)
- [ ] ICP match: false
- [ ] Lead created anyway (still added to database)

### Test 2D: Edge Case - Empty Signal
- [ ] Submit with empty signal_text: ""
- [ ] Result: Error message OR score 0
- [ ] Result: NOT a server crash

### Test 2E: Edge Case - Very Long Signal
- [ ] Create 5000+ word text file
- [ ] Submit as signal
- [ ] Result: Completes in < 30 seconds OR returns timeout error
- [ ] Result: NOT a crash or OOM

**Workflow 2 Result**: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

## Workflow 3: Image OCR

**Objective**: Test Tesseract OCR and contact extraction

### Preparation
- [ ] Create or download test image (screenshot, business card, etc.)
- [ ] Image should have text, email, phone if possible
- [ ] Save as `test.jpg` in your working directory

### Test 3A: OCR Only
```bash
curl -X POST http://localhost:8000/api/ingest/ocr \
  -F "file=@test.jpg"
```

- [ ] Request completes without error
- [ ] Returns extracted_text (not empty)
- [ ] Detected emails array returned
- [ ] Detected phones array returned
- [ ] Detected names array returned

### Test 3B: OCR + Classify
```bash
curl -X POST http://localhost:8000/api/ingest/ocr-and-classify \
  -F "file=@test.jpg" \
  -F "company_name=TestCompany"
```

- [ ] Request completes
- [ ] Text extracted successfully
- [ ] Classification score returned (0-100)
- [ ] Lead created with lead_id shown

### Test 3C: Bad Image (No Text)
- [ ] Use image with no readable text (photo, etc.)
- [ ] Submit to /ocr-and-classify
- [ ] Result: Error message "Failed to extract text" OR generic 400 error
- [ ] Result: NOT a server crash

**Workflow 3 Result**: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

## Workflow 4: PDF Processing

**Objective**: Test PDF text extraction

### Preparation
- [ ] Create or download 2 test PDFs:
  - **Good**: Digital PDF (selectable text)
  - **Bad**: Scanned PDF (image-based)

### Test 4A: Digital PDF
```bash
curl -X POST http://localhost:8000/api/ingest/ocr-and-classify \
  -F "file=@digital.pdf" \
  -F "company_name=PDFCompany"
```

- [ ] Request completes
- [ ] Text extracted from all pages
- [ ] Classification works on extracted text
- [ ] Lead created with correct score

### Test 4B: Scanned PDF
- [ ] Upload scanned PDF
- [ ] Result: Error message OR note about image-based PDF
- [ ] Result: NOT a server crash or silent failure

### Test 4C: Corrupt PDF
- [ ] Create corrupt/invalid PDF file
- [ ] Upload to endpoint
- [ ] Result: Clear error message
- [ ] Result: NOT a server crash

**Workflow 4 Result**: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

## Workflow 5: CSV Bulk Import

### Preparation
Create `bulk_import.csv`:
```csv
company_name,company_website,signal_text
TechStartup1,tech1.in,Hiring marketing manager. 2 person team. Need help with customer acquisition.
FashionD2C,fashion1.in,D2C skincare. $100k MRR. Need growth hacker. Based in India.
EnterpriseCorp,large.com,Hiring 10 marketing VPs. Series C funded. California only.
```

### Test 5A: Valid CSV
```bash
curl -X POST http://localhost:8000/api/ingest/csv \
  -F "file=@bulk_import.csv"
```

- [ ] Response returns JSON (not error)
- [ ] "total_processed": 3
- [ ] "total_created": 3
- [ ] Results array has 3 items with lead_id and score
- [ ] Scores differ (row 1 & 2 high, row 3 low)

### Test 5B: CSV with Missing Column
Create `bad.csv` with "wrong_column" instead of "signal_text":
- [ ] Upload to /csv endpoint
- [ ] Result: Error message about missing column
- [ ] Result: NOT "0 rows processed silently"

### Test 5C: Empty CSV
Create CSV with headers but no data:
- [ ] Upload to /csv endpoint
- [ ] Result: Response with "0 rows processed"
- [ ] Result: NOT an error, graceful handling

**Workflow 5 Result**: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

## Workflow 6: ICP Management

**Objective**: Test ICP CRUD and integration with classification

### Test 6A: Create ICP
```bash
curl -X POST http://localhost:8000/api/icp \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test ICP",
    "description": "Test description",
    "size_buckets": ["2-5"],
    "industries": ["saas"],
    "locations": ["india"],
    "hiring_keywords": ["marketer"],
    "pain_keywords": ["growth"]
  }'
```

- [ ] Returns ICP object with id
- [ ] Fields match what was submitted

### Test 6B: List ICPs
```bash
curl http://localhost:8000/api/icp/
```

- [ ] Returns array of ICPs
- [ ] Created ICP appears in list

### Test 6C: Edit ICP
```bash
curl -X PATCH http://localhost:8000/api/icp/{id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

- [ ] Request succeeds
- [ ] List shows updated name

### Test 6D: Delete ICP
```bash
curl -X DELETE http://localhost:8000/api/icp/{id}
```

- [ ] Request succeeds
- [ ] ICP removed from list

**Workflow 6 Result**: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

## Workflow 7: Lead Lifecycle

**Objective**: Test lead status updates and deletion

### Test 7A: View Leads
- [ ] Navigate to http://localhost:3000/leads
- [ ] Leads from previous workflows appear
- [ ] Can filter by score
- [ ] Can see lead details when clicked

### Test 7B: Update Status
- [ ] Select a lead
- [ ] Find Status dropdown
- [ ] Change from "new" → "contacted"
- [ ] [ ] Status updates immediately
- [ ] [ ] Refresh page → status persists

### Test 7C: Status Journey
- [ ] Change status through workflow:
  - [ ] new → contacted ✅
  - [ ] contacted → qualified ✅
  - [ ] qualified → pitched ✅
  - [ ] pitched → won ✅
- [ ] Each change persists after refresh

### Test 7D: Delete Lead
- [ ] Select a lead
- [ ] Click Delete button
- [ ] Confirmation dialog appears
- [ ] Confirm deletion
- [ ] Lead removed from list
- [ ] Refresh page → still gone

**Workflow 7 Result**: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

## Summary Results

| Workflow | Status | Notes |
|----------|--------|-------|
| 1: Stack | ✅/⚠️/❌ | |
| 2: Signals | ✅/⚠️/❌ | |
| 3: Image OCR | ✅/⚠️/❌ | |
| 4: PDF OCR | ✅/⚠️/❌ | |
| 5: CSV Import | ✅/⚠️/❌ | |
| 6: ICP Mgmt | ✅/⚠️/❌ | |
| 7: Lead Lifecycle | ✅/⚠️/❌ | |

### Overall Result
- [ ] ✅ All Workflows PASS
- [ ] ⚠️ Some Workflows PARTIAL
- [ ] ❌ Some Workflows FAIL

### Critical Issues Found
```
[List any 🔴 CRITICAL issues that prevent basic functionality]
```

### High Priority Issues
```
[List any 🟠 MEDIUM issues that cause bad user experience]
```

### Low Priority Issues
```
[List any 🟡 LOW issues or nice-to-haves]
```

---

## What Happens Next

**All PASS ✅**:
- Proceed to PHASE C (edge case hardening)
- System ready for dogfooding

**Some PARTIAL ⚠️**:
- Document the issues
- We fix in PHASE C
- Re-test those workflows

**Some FAIL ❌**:
- Document error messages
- We fix in PHASE C
- Full re-test before proceeding

---

## Quick Reference: Important URLs

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Backend Health: `http://localhost:8000/` or `/health`
- Ollama: `http://localhost:11434`

---

## Important Logs to Check

When tests fail, check these for error messages:

1. **Backend Terminal** (Terminal 2)
   - Look for ERROR or CRITICAL messages
   - Note exact error text

2. **Browser Console** (F12 in browser)
   - Network tab for failed requests
   - Console tab for JavaScript errors

3. **Network Tab** (DevTools F12)
   - Failed requests (red status codes)
   - Check response body for error messages

---

**Date Started**: __________
**Date Completed**: __________
**Tester Name**: __________

**After completing, share results and we'll proceed to PHASE C (Hardening)**
