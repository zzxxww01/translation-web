# Translation Agent 全局视觉系统设计

**Created:** 2026-04-20  
**Design Theme:** Liquid Modernism（液态现代主义）  
**Core Concept:** 流动的语言 · Fluid Language

---

## 设计哲学

语言是流动的、有机的、跨越边界的。本设计采用**液态现代主义**美学，通过流动的渐变、柔和的曲线、动态的过渡，象征语言在不同文化间的自然流动。

### 核心原则

1. **流动性（Fluidity）：** 渐变、曲线、动态过渡
2. **呼吸感（Breathing）：** 充足留白、柔和阴影、微妙动画
3. **层次感（Depth）：** 玻璃态、重叠、z-index 层次
4. **独特性（Uniqueness）：** 避免 AI 生成的通用美学

---

## 色彩系统

### 主色调：深海到紫罗兰

```css
:root {
  /* 主色渐变 */
  --color-primary-start: #1a365d;    /* 深海蓝 */
  --color-primary-mid: #3730a3;      /* 靛蓝 */
  --color-primary-end: #5b21b6;      /* 紫罗兰 */
  
  /* 辅助色渐变 */
  --color-secondary-start: #0891b2;  /* 青绿 */
  --color-secondary-end: #3b82f6;    /* 天蓝 */
  
  /* 强调色渐变 */
  --color-accent-start: #f59e0b;     /* 琥珀金 */
  --color-accent-end: #f97316;       /* 珊瑚橙 */
  
  /* 背景层次 */
  --color-bg-base: #f8fafc;          /* 极浅灰蓝 */
  --color-bg-elevated: #ffffff;      /* 纯白 */
  --color-bg-subtle: #f1f5f9;        /* 浅灰蓝 */
  
  /* 文本层次 */
  --color-text-primary: #0f172a;     /* 深灰蓝 */
  --color-text-secondary: #475569;   /* 中灰 */
  --color-text-muted: #94a3b8;       /* 浅灰 */
  
  /* 语义色 */
  --color-success: #10b981;          /* 翠绿 */
  --color-warning: #f59e0b;          /* 琥珀 */
  --color-error: #ef4444;            /* 红色 */
  --color-info: #3b82f6;             /* 蓝色 */
}
```

### 渐变预设

```css
/* 主渐变 */
.gradient-primary {
  background: linear-gradient(135deg, var(--color-primary-start) 0%, var(--color-primary-end) 100%);
}

/* 辅助渐变 */
.gradient-secondary {
  background: linear-gradient(135deg, var(--color-secondary-start) 0%, var(--color-secondary-end) 100%);
}

/* 强调渐变 */
.gradient-accent {
  background: linear-gradient(135deg, var(--color-accent-start) 0%, var(--color-accent-end) 100%);
}

/* 流动网格背景 */
.gradient-mesh-fluid {
  background:
    radial-gradient(at 0% 0%, rgba(26, 54, 93, 0.08) 0px, transparent 50%),
    radial-gradient(at 100% 0%, rgba(91, 33, 182, 0.08) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(8, 145, 178, 0.08) 0px, transparent 50%),
    radial-gradient(at 0% 100%, rgba(59, 130, 246, 0.08) 0px, transparent 50%);
  animation: meshFlow 20s ease-in-out infinite;
}

@keyframes meshFlow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}
```

---

## 字体系统

### 字体族

```css
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Outfit:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --font-display: 'Sora', sans-serif;           /* 标题 */
  --font-body: 'Outfit', sans-serif;            /* 正文 */
  --font-chinese: 'Noto Sans SC', sans-serif;   /* 中文 */
  --font-mono: 'JetBrains Mono', monospace;     /* 代码 */
}
```

### 字体层级

```css
/* 超大标题 */
.text-display {
  font-family: var(--font-display);
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

/* 大标题 */
.text-heading-1 {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

/* 中标题 */
.text-heading-2 {
  font-family: var(--font-display);
  font-size: 1.875rem;
  font-weight: 600;
  line-height: 1.3;
}

/* 小标题 */
.text-heading-3 {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.4;
}

/* 正文 */
.text-body {
  font-family: var(--font-body);
  font-size: 1rem;
  font-weight: 400;
  line-height: 1.6;
}

/* 小字 */
.text-small {
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 400;
  line-height: 1.5;
}

/* 中文优化 */
.text-chinese {
  font-family: var(--font-chinese);
  font-weight: 500;
}
```

---

## 动效系统

### 核心动画

```css
/* 液态上升 */
@keyframes liquidRise {
  from {
    opacity: 0;
    transform: translateY(40px) scale(0.95);
    filter: blur(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
}

.animate-liquid-rise {
  animation: liquidRise 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* 波纹扩散 */
@keyframes rippleExpand {
  0% {
    transform: scale(0);
    opacity: 1;
  }
  100% {
    transform: scale(4);
    opacity: 0;
  }
}

.animate-ripple {
  animation: rippleExpand 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

/* 渐变流动 */
@keyframes gradientFlow {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

.animate-gradient-flow {
  background-size: 200% 200%;
  animation: gradientFlow 8s ease infinite;
}

/* 呼吸发光 */
@keyframes breathingGlow {
  0%, 100% {
    box-shadow: 0 0 20px rgba(91, 33, 182, 0.3);
  }
  50% {
    box-shadow: 0 0 40px rgba(91, 33, 182, 0.6);
  }
}

.animate-breathing-glow {
  animation: breathingGlow 3s ease-in-out infinite;
}

/* 浮动 */
@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

.animate-float {
  animation: float 3s ease-in-out infinite;
}
```

