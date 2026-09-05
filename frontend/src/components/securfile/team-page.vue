<script setup lang="ts">
import { Code, GraduationCap, LockKeyhole, Palette, Send, Server, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Component } from 'vue'

interface TeamMember {
  name: string
  role: string
  icon: Component
  initials: string
  bio: string
  detail: string
  accent: string
  mosaic: string
  stickerTone: string
  tileRot: string
}

const members: TeamMember[] = [
  {
    name: 'Asad Malik',
    role: 'Supervisor',
    icon: GraduationCap,
    initials: 'AM',
    bio: 'Guides the SecureView project — scope, technical direction, and evaluation.',
    detail:
      'Provides academic supervision and project guidance so the team keeps a coherent security architecture, realistic milestones, and a platform that stands up to FYP review.',
    accent: 'from-amber-500/20 via-transparent to-amber-500/5',
    mosaic: 'mosaic-tile-supervisor',
    stickerTone: 'sticker-amber',
    tileRot: '-0.6deg',
  },
  {
    name: 'Wen Shuoxun',
    role: 'Testing Engineer',
    icon: Palette,
    initials: 'WS',
    bio: 'Designs user-first security workflows and plans product strategy.',
    detail:
      'Owns end-to-end validation across encryption flows, sharing edge cases, and release readiness so the platform stays trustworthy under real coursework and demo pressure.',
    accent: 'from-[rgb(0,109,199)]/25 via-transparent to-[rgb(0,109,199)]/5',
    mosaic: 'mosaic-tile-hero',
    stickerTone: 'sticker-blue',
    tileRot: '-1.2deg',
  },
  {
    name: 'Chen Tai',
    role: 'Encryption Engineer',
    icon: LockKeyhole,
    initials: 'CT',
    bio: 'Builds encryption modules and ensures secure key management.',
    detail:
      'Implements browser-side cryptography, key wrapping, and recovery paths so plaintext never needs to leave the client trust boundary.',
    accent: 'from-emerald-500/20 via-transparent to-emerald-500/5',
    mosaic: 'mosaic-tile-tall',
    stickerTone: 'sticker-emerald',
    tileRot: '1.4deg',
  },
  {
    name: 'Li Junyan',
    role: 'Frontend Developer',
    icon: Code,
    initials: 'LJ',
    bio: 'Develops responsive interfaces and interaction experiences.',
    detail:
      'Shapes the SecureView UI — navigation, workspace flows, and motion — so security features remain readable and approachable on every screen size.',
    accent: 'from-sky-500/20 via-transparent to-sky-500/5',
    mosaic: 'mosaic-tile-wide',
    stickerTone: 'sticker-sky',
    tileRot: '-0.8deg',
  },
  {
    name: 'Jason Huang',
    role: 'Backend Engineer',
    icon: Server,
    initials: 'JH',
    bio: 'Maintains APIs, file pipelines, and system reliability.',
    detail:
      'Keeps FastAPI routes, storage pipelines, and audit persistence stable so encrypted collaboration has a dependable server backbone.',
    accent: 'from-slate-500/20 via-transparent to-slate-500/5',
    mosaic: 'mosaic-tile-square',
    stickerTone: 'sticker-slate',
    tileRot: '1deg',
  },
]

/** Demo-only contact form — nothing is sent to a server yet. */
const feedbackName = ref('')
const feedbackEmail = ref('')
const feedbackTopic = ref('feedback')
const feedbackMessage = ref('')
const feedbackSubmitted = ref(false)
const feedbackError = ref('')

function submitFeedback() {
  feedbackError.value = ''
  if (!feedbackName.value.trim() || !feedbackEmail.value.trim() || !feedbackMessage.value.trim()) {
    feedbackError.value = 'Please fill in your name, email, and message.'
    return
  }
  // Placeholder only: pretend the note was accepted so the UI can be reviewed.
  feedbackSubmitted.value = true
}

function resetFeedback() {
  feedbackName.value = ''
  feedbackEmail.value = ''
  feedbackTopic.value = 'feedback'
  feedbackMessage.value = ''
  feedbackSubmitted.value = false
  feedbackError.value = ''
}

const HOVER_OPEN_MS = 2000
const hoveredId = ref<string | null>(null)
const pinnedId = ref<string | null>(null)
let openTimer = 0
let closeTimer = 0

