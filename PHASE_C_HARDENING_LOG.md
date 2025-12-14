# PHASE C: Hardening - Changes Made

**Status**: ✅ IN PROGRESS (6 of 10 issues fixed)
**Date**: 2025-11-16
**Objective**: Fix critical/medium issues identified in PHASE B analysis

---

## Fixed Issues

### 🔴 CRITICAL #1: Ollama Connectivity Failure
**File**: `backend/main.py` (lifespan handler)
**What Was Wrong**:
- If Ollama not running, backend crashed with no helpful message
- User saw: Connection refused (confusing)

**What We Fixed**:
```python
# Added try/except around Ollama initialization
try:
    ollama_manager = OllamaManager()
    await ollama_manager.ensure_models_loaded()
except ConnectionError:
    print(f"⚠️  CRITICAL: Cannot connect to Ollama at {settings.ollama_base_url}")
    print(f"   Make sure Ollama is running: ollama serve")
    raise RuntimeError("Ollama not reachable...")
```

**Result**:
- ✅ Clear error message on startup if Ollama not running
- ✅ Instructions on how to fix it
- ✅ Backend fails fast instead of hanging

---

### 🔴 CRITICAL #2: Missing System Dependencies
**Files**:
- `backend/dependency_check.py` (NEW)
- `backend/main.py` (integrated)

**What Was Wrong**:
- Tesseract OCR not checked - image upload failed silently with 500 error
- pypdf not checked - PDF upload failed silently with 500 error
- No startup validation of system requirements

**What We Fixed**:
1. Created `dependency_check.py` with:
   - `check_tesseract()` - verifies Tesseract is installed
   - `check_pypdf()` - verifies pypdf library is available
   - `check_ollama_models()` - verifies Ollama is running
   - `run_startup_checks()` - runs all checks at startup

2. Integrated into main.py startup:
```python
if not run_startup_checks(...):
    raise RuntimeError("Critical dependencies missing...")
```

**Result**:
- ✅ Clear error messages on startup for missing dependencies
- ✅ Instructions on how to install each dependency
- ✅ System won't start until dependencies are available
- ✅ Users know what's wrong before trying to use it

---

### 🟠 MEDIUM #3: CSV Header Validation Missing
**File**: `backend/routers/ingest.py` (csv endpoint)
**What Was Wrong**:
- CSV without "signal_text" column silently processed 0 rows
- User saw: "Processed 0 rows, created 0 leads" (confusing, no error)
- User had to guess what went wrong

**What We Fixed**:
```python
# Validate CSV headers before processing
if not csv_reader.fieldnames or "signal_text" not in csv_reader.fieldnames:
    raise HTTPException(
        status_code=400,
        detail=f"CSV must have 'signal_text' column. Found columns: {csv_reader.fieldnames}. "
                "Required: signal_text, company_name (optional), company_website (optional)"
    )
```

**Result**:
- ✅ Clear error message listing required columns
- ✅ Shows what columns were found in user's CSV
- ✅ User knows exactly what to fix

---

### 🟠 MEDIUM #4: Signal Text Validation Missing
**File**: `backend/routers/classify.py` (classify_signal endpoint)
**What Was Wrong**:
- Empty signal text accepted → model gets empty prompt → returns score 0 silently
- Huge signal (1MB) accepted → potential model overload/timeout
- No feedback to user that something went wrong

**What We Fixed**:
```python
# Validate signal text at start
signal_text = signal.signal_text.strip()

if not signal_text:
    raise HTTPException(
        status_code=400,
        detail="Signal text cannot be empty. Please provide text to classify."
    )

if len(signal_text) > 50000:
    raise HTTPException(
        status_code=400,
        detail=f"Signal text too long ({len(signal_text)} chars). Max 50,000 characters."
    )
```

**Result**:
- ✅ Empty signals rejected with clear error
- ✅ Oversized signals rejected with clear error
- ✅ Prevents silent failures and model overload
- ✅ Users get immediate feedback

---

### 🟠 MEDIUM #5: Ollama Response Parsing Failures Hidden
**File**: `backend/ollama_wrapper.py` (classify_signal and generate_dossier methods)
**What Was Wrong**:
- Model returns invalid JSON → silently falls back to score 0
- User thinks signal is weak, actually model failed
- Developers can't debug without manually checking logs
- Log messages not prominent

**What We Fixed**:
1. Added detailed error logging:
```python
# When JSON parsing fails:
logger.error(f"🔴 1B Model response parsing failed: {error}")
logger.error(f"   Response text: {response[:300]}")
logger.warning("Using default classification (score: 0) as fallback")
```

2. More descriptive fallback messages in logs:
```
🔴 No JSON found in 1B model response
   Using default classification as fallback
```

3. Same improvements for 4B dossier generation

**Result**:
- ✅ Developers see clear 🔴 RED FLAGS in logs when models fail
- ✅ Easy to debug: see what response came back
- ✅ Clear indication of fallback being used
- ✅ Users can check logs to understand why score was 0

---

### 🟡 LOW #6: Health Check Endpoint Fake
**File**: `backend/main.py` (/health endpoint)
**What Was Wrong**:
- `/health` endpoint always returned "ollama": "checking..." hardcoded
- No actual verification that Ollama was running
- Users got false confidence that system was ready

**What We Fixed**:
```python
@app.get("/health")
async def health():
    """Full health check including Ollama status."""
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            if response.status_code == 200:
                ollama_status = "ok"
            else:
                ollama_status = f"error ({response.status_code})"
    except Exception as e:
        ollama_status = f"unreachable ({type(e).__name__})"

    return {
        "api": "ok",
        "ollama": ollama_status,
        "database": "ok",
        "timestamp": "...",
    }
```

