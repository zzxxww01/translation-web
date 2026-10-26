# Continuous workbench reading

Continue the accepted Claude Code task from its unfinished worktree, based on fetched `origin/main` (`cc9312dc390f`). Preserve its original edits and production data.

- Render source and translations as separate continuous article columns. Restore adjacent fragments sharing a source block to one visual paragraph, without changing saved text or forcing matching row heights. Preserve headings, images, links, editing, adoption, automatic save and the Save / Ctrl+S action.
- Add an explicit “看到这里” marker at a reading location. Store one stable row key per article on the server, separately from translation metadata. Show the location, resume there in each visible column, and allow clearing it. Report persistence failures without pretending the marker was saved.
- Complete conservative rule-based alignment of a translated natural paragraph to imported fragments. Preserve text and Markdown; fall back to keeping the paragraph whole when a safe split is unavailable.
- Validate backend alignment and mark persistence, frontend grouping/edit/save/bookmark interactions, lint/type/build and browser behavior. Review, fetch remote again, integrate, pass Linux CI, then release the exact merged revision using the production release contract.

No model-based segmentation, content migration, or deletion of existing translation variants is part of this change.