### 过渡曲线

```css
:root {
  --ease-fluid: cubic-bezier(0.34, 1.56, 0.64, 1);      /* 弹性流动 */
  --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);          /* 平滑 */
  --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55); /* 弹跳 */
}
```

---

## 组件样式

### 玻璃态卡片

```css
.card-glass {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 24px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  transition: all 0.4s var(--ease-fluid);
}

.card-glass:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 
    0 16px 48px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}
```

### 流动按钮

```css
.button-fluid {
  position: relative;
  padding: 12px 32px;
  font-family: var(--font-display);
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, var(--color-primary-start), var(--color-primary-end));
  background-size: 200% 200%;
  border: none;
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.4s var(--ease-fluid);
  animation: gradientFlow 8s ease infinite;
}

.button-fluid::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.button-fluid:hover::before {
  width: 300px;
  height: 300px;
}

.button-fluid:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(91, 33, 182, 0.3);
}
```

### 输入框

```css
.input-fluid {
  padding: 14px 20px;
  font-family: var(--font-body);
  font-size: 1rem;
  color: var(--color-text-primary);
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid transparent;
  border-radius: 16px;
  outline: none;
  transition: all 0.3s var(--ease-smooth);
}

.input-fluid:focus {
  background: white;
  border-color: var(--color-primary-end);
  box-shadow: 
    0 0 0 4px rgba(91, 33, 182, 0.1),
    0 8px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}
```

---

## 布局系统

### 非对称网格

```css
.grid-fluid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  grid-auto-flow: dense;
  gap: 24px;
}

.grid-fluid > *:nth-child(3n+1) {
  transform: rotate(-0.5deg);
}

.grid-fluid > *:nth-child(3n+2) {
  transform: rotate(0.5deg);
}

.grid-fluid > *:nth-child(3n+3) {
  transform: rotate(-0.3deg);
}
```

### 流动容器

```css
.container-fluid {
  max-width: 1400px;
  margin: 0 auto;
  padding: 48px 24px;
}

@media (min-width: 768px) {
  .container-fluid {
    padding: 64px 48px;
  }
}

@media (min-width: 1024px) {
  .container-fluid {
    padding: 80px 64px;
  }
}
```

---

## 模块特定设计

### 1. 文档翻译（Document）

**主题：** 专业编辑器  
**特色：**
- 双栏布局，左侧原文右侧译文
- 段落级高亮对比
- 实时术语标注（下划线 + tooltip）
- 进度条使用流动渐变

### 2. Slack 回复（Slack）

**主题：** Editorial/Magazine（已实现）  
**特色：**
- Playfair Display 标题
- 版本卡片错落布局
- 金色强调色
- 纸张纹理背景

### 3. 微信排版（Wechat）

**主题：** 预览为中心  
**特色：**
- 大预览区域（玻璃态边框）
- 主题选择器使用卡片网格
- 实时渲染动画

### 4. 帖子翻译（Post）

**主题：** 快速迭代  
**特色：**
- 版本历史时间轴
- 优化建议卡片（带图标）
- 快捷操作按钮组

### 5. 术语管理（Glossary）

**主题：** 数据表格  
**特色：**
- 流动表格（圆角、阴影）
- 标签云可视化
- 搜索框带动画

---

## 实现优先级

### P0 - 核心系统（立即实施）
1. 全局 CSS 变量和字体
2. 色彩系统和渐变
3. 核心动画（liquidRise, gradientFlow）
4. 玻璃态卡片和按钮

### P1 - 组件优化（1-2 天）
5. 输入框和表单元素
6. 导航栏和侧边栏
7. 加载状态和骨架屏
8. Toast 通知样式

### P2 - 模块定制（2-3 天）
9. 文档翻译界面
10. 微信排版界面
11. 帖子翻译界面
12. 术语管理界面

### P3 - 细节打磨（1-2 天）
13. 微交互动画
14. 响应式优化
15. 暗色模式
16. 无障碍增强

---

## 成功标准

- ✅ 视觉风格独特，避免通用 AI 美学
- ✅ 动画流畅，帧率 > 55fps
- ✅ 色彩对比度符合 WCAG AA 标准
- ✅ 字体加载优化，FOUT 最小化
- ✅ 响应式设计，支持 320px - 2560px
- ✅ 用户反馈积极，美学评分 > 4.5/5

---

## 参考灵感

- **Stripe Dashboard：** 玻璃态和渐变
- **Linear App：** 流畅动画和微交互
- **Vercel：** 极简主义和留白
- **Framer：** 大胆的色彩和排版
- **Notion：** 清晰的层次和组织

---

## 下一步

1. 创建全局主题 CSS 文件
2. 更新 `index.css` 引入新系统
3. 逐模块应用新设计
4. 用户测试和迭代优化
