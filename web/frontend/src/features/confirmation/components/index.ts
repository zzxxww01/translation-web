/**
 * 分段确认工作流 - 组件导出
 */

export { ConfirmationFeature } from '../index';

// Panels
export { SourcePanel } from './panels/SourcePanel';
export { VersionsPanel } from './panels/VersionsPanel';
export { AIInsightPanel } from './panels/AIInsightPanel';
export { RetranslatePanel } from './panels/RetranslatePanel';

// Cards
export { VersionCard } from './cards/VersionCard';
export { EditCard } from './cards/EditCard';

// Modals
export { ImportVersionModal } from './modals/ImportVersionModal';
export { AlignmentModal } from './modals/AlignmentModal';
export { GlossaryModal } from './modals/GlossaryModal';
export { RetranslateOptionsModal } from './modals/RetranslateOptionsModal';

// Common
export { ProgressBar } from './common/ProgressBar';
export { NavigationControls } from './common/NavigationControls';
export { KeyboardShortcutsHelp } from './common/KeyboardShortcutsHelp';
export { ConfirmationErrorBoundary } from './common/ConfirmationErrorBoundary';
export { Skeleton, VersionCardSkeleton, ParagraphSkeleton } from './common/Skeleton';