**Result**:
- ✅ `/health` actually checks if Ollama is reachable
- ✅ Returns real status: "ok", "error (500)", "unreachable (ConnectionError)", etc.
- ✅ Users can verify system health before trying to use it
- ✅ Adds timestamp so you can check if health check is fresh

---

### 🟡 LOW #7: Error Messages Not Human-Readable
**Files**:
- `backend/error_handler.py` (NEW)
- `backend/main.py` (integrated)

**What Was Wrong**:
- Validation errors returned raw Pydantic JSON:
```json
{
  "detail": [
    {"loc": ["body", "signal_text"], "msg": "field required"}
  ]
}
```
- Generic 500 errors with no context
- Users can't understand what went wrong

**What We Fixed**:
1. Created `error_handler.py` with:
   - `validation_error_handler()` - formats validation errors nicely
   - `general_exception_handler()` - handles unexpected errors safely
   - `APIError` class - standard error response format

2. Integrated into main.py:
```python
register_error_handlers(app)
```

**Result**:
- ✅ Validation errors return human-readable format:
```json
{
  "error": true,
  "code": "VALIDATION_ERROR",
  "message": "Invalid request format",
  "details": {"signal_text": "field required"}
}
```
- ✅ Unexpected errors don't expose internal details
- ✅ All errors have standard format (code, message, detail)
- ✅ Developers can identify error types by code

---

## Not Yet Fixed (Next)

### 🟠 MEDIUM #8: Request Timeout Handling
**Issue**: Requests don't handle timeouts gracefully
**Status**: IN PROGRESS
**Next Step**: Add timeout wrapper with retry logic

### 🟠 MEDIUM #9: Frontend API URL Configuration
**Issue**: API URL hardcoded in docs, not in code
**Status**: Documented in MANUAL_TEST_GUIDE.md
**Next Step**: Create environment setup guide

### 🟠 MEDIUM #10: Batch Signal Endpoint Issues
**Issue**: Batch endpoint doesn't validate signals like single endpoint
**Status**: PENDING
**Next Step**: Apply same validation as single endpoint

---

## Summary of Changes

| Category | Change | Impact |
|----------|--------|--------|
| Startup | Added dependency checks | Users know what's missing before trying to use system |
| Errors | Better Ollama connectivity messages | Clear instructions when Ollama not running |
| Errors | Signal text validation | Prevents silent failures |
| Errors | CSV header validation | Clear error messages for wrong CSV format |
| Errors | Response parsing error logging | Developers can debug model failures |
| Health | Real Ollama connectivity check | Users can verify system health |
| Errors | Human-readable error responses | Users understand what went wrong |

---

## Files Modified

1. **backend/main.py**
   - Added Ollama error handling with clear messages
   - Integrated dependency checks at startup
   - Fixed health check to verify Ollama
   - Registered error handlers
   - Added imports for new modules

2. **backend/routers/classify.py**
   - Added signal text validation (empty, too long)
   - Validates before attempting classification

3. **backend/routers/ingest.py**
   - Added CSV header validation
   - Clear error messages for missing columns

4. **backend/ollama_wrapper.py**
   - Improved error logging in classify_signal()
   - Improved error logging in generate_dossier()
   - Added 🔴 emoji for error visibility in logs
   - Added response text in error logs for debugging

## Files Created

1. **backend/dependency_check.py** (NEW)
   - Checks Tesseract, pypdf, Ollama availability
   - Provides installation instructions
   - Runs at startup

2. **backend/error_handler.py** (NEW)
   - Custom error response formatting
   - Human-readable validation errors
   - Safe exception handling

---

## Testing These Changes

### How to Verify

1. **Test Ollama Error**:
   ```bash
   # Start backend WITHOUT Ollama running
   python main.py
   # Should see: "⚠️  CRITICAL: Cannot connect to Ollama..."
   ```

2. **Test Dependency Check**:
   - Tesseract will show error on startup if missing
   - pypdf will show warning if missing

3. **Test CSV Header Validation**:
   ```bash
   # Upload CSV without "signal_text" column
   curl -X POST http://localhost:8000/api/ingest/csv -F "file=@bad.csv"
   # Should see: "CSV must have 'signal_text' column. Found columns: ..."
   ```

4. **Test Signal Validation**:
   ```bash
   # Send empty signal
   curl -X POST http://localhost:8000/api/classify/signal \
     -H "Content-Type: application/json" \
     -d '{"signal_text": ""}'
   # Should see: "Signal text cannot be empty..."
   ```

5. **Test Health Check**:
   ```bash
   # Check health
   curl http://localhost:8000/health
   # Should show real Ollama status, not hardcoded "checking..."
   ```

---

## Impact on Testing

These changes make PHASE B testing much better:
- ✅ Clear error messages when things fail
- ✅ System validates input before attempting to process
- ✅ Ollama connectivity checked at startup (fail fast)
- ✅ Dependencies checked at startup
- ✅ Better logs for debugging failures

**User Experience**: Much clearer what went wrong and how to fix it

---

## Next: PHASE D (Code Cleanup)

After these hardening fixes, PHASE D will:
1. Remove dead code
2. Simplify error handling patterns
3. Add docstrings where missing
4. Review types and interfaces
5. Prepare for production

---

**Progress**: 7 of 10 issues fixed
**Status**: READY FOR TESTING
**Next Step**: Complete timeout handling, then document all changes

Created by Claude Code
PHASE C: Hardening In Progress 🔧
