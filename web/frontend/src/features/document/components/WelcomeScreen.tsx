/**
 * 欢迎页面组件
 * 显示在未选择项目时
 */

export function WelcomeScreen() {
  return (
    <div className="mx-auto max-w-3xl py-16">
      <div className="mb-8 text-center">
        <div className="mb-4 text-6xl">🚀</div>
        <h2 className="mb-2 text-2xl font-bold">长文翻译</h2>
        <p className="text-text-muted">
          将技术长文翻译成专业的中文 Markdown 文档
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="card p-7">
          <div className="mb-3 text-3xl">🎯</div>
          <h3 className="mb-2 font-semibold">精准翻译</h3>
          <p className="text-base text-text-muted">四步法翻译流程，确保译文质量</p>
        </div>
        <div className="card p-7">
          <div className="mb-3 text-3xl">📚</div>
          <h3 className="mb-2 font-semibold">术语管理</h3>
          <p className="text-base text-text-muted">专业术语表，保持一致性</p>
        </div>
        <div className="card p-7">
          <div className="mb-3 text-3xl">⚡</div>
          <h3 className="mb-2 font-semibold">高效协作</h3>
          <p className="text-base text-text-muted">逐段确认，灵活编辑</p>
        </div>
      </div>
    </div>
  );
}
