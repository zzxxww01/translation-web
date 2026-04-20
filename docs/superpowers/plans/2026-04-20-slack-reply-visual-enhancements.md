# Slack Reply UX Redesign - Phase 2: Visual Enhancements

**Created:** 2026-04-20  
**Status:** Ready for Implementation  
**Related Spec:** [2026-04-19-slack-reply-ux-redesign.md](../specs/2026-04-19-slack-reply-ux-redesign.md)  
**Depends On:** Phase 1 (Core Features)

## Overview

This plan implements the P1 visual enhancements from the Slack Reply UX redesign:
- Editorial/Magazine style typography system
- Custom color palette (deep ink blue + warm beige + gold)
- Enhanced animations and micro-interactions
- Refined spacing and layout

## Implementation Strategy

**Approach:** CSS-first with Tailwind customization  
**Testing:** Visual regression tests + manual verification  
**Rollout:** Gradual rollout with feature flag

---

## Phase 1: Typography System

### Step 1.1: Install custom fonts

**File:** `web/frontend/index.html`

Add Google Fonts link:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Serif+SC:wght@400;600&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
```

**Commit:** `feat(slack): add Editorial style fonts`

---

### Step 1.2: Configure Tailwind theme

**File:** `web/frontend/tailwind.config.js`

```javascript
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        display: ['Playfair Display', 'serif'],
        sans: ['IBM Plex Sans', 'sans-serif'],
        serif: ['Noto Serif SC', 'serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      colors: {
        editorial: {
          primary: '#1a2332',      // 深墨蓝
          secondary: '#f5f1e8',    // 暖米色
          accent: '#d4a574',       // 金色
          muted: '#8b8680',        // 灰褐色
          border: '#e0dcd3',       // 浅褐色
          surface: '#ffffff',      // 纯白
        },
      },
    },
  },
};
```

**Commit:** `feat(slack): configure Editorial theme in Tailwind`

---

### Step 1.3: Create CSS variables

**File:** `web/frontend/src/features/slack/styles.css` (new)

```css
.slack-editorial-theme {
  /* Typography */
  --font-display: 'Playfair Display', serif;
  --font-body: 'IBM Plex Sans', sans-serif;
  --font-chinese: 'Noto Serif SC', serif;
  --font-mono: 'IBM Plex Mono', monospace;

  /* Colors */
  --color-primary: #1a2332;
  --color-secondary: #f5f1e8;
  --color-accent: #d4a574;
  --color-muted: #8b8680;
  --color-border: #e0dcd3;
  --color-surface: #ffffff;

  /* Spacing */
  --spacing-card: 32px;
  --spacing-section: 48px;

  /* Transitions */
  --transition-base: 300ms ease-out;
  --transition-fast: 200ms ease-out;
}
```

**Import in:** `web/frontend/src/features/slack/index.tsx`

```typescript
import './styles.css';
```

**Commit:** `feat(slack): add Editorial theme CSS variables`

---

## Phase 2: Component Styling

### Step 2.1: Update VersionCard styling

**File:** `web/frontend/src/features/slack/components/VersionCard.tsx`

**Changes:**
1. Add Editorial theme classes
2. Update card padding to 32px
3. Add subtle box-shadow
4. Add editing state border highlight
5. Add saving state opacity

**Key CSS classes:**

```typescript
<Card className={cn(
  "p-8 transition-all duration-300",
  "bg-editorial-surface border-editorial-border",
  "shadow-[0_2px_8px_rgba(26,35,50,0.04)]",
  isEditing && "border-editorial-accent shadow-[0_4px_16px_rgba(212,165,116,0.15)] scale-[1.02]",
  refineMutation.isPending && "opacity-60"
)}>
```

**Style tag:**

```typescript
<span className="font-mono text-[11px] tracking-wider uppercase text-editorial-accent border border-editorial-accent px-3 py-1 rounded">
  {version.style}
</span>
```

**Commit:** `feat(slack): apply Editorial styling to VersionCard`

---

### Step 2.2: Update ConversationBubbles styling

**File:** `web/frontend/src/features/slack/components/MessageBubble.tsx`

**Changes:**
1. Update bubble border-radius (16px with asymmetric corners)
2. Apply Editorial colors
3. Update padding to 16px 20px
4. Add max-width 70%

**Bubble styles:**

```typescript
// Them bubble
<div className={cn(
  "rounded-2xl rounded-bl-sm max-w-[70%] self-start",
  "bg-muted px-5 py-4",
  "font-body text-sm leading-relaxed"
)}>

