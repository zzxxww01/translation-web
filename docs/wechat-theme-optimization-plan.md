# 微信公众号排版优化方案

## 一、字体优化

### 1.1 字体栈优化
**当前问题：**
- 字体栈较简单，缺少中文优化字体
- 无衬线/衬线/等宽字体选项

**优化方案：**
```css
/* 无衬线（默认） */
--md-font-family: -apple-system-font, BlinkMacSystemFont, Helvetica Neue, 
  PingFang SC, Hiragino Sans GB, Microsoft YaHei UI, Microsoft YaHei, Arial, sans-serif;

/* 衬线（优雅阅读） */
--md-font-family-serif: Optima-Regular, Optima, PingFangSC-light, PingFangTC-light, 
  'PingFang SC', Cambria, Cochin, Georgia, Times, 'Times New Roman', serif;

/* 等宽（代码） */
--md-font-family-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', 
  Menlo, 'Courier New', monospace;
```

### 1.2 字号系统
**当前问题：**
- 标题使用固定 em 值，不够灵活
- 缺少字号选项（14px/15px/16px/17px/18px）

**优化方案：**
```css
/* 使用相对计算 */
h1 { font-size: calc(var(--md-font-size) * 1.5); }
h2 { font-size: calc(var(--md-font-size) * 1.3); }
h3 { font-size: calc(var(--md-font-size) * 1.15); }
h4 { font-size: calc(var(--md-font-size) * 1.05); }
```

### 1.3 字重优化
**当前问题：**
- 所有标题都是 600，层次感不足

**优化方案：**
```css
h1 { font-weight: 700; }  /* 加粗 */
h2 { font-weight: 600; }  /* 半粗 */
h3 { font-weight: 600; }
h4 { font-weight: 500; }  /* 中等 */
h5, h6 { font-weight: 500; }
```

## 二、细节优化

### 2.1 字间距（letter-spacing）
**关键发现：** doocs-md 使用 `letter-spacing: 0.1em` 让中文更易读

**优化方案：**
```css
p {
  letter-spacing: 0.1em;  /* 增加字间距 */
}

blockquote p {
  letter-spacing: 0.1em;
}

/* 标题不需要字间距 */
h1, h2, h3, h4, h5, h6 {
  letter-spacing: 0;
}
```

### 2.2 段落边距
**当前问题：**
- 段落贴边，视觉不舒适

**优化方案：**
```css
p {
  margin: 1.5em 8px;  /* 左右 8px 边距 */
}
```

### 2.3 图片题注
**当前缺失：** 无图片题注样式

**优化方案：**
```css
figure {
  margin: 1.5em 8px;
}

figcaption {
  text-align: center;
  color: #888;
  font-size: 0.85em;
  margin-top: 0.5em;
  font-style: italic;
}
```

### 2.4 强调样式优化
**当前问题：**
- `strong` 使用纯黑色，不够突出

**优化方案：**
```css
strong {
  font-weight: 600;
  color: var(--md-primary-color);  /* 使用主题色 */
}
```

### 2.5 代码块优化
**当前问题：**
- 代码字号固定，不随基础字号变化
- 缺少行号支持

**优化方案：**
```css
code {
  font-size: 90%;  /* 相对字号 */
  font-family: var(--md-font-family-mono);
}

pre code {
  font-size: 90%;
  line-height: 1.6;  /* 代码行高 */
}
```

### 2.6 列表优化
**当前问题：**
- 列表项间距不足

**优化方案：**
```css
li {
  margin: 0.5em 0;
  line-height: 1.8;
}

/* 嵌套列表 */
li > ul, li > ol {
  margin: 0.3em 0;
}
```

### 2.7 表格斑马纹
**当前缺失：** 无斑马纹效果

**优化方案：**
```css
tbody tr:nth-child(even) {
  background: #f9fafb;
}

tbody tr:hover {
  background: #f3f4f6;
}
```

### 2.8 分隔线优化
**当前问题：**
- 分隔线太细，不明显

**优化方案：**
```css
hr {
  margin: 2em 0;
  border: none;
  border-top: 2px solid rgba(0, 0, 0, 0.1);
  transform: scaleY(0.5);  /* 视觉上更细 */
}
```

