# JY-changelog

Author / 署名: **JY-changelog**  
Date / 日期: 2026-08-27  
Scope / 范围: Frontend UI — header theme control, brand marks, favicon  
Branch note / 分支说明: pending commit on `Junyan(FrontEnd)`

This file records one frontend UI pass about to be pushed. Product-facing entries are also
summarised under `[Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md).

本文件记录即将提交的一轮前端 UI 改动。面向产品的条目也汇总在
[`CHANGELOG.md`](CHANGELOG.md) 的 `[Unreleased]` 小节中。

---

## Files in this change / 本次涉及文件

| Path | Role |
| --- | --- |
| `frontend/src/composables/useTheme.ts` | Preference model: `system` / `light` / `dark` |
| `frontend/src/App.vue` | Wires preference into the header |
| `frontend/src/components/securfile/header.vue` | Theme dropdown; logo; Light/Dark text contrast |
| `frontend/src/components/securfile/footer.vue` | Same brand logo as the header |
| `frontend/src/components/brand/SecureViewMark.vue` | Inlines SVG so `currentColor` tracks theme |
| `frontend/src/assets/brand/secure-view-logo.svg` | Wordmark logo for chrome |
| `frontend/src/assets/brand/secure-view-icon.svg` | Shield mark (source asset) |
| `frontend/public/favicon.svg` | Tab icon, permanent brand blue |
| `frontend/index.html` | Links the favicon |
| `frontend/src/vite-env.d.ts` | Types for `*.svg?raw` imports |

---

## Why these changes / 为什么改

### Theme control becomes a fixed-width dropdown / 主题改为固定宽度下拉

- The old control was a binary Light ↔ Dark toggle. That cannot express “follow the OS”, and
  swapping the label between short and long strings resized the button and shoved Sign In /
  Get Started sideways. The control is now a dropdown of System / Light / Dark with a fixed
  `w-[7.25rem]` trigger and an absolutely positioned menu, so choosing an option never moves
  neighbouring header text.
- 旧控件只能在 Light 与 Dark 之间切换，表达不了“跟随系统”，且短/长文案切换会改变按钮宽度，把
  Sign In / Get Started 挤歪。现在改为 System / Light / Dark 下拉，触发器固定 `w-[7.25rem]`，
  菜单绝对定位展开，选中任一项都不会带动旁边的页头文字。

### Header text contrast / 页头文字对比度

- Navigation chrome (brand, links, theme control, Sign In / Log Out, mobile menu) uses black
  in Light and white in Dark instead of the washed-out `muted-foreground` token on the
  translucent header bar. Primary CTAs keep their existing button colours.
- 页头导航文字（品牌、链接、主题控件、Sign In / Log Out、移动端菜单）在 Light 下为黑、Dark 下为
  白，而不再用半透明页头上偏灰发虚的 `muted-foreground`。主色 CTA 仍沿用原有按钮配色。

### Brand logo and favicon / 品牌 Logo 与站点图标

- Replaced the Lucide FileLock + plain “SecureView” text in the header and footer with the
  real wordmark SVG, inlined so fills use `currentColor` and track the surrounding theme
  colour. Instance ids are rewritten so header and footer can mount the same mark without
  colliding mask references.
- 页头与页脚用真实的字标 SVG 替换了 Lucide FileLock + 纯文字 “SecureView”；内联渲染使填充色走
  `currentColor`，跟随周围主题色。实例 id 会改写，因此页头与页脚可同时挂载同一套图形而不冲突
  mask。
- The tab favicon is permanently brand blue (`#006DC7`). A favicon is a separate document and
  cannot inherit page `currentColor`; tinting it with the theme also made the tab icon flicker
  and disagree with the marketing blue. A fixed blue mark stays recognisable in every theme.
- 标签页图标固定为品牌蓝（`#006DC7`）。favicon 是独立文档，继承不了页面的 `currentColor`；再按
  主题着色还会让标签图标闪烁，并与对外品牌蓝不一致。固定蓝色在任何主题下都可辨认。

---

## Out of scope / 未纳入本条

- Backend, API, or crypto behaviour.
- Password-field Edge `::-ms-reveal` hiding (already present on this line’s tree; not part of
  the pending diff above).
- 后端、API 或密码学行为。
- 密码框隐藏 Edge `::-ms-reveal`（本分支树中已有，不在上述待提交 diff 内）。
