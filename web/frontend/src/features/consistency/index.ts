/**
 * 一致性审查功能模块
 */

export { ConsistencyReviewPanel } from './components/ConsistencyReviewPanel';
export { consistencyApi } from './api/consistencyApi';
export { useConsistencyReview } from './hooks/useConsistencyReview';
export type {
  ConsistencyIssue,
  ConsistencyReviewResult,
  TermStats,
  Suggestion,
} from './api/consistencyApi';
