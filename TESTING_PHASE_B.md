# PHASE B: Testing & Failure Analysis

## Critical Failure Points Identified

### 1. **Ollama Connectivity (SEVERITY: CRITICAL)**
**Issue**: If Ollama is not running or unreachable, startup fails hard.
- `main.py` line 41: `await ollama_manager.ensure_models_loaded()` - no try/except at top level
- **Failure Mode**: Backend exits, frontend shows "Connection refused"
- **Test**: Start backend WITHOUT Ollama running
- **Expected Behavior**: Should show helpful error message
- **Current Behavior**: Process crashes

### 2. **Missing System Dependencies (SEVERITY: CRITICAL)**
**A. Tesseract OCR**
- `ingest.py` uses `pytesseract.image_to_string()` directly (line 96)
- If Tesseract binary not installed, raises `TesseractNotFoundError`
- **Failure Mode**: Image OCR endpoint crashes
- **Test**: Try `/api/ingest/ocr-and-classify` with PNG file without Tesseract installed
- **Current Behavior**: 500 error with raw Python exception in response

**B. pypdf Library**
- Graceful check exists: `ImportError` caught (line 17-20)
- But returns 500 HTTPException instead of checking at startup
- **Failure Mode**: PDF upload silently works in /ocr but fails in /ocr-and-classify
- **Test**: Upload PDF → See if error message is clear

### 3. **Empty Text Extraction (SEVERITY: MEDIUM)**
**Issue**: Properly handled in code (line 121-122), but user gets generic 400 error
- **Failure Mode**: User uploads scanned image → Tesseract finds no text → "Failed to extract text from file"
- **Test**: Scan a photo (not document) and try OCR
- **Expected Behavior**: Should say "No readable text found. Try a clearer image."
- **Current Behavior**: Generic error message

### 4. **CSV Encoding Issues (SEVERITY: MEDIUM)**
**Issue**: CSV endpoint assumes UTF-8 (line 221)
- **Failure Mode**: User uploads CSV in UTF-16 or other encoding → File appears empty
- **Test**: Create CSV with non-UTF-8 characters or encoding
- **Current Behavior**: Silent failure or garbled text

### 5. **CSV Header Validation (SEVERITY: MEDIUM)**
**Issue**: No validation that required columns exist
- `csv_reader` expects "signal_text" but silently skips rows if missing (line 228)
- **Failure Mode**: User uploads CSV with wrong column names → All rows skipped, returns "processed 0 rows"
- **Test**: Upload CSV with columns "text" and "company" instead of "signal_text" and "company_name"
- **Expected Behavior**: Return error listing expected columns
- **Current Behavior**: Silent success with 0 rows processed

### 6. **Signal Text Validation (SEVERITY: MEDIUM)**
**Issue**: No validation on signal text length or content
- `classify.py` passes signal_text directly to model (line 101)
- **Failure Mode A**: Empty signal → Model gets empty prompt → Returns default classification (score 0)
- **Failure Mode B**: Huge signal (1MB) → Timeouts or OOM on Ollama
- **Test**: Send empty string, send 10MB of text
- **Current Behavior**: Both accepted, second may timeout silently

### 7. **Ollama Response Parsing Failures (SEVERITY: MEDIUM)**
**Issue**: Has fallback (line 146), but doesn't log loudly or inform user
- When model returns non-JSON, uses `_default_classification()` (score 0)
- User thinks signal was weak, actually means model failed silently
- **Test**: Send signal, check logs for "Could not parse JSON" warnings
- **Expected Behavior**: API should return { "status": "degraded", "reason": "Model failed" }
- **Current Behavior**: Returns score: 0 silently

### 8. **Timeout Issues (SEVERITY: MEDIUM)**
**Issue**: httpx timeout is 300s per request, but no per-operation timeout
- **Failure Mode A**: Model pull takes >300s → Client disconnects, but Ollama keeps pulling
- **Failure Mode B**: Classification hangs indefinitely if Ollama freezes
- **Test**: Send classification request, kill Ollama while processing
- **Current Behavior**: Request hangs for 300s, then 500 error

### 9. **Frontend API Configuration (SEVERITY: LOW)**
**Issue**: API_BASE URL not documented in quickstart
- `lib/api.ts` line 5: uses `NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'`
- If backend runs on different port, frontend silently fails with CORS errors
- **Test**: Run backend on port 8001, frontend still targets :8000
- **Expected Behavior**: Clear setup instruction or auto-detect
- **Current Behavior**: Network errors in browser console

