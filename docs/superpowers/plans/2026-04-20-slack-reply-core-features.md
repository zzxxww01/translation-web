# Slack Reply UX Redesign - Phase 1: Core Features (P0)

**Created:** 2026-04-20  
**Status:** Ready for Implementation  
**Related Spec:** [2026-04-19-slack-reply-ux-redesign.md](../specs/2026-04-19-slack-reply-ux-redesign.md)

## Overview

This plan implements the P0 core functionality from the Slack Reply UX redesign:
- Version card inline editing with single-version refinement
- Unified workspace for both scenarios (incoming/draft)
- Three adjustment methods: direct selection, regeneration, inline editing

## Implementation Strategy

**Approach:** TDD with incremental commits  
**Testing:** Unit tests → Integration tests → Manual verification  
**Rollout:** Feature flag controlled (default: enabled)

---

## Phase 1: Backend Foundation

### Step 1.1: Add `style` field to `SlackReplyVariant`

**File:** `src/api/routers/slack_models.py`

```python
class SlackReplyVariant(BaseModel):
    version: str
    english: str
    chinese: str = ""
    style: str = ""  # NEW: "简洁" | "正式" | "友好"
```

**Test:** Verify model validation accepts `style` field

```bash
pytest tests/api/test_slack_models.py::test_variant_with_style -v
```

**Commit:** `feat(slack): add style field to SlackReplyVariant`

---

### Step 1.2: Create `/api/slack/refine-version` endpoint

**File:** `src/api/routers/slack_refine_version.py` (new)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.api.routers.slack_models import SlackReplyVariant

router = APIRouter()

class RefineVersionRequest(BaseModel):
    original_variant: SlackReplyVariant
    chinese_edit: str

class RefineVersionResponse(BaseModel):
    refined_variant: SlackReplyVariant

@router.post("/refine-version")
async def refine_version(req: RefineVersionRequest) -> RefineVersionResponse:
    """Refine a single version based on edited Chinese text."""
    # TODO: Call LLM to translate chinese_edit → english
    # Preserve version and style from original_variant
    pass
```

**Register route in:** `src/api/main.py`

```python
from src.api.routers import slack_refine_version
app.include_router(slack_refine_version.router, prefix="/api/slack", tags=["slack"])
```

**Test:** API contract test

```bash
pytest tests/api/test_slack_refine_version.py::test_refine_version_endpoint -v
```

**Commit:** `feat(slack): add refine-version API endpoint`

---

### Step 1.3: Implement LLM translation logic

**File:** `src/api/routers/slack_refine_version.py`

```python
from src.llm.client import get_llm_client

async def refine_version(req: RefineVersionRequest) -> RefineVersionResponse:
    client = get_llm_client()
    
    prompt = f"""Translate the following Chinese text to English, maintaining the style: {req.original_variant.style}

Chinese: {req.chinese_edit}

Return only the English translation, no explanations."""

    english_refined = await client.generate(prompt)
    
    return RefineVersionResponse(
        refined_variant=SlackReplyVariant(
            version=req.original_variant.version,
            english=english_refined.strip(),
            chinese=req.chinese_edit,
            style=req.original_variant.style,
        )
    )
```

**Test:** Integration test with mock LLM

```bash
pytest tests/api/test_slack_refine_version.py::test_refine_preserves_style -v
```

**Commit:** `feat(slack): implement LLM translation in refine-version`

---

### Step 1.4: Update existing endpoints to include `style`

**Files to modify:**
- `src/api/routers/slack_process.py` → Add style labels to `suggested_replies`
- `src/api/routers/slack_compose.py` → Add style labels to `versions`

**Example change in `slack_compose.py`:**

```python
# After LLM generates versions A/B/C
versions = [
    SlackReplyVariant(version="A", english=..., chinese=req.content, style="简洁"),
    SlackReplyVariant(version="B", english=..., chinese=req.content, style="正式"),
    SlackReplyVariant(version="C", english=..., chinese=req.content, style="友好"),
]
```

**Test:** Verify style labels in responses

```bash
pytest tests/api/test_slack_compose.py::test_compose_includes_style -v
pytest tests/api/test_slack_process.py::test_process_includes_style -v
```

**Commit:** `feat(slack): add style labels to compose and process endpoints`

---

## Phase 2: Frontend State Management

### Step 2.1: Update frontend types

**File:** `web/frontend/src/features/slack/types.ts`

```typescript
export interface RefinementVariant {
  version: string;
  english: string;
  chinese: string;
  style: string; // NEW
}

