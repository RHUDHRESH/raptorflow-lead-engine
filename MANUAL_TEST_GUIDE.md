# Manual Testing Guide - PHASE B Execution

## Prerequisites Checklist

Before starting, verify you have:

- [ ] Python 3.9+ installed (`python --version`)
- [ ] Ollama installed and Gemma 3 1B/4B models downloaded
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Backend dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] Frontend dependencies installed (`npm install` in project root)
- [ ] Tesseract OCR installed (Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki)

## Quick Setup (Run These in Order)

### Step 1: Start Ollama
```bash
# Windows: Open Command Prompt or PowerShell
ollama serve
# You should see: "Listening on 127.0.0.1:11434"
```
**Keep this terminal open. Do NOT close it.**

### Step 2: Start Backend (New Terminal)
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Expected Output**:
```
🚀 Initializing Raptorflow Lead Engine...
📡 Checking Ollama models...
✅ System ready!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**If you see errors**:
- "Ollama refused connection" → Make sure Ollama is running in Step 1
- "Module not found" → Run `pip install -r requirements.txt` again
- "TesseractNotFoundError" → Install Tesseract, add to PATH
- "pypdf module not found" → Run `pip install pypdf==4.0.1`

**Keep this terminal open. Do NOT close it.**

### Step 3: Start Frontend (New Terminal)
```bash
# Make sure you're in the project root
npm install
npm run dev
```

**Expected Output**:
```
  ▲ Next.js 14.2.5
  - Local:        http://localhost:3000
  ✓ Ready in 3.2s
```

Open browser and go to: **http://localhost:3000/dashboard**

**If you see errors**:
- "CORS error" → Backend not running, start Step 2 again
- "API connection refused" → Check backend is on port 8000
- Page loads but no data → Check browser console (F12) for errors

**You should now have all 3 services running!**

---

## Workflow 1: Verify Stack is Running ✅

### Test A: Backend Health Check
```bash
# Open a new PowerShell/Command Prompt and run:
curl http://localhost:8000/
```

**Expected Response**:
```json
{
  "status": "ok",
  "service": "Raptorflow Lead Engine",
  "version": "0.1.0"
}
```

### Test B: Frontend Loads
- Navigate to http://localhost:3000/dashboard
- **Expected**: Dashboard shows "Lead Pipeline" with 4 empty cards (0 red hot, 0 warm, etc.)

### Test C: API Connection
- Open browser DevTools (F12)
- Go to Network tab
- **Expected**: No 500 errors, CORS errors, or "Connection refused" messages

---

## Workflow 2: Manual Signal Classification

### Test A: Create ICP Profile
1. Click "📋 ICP Profiles" tab (or navigation)
2. Click "+ New Profile"
3. Fill in:
   - **Profile Name**: "Micro D2C Brands"
   - **Description**: "Early-stage D2C brands struggling with marketing"
   - **Company Size**: Check "1" and "2-5"
   - **Industries**: Check "d2c" and "ecommerce"
   - **Channels**: Check "tiktok", "instagram", "email"
4. Click "Save Profile"
5. **Expected**: Profile appears in list on left

### Test B: Classify STRONG Signal
1. Navigate to "📸 OCR Ingest" tab or manual classification endpoint
2. **If using frontend**: Find the Signal Classification section
3. **If using curl**:
   ```bash
   curl -X POST http://localhost:8000/api/classify/signal \
     -H "Content-Type: application/json" \
     -d '{
       "signal_text": "Hiring: Growth Marketer. We are a 3-person D2C skincare brand, launched 6 months ago. Currently spending $500/month on ads with 2% ROAS. Our founder is doing all marketing but burning out. Need someone to help with TikTok and email strategy. Location: India.",
       "company_name": "SkinGlow D2C",
       "company_website": "skinglow.in"
     }'
   ```

4. **Expected Response**:
   ```json
   {
     "icp_match": true,
     "total_score": 75-85,
     "score_bucket": "red_hot",
     "lead_id": 1,
     "classification": {
       "role_type": "first_marketer" or "extra_headcount",
       "pain_tags": ["marketing_pain", "hiring_growth", "founder_burnout"],
       "score_fit": 40-50,
       "score_pain": 30-40
     }
   }
   ```

5. **Record**:
   - ✅ PASS if score >= 75 and bucket is "red_hot"
   - ❌ FAIL if score < 60 or bucket is not "red_hot"
   - ⚠️ PARTIAL if classification works but ICP matching is off

### Test C: Classify WEAK Signal
```bash
curl -X POST http://localhost:8000/api/classify/signal \
  -H "Content-Type: application/json" \
  -d '{
    "signal_text": "We are growing our enterprise SaaS team in California. Just funded Series C, hiring 50 engineers.",
    "company_name": "EnterpriseScale Inc",
    "company_website": "enterprisescale.com"
  }'