### 10. **Health Check Endpoint (SEVERITY: LOW)**
**Issue**: `/health` doesn't actually check Ollama
- `main.py` line 86: returns "ollama": "checking..." hardcoded
- **Test**: Call `/health` when Ollama is down
- **Current Behavior**: Always returns "ok" even if Ollama is unreachable

---

## Test Workflow Execution Plan

### Workflow 1: Start Stack ✅ READY
**Objective**: Verify all 3 services start cleanly
**Steps**:
1. Terminal 1: Start Ollama
2. Terminal 2: Start backend (`python main.py` from backend/)
3. Terminal 3: Start frontend (`npm run dev` from frontend/)
4. Check: `curl http://localhost:8000/` → should return health
5. Check: `curl http://localhost:3000/` → should load frontend

**Expected Outputs**:
- Backend logs: "✅ System ready!"
- Frontend loads without console errors
- Can access http://localhost:3000/dashboard

**Failure Modes to Watch**:
- "Ollama refused connection" → Ollama not running
- "Database is locked" → SQLite db open in another process
- CORS errors in browser → Check API_BASE config

---

### Workflow 2: Manual Signal Classification ✅ READY
**Objective**: Test 1B classifier with real + edge case signals
**Steps**:
1. Navigate to http://localhost:3000/dashboard
2. Create ICP: "Micro D2C Fashion"
   - Size: "1", "2-5"
   - Industry: "d2c"
   - Pain Keywords: "marketing", "growth", "customer acquisition"
   - Hiring Keywords: "marketing", "growth manager"

3. Go to Lead Classification page
4. Test Signal A (STRONG):
   ```
   Hiring: Growth Marketer (0-2 yrs exp)
   We are a 3-person D2C skincare brand, launched 6 months ago.
   Currently spending $500/month on ads with 2% ROAS.
   Our founder is doing all marketing but burning out.
   Need someone to help with TikTok + email strategy.
   Location: India
   ```
   **Expected Score**: 75-85 (Red Hot)
   **Expect ICP Match**: true
   **Expect Pain Tags**: ["marketing_pain", "hiring_growth", "cash_constrained", "founder_burnout"]

5. Test Signal B (WEAK):
   ```
   We are growing our enterprise SaaS team in California.
   Just funded Series C, hiring 50 engineers.
   ```
   **Expected Score**: 20-30 (Parked)
   **Expect ICP Match**: false
   **Expect Pain Tags**: []

6. Test Signal C (EDGE - Empty):
   ```
   [send empty string]
   ```
   **Expected Response**: Error message or score 0 with warning
   **Expect**: NOT a server crash

7. Test Signal D (EDGE - Very Long):
   ```
   [send 5000 word paragraph about marketing]
   ```
   **Expected**: Should process or timeout gracefully
   **Not Expected**: OOM or crash

**Failure Modes to Watch**:
- Classifier returns score 0 for signal A → Model not loaded
- Timeout > 30s for signal D → Model overloaded
- Server crash on empty signal → Validation missing
- Dossier endpoint fails for red_hot leads → 4B model issue

---

### Workflow 3: OCR Image Upload ✅ READY
**Objective**: Test image OCR + contact extraction
**Steps**:
1. Create test image:
   - Screenshot of a business card or job posting
   - Text should include: name, email, phone, company
2. Upload to `/api/ingest/ocr-and-classify`
3. Verify:
   - Text extracted correctly
   - Email/phone/name detected
   - Classification runs on extracted text
   - Lead created with correct score

**Test Cases**:
- **Case A**: Clear image of job posting
  - **Expected**: All contacts extracted, score >70

- **Case B**: Blurry photo
  - **Expected**: Partial extraction, graceful error or low confidence note

- **Case C**: Image with no text
  - **Expected**: Error "No text found" (NOT crash)

**Failure Modes to Watch**:
- "Tesseract not found" error → Dependency missing
- Email extraction misses valid emails → Regex too restrictive
- Phone extraction false positives → Need to validate
- Classification skipped after OCR → pipeline break

---

### Workflow 4: OCR PDF Upload ✅ READY
**Objective**: Test PDF text extraction + classification
**Steps**:
1. Create test PDF:
   - A2: Digital document (good test)
   - B2: Scanned PDF (bad test - should show limitation)
2. Upload to `/api/ingest/ocr-and-classify`
3. Verify text extraction and classification

**Test Cases**:
- **Case A**: Digital PDF (text selectable)
  - **Expected**: Full text extracted, classified correctly

- **Case B**: Scanned PDF (image)
  - **Expected**: Error or "PDF is scanned, try digital version"