const activeId = computed(() => pinnedId.value ?? hoveredId.value)
const activeMember = computed(() => members.find((m) => m.name === activeId.value) ?? null)

function cancelOpen() {
  window.clearTimeout(openTimer)
  openTimer = 0
}

function cancelClose() {
  window.clearTimeout(closeTimer)
  closeTimer = 0
}

function scheduleOpen(name: string) {
  cancelClose()
  cancelOpen()
  if (activeId.value === name) return
  openTimer = window.setTimeout(() => {
    hoveredId.value = name
    openTimer = 0
  }, HOVER_OPEN_MS)
}

function scheduleClose() {
  cancelOpen()
  if (pinnedId.value) return
  cancelClose()
  closeTimer = window.setTimeout(() => {
    hoveredId.value = null
  }, 140)
}

function togglePin(name: string) {
  cancelOpen()
  cancelClose()
  pinnedId.value = pinnedId.value === name ? null : name
  hoveredId.value = pinnedId.value
}

function dismissOverlay() {
  cancelOpen()
  cancelClose()
  pinnedId.value = null
  hoveredId.value = null
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') dismissOverlay()
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  cancelOpen()
  cancelClose()
})
</script>

<template>
  <section class="relative overflow-hidden py-16 md:py-24">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_12%,color-mix(in_oklab,var(--primary)_14%,transparent),transparent_42%),radial-gradient(circle_at_88%_78%,color-mix(in_oklab,var(--primary)_10%,transparent),transparent_46%)]" />

    <div class="container relative mx-auto px-4">
      <div class="mb-10 max-w-3xl md:mb-12">
        <p class="mb-3 text-xs font-semibold uppercase tracking-[0.32em] text-primary">SecureView</p>
        <h1 class="text-4xl font-bold tracking-tight text-foreground sm:text-5xl md:text-6xl">
          Contact
          <span class="text-primary"> us</span>
        </h1>
        <p class="mt-4 max-w-2xl text-base text-muted-foreground md:text-lg">
          Send feedback or a suggestion, then meet the people behind SecureView.
        </p>
      </div>

      <div class="mb-14 max-w-3xl rounded-3xl border border-border bg-card/90 p-6 shadow-[0_10px_28px_color-mix(in_oklab,var(--foreground)_5%,transparent)] md:mb-16 md:p-8">
        <div class="mb-6">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Feedback</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-foreground">Share a note with the team</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Tell us what worked, what did not, or what you would like next. We read every message.
          </p>
        </div>

        <div
          v-if="feedbackSubmitted"
          class="rounded-2xl border border-primary/25 bg-primary/10 px-5 py-6"
        >
          <p class="text-base font-medium text-foreground">Feedback submitted successfully.</p>
          <p class="mt-2 text-sm text-muted-foreground">
            Thank you for your note. Our team has received it and will review it shortly.
          </p>
          <button
            type="button"
            class="mt-5 inline-flex h-10 items-center rounded-full border border-border bg-card px-5 text-sm text-foreground transition-colors hover:bg-secondary"
            @click="resetFeedback"
          >
            Submit another message
          </button>
        </div>

        <form v-else class="space-y-5" @submit.prevent="submitFeedback">
          <div class="grid gap-5 sm:grid-cols-2">
            <label class="block space-y-2">
              <span class="text-sm font-medium text-foreground">Name</span>
              <input
                v-model="feedbackName"
                type="text"
                autocomplete="name"
                placeholder="Your name"
                class="h-11 w-full rounded-2xl border border-border bg-background px-4 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
              />
            </label>
            <label class="block space-y-2">
              <span class="text-sm font-medium text-foreground">Email</span>
              <input
                v-model="feedbackEmail"
                type="email"
                autocomplete="email"
                placeholder="you@example.com"
                class="h-11 w-full rounded-2xl border border-border bg-background px-4 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
              />
            </label>
          </div>

          <label class="block space-y-2">
            <span class="text-sm font-medium text-foreground">Topic</span>
            <select
              v-model="feedbackTopic"
              class="h-11 w-full rounded-2xl border border-border bg-background px-4 text-sm text-foreground outline-none transition-colors focus:border-primary"
            >
              <option value="feedback">General feedback</option>
              <option value="suggestion">Feature suggestion</option>
              <option value="bug">Bug report</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label class="block space-y-2">
            <span class="text-sm font-medium text-foreground">Message</span>
            <textarea
              v-model="feedbackMessage"
              rows="5"
              placeholder="Tell us what worked, what did not, or what you would like next…"
              class="w-full resize-y rounded-2xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
            />
          </label>

          <p v-if="feedbackError" class="text-sm text-destructive">{{ feedbackError }}</p>

          <button
            type="submit"
            class="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <Send class="h-4 w-4" />
            Send feedback
          </button>
        </form>
      </div>

      <div class="mb-8 max-w-3xl md:mb-10">
        <p class="mb-2 text-xs font-semibold uppercase tracking-[0.32em] text-primary">Development Team</p>
        <h2 class="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Meet the
          <span class="text-primary"> people</span>
        </h2>
        <p class="mt-3 max-w-2xl text-base text-muted-foreground md:text-lg">
          We are a team of builders united by encrypted collaboration. Each member is a unique piece of the puzzle, crafting secure, decentralized solutions together.
        </p>
      </div>

      <div class="team-mosaic" @mouseleave="scheduleClose">
        <article
          v-for="member in members"
          :key="member.name"
          class="team-tile group"
          :class="[member.mosaic, { 'team-tile-active': activeId === member.name }]"
          :style="{ '--tile-rot': member.tileRot }"
          tabindex="0"
          :aria-expanded="activeId === member.name"
          @mouseenter="scheduleOpen(member.name)"
          @focusin="scheduleOpen(member.name)"
          @focusout="scheduleClose"
          @click="togglePin(member.name)"
          @keydown.enter.prevent="togglePin(member.name)"
          @keydown.space.prevent="togglePin(member.name)"
        >
          <div class="team-tile__frame" :class="`bg-gradient-to-br ${member.accent}`">
            <div class="team-tile__split">
              <div class="team-tile__identity">
                <div class="team-sticker" :class="member.stickerTone">
                  <span class="team-sticker__tape" aria-hidden="true" />
                  <span class="team-sticker__initials">{{ member.initials }}</span>
                  <span class="team-sticker__badge">
                    <component :is="member.icon" class="h-4 w-4" />
                  </span>
                </div>
                <h2 class="mt-4 text-xl font-semibold tracking-tight text-foreground md:text-2xl">
                  {{ member.name }}
                </h2>
                <p class="mt-1 text-sm font-medium text-primary">{{ member.role }}</p>
              </div>

              <div class="team-tile__bio">
                <p class="text-[0.7rem] font-semibold uppercase tracking-[0.22em] text-muted-foreground">Intro</p>
                <p class="mt-3 text-sm leading-relaxed text-muted-foreground md:text-base">
                  {{ member.bio }}
                </p>
                <p class="mt-4 text-xs text-primary/80 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                  Hold 2s to enlarge
                </p>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="team-overlay">
        <div
          v-if="activeMember"
          class="team-overlay"
          role="dialog"
          aria-modal="true"
          :aria-label="`${activeMember.name} profile`"
          @mouseenter="cancelClose"
          @mouseleave="scheduleClose"
          @click.self="dismissOverlay"
        >
          <div class="team-popup" :class="activeMember.stickerTone">
            <button
              type="button"
              class="team-popup__close"
              aria-label="Close profile"
              @click="dismissOverlay"
            >
              <X class="h-4 w-4" />
            </button>

            <div class="team-popup__layout">
              <div class="team-popup__left">
                <div class="team-sticker team-sticker--xl" :class="activeMember.stickerTone">
                  <span class="team-sticker__tape" aria-hidden="true" />
                  <span class="team-sticker__initials">{{ activeMember.initials }}</span>
                  <span class="team-sticker__badge">
                    <component :is="activeMember.icon" class="h-5 w-5" />
                  </span>
                </div>
                <h2 class="mt-6 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
                  {{ activeMember.name }}
                </h2>
                <p class="mt-2 text-base font-medium text-primary md:text-lg">{{ activeMember.role }}</p>
              </div>

              <div class="team-popup__right">
                <p class="text-xs font-semibold uppercase tracking-[0.28em] text-muted-foreground">About</p>
                <p class="mt-3 text-base leading-relaxed text-foreground md:text-lg">
                  {{ activeMember.bio }}
                </p>
                <p class="mt-5 text-sm leading-relaxed text-muted-foreground md:text-base">
                  {{ activeMember.detail }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.team-mosaic {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

.team-tile {
  position: relative;
  transform: rotate(var(--tile-rot, 0deg));
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), z-index 0s;
  cursor: pointer;
  outline: none;
}

.team-tile:hover,
.team-tile:focus-within,
.team-tile-active {
  z-index: 3;
  transform: rotate(0deg) translateY(-4px) scale(1.015);
}

.team-tile__frame {
  height: 100%;
  min-height: 14rem;
  border: 1px solid var(--border);
  border-radius: 1.25rem;
  background: color-mix(in oklab, var(--card) 94%, transparent);
  backdrop-filter: blur(12px);
  box-shadow: 0 18px 40px color-mix(in oklab, var(--foreground) 7%, transparent);
  overflow: hidden;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.team-tile:hover .team-tile__frame,
.team-tile-active .team-tile__frame {
  border-color: color-mix(in oklab, var(--primary) 42%, var(--border));
  box-shadow: 0 26px 56px color-mix(in oklab, var(--foreground) 12%, transparent);
}

.team-tile__split {
  display: grid;
  grid-template-columns: minmax(9rem, 0.9fr) minmax(0, 1.1fr);
  height: 100%;
  min-height: inherit;
}

.team-tile__identity {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 1.25rem 1.1rem 1.25rem 1.25rem;
  border-right: 1px dashed color-mix(in oklab, var(--border) 85%, var(--primary));
  background: color-mix(in oklab, var(--secondary) 55%, transparent);
}

.team-tile__bio {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 1.25rem 1.35rem;
}

.team-sticker {
  position: relative;
  width: 5.5rem;
  height: 6.4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.85rem;
  border: 1px solid color-mix(in oklab, var(--border) 70%, transparent);
  background:
    linear-gradient(145deg, color-mix(in oklab, white 18%, transparent), transparent 55%),
    color-mix(in oklab, var(--card) 88%, var(--primary));
  box-shadow:
    0 10px 24px color-mix(in oklab, var(--foreground) 10%, transparent),
    inset 0 1px 0 color-mix(in oklab, white 35%, transparent);
  transform: rotate(-4deg);
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.team-tile:hover .team-sticker,
.team-tile-active .team-sticker {
  transform: rotate(0deg) scale(1.04);
}

.team-sticker__tape {
  position: absolute;
  top: -0.45rem;
  left: 50%;
  width: 2.4rem;
  height: 0.7rem;
  transform: translateX(-50%) rotate(-2deg);
  border-radius: 0.15rem;
  background: color-mix(in oklab, var(--primary) 28%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--primary) 18%, transparent);
}

.team-sticker__initials {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--foreground);
}

.team-sticker__badge {
  position: absolute;
  right: -0.45rem;
  bottom: -0.45rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--primary);
  box-shadow: 0 6px 14px color-mix(in oklab, var(--foreground) 10%, transparent);
}