```

**Expected**:
- score: 20-30
- bucket: "parked"
- icp_match: false

### Test D: Edge Case - Empty Signal
```bash
curl -X POST http://localhost:8000/api/classify/signal \
  -H "Content-Type: application/json" \
  -d '{
    "signal_text": "",
    "company_name": "NoInfo Inc"
  }'
```

**Expected**:
- Either error message OR
- score: 0 with note "No valid data"
- NOT: Server crash

### Test E: Edge Case - Very Long Signal
```bash
# Create a file with 5000 words of marketing content
# Then classify it
```

**Expected**:
- Should complete in < 30 seconds OR
- Return timeout error with message "Model processing took too long"
- NOT: OOM or crash

---

## Workflow 3: OCR Image Upload

### Preparation
1. Create a test image:
   - Take screenshot of job posting or business card
   - Or download a sample image with text
   - Save as `test.jpg` or `test.png`

### Test A: Upload Image
```bash
curl -X POST http://localhost:8000/api/ingest/ocr \
  -F "file=@test.jpg"
```

**Expected Response**:
```json
{
  "extracted_text": "[text from image]",
  "detected_emails": ["email@example.com"],
  "detected_phones": ["+919876543210"],
  "detected_names": ["Name", "Person"],
  "detected_company": "CompanyName"
}
```

**Record**:
- ✅ PASS if text extracted correctly
- ⚠️ PARTIAL if some contact info missing
- ❌ FAIL if no text extracted or error

### Test B: OCR + Classify
```bash
curl -X POST http://localhost:8000/api/ingest/ocr-and-classify \
  -F "file=@test.jpg" \
  -F "company_name=TestCompany"
```

**Expected**: Should return ClassificationResult with lead_id and score

---

## Workflow 4: PDF Upload

### Preparation
1. Create a test PDF:
   - Option A: Digital PDF (selectable text) - BEST TEST
   - Option B: Scanned PDF (image) - Should show graceful failure

### Test A: Upload Digital PDF
```bash
curl -X POST http://localhost:8000/api/ingest/ocr-and-classify \
  -F "file=@document.pdf" \
  -F "company_name=PDFCompany"
```

**Expected**:
- ✅ PASS: Full text extracted and classified
- ⚠️ PARTIAL: Partial text but classified
- ❌ FAIL: Error or silent failure

### Test B: Upload Scanned PDF
**Expected**: Error message or note "PDF appears to be scanned. Extract text failed."

---

## Workflow 5: CSV Bulk Import

### Preparation
Create `test.csv`:
```csv
company_name,company_website,signal_text
TechStartup1,techstartup1.in,Hiring marketing manager. We are 2 person team struggling with customer acquisition in India.
FashionD2C,fashiond2c.in,D2C skincare brand. $100k MRR. Need growth hacker. Based in Bangalore.
EnterpriseCorp,large-corp.com,Looking to hire 10 marketing VPs. Series C funded. California.
```

### Test A: Valid CSV
```bash
curl -X POST http://localhost:8000/api/ingest/csv \
  -F "file=@test.csv"