export interface VersionEditState {
  versionId: string;
  isEditing: boolean;
  editedChinese: string;
  isRefining: boolean;
  error: string | null;
}
```

**Commit:** `feat(slack): add style and edit state to frontend types`

---

### Step 2.2: Add edit state to Zustand store

**File:** `web/frontend/src/features/slack/store.ts`

```typescript
interface SlackState {
  // ... existing fields
  versionEditStates: Record<string, VersionEditState>;
  
  // Actions
  startEditingVersion: (versionId: string, currentChinese: string) => void;
  updateEditedChinese: (versionId: string, chinese: string) => void;
  cancelEditingVersion: (versionId: string) => void;
  setVersionRefining: (versionId: string, isRefining: boolean) => void;
  setVersionError: (versionId: string, error: string | null) => void;
}

export const useSlackStore = create<SlackState>()(
  persist(
    (set) => ({
      versionEditStates: {},
      
      startEditingVersion: (versionId, currentChinese) =>
        set((state) => ({
          versionEditStates: {
            ...state.versionEditStates,
            [versionId]: {
              versionId,
              isEditing: true,
              editedChinese: currentChinese,
              isRefining: false,
              error: null,
            },
          },
        })),
      
      // ... implement other actions
    }),
    { name: 'slack-store', partialize: (state) => ({ selectedModel: state.selectedModel }) }
  )
);
```

**Test:** Zustand store unit tests

```bash
npm test -- store.test.ts
```

**Commit:** `feat(slack): add version edit state management`

---

### Step 2.3: Create `useRefineVersion` hook

**File:** `web/frontend/src/features/slack/hooks.ts`

```typescript
export function useRefineVersion() {
  const { versionEditStates, setVersionRefining, setVersionError, updateCurrentVersions } = useSlackStore();
  
  return useMutation({
    mutationFn: async ({ 
      originalVariant, 
      chineseEdit 
    }: { 
      originalVariant: RefinementVariant; 
      chineseEdit: string 
    }) => {
      const response = await fetch('/api/slack/refine-version', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_variant: originalVariant,
          chinese_edit: chineseEdit,
        }),
      });
      
      if (!response.ok) throw new Error('Refinement failed');
      
      const data = await response.json();
      return data.refined_variant as RefinementVariant;
    },
    
    onMutate: ({ originalVariant }) => {
      setVersionRefining(originalVariant.version, true);
    },
    
    onSuccess: (refinedVariant) => {
      // Update the specific version in currentVersions
      updateCurrentVersions((versions) =>
        versions.map((v) =>
          v.version === refinedVariant.version ? refinedVariant : v
        )
      );
      setVersionRefining(refinedVariant.version, false);
    },
    
    onError: (error, { originalVariant }) => {
      setVersionError(originalVariant.version, error.message);
      setVersionRefining(originalVariant.version, false);
    },
  });
}
```

**Test:** Hook integration test with MSW

```bash
npm test -- hooks.test.ts
```

**Commit:** `feat(slack): add useRefineVersion hook`

---

## Phase 3: UI Components

### Step 3.1: Update `VersionCard` with inline editing

**File:** `web/frontend/src/features/slack/components/VersionCard.tsx`

**Key changes:**
1. Add "Edit" button next to version label
2. Toggle between display mode and edit mode
3. In edit mode: show Textarea for Chinese + Save/Cancel buttons
4. Call `useRefineVersion` on Save
5. Show loading spinner during refinement
6. Display error message if refinement fails

**Pseudo-code:**

```typescript
export function VersionCard({ variant }: { variant: RefinementVariant }) {
  const editState = useSlackStore((s) => s.versionEditStates[variant.version]);
  const { startEditingVersion, updateEditedChinese, cancelEditingVersion } = useSlackStore();
  const refineMutation = useRefineVersion();
  
  const handleEdit = () => startEditingVersion(variant.version, variant.chinese);
  
  const handleSave = () => {
    refineMutation.mutate({
      originalVariant: variant,
      chineseEdit: editState.editedChinese,
    });
  };
  
  const handleCancel = () => cancelEditingVersion(variant.version);
  
  if (editState?.isEditing) {
    return (
      <Card>
        <Textarea 
          value={editState.editedChinese}
          onChange={(e) => updateEditedChinese(variant.version, e.target.value)}
        />
        <Button onClick={handleSave} disabled={editState.isRefining}>
          {editState.isRefining ? <Spinner /> : 'Save'}
        </Button>
        <Button onClick={handleCancel}>Cancel</Button>
        {editState.error && <ErrorMessage>{editState.error}</ErrorMessage>}
      </Card>
    );
  }
  
  return (
    <Card>
      <div>{variant.style} - Version {variant.version}</div>
      <Button onClick={handleEdit}>Edit</Button>
      <p>{variant.chinese}</p>
      <p>{variant.english}</p>
    </Card>
  );
}
```

**Test:** Component test with React Testing Library

```bash
npm test -- VersionCard.test.tsx
```

**Commit:** `feat(slack): add inline editing to VersionCard`

---

### Step 3.2: Update `ReplyWorkspace` to show style labels

**File:** `web/frontend/src/features/slack/components/ReplyWorkspace.tsx`

**Change:** Pass `variant.style` to `VersionCard` and ensure it's displayed

**Commit:** `feat(slack): display style labels in ReplyWorkspace`

---

## Phase 4: Integration & Testing

### Step 4.1: End-to-end test

**Test scenario:**
1. User receives English message → generates 3 versions with styles
2. User clicks "Edit" on Version B
3. User modifies Chinese text
4. User clicks "Save" → API called → Version B updated
5. Verify Version A and C unchanged
6. User selects Version B → added to conversation history

**Test file:** `tests/e2e/slack_reply_workflow.spec.ts`

**Run:**
```bash
npm run test:e2e
```

**Commit:** `test(slack): add e2e test for version editing workflow`

---

### Step 4.2: Manual verification checklist

- [ ] Start dev server: `npm run dev`
- [ ] Navigate to Slack Reply feature
- [ ] Test incoming message scenario:
  - [ ] Enter English message → verify 3 versions generated with style labels
  - [ ] Click "Edit" on Version A → verify edit mode activated
  - [ ] Modify Chinese text → click "Save" → verify loading state
  - [ ] Verify Version A updated, B/C unchanged
  - [ ] Click "Cancel" during edit → verify reverts to display mode
- [ ] Test draft scenario:
  - [ ] Enter Chinese message → verify 3 versions generated
  - [ ] Edit Version C → verify same behavior as above
- [ ] Test error handling:
  - [ ] Disconnect network → try to save edit → verify error message shown
  - [ ] Verify error dismisses on retry

---

## Phase 5: Documentation & Deployment

### Step 5.1: Update API documentation

**File:** `docs/api/slack-endpoints.md`

Add documentation for `/api/slack/refine-version` endpoint.

**Commit:** `docs(slack): document refine-version API endpoint`

---

### Step 5.2: Update user guide

**File:** `docs/user-guide/slack-reply.md`

Add section explaining inline editing feature.

**Commit:** `docs(slack): add inline editing to user guide`

---

### Step 5.3: Create migration guide (if needed)

If breaking changes to existing data structures, create migration script.

**Commit:** `chore(slack): add migration for style field`

---

## Rollout Plan

1. **Merge to `main`** after all tests pass
2. **Deploy to staging** → manual QA
3. **Deploy to production** with feature flag enabled
4. **Monitor** error rates and user feedback for 48 hours
5. **Proceed to Phase 2** (visual enhancements) if stable

---

## Success Criteria

- [ ] All unit tests pass (>90% coverage)
- [ ] All integration tests pass
- [ ] E2E test passes
- [ ] Manual verification checklist completed
- [ ] No console errors in browser
- [ ] API response time <500ms for refine-version
- [ ] Zero crashes in production for 48 hours post-deploy

---

## Estimated Timeline

- Backend (Steps 1.1-1.4): 4 hours
- Frontend State (Steps 2.1-2.3): 3 hours
- UI Components (Steps 3.1-3.2): 4 hours
- Testing (Steps 4.1-4.2): 3 hours
- Documentation (Steps 5.1-5.3): 2 hours

**Total:** ~16 hours (2 working days)

---

## Next Steps After Phase 1

Once P0 features are stable, proceed to:
- **Phase 2:** Visual enhancements (Editorial style, typography, colors)
- **Phase 3:** Animation and micro-interactions
- **Phase 4:** Polish and accessibility improvements