// Me bubble
<div className={cn(
  "rounded-2xl rounded-br-sm max-w-[70%] self-end",
  "bg-editorial-primary text-editorial-surface px-5 py-4",
  "font-body text-sm leading-relaxed"
)}>
```

**Commit:** `feat(slack): apply Editorial styling to conversation bubbles`

---

### Step 2.3: Update ReplyWorkspace styling

**File:** `web/frontend/src/features/slack/components/ReplyWorkspace.tsx`

**Changes:**
1. Add background texture (noise pattern)
2. Update section spacing to 48px
3. Apply Editorial colors to input area

**Background texture:**

```typescript
<Card className="relative p-6 space-y-6 bg-editorial-secondary">
  {/* Noise texture overlay */}
  <div 
    className="absolute inset-0 pointer-events-none opacity-[0.03]"
    style={{
      backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
    }}
  />
  
  {/* Content */}
  <div className="relative z-10">
    {/* ... existing content */}
  </div>
</Card>
```

**Commit:** `feat(slack): apply Editorial styling to ReplyWorkspace`

---

## Phase 3: Animations

### Step 3.1: Add version card fade-in animation

**File:** `web/frontend/src/features/slack/styles.css`

```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.version-card-animate {
  animation: fadeInUp 400ms ease-out both;
}

.version-card-animate:nth-child(1) {
  animation-delay: 0ms;
}

.version-card-animate:nth-child(2) {
  animation-delay: 100ms;
}

.version-card-animate:nth-child(3) {
  animation-delay: 200ms;
}
```

**Apply in:** `web/frontend/src/features/slack/components/ReplyWorkspace.tsx`

```typescript
{currentVersions.map((version, index) => (
  <div key={version.version} className="version-card-animate">
    <VersionCard ... />
  </div>
))}
```

**Commit:** `feat(slack): add staggered fade-in animation for version cards`

---

### Step 3.2: Add button hover effects

**File:** `web/frontend/src/features/slack/styles.css`

```css
.button-editorial {
  position: relative;
  overflow: hidden;
  transition: var(--transition-fast);
}

.button-editorial::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--color-accent);
  transition: width var(--transition-fast);
}

.button-editorial:hover::after {
  width: 100%;
}
```

**Apply to primary buttons:**

```typescript
<Button className="button-editorial">
  发送
</Button>
```

**Commit:** `feat(slack): add underline hover effect to buttons`

---

### Step 3.3: Add save success animation

**File:** `web/frontend/src/features/slack/styles.css`

```css
@keyframes successPulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 2px 8px rgba(26, 35, 50, 0.04);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 4px 20px rgba(212, 165, 116, 0.3);
  }
}

.save-success {
  animation: successPulse 500ms ease-out;
}
```

**Apply in:** `web/frontend/src/features/slack/components/VersionCard.tsx`

```typescript
const [showSuccess, setShowSuccess] = useState(false);

const handleSave = async () => {
  // ... existing save logic
  
  setShowSuccess(true);
  setTimeout(() => setShowSuccess(false), 500);
};

<Card className={cn(
  // ... existing classes
  showSuccess && "save-success"
)}>
```

**Commit:** `feat(slack): add success pulse animation on save`

---

## Phase 4: Layout Refinements

### Step 4.1: Add asymmetric layout for version cards

**File:** `web/frontend/src/features/slack/components/ReplyWorkspace.tsx`

```typescript
<div className="space-y-2">
  {currentVersions.map((version, index) => (
    <div 
      key={version.version}
      className={cn(
        "version-card-animate",
        index === 1 && "ml-4"  // Offset middle card
      )}
    >
      <VersionCard ... />
    </div>
  ))}
</div>
```

**Commit:** `feat(slack): add asymmetric layout for version cards`

---

### Step 4.2: Update main container spacing

**File:** `web/frontend/src/features/slack/index.tsx`

```typescript
<div className="slack-editorial-theme mx-auto flex h-full w-full max-w-5xl flex-col gap-12 p-6">
  {/* Header with display font */}
  <div className="flex items-center justify-between">
    <div>
      <h2 className="font-display text-2xl font-semibold text-editorial-primary">
        Slack 回复助手
      </h2>
      <p className="font-body text-sm text-editorial-muted mt-1">
        粘贴对方英文或输入中文，生成专业回复
      </p>
    </div>
    {/* ... model selector */}
  </div>
  
  {/* ... rest of content */}