```

**Expected Response**:
```json
{
  "total_processed": 3,
  "total_created": 3,
  "results": [
    {"company": "TechStartup1", "score": 75.5, "bucket": "red_hot", "status": "created"},
    {"company": "FashionD2C", "score": 70.2, "bucket": "red_hot", "status": "created"},
    {"company": "EnterpriseCorp", "score": 25.1, "bucket": "parked", "status": "created"}
  ]
}
```

**Record**:
- ✅ PASS if all 3 rows processed and scores correct
- ⚠️ PARTIAL if some rows fail
- ❌ FAIL if 0 rows processed or generic error

### Test B: Invalid CSV (Missing Column)
Create `bad.csv`:
```csv
company_name,company_website,wrong_column
TechStartup1,techstartup1.in,Some text
```

**Expected**: Error message saying "Missing required column: signal_text"

---

## Workflow 6: ICP Management

### Test A: Create ICP
```bash
curl -X POST http://localhost:8000/api/icp \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Scaling Chaos",
    "description": "Disorganized startups in growth phase",
    "size_buckets": ["2-5", "6-10"],
    "industries": ["saas", "d2c"],
    "locations": ["india"],
    "hiring_keywords": ["cmo", "ops", "marketer"],
    "pain_keywords": ["chaos", "disorganized", "scaling"]
  }'
```

**Expected**: Returns ICP object with id

### Test B: List ICPs
```bash
curl http://localhost:8000/api/icp/
```

**Expected**: Array with the ICP created above

### Test C: Use in Classification
Classify a signal that mentions "disorganized" and see if ICP matches

---

## Workflow 7: Lead Lifecycle

### Test A: View Leads
1. Go to http://localhost:3000/leads (or navigate to Leads tab)
2. **Expected**: Should show the leads created in previous workflows

### Test B: Update Status
1. Click on a lead (select one from the list)
2. In the detail panel, find Status dropdown
3. Change from "new" → "contacted"
4. **Expected**: Status updates immediately

### Test C: Delete Lead
1. Select a lead
2. Click "Delete" button
3. Confirm deletion
4. **Expected**: Lead removed from list

---

## Test Results Template

Copy this for each workflow:

```
=== WORKFLOW [NUMBER]: [NAME] ===
Date: [Date]
Backend: http://localhost:8000
Frontend: http://localhost:3000

TEST A: [Test Name]
Status: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL
Details: [What happened]
Score: [Expected vs Actual]

TEST B: [Test Name]
Status: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL
Details: [What happened]

ISSUES FOUND:
- [List any problems]

LOGS:
[Copy any error messages from backend terminal]

RECOMMENDATIONS:
[What should be fixed]
```

---

## Common Errors & Solutions

### Error: "Ollama refused connection"
**Solution**: Start Ollama first. Open new PowerShell and run `ollama serve`

### Error: "No module named 'pytesseract'"
**Solution**:
```bash
pip install pytesseract
# On Windows, also download Tesseract from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

### Error: "TesseractNotFoundError"
**Solution**: Tesseract binary not found. Set path in Windows or environment

### Error: "pypdf module not found"
**Solution**:
```bash
pip install pypdf==4.0.1
```

### Error: "CORS error in browser"
**Solution**: Backend not running or frontend can't reach it
- Verify backend is on http://localhost:8000
- Check firewall not blocking port 8000
- Check browser console for exact error

### Error: "Database is locked"
**Solution**: You have raptorflow_leads.db open elsewhere
- Close other terminals with backend running
- Delete raptorflow_leads.db to start fresh

### Error: "Model not found: gemma3:1b"
**Solution**: Ollama model not pulled yet
```bash
ollama pull gemma3:1b
ollama pull gemma3:4b
```

---

## Success Criteria

**WORKFLOW PASSES if**:
1. Backend starts without crashing
2. Frontend loads and connects to backend
3. Classification produces valid scores (0-100)
4. OCR extracts text correctly
5. CSV processes multiple rows
6. ICP creation and listing work
7. Lead status updates and deletion work

**If any workflow has ❌ FAIL status**: Note the error and skip to PHASE C (Hardening)

---

## Next Steps

After completing all 7 workflows:

**If all PASS**: Great! System is functional. Move to PHASE C.

**If some FAIL**: Document the failures and we'll fix them in PHASE C before proceeding.

Created: 2025-11-16
Updated: Manual testing guide for Windows