.team-sticker--xl {
  width: 8.5rem;
  height: 10rem;
  transform: rotate(-3deg);
}

.team-sticker--xl .team-sticker__initials {
  font-size: 2.4rem;
}

.sticker-blue {
  background:
    linear-gradient(145deg, color-mix(in oklab, white 20%, transparent), transparent 50%),
    linear-gradient(160deg, color-mix(in oklab, rgb(0, 109, 199) 18%, var(--card)), var(--card));
}

.sticker-emerald {
  background:
    linear-gradient(145deg, color-mix(in oklab, white 20%, transparent), transparent 50%),
    linear-gradient(160deg, color-mix(in oklab, rgb(16, 185, 129) 16%, var(--card)), var(--card));
}

.sticker-sky {
  background:
    linear-gradient(145deg, color-mix(in oklab, white 20%, transparent), transparent 50%),
    linear-gradient(160deg, color-mix(in oklab, rgb(14, 165, 233) 16%, var(--card)), var(--card));
}

.sticker-slate {
  background:
    linear-gradient(145deg, color-mix(in oklab, white 20%, transparent), transparent 50%),
    linear-gradient(160deg, color-mix(in oklab, rgb(100, 116, 139) 16%, var(--card)), var(--card));
}

.sticker-amber {
  background:
    linear-gradient(145deg, color-mix(in oklab, white 20%, transparent), transparent 50%),
    linear-gradient(160deg, color-mix(in oklab, rgb(217, 119, 6) 16%, var(--card)), var(--card));
}

