/* 主题定义：完整覆盖 app.css 的原始颜色 token + theme.css 语义别名。
   切主题 = 把整套 token 写到 documentElement（ThemeProvider 执行）。
   paper 取 app.css :root 原值（默认零变化）；midnight 为书香暗夜（暖褐黑 + 亮铜金）。 */

export const THEMES = {
  paper: {
    label: '宣纸',
    vars: {
      /* surfaces */
      '--bg-app': 'oklch(97.4% 0.008 90)',
      '--bg-side': 'oklch(94.5% 0.012 88)',
      '--bg-raise': 'oklch(99% 0.006 90)',
      '--bg-hover': 'oklch(92% 0.014 70)',
      '--bg-main-card': 'oklch(98% 0.015 90)',
      /* ink */
      '--ink': 'oklch(28% 0.012 60)',
      '--ink-2': 'oklch(43% 0.014 60)',
      '--muted': 'oklch(58% 0.02 60)',
      '--rule': 'oklch(88% 0.018 80)',
      /* gold */
      '--acc': 'oklch(56% 0.09 70)',
      '--acc-deep': 'oklch(45% 0.09 65)',
      '--acc-soft': 'oklch(95.5% 0.025 80)',
      '--acc-ink': 'oklch(38% 0.07 65)',
      /* ink-panel */
      '--ink-panel': 'oklch(30% 0.012 60)',
      '--ink-panel-fg': 'oklch(96% 0.01 80)',
      /* states */
      '--ok': 'oklch(52% 0.07 160)',
      '--warn': 'oklch(60% 0.11 65)',
      '--err': 'oklch(52% 0.11 28)',
      /* shadow */
      '--shadow':
        '0 1px 2px oklch(30% 0.02 60 / 0.06), 0 10px 28px oklch(30% 0.02 60 / 0.07)',
      /* 语义别名（theme.css）*/
      '--paper': 'oklch(97.4% 0.008 90)',
      '--gold': 'oklch(56% 0.09 70)',
      '--paper-cloud': 'oklch(94.5% 0.012 88)',
      '--line': 'oklch(88% 0.018 80)',
      '--accent': 'oklch(45% 0.09 65)',
    },
  },
  midnight: {
    label: '暗夜',
    vars: {
      /* surfaces：暖褐黑体系 */
      '--bg-app': 'oklch(21% 0.012 80)',
      '--bg-side': 'oklch(24% 0.014 80)',
      '--bg-raise': 'oklch(28% 0.015 80)',
      '--bg-hover': 'oklch(32% 0.018 75)',
      '--bg-main-card': 'oklch(30% 0.02 85)',
      /* ink：亮米白文字 */
      '--ink': 'oklch(91% 0.01 85)',
      '--ink-2': 'oklch(79% 0.012 85)',
      '--muted': 'oklch(64% 0.015 80)',
      '--rule': 'oklch(37% 0.015 80)',
      /* gold：亮铜金，acc-deep 反转为更亮（暗底文字用）*/
      '--acc': 'oklch(72% 0.09 80)',
      '--acc-deep': 'oklch(80% 0.07 85)',
      '--acc-soft': 'oklch(33% 0.05 80)',
      '--acc-ink': 'oklch(18% 0.02 80)',
      /* ink-panel：比侧栏亮一档的块 */
      '--ink-panel': 'oklch(37% 0.02 80)',
      '--ink-panel-fg': 'oklch(94% 0.01 85)',
      /* states */
      '--ok': 'oklch(72% 0.07 160)',
      '--warn': 'oklch(76% 0.11 70)',
      '--err': 'oklch(70% 0.11 28)',
      /* shadow：加深 */
      '--shadow': '0 1px 2px oklch(0% 0 0 / 0.3), 0 10px 28px oklch(0% 0 0 / 0.35)',
      /* 语义别名 */
      '--paper': 'oklch(21% 0.012 80)',
      '--gold': 'oklch(72% 0.09 80)',
      '--paper-cloud': 'oklch(24% 0.014 80)',
      '--line': 'oklch(37% 0.015 80)',
      '--accent': 'oklch(80% 0.07 85)',
    },
  },
}

export const THEME_IDS = Object.keys(THEMES)
