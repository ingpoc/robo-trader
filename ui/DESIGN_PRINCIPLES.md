# Swiss Digital Minimalism Design Principles

This document explains the strict design constraints applied to this application.

## Dieter Rams' 10 Principles

### 1. Good design is innovative
- WebSocket reconnection with exponential backoff
- CSS-only rolling number animations
- Virtual scrolling for large datasets
- Progressive enhancement approach

### 2. Good design makes a product useful
- Every element serves the user's trading goals
- No decorative components
- Information hierarchy optimized for decision-making
- Quick actions prominently placed

### 3. Good design is aesthetic
- Mathematical 8px spacing system
- Precise typography hierarchy
- Balanced composition
- Visual rhythm through repetition

### 4. Good design makes a product understandable
- Clear navigation structure
- Consistent component patterns
- Predictable interactions
- Self-documenting interfaces

### 5. Good design is unobtrusive
- Interface fades to background
- Content (portfolio data) takes center stage
- Minimal visual noise
- No attention-grabbing animations

### 6. Good design is honest
- No fake loading states
- Real data only
- Clear error messages
- Transparent system status

### 7. Good design is long-lasting
- Timeless grayscale palette
- No trendy gradients or effects
- Classic typography
- Functional over fashionable

### 8. Good design is thorough
- Every detail considered
- Consistent spacing throughout
- Proper accessibility
- Complete error handling

### 9. Good design is environmentally friendly
- Efficient rendering (60fps)
- Optimized bundle size
- Minimal network requests
- Performance-first architecture

### 10. Good design is as little design as possible
- Essential elements only
- No unnecessary features
- Maximum information density
- Purity of form

## Color System Constraints

### The ONE Accent Rule
```css
Accent: #2563eb (blue) - ONLY color allowed
Grayscale: #fafafa → #171717 (50 shades)
```

### Usage Rules
- **Accent color** - Interactive elements only (links, primary buttons)
- **Black (900)** - Primary text, high importance
- **Gray (600)** - Secondary text, labels
- **Gray (400)** - Tertiary text, disabled states
- **Gray (200)** - Borders, separators
- **White (50)** - Backgrounds

### Forbidden
❌ Color-coded status (red/green for profit/loss)
❌ Multiple accent colors
❌ Gradients
❌ Semi-transparent overlays

## Typography Hierarchy

### Creating Hierarchy Without Color
```css
Display:  36px, 700 weight, -0.03em spacing
Heading:  24px, 600 weight, -0.02em spacing
Body:     16px, 400 weight, 0 spacing
Label:    14px, 500 weight, 0 spacing
Caption:  12px, 400 weight, 0.01em spacing
```

### Rules
- Size creates primary hierarchy
- Weight creates secondary hierarchy
- Letter-spacing adds refinement
- Line-height ensures readability
- **Never use color for meaning**

### Examples
```html
<!-- Good: Size creates hierarchy -->
<h1 class="text-2xl font-semibold">Portfolio</h1>
<p class="text-base">Your holdings</p>

<!-- Bad: Color creates hierarchy -->
<h1 class="text-blue-500">Portfolio</h1>
<p class="text-gray-500">Your holdings</p>
```

## Spacing System

### The 8px Base Unit
```
1 unit = 8px
2 units = 16px
3 units = 24px
4 units = 32px
5 units = 40px
6 units = 48px
```

### Application
- **Padding** - Always multiples of 8px
- **Margins** - Always multiples of 8px
- **Gaps** - Always multiples of 8px
- **Component heights** - Multiples of 8px (40px, 48px)

### Mathematical Precision
```css
/* Good: 8px system */
.card { padding: 16px; gap: 24px; }

/* Bad: Arbitrary values */
.card { padding: 15px; gap: 22px; }
```

## Interaction Constraints

### Maximum Subtlety
```css
/* Allowed: Opacity change only */
button:hover { opacity: 0.8; }

/* Forbidden: Scale effects */
button:hover { transform: scale(1.05); }

/* Forbidden: Complex transitions */
button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
```

### Transition Rules
- **Duration** - Maximum 150ms
- **Easing** - Ease-out only
- **Properties** - Opacity, transform (Y only)
- **Scale** - Maximum 1.005x (imperceptible)

### Forbidden Interactions
❌ Bounce effects
❌ Spring animations
❌ Parallax scrolling
❌ Cursor trails
❌ Particle effects
❌ Rotation animations

## Layout Principles

### Flat Design Only
```css
/* Good: Flat card */
.card {
  background: white;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
}

/* Bad: Shadow depth */
.card {
  background: white;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  border-radius: 8px;
}
```

### Border Radius Rules
- **None** - 0px (full sharp)
- **Small** - 2px (subtle)
- **Default** - 4px (standard)
- **Medium** - 6px (buttons)
- **Large** - 8px (cards)
- **Never** - > 8px

### Grid System
- Use CSS Grid for layout
- Gaps in multiples of 8px
- Responsive breakpoints: 640px, 768px, 1024px, 1280px
- Mobile-first approach