.mosaic-tile-supervisor,
.mosaic-tile-hero,
.mosaic-tile-tall,
.mosaic-tile-wide,
.mosaic-tile-square {
  min-height: 15rem;
}

@media (min-width: 768px) {
  .team-mosaic {
    grid-template-columns: repeat(12, minmax(0, 1fr));
    grid-auto-rows: minmax(11rem, auto);
    gap: 1.15rem;
  }

  .mosaic-tile-supervisor {
    grid-column: span 12;
    grid-row: span 1;
    min-height: 14.5rem;
  }

  .mosaic-tile-hero {
    grid-column: span 7;
    grid-row: span 2;
    min-height: 22rem;
  }

  .mosaic-tile-tall {
    grid-column: span 5;
    grid-row: span 2;
    min-height: 22rem;
  }

  .mosaic-tile-wide {
    grid-column: span 7;
    grid-row: span 1;
    min-height: 13.5rem;
  }

  .mosaic-tile-square {
    grid-column: span 5;
    grid-row: span 1;
    min-height: 13.5rem;
  }

  .team-tile__identity {
    padding: 1.6rem;
  }

  .team-tile__bio {
    padding: 1.6rem 1.75rem;
  }
}

@media (max-width: 639px) {
  .team-tile {
    transform: none;
  }

  .team-tile__split {
    grid-template-columns: 1fr;
  }

  .team-tile__identity {
    border-right: 0;
    border-bottom: 1px dashed color-mix(in oklab, var(--border) 85%, var(--primary));
  }
}

