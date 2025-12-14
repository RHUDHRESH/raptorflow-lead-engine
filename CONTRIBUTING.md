# Contributing to Raptorflow Lead Engine

Thanks for your interest! This is a lean, local-first system. Keep it simple.

## Setup

### Requirements
- Python 3.11+ (3.9+ minimum, but 3.11+ recommended)
- Node.js 20+ (18+ minimum)
- Ollama with Gemma 3 1B/4B models

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
npm install
npm run dev

# Ollama (another terminal)
ollama serve
```

Both API and frontend should run on localhost (8000 and 3000).

## Code Style

### Python
- Use type hints (PEP 484)
- Keep functions small (<50 lines)
- Add docstrings for public functions
- Use f-strings for formatting

### TypeScript/React
- Use functional components
- Keep components under 200 lines
- Export types in `.ts` files, not in `.tsx`
- Use TailwindCSS for styling (no CSS files)

## Testing

Before submitting changes:

```bash
# Run the 7 workflows from MANUAL_TEST_GUIDE.md
# Verify no regressions
```

Key workflows:
1. Signal classification (manual)
2. Image OCR
3. PDF extraction
4. CSV import
5. ICP management
6. Lead status updates
7. Lead deletion

## Commits

- Keep commits small and focused
- Write clear commit messages
- Reference the issue or feature (if applicable)

Example:
```
Fix: CSV header validation should show found columns
- Add column list to error response
- Closes #42
```

## Architecture Notes

### Backend Structure
- `main.py` – Entry point, startup, middleware
- `database.py` – Models, ORM setup
- `routers/` – API endpoints (classify, ingest, icp, leads)
- `ollama_wrapper.py` – Model integration
- `config.py` – Settings from .env
- `dependency_check.py` – Startup validation
- `error_handler.py` – Error response formatting

### Key Constraints
- **Local-only**: No external API calls except Ollama
- **SQLite**: Keep database lightweight (no migrations needed)
- **Ollama**: Always use timeout=5.0 for checks, 300.0 for classification
- **Errors**: Always return JSON with `error: true`, `code`, `message`, `detail`

### Frontend Structure
- `lib/api.ts` – API client (single source of truth)
- `components/` – React components (one file per component)
- `app/` – Next.js pages and layout

## Common Tasks

### Add a New API Endpoint

1. Create in `routers/` (e.g., `routers/new_feature.py`)
2. Define Pydantic model for input/output
3. Add to `main.py` via `app.include_router()`
4. Implement error handling with HTTPException
5. Add curl example to docs

Example:
```python
# routers/my_feature.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class MyRequest(BaseModel):
    field: str

@router.post("/myendpoint")
async def my_endpoint(req: MyRequest):
    if not req.field:
        raise HTTPException(status_code=400, detail="Field required")
    return {"result": req.field}
```

### Add a New React Component

1. Create in `components/` (e.g., `components/MyComponent.tsx`)
2. Use TypeScript, add types for props
3. Use `lib/api.ts` for backend calls
4. Style with TailwindCSS
5. Add to page where needed

Example:
```typescript
// components/MyComponent.tsx
import { useState } from 'react';
import { myApiCall } from '@/lib/api';

export default function MyComponent() {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      const result = await myApiCall();
      // Handle result
    } finally {
      setLoading(false);
    }
  };

  return <button onClick={handleClick}>Do Something</button>;
}
```

## When to File an Issue

- Bug: reproducible error with steps
- Enhancement: clear problem statement + proposed solution
- Question: ask in discussion, not issues

## Pull Request Process

1. Fork or create a branch
2. Make your changes
3. Test with the 7 workflows (no regressions)
4. Submit PR with clear description
5. Link any related issues

## What NOT to Change (MVP Frozen)

These are intentionally constrained for the MVP:

- ❌ Add new ML models (stick with Gemma 3 1B/4B)
- ❌ Add cloud storage (stay local)
- ❌ Add authentication (single-user only)
- ❌ Migrate to Postgres (SQLite for MVP)
- ❌ Add websockets (keep HTTP/REST)

For Phase 2, we'll revisit these.

## Questions?

Open an issue or check `docs/WORK_SUMMARY.md` for context on decisions made.

---

**Keep it lean. Keep it local. Keep it simple.**