### 2.9 引用块优化
**当前问题：**
- 引用块样式单一

**优化方案：**
```css
blockquote {
  margin: 1.5em 8px;
  padding: 1em 1.5em;
  border-left: 4px solid var(--md-primary-color);
  background: var(--blockquote-background);
  border-radius: 4px;
  font-style: normal;
}

blockquote p {
  margin: 0.5em 0;
  letter-spacing: 0.1em;
}

/* 引用块内的第一个段落 */
blockquote > p:first-child {
  margin-top: 0;
}

/* 引用块内的最后一个段落 */
blockquote > p:last-child {
  margin-bottom: 0;
}
```

## 三、主题色系统

### 3.1 多色彩方案
**当前问题：**
- 只有蓝色主题

**优化方案：**
提供 10 种主题色选项：
- 经典蓝 `#0F4C81`
- 翡翠绿 `#009874`
- 活力橘 `#FA5151`
- 柠檬黄 `#FECE00`
- 薰衣紫 `#92617E`
- 天空蓝 `#55C9EA`
- 玫瑰金 `#B76E79`
- 橄榄绿 `#556B2F`
- 石墨黑 `#333333`
- 雾烟灰 `#A9A9A9`

### 3.2 CSS 变量扩展
```css
:root {
  --md-primary-color: #3b82f6;
  --md-font-family: ...;
  --md-font-size: 16px;
  --md-line-height: 1.75;
  --md-letter-spacing: 0.1em;
  
  /* 背景色 */
  --blockquote-background: #f8f9fa;
  --code-background: #f6f8fa;
  
  /* 文字色 */
  --text-color: #333;
  --text-muted: #666;
  --text-light: #888;
}
```

## 四、实施优先级

### P0（必须实现）
1. ✅ 字间距优化（letter-spacing: 0.1em）
2. ✅ 段落边距（margin: 1.5em 8px）
3. ✅ 强调色优化（strong 使用主题色）
4. ✅ 代码相对字号（font-size: 90%）
5. ✅ 标题相对计算（calc()）

### P1（重要优化）
1. ⏳ 图片题注支持
2. ⏳ 表格斑马纹
3. ⏳ 列表间距优化
4. ⏳ 引用块细节优化

### P2（增强体验）
1. ⏳ 多字体选项（无衬线/衬线/等宽）
2. ⏳ 多字号选项（14-18px）
3. ⏳ 10 种主题色
4. ⏳ 分隔线视觉优化

## 五、技术实现

### 5.1 后端改动
```python
# src/services/wechat_formatter.py
class WechatFormatRequest:
    markdown: str
    theme: str = "default"
    font_family: str = "sans-serif"  # 新增
    font_size: str = "16px"          # 新增
    primary_color: str = "#3b82f6"   # 新增
    upload_images: bool = False
    image_to_base64: bool = False
```

### 5.2 前端改动
```typescript
// 添加字体选择器
<Select value={fontFamily} onValueChange={setFontFamily}>
  <SelectItem value="sans-serif">无衬线</SelectItem>
  <SelectItem value="serif">衬线</SelectItem>
</Select>

// 添加字号选择器
<Select value={fontSize} onValueChange={setFontSize}>
  <SelectItem value="14px">14px（更小）</SelectItem>
  <SelectItem value="16px">16px（推荐）</SelectItem>
  <SelectItem value="18px">18px（更大）</SelectItem>
</Select>

// 添加主题色选择器
<ColorPicker value={primaryColor} onChange={setPrimaryColor} />
```

## 六、对比效果

### 优化前
- 字间距紧凑，阅读费力
- 段落贴边，视觉压抑
- 强调不明显
- 代码字号固定
- 缺少图片题注

### 优化后
- 字间距舒适（+0.1em）
- 段落有呼吸感（8px 边距）
- 强调醒目（主题色）
- 代码自适应（90%）
- 图片题注完整

## 七、参考资源

- doocs/md: https://github.com/doocs/md
- markdown-nice: https://github.com/mdnice/markdown-nice
- 微信公众号排版规范
- 中文排版指南