.team-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  background: color-mix(in oklab, var(--background) 42%, transparent);
  backdrop-filter: blur(10px);
}

.team-popup {
  position: relative;
  width: min(92vw, 52rem);
  border: 1px solid color-mix(in oklab, var(--primary) 35%, var(--border));
  border-radius: 1.5rem;
  background: color-mix(in oklab, var(--card) 96%, transparent);
  box-shadow: 0 30px 80px color-mix(in oklab, var(--foreground) 18%, transparent);
  padding: 1.5rem;
  overflow: hidden;
}

.team-popup::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle at 12% 18%, color-mix(in oklab, var(--primary) 14%, transparent), transparent 42%);
}

.team-popup__close {
  position: absolute;
  top: 0.9rem;
  right: 0.9rem;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--muted-foreground);
  transition: background 0.2s ease, color 0.2s ease;
}

.team-popup__close:hover {
  background: var(--secondary);
  color: var(--foreground);
}

.team-popup__layout {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 1.5rem;
}

.team-popup__left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding-right: 0.5rem;
}

.team-popup__right {
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-top: 1px dashed var(--border);
  padding-top: 1.25rem;
}

@media (min-width: 768px) {
  .team-popup {
    padding: 2.25rem 2.5rem;
  }

  .team-popup__layout {
    grid-template-columns: minmax(14rem, 0.85fr) minmax(0, 1.15fr);
    gap: 2rem;
    align-items: stretch;
  }

  .team-popup__right {
    border-top: 0;
    border-left: 1px dashed var(--border);
    padding-top: 0;
    padding-left: 2rem;
  }
}

.team-overlay-enter-active,
.team-overlay-leave-active {
  transition: opacity 0.28s ease;
}

.team-overlay-enter-active .team-popup,
.team-overlay-leave-active .team-popup {
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.35s ease;
}

.team-overlay-enter-from,
.team-overlay-leave-to {
  opacity: 0;
}

.team-overlay-enter-from .team-popup,
.team-overlay-leave-to .team-popup {
  opacity: 0;
  transform: translateY(18px) scale(0.94);
}

@media (prefers-reduced-motion: reduce) {
  .team-tile,
  .team-sticker,
  .team-tile__frame,
  .team-overlay-enter-active,
  .team-overlay-leave-active,
  .team-overlay-enter-active .team-popup,
  .team-overlay-leave-active .team-popup {
    transition: none;
  }

  .team-tile {
    transform: none;
  }
}
</style>
