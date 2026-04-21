import { useEffect, useState } from 'react';
import { fullTranslationService } from '../services/fullTranslationService';
import type { TermConflictData } from '../services/fullTranslationService';

interface ConflictResolver {
  resolve: (value: { chosenTranslation: string; applyToAll: boolean }) => void;
}

export function useTermConflictDialog() {
  const [conflictDialogOpen, setConflictDialogOpen] = useState(false);
  const [currentConflict, setCurrentConflict] = useState<TermConflictData | null>(null);
  const [conflictResolver, setConflictResolver] = useState<ConflictResolver | null>(null);

  useEffect(() => {
    fullTranslationService.setTermConflictCallback(async conflict => {
      return new Promise(resolve => {
        setCurrentConflict(conflict);
        setConflictDialogOpen(true);
        setConflictResolver({ resolve });
      });
    });

    return () => {
      fullTranslationService.setTermConflictCallback(null);
    };
  }, []);

  const clearConflictState = () => {
    setConflictDialogOpen(false);
    setCurrentConflict(null);
    setConflictResolver(null);
  };

  const resolveConflict = (chosenTranslation: string, applyToAll: boolean = true) => {
    conflictResolver?.resolve({ chosenTranslation, applyToAll });
    clearConflictState();
  };

  const closeWithDefaultResolution = () => {
    if (conflictResolver && currentConflict) {
      conflictResolver.resolve({
        chosenTranslation: currentConflict.existing_translation,
        applyToAll: true,
      });
    }
    clearConflictState();
  };

  return {
    clearConflictState,
    closeWithDefaultResolution,
    conflictDialogOpen,
    conflictResolver,
    currentConflict,
    resolveConflict,
  };
}
