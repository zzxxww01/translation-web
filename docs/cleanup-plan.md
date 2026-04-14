# Terminology System Cleanup Plan

## Overview

After successful migration of 513 terms to the new storage system, we need to remove obsolete old system code while preserving the new system.

## File Categorization

### OLD SYSTEM (To Remove) ❌

1. **Core Old System**
   - `src/core/glossary.py` - Old GlossaryManager class
   - `src/core/models/glossary.py` - Old Glossary, GlossaryTerm models
   - `src/core/models/enums.py` - Old TranslationStrategy enum (if only used by glossary)
   - `src/core/term_matcher.py` - Old term matcher (replaced by new matcher)

2. **API Routes (Old System)**
   - `src/api/routers/glossary.py` - Uses old GlossaryManager
   - `src/api/routers/project_glossary.py` - Uses old GlossaryManager
   - `src/api/utils/glossary.py` - Uses old GlossaryManager

3. **Services (Old System)**
   - `src/services/terminology_review_service.py` - Uses old GlossaryManager
   - `src/services/confirmation_service.py` - Uses old GlossaryManager (if exists)

4. **Dependencies**
   - `src/api/dependencies.py` - Contains GlossaryManagerDep (needs update)

### NEW SYSTEM (Keep) ✅

1. **Core New System**
   - `src/models/terminology.py` - New Term, TermMetadata, DecisionRecord
   - `src/services/glossary_storage.py` - New storage service
   - `src/services/term_matcher/` - New term matching engine
   - `src/services/term_extraction_service.py`
   - `src/services/term_conflict_detector.py`
   - `src/services/term_confirmation_service.py`
   - `src/services/translation_session_service.py`
   - `src/services/term_injection_service.py`
   - `src/services/term_validation_service.py`

2. **CLI (New System)**
   - `src/cli/glossary.py` - Uses new GlossaryStorage ✅

3. **Agents**
   - `src/agents/four_step_translator.py` - Uses new system

### SHARED/UTILITY (Analyze) ⚠️

1. **Prompt Generation**
   - `src/core/glossary_prompt.py` - May be used by both systems
   - `src/prompts/longform/terminology/` - Prompt templates

2. **Validation**
   - `src/services/glossary_validator.py` - May work with new system

## Files Using Old System

Based on grep results:
- `src/api/dependencies.py` - GlossaryManager dependency
- `src/api/routers/glossary.py` - Old models
- `src/api/routers/project_glossary.py` - Old models
- `src/api/utils/glossary.py` - Old GlossaryManager
- `src/core/term_matcher.py` - Old models
- `src/services/batch_translation_service.py` - infer_glossary_tags
- `src/services/confirmation_service.py` - Old GlossaryManager
- `src/services/source_metadata_service.py` - Old Glossary model
- `src/services/terminology_review_service.py` - Old GlossaryManager

## Cleanup Strategy

### Phase 1: Identify Dependencies
1. Check if any production code still depends on old system
2. Verify new system is fully integrated
3. Check test files for dependencies

### Phase 2: Safe Removal
1. Remove old core files
2. Remove old API routes (if not in use)
3. Update or remove dependent files
4. Clean up imports

### Phase 3: Verification
1. Run tests to ensure nothing breaks
2. Verify new system still works
3. Check for any remaining references

## Decision Points

### Question 1: Are old API routes still in use?
- If YES: Need to create new API routes using new system first
- If NO: Can remove directly

### Question 2: Is glossary_prompt.py used by new system?
- Need to check if it's compatible with new Term model
- May need to update or keep as utility

### Question 3: What about infer_glossary_tags?
- Used by batch_translation_service.py
- May need to extract as standalone utility

## Recommended Action

**CONSERVATIVE APPROACH:**
1. Do NOT remove files yet
2. First verify that new system is fully operational in production
3. Create new API routes if needed
4. Then proceed with removal in a separate phase

**REASON:** Migration just completed. Better to ensure stability before removing old code.

## Next Steps

1. Check if old API routes are actively used
2. Verify new system integration is complete
3. Run full test suite
4. Make removal decision based on findings
