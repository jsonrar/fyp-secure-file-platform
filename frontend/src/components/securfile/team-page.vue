<script setup lang="ts">
import { ArrowUpRight, Bug, Code, Github, GraduationCap, Lightbulb, LockKeyhole, Mail, MessageSquare, Palette, Send, Server, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Component } from 'vue'
import asadPhoto from '@/assets/people/asad-malik.jpg'

/**
 * Contact us: feedback, then the supervisor and the development team as tilted sticker tiles.
 *
 * The tile design is Junyan Li's and is kept as it was. What changed is the information on it:
 * names, roles and one-line responsibilities follow the group's MCS21 presentation, each member
 * links their GitHub profile and Monash student email, and the supervisor's tile carries the
 * title, research interests, photo and profile link from his Monash research profile.
 */

const SUPERVISOR_PROFILE_URL = 'https://research.monash.edu/en/persons/asad-malik/'

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
  /** The supervisor's tile shows his portrait in the sticker and a profile link. */
  photo?: string
  title?: string
  affiliation?: string
  interests?: string[]
  profileUrl?: string
  github?: { url: string; handle: string }
  email?: string
}

const members: TeamMember[] = [
  {
    name: 'Dr. Asad Malik',
    role: 'Project supervisor',
    icon: GraduationCap,
    initials: 'AM',
    bio: 'Lecturer and Cybersecurity Group Leader, School of Information Technology, Monash University Malaysia.',
    detail:
      'Guides SecureView on scope, technical direction and evaluation, so the team keeps a coherent security architecture, realistic milestones and a platform that stands up to review.',
    accent: 'from-amber-500/20 via-transparent to-amber-500/5',
    mosaic: 'mosaic-tile-supervisor',
    stickerTone: 'sticker-amber',
    tileRot: '-0.6deg',
    photo: asadPhoto,
    title: 'Lecturer and Cybersecurity Group Leader',
    affiliation: 'School of Information Technology, Monash University Malaysia',
    interests: ['Cybersecurity', 'Multimedia forensics', 'DeepFake detection', 'Trustworthy AI'],
    profileUrl: SUPERVISOR_PROFILE_URL,
  },
  {
    name: 'Shuoxun Wen',
    role: 'Project Lead',
    icon: Palette,
    initials: 'SW',
    bio: 'Backlog, server and deployment, MySQL, testing and documentation.',
    detail:
      'Runs the backlog and the release process, owns the staging server and its deployment, the MySQL database, and the testing and documentation that show the platform does what it claims.',
    accent: 'from-[rgb(0,109,199)]/25 via-transparent to-[rgb(0,109,199)]/5',
    mosaic: 'mosaic-tile-hero',
    stickerTone: 'sticker-blue',
    tileRot: '-1.2deg',
    github: { url: 'https://github.com/Waldo0926', handle: 'Waldo0926' },
    email: 'swen0027@student.monash.edu',
  },
  {
    name: 'Tai Chen',
    role: 'Cryptography',
    icon: LockKeyhole,
    initials: 'TC',
    bio: 'Browser encryption, file envelope, key wrapping and test vectors.',
    detail:
      'Implements the browser-side cryptography, the encrypted file envelope and key wrapping, and the test vectors that check them, so plaintext never needs to leave the client trust boundary.',
    accent: 'from-emerald-500/20 via-transparent to-emerald-500/5',
    mosaic: 'mosaic-tile-tall',
    stickerTone: 'sticker-emerald',
    tileRot: '1.4deg',
    github: { url: 'https://github.com/Charter888', handle: 'Charter888' },
    email: 'tche0186@student.monash.edu',
  },
  {
    name: 'Junyan Li',
    role: 'Frontend and Interface',
    icon: Code,
    initials: 'JL',
    bio: 'Vue pages, product journeys, Education and Help content.',
    detail:
      'Builds the SecureView interface: the Vue pages, the product journeys, and the Education and Help content, so security features stay readable and approachable on every screen size.',
    accent: 'from-sky-500/20 via-transparent to-sky-500/5',
    mosaic: 'mosaic-tile-wide',
    stickerTone: 'sticker-sky',
    tileRot: '-0.8deg',
    github: { url: 'https://github.com/jlii0421', handle: 'jlii0421' },
    email: 'jlii0421@student.monash.edu',
  },
  {
    name: 'Jason Huang',
    role: 'Backend and APIs',
    icon: Server,
    initials: 'JH',
    bio: 'FastAPI services, authentication, sharing and audit endpoints.',
    detail:
      'Maintains the FastAPI services behind the platform: authentication, file storage, sharing and the audit endpoints, so encrypted collaboration has a dependable server backbone.',
    accent: 'from-slate-500/20 via-transparent to-slate-500/5',
    mosaic: 'mosaic-tile-square',
    stickerTone: 'sticker-slate',
    tileRot: '1deg',
    github: { url: 'https://github.com/jsonrar', handle: 'jsonrar' },
    email: 'jhua0176@student.monash.edu',
  },
]

