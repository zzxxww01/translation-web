/**
 * 质量报告功能 - 集成说明
 *
 * 本文件说明如何在确认工作流中集成质量报告面板
 */

/**
 * 方式 1: 使用 ConfirmationWithQuality 包装器（推荐）
 *
 * 在 router.tsx 中，将 ConfirmationRoute 改为使用 ConfirmationWithQuality：
 *
 * ```tsx
 * import { ConfirmationWithQuality } from './features/quality-report/ConfirmationWithQuality';
 *
 * function ConfirmationRoute() {
 *   const { projectId = '' } = useParams<{ projectId: string }>();
 *   return (
 *     <LazyPage>
 *       <ConfirmationWithQuality projectId={projectId} />
 *     </LazyPage>
 *   );
 * }
 * ```
 *
 * 这种方式会在确认工作流右侧添加一个可折叠的质量报告面板。
 */

/**
 * 方式 2: 在确认工作流顶部添加质量报告按钮
 *
 * 在 confirmation/index.tsx 的顶部导航区域添加：
 *
 * ```tsx
 * import { BarChart3 } from 'lucide-react';
 *
 * // 在导出按钮旁边添加
 * <Button
 *   variant="outline"
 *   onClick={() => navigate(`/document/${projectId}/quality-report`)}
 *   leftIcon={<BarChart3 className="h-4 w-4" />}
 * >
 *   质量报告
 * </Button>
 * ```
 */

/**
 * 方式 3: 在文档列表中添加质量报告入口
 *
 * 在项目列表或文档侧边栏中添加质量报告链接：
 *
 * ```tsx
 * <a href={`/document/${projectId}/quality-report`}>
 *   查看质量报告
 * </a>
 * ```
 */

export {};
