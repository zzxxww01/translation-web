# Terminology System Cleanup Decision

## Current Status

✅ Migration completed: 513 terms migrated successfully
✅ New system operational: GlossaryStorage, Term, TermMetadata models working
✅ Validation passed: All 4 validation checks passed
⚠️ Old system still present: Old code still exists and is importable

## Analysis Results

### Old System Usage
- **API Routes**: 31 router files exist, at least 2 use old GlossaryManager
  - `src/api/routers/glossary.py` - Global glossary API (old system)
  - `src/api/routers/project_glossary.py` - Project glossary API (old system)
- **Services**: Multiple services still import old GlossaryManager
  - `src/services/terminology_review_service.py`
  - `src/services/confirmation_service.py`
  - `src/api/utils/glossary.py`
- **Dependencies**: `src/api/dependencies.py` provides GlossaryManagerDep

### New System Usage
- **Core Translation**: `four_step_translator.py` uses new system ✅
- **Session Management**: TranslationSessionService integrated ✅
- **Term Services**: Only 3 files currently use new session service

## Decision: DEFER CLEANUP

### Rationale

1. **Migration Just Completed**: The data migration finished successfully, but we haven't verified that all production workflows work with the new system.

2. **API Routes Still Active**: The old API routes (`/glossary`, `/projects/{id}/glossary`) are likely still being used by frontend or external clients. Removing them would break existing integrations.

3. **Dual System Period Needed**: We need a transition period where:
   - Old API routes continue to work (reading from old storage)
   - New system is used for new translations
   - Both systems coexist until all clients migrate

4. **Risk of Breaking Changes**: Removing old code now could:
   - Break existing API clients
   - Break CLI tools that depend on old system
   - Cause production issues we haven't discovered yet

### Recommended Next Steps

**Phase 1: Verification (Current Phase - Complete)**
- ✅ Data migration completed
- ✅ Validation passed
- ✅ New storage system operational

**Phase 2: Integration Testing (Next Phase - TODO)**
- Test all translation workflows with new system
- Verify API routes work correctly
- Test CLI commands
- Run full integration test suite

**Phase 3: API Migration (Future Phase - TODO)**
- Create new API routes using GlossaryStorage
- Deprecate old API routes (but keep them working)
- Update API documentation
- Notify API clients of deprecation

**Phase 4: Cleanup (Future Phase - TODO)**
- Remove old API routes after deprecation period
- Remove old GlossaryManager and related code
- Remove old models
- Clean up imports

## What to Do Now

### Mark Old System Files for Future Removal

Create a marker file listing all old system files to be removed later:

```
src/core/glossary.py
src/core/models/glossary.py
src/core/term_matcher.py
src/api/routers/glossary.py (after creating new version)
src/api/routers/project_glossary.py (after creating new version)
src/api/utils/glossary.py
src/services/terminology_review_service.py (if not updated)
src/services/confirmation_service.py (if not updated)
```

### Update Documentation

Document that:
1. New storage system is active for translations
2. Old API routes still work but are deprecated
3. Migration to new API routes is planned
4. Old system will be removed in future release

## Conclusion

**DO NOT remove old code yet.** The migration is complete and successful, but we need to ensure system stability and give API clients time to migrate before removing old code.

This is the safe, professional approach that minimizes risk of production issues.