const topics = [
  { icon: MessageSquare, label: 'General feedback', hint: 'What worked and what did not' },
  { icon: Lightbulb, label: 'Feature suggestion', hint: 'What you would like next' },
  { icon: Bug, label: 'Bug report', hint: 'Something that broke or looked wrong' },
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

const fieldClass =
  'h-11 w-full rounded-xl border border-border bg-background px-4 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary'

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
  <section class="relative overflow-hidden py-14 md:py-20">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_12%,color-mix(in_oklab,var(--primary)_14%,transparent),transparent_42%),radial-gradient(circle_at_88%_78%,color-mix(in_oklab,var(--primary)_10%,transparent),transparent_46%)]" />

    <div class="container relative mx-auto max-w-6xl px-4">
      <header class="mb-12 max-w-3xl md:mb-14">
        <p class="mb-3 text-xs font-semibold uppercase tracking-[0.32em] text-primary">SecureView</p>
        <h1 class="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Contact <span class="text-primary">us</span>
        </h1>
        <p class="mt-4 text-base text-muted-foreground md:text-lg">
          Send us feedback, then meet the supervisor and the team behind SecureView.
        </p>
      </header>

      <!-- Feedback: the pitch on the left, the form on the right, so a wide screen is used and not left half empty. -->
      <div class="mb-16 grid gap-8 md:mb-20 lg:grid-cols-5 lg:gap-12" data-testid="team-feedback">
        <div class="lg:col-span-2">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Feedback</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
            Share a note with the team
          </h2>
          <p class="mt-3 text-sm text-muted-foreground md:text-base">
            Tell us what worked, what did not, or what you would like next. We read every message.
          </p>
          <ul class="mt-6 space-y-3">
            <li v-for="topic in topics" :key="topic.label" class="flex items-start gap-3">
              <span class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <component :is="topic.icon" class="h-4 w-4" />
              </span>
              <span>
                <span class="block text-sm font-medium text-foreground">{{ topic.label }}</span>
                <span class="block text-sm text-muted-foreground">{{ topic.hint }}</span>
              </span>
            </li>
          </ul>
        </div>

        <div class="rounded-3xl border border-border bg-card p-6 shadow-sm md:p-8 lg:col-span-3">
          <div
            v-if="feedbackSubmitted"
            class="rounded-2xl border border-primary/25 bg-primary/10 px-5 py-6"
            role="status"
          >
            <p class="text-base font-medium text-foreground">Feedback submitted successfully.</p>
            <p class="mt-2 text-sm text-muted-foreground">
              Thank you for your note. Our team has received it and will review it shortly.
            </p>
            <button
              type="button"
              class="mt-5 inline-flex h-11 items-center rounded-full border border-border bg-card px-5 text-sm text-foreground transition-colors hover:bg-secondary"
              @click="resetFeedback"
            >
              Submit another message
            </button>
          </div>

          <form v-else class="space-y-5" @submit.prevent="submitFeedback">
            <div class="grid gap-5 sm:grid-cols-2">
              <label class="block space-y-2">
                <span class="text-sm font-medium text-foreground">Name</span>
                <input v-model="feedbackName" type="text" autocomplete="name" placeholder="Your name" :class="fieldClass" />
              </label>
              <label class="block space-y-2">
                <span class="text-sm font-medium text-foreground">Email</span>
                <input v-model="feedbackEmail" type="email" autocomplete="email" placeholder="you@example.com" :class="fieldClass" />
              </label>
            </div>

            <label class="block space-y-2">
              <span class="text-sm font-medium text-foreground">Topic</span>
              <select v-model="feedbackTopic" :class="fieldClass">
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
                class="w-full resize-y rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
              />
            </label>

            <p v-if="feedbackError" class="text-sm text-destructive" role="alert">{{ feedbackError }}</p>

            <button
              type="submit"
              class="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <Send class="h-4 w-4" />
              Send feedback
            </button>
          </form>
        </div>
      </div>

      <div class="mb-8 max-w-3xl md:mb-10">
        <p class="mb-2 text-xs font-semibold uppercase tracking-[0.32em] text-primary">Supervisor and development team · Group MCS21</p>
        <h2 class="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Meet the
          <span class="text-primary"> people</span>
        </h2>
        <p class="mt-3 max-w-2xl text-base text-muted-foreground md:text-lg">
          We are a team of builders united by encrypted collaboration. Each member is a unique piece of the puzzle, crafting secure, decentralized solutions together.
        </p>
      </div>

      <div class="team-mosaic" data-testid="team-members" @mouseleave="scheduleClose">
        <article
          v-for="member in members"
          :key="member.name"
          class="team-tile group"
          :data-testid="member.profileUrl ? 'team-supervisor' : 'team-member'"
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
                  <img
                    v-if="member.photo"
                    :src="member.photo"
                    :alt="`Portrait of ${member.name}`"
                    width="640"
                    height="789"
                    class="team-sticker__photo"
                    loading="lazy"
                  />
                  <span v-else class="team-sticker__initials">{{ member.initials }}</span>
                  <span class="team-sticker__tape" aria-hidden="true" />
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
                <p v-if="member.interests" class="mt-3 text-xs text-muted-foreground">
                  {{ member.interests.join(' · ') }}
                </p>
                <div class="team-links" @click.stop @keydown.enter.stop @keydown.space.stop>
                  <a
                    v-if="member.profileUrl"
                    :href="member.profileUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="team-link"
                    data-testid="supervisor-profile-link"
                  >
                    <ArrowUpRight class="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>View Monash profile</span>
                  </a>
                  <template v-else>
                    <a
                      :href="member.github!.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="team-link"
                      :aria-label="`${member.name} on GitHub`"
                      data-testid="member-github"
                    >
                      <Github class="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span>@{{ member.github!.handle }}</span>
                    </a>
                    <a
                      :href="`mailto:${member.email}`"
                      class="team-link"
                      :aria-label="`Email ${member.name}`"
                      data-testid="member-email"
                    >
                      <Mail class="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span>{{ member.email!.split('@')[0] }}@<wbr />{{ member.email!.split('@')[1] }}</span>
                    </a>
                  </template>
                </div>
                <p class="mt-3 text-xs text-primary/80 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
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
                  <img
                    v-if="activeMember.photo"
                    :src="activeMember.photo"
                    :alt="`Portrait of ${activeMember.name}`"
                    class="team-sticker__photo"
                  />
                  <span v-else class="team-sticker__initials">{{ activeMember.initials }}</span>
                  <span class="team-sticker__tape" aria-hidden="true" />
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
                <template v-if="activeMember.interests">
                  <p class="mt-5 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Research interests</p>
                  <ul class="mt-2 flex flex-wrap gap-2">
                    <li
                      v-for="interest in activeMember.interests"
                      :key="interest"
                      class="rounded-full border border-border bg-secondary/60 px-3 py-1 text-sm text-foreground"
                    >
                      {{ interest }}
                    </li>
                  </ul>
                </template>
                <div class="team-links team-links--popup">
                  <a
                    v-if="activeMember.profileUrl"
                    :href="activeMember.profileUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="team-link"
                  >
                    <ArrowUpRight class="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>View Monash profile</span>
                  </a>
                  <template v-else-if="activeMember.github">
                    <a :href="activeMember.github.url" target="_blank" rel="noopener noreferrer" class="team-link">
                      <Github class="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span>@{{ activeMember.github.handle }}</span>
                    </a>
                    <a :href="`mailto:${activeMember.email}`" class="team-link">
                      <Mail class="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span>{{ activeMember.email!.split('@')[0] }}@<wbr />{{ activeMember.email!.split('@')[1] }}</span>
                    </a>
                  </template>
                </div>
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

.team-sticker__photo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  object-fit: cover;
  object-position: top;
}

.team-sticker__tape {
  z-index: 1;
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

.team-links {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-top: 0.75rem;
}

.team-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.5rem;
  width: fit-content;
  max-width: 100%;
  padding: 0 0.4rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  color: var(--foreground);
  overflow-wrap: break-word;
  transition: background 0.2s ease, color 0.2s ease;
}

.team-link:hover {
  background: var(--secondary);
  color: var(--primary);
}

.team-links--popup {
  margin-top: 1.25rem;
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