</div>
```

**Commit:** `feat(slack): apply Editorial typography to main container`

---

## Phase 5: Polish & Details

### Step 5.1: Add focus states

**File:** `web/frontend/src/features/slack/styles.css`

```css
.editorial-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(212, 165, 116, 0.1);
}

.editorial-textarea:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(212, 165, 116, 0.1);
}
```

**Apply to inputs:**

```typescript
<Textarea className="editorial-textarea" />
```

**Commit:** `feat(slack): add Editorial focus states`

---

### Step 5.2: Add loading skeleton

**File:** `web/frontend/src/features/slack/components/VersionCardSkeleton.tsx` (new)

```typescript
export function VersionCardSkeleton() {
  return (
    <Card className="p-8 bg-editorial-surface border-editorial-border animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-6 w-16 bg-editorial-border rounded" />
        <div className="h-6 w-20 bg-editorial-border rounded" />
      </div>
      <div className="space-y-2">
        <div className="h-4 bg-editorial-border rounded w-full" />
        <div className="h-4 bg-editorial-border rounded w-5/6" />
        <div className="h-4 bg-editorial-border rounded w-4/6" />
      </div>
    </Card>
  );
}
```

**Use in ReplyWorkspace:**

```typescript
{isGenerating && (
  <div className="space-y-2">
    <VersionCardSkeleton />
    <VersionCardSkeleton />
    <VersionCardSkeleton />
  </div>
)}
```

**Commit:** `feat(slack): add loading skeleton for version cards`

---

## Phase 6: Testing & Verification

### Step 6.1: Visual regression tests

**Test checklist:**
- [ ] Fonts load correctly (Playfair Display, IBM Plex Sans, Noto Serif SC)
- [ ] Colors match Editorial palette
- [ ] Version cards have correct padding (32px)
- [ ] Editing state shows accent border and scale effect
- [ ] Saving state shows opacity reduction
- [ ] Fade-in animation plays with stagger
- [ ] Button hover underline effect works
- [ ] Save success pulse animation plays
- [ ] Asymmetric layout applied to middle card
- [ ] Focus states show accent color
- [ ] Loading skeleton displays during generation

---

### Step 6.2: Browser compatibility

**Test browsers:**
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

**Test features:**
- [ ] CSS custom properties
- [ ] CSS animations
- [ ] Google Fonts loading
- [ ] SVG background patterns

---

### Step 6.3: Performance check

**Metrics:**
- [ ] First Contentful Paint < 1.5s
- [ ] Largest Contentful Paint < 2.5s
- [ ] Cumulative Layout Shift < 0.1
- [ ] Animation frame rate > 55fps

**Tools:**
- Lighthouse audit
- Chrome DevTools Performance tab

---

## Rollout Plan

1. **Merge to `main`** after visual verification
2. **Deploy to staging** → design review
3. **A/B test** (50% users) for 1 week
4. **Collect feedback** on visual appeal and usability
5. **Full rollout** if positive feedback

---

## Success Criteria

- [ ] All visual regression tests pass
- [ ] Browser compatibility verified
- [ ] Performance metrics meet targets
- [ ] Design team approval
- [ ] User feedback score > 4.0/5.0
- [ ] No accessibility regressions (WCAG AA)

---

## Estimated Timeline

- Typography system (Steps 1.1-1.3): 2 hours
- Component styling (Steps 2.1-2.3): 4 hours
- Animations (Steps 3.1-3.3): 3 hours
- Layout refinements (Steps 4.1-4.2): 2 hours
- Polish & details (Steps 5.1-5.2): 2 hours
- Testing (Steps 6.1-6.3): 3 hours

**Total:** ~16 hours (2 working days)

---

## Next Steps After Phase 2

Once visual enhancements are stable, proceed to:
- **Phase 3:** Accessibility improvements (keyboard navigation, screen reader support)
- **Phase 4:** Mobile responsive design
- **Phase 5:** Dark mode support
