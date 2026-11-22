import { useNavigate, useSearchParams } from 'react-router-dom';
import { GlossaryCenter } from './GlossaryCenter';
import type { GlossaryScope } from './types';

export { GlossaryCenter } from './GlossaryCenter';

export function GlossaryFeature() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('projectId');
  const projectTitle = searchParams.get('projectTitle');
  const from = searchParams.get('from');
  const scope = searchParams.get('scope');

  const defaultScope: GlossaryScope =
    scope === 'project' || scope === 'recommendations' || scope === 'global' ? scope : 'global';

  return (
    <GlossaryCenter
      projectId={projectId}
      projectTitle={projectTitle}
      defaultScope={defaultScope}
      // 术语库现在在主导航里；只有从某个项目点进来（带 from）时才显示「返回」
      onBack={from ? () => navigate(from) : undefined}
    />
  );
}