## Component Patterns

### Metric Cards
```typescript
// Good: Typography creates hierarchy
<div className="text-2xl font-semibold text-gray-900">₹100,000</div>
<div className="text-sm text-gray-600">Available Cash</div>

// Bad: Color creates hierarchy
<div className="text-xl text-blue-500">₹100,000</div>
<div className="text-base text-green-500">Available Cash</div>
```

### Status Indicators
```typescript
// Good: Shape indicates status
<div className="w-2 h-2 rounded-full bg-gray-900" /> Connected
<div className="w-2 h-2 rounded-full bg-gray-300" /> Disconnected

// Bad: Color indicates status
<div className="w-2 h-2 rounded-full bg-green-500" /> Connected
<div className="w-2 h-2 rounded-full bg-red-500" /> Disconnected
```

### Buttons
```typescript
// Good: Variants through fill
<button className="bg-accent text-white" />      // Primary
<button className="bg-gray-100 text-gray-900" /> // Secondary
<button className="bg-transparent border" />     // Outline

// Bad: Multiple accent colors
<button className="bg-blue-500" />
<button className="bg-green-500" />
<button className="bg-red-500" />
```

## Information Density

### Maximum Content, Minimum Chrome
- Headers: 64px height (minimal)
- Sidebars: 256px width (essential nav only)
- Content area: 100% available space
- Padding: Minimum needed for readability

### Data Tables
- Row height: 60px (readable, scannable)
- Column padding: 16px (comfortable)
- Border: 1px bottom only (subtle separation)
- Header: Sticky, gray background

### Charts
- No grid lines unless essential
- Single color data series (black)
- Minimal axis labels
- No legends (direct labeling)

## Accessibility Without Compromise

### ARIA Labels Replace Visual Cues
```html
<!-- Good: Semantic + ARIA -->
<button aria-label="Execute trade">Execute</button>

<!-- Bad: Icon only -->
<button>→</button>
```

### Focus Indicators
```css
*:focus-visible {
  outline: none;
  ring: 2px solid var(--accent);
  ring-offset: 2px;
}
```

### Keyboard Navigation
- Tab order follows visual order
- All actions keyboard accessible
- Escape closes modals
- Enter submits forms

## Performance as Design

### Load Time is UX
- Bundle size < 200KB gzipped
- Initial render < 2s on 3G
- Interaction ready < 3s
- Route changes instant

### Animation Budget
- 60fps or don't animate
- GPU-accelerated only (transform, opacity)
- Total animation time < 500ms
- Prefer no animation to janky animation

### Data Loading
- Show skeleton states (gray rectangles)
- Never block UI on data
- Optimistic updates for instant feel
- Background refetch invisible to user

## Validation Checklist

Before committing any design change:

### Color Check
- [ ] Only grayscale + single accent used?
- [ ] No color-coded meaning (red=bad, green=good)?
- [ ] Status indicated by typography or shape?

### Typography Check
- [ ] Hierarchy through size/weight only?
- [ ] Line heights comfortable?
- [ ] Letter spacing refined?
- [ ] No colored text for emphasis?

### Spacing Check
- [ ] All spacing multiples of 8px?
- [ ] Consistent gaps throughout?
- [ ] Padding comfortable but not excessive?

### Interaction Check
- [ ] Transitions < 150ms?
- [ ] Opacity changes only?
- [ ] No scale/bounce/spring effects?
- [ ] 60fps or no animation?

### Layout Check
- [ ] Flat design (no shadows)?
- [ ] Border radius ≤ 8px?
- [ ] Maximum information density?
- [ ] Grid aligned?

### Accessibility Check
- [ ] ARIA labels present?
- [ ] Keyboard navigable?
- [ ] Focus indicators visible?
- [ ] Semantic HTML used?

## Examples: Good vs Bad

### Good: Swiss Minimalism
```typescript
<div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded">
  <h3 className="text-lg font-semibold text-gray-900">Portfolio</h3>
  <div className="text-2xl font-medium text-gray-900">₹100,000</div>
  <div className="text-sm text-gray-600">Available Cash</div>
</div>
```

### Bad: Trendy Design
```typescript
<div className="flex flex-col gap-4 p-6 bg-gradient-to-br from-blue-500 to-purple-600
            shadow-xl rounded-2xl transform hover:scale-105 transition-all duration-300">
  <h3 className="text-2xl font-bold text-white drop-shadow-lg">💰 Portfolio</h3>
  <div className="text-4xl font-black text-yellow-300">₹100,000</div>
  <div className="text-base text-blue-100">Available Cash 💵</div>
</div>
```

## Philosophy

> "Less, but better - because it concentrates on the essential aspects, and the products are not burdened with non-essentials. Back to purity, back to simplicity."
> — Dieter Rams

Every pixel serves the user's goal of making informed trading decisions. Anything that doesn't serve this purpose is removed. The result is an interface that disappears, allowing the data to speak.