- **Case C**: Corrupt/encrypted PDF
  - **Expected**: Helpful error, not crash

**Failure Modes to Watch**:
- "pypdf not installed" error → Should be caught at startup
- PDF opens but no text extracted → Silent failure
- Wrong MIME type detection → Check for .pdf extension fallback

---

### Workflow 5: CSV Bulk Ingest ✅ READY
**Objective**: Test CSV upload + batch classification
**Steps**:
1. Create test CSV:
   ```
   company_name,company_website,signal_text
   TechStartup1,techstartup1.in,"Hiring marketing manager, 2 person team, struggling with customer acquisition"
   FashionD2C,fashiond2c.in,"D2C skincare, $100k MRR, need growth hacker"
   EnterpriseCorp,large-corp.com,"Looking to hire 10 marketing VPs, Series C funded"
   ```

2. Upload to `/api/ingest/csv`
3. Verify:
   - All 3 rows processed
   - Scores assigned (row 1&2 high, row 3 low)
   - Leads created with company info
   - Error handling if rows fail

**Test Cases**:
- **Case A**: Valid CSV
  - **Expected**: 3 leads created, summary shows all processed

- **Case B**: CSV with missing "signal_text" column
  - **Expected**: Error message listing required columns

- **Case C**: CSV with non-UTF-8 encoding
  - **Expected**: Either process or show encoding error

- **Case D**: Empty CSV
  - **Expected**: Message "0 rows processed", not error

**Failure Modes to Watch**:
- CSV silently processes 0 rows → Header mismatch, needs error
- Some rows error but response says "all created" → Error tracking broken
- No indication of which rows failed → Need per-row error details

---

### Workflow 6: ICP Management ✅ READY
**Objective**: Test ICP creation, listing, and usage in classification
**Steps**:
1. Create ICP "Chaos Startups" (scenario that should trigger dossier)
   - Industries: "saas", "d2c"
   - Pain keywords: "chaos", "disorganized", "scaling"
   - Hiring keywords: "ops", "cmo", "marketer"

2. Create another ICP "Enterprise Only"
   - Size: "11-20"
   - Industries: "consulting"

3. List ICPs → Should show both

4. Edit first ICP → Change name to "Scaling Chaos"

5. Delete second ICP

6. Classify signal with "Chaos Startups" context → Should match

**Failure Modes to Watch**:
- ICP creation returns 500 error → DB issue
- Created ICP not returned in list → Query missing
- Classification ignores ICP keywords → Context not passed to model
- Edit/delete not reflected immediately → Cache issue

---

### Workflow 7: Lead Lifecycle ✅ READY
**Objective**: Test lead status workflow and deletion
**Steps**:
1. From Workflow 2, take the RED HOT lead (Signal A)
2. Navigate to Leads page
3. Filter by score: 70+
4. Find the lead created in Workflow 2
5. Click to view details
6. Status journey:
   - Change from "new" → "contacted"
   - Change from "contacted" → "qualified"
   - Change from "qualified" → "pitched"
   - Change from "pitched" → "won"
7. Verify each change persists (refresh page)
8. Delete the lead (confirm dialog)
9. Verify lead removed from list

**Failure Modes to Watch**:
- Status dropdown doesn't update → API call not wired
- Update succeeds but page doesn't refresh → State sync issue
- Delete doesn't show confirm dialog → UX broken
- Deleted lead still appears until page refresh → Cache issue
- Database error on delete → Constraint violation

---

## Results Template

**After each workflow, record**:
```
Workflow: [Number & Name]
Status: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL
Issues Found: [list]
Error Messages: [copy-paste]
Screenshots: [if relevant]
Recommendation: [fix needed?]
```

---

## Summary of What We're Testing

1. **System Startup**: Can all services start without crashing?
2. **Model Integration**: Is Ollama actually running classification?
3. **Error Handling**: Do we gracefully handle missing dependencies?
4. **Data Flow**: Does signal → classification → lead work end-to-end?
5. **File Processing**: Do OCR and CSV handling work correctly?
6. **Data Validation**: Do we catch bad inputs?
7. **UI Responsiveness**: Does frontend respond to API changes?
8. **Graceful Degradation**: If something fails, do users understand why?

---

## Next Steps After Testing

If **all 7 workflows PASS**: Jump to PHASE C (Hardening)
If **issues found**: Document, then:
1. PHASE C: Fix critical issues (crashes, silent failures)
2. PHASE D: Improve error messages
3. PHASE E: Update documentation

---

Last Updated: 2025-11-16
Phase Status: READY TO EXECUTE
