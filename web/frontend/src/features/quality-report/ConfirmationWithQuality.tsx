/**
 * 带质量面板的确认工作流包装器
 *
 * 在原有确认工作流基础上添加可折叠的质量面板
 */

import { useState } from 'react';
import { ChevronRight, BarChart3 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { ConfirmationFeature } from '../confirmation/index';
import { DocumentQualityPanel } from '../quality-report/components/DocumentQualityPanel';

interface ConfirmationWithQualityProps {
  projectId: string;
  onComplete?: () => void;
}

export function ConfirmationWithQuality({ projectId, onComplete }: ConfirmationWithQualityProps) {
  const [showQualityPanel, setShowQualityPanel] = useState(false);
  const [currentSectionId] = useState<string>();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* 主确认工作流区域 */}
      <div className={cn(
        'flex-1 transition-all duration-300',
        showQualityPanel ? 'mr-0' : 'mr-0'
      )}>
        <ConfirmationFeature
          projectId={projectId}
          onComplete={onComplete}
        />
      </div>

      {/* 质量面板切换按钮 */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 z-10">
        {!showQualityPanel && (
          <Button
            variant="default"
            size="sm"
            className="rounded-l-lg rounded-r-none shadow-lg"
            onClick={() => setShowQualityPanel(true)}
            title="显示质量报告"
          >
            <BarChart3 className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* 质量面板 */}
      <div
        className={cn(
          'h-screen border-l border-border bg-background transition-all duration-300 overflow-hidden',
          showQualityPanel ? 'w-96' : 'w-0'
        )}
      >
        {showQualityPanel && (
          <div className="h-full flex flex-col">
            {/* 面板头部 */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                质量报告
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowQualityPanel(false)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* 面板内容 */}
            <div className="flex-1 overflow-y-auto p-4">
              <DocumentQualityPanel
                projectId={projectId}
                currentSectionId={currentSectionId}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
