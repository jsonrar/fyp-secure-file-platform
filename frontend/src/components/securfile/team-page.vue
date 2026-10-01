<script setup lang="ts">
import { ArrowUpRight, Bug, Github, Lightbulb, Mail, MessageSquare, Send } from 'lucide-vue-next'
import { ref } from 'vue'
import asadPhoto from '@/assets/people/asad-malik.jpg'

/**
 * Contact us: feedback, the project supervisor, and the four-person development team.
 *
 * Roles and one-line responsibilities follow the group's MCS21 presentation. The supervisor's
 * title, research interests and photo come from his Monash University research profile, which
 * is linked from the card.
 */

const SUPERVISOR_PROFILE_URL = 'https://research.monash.edu/en/persons/asad-malik/'

const supervisor = {
  name: 'Dr. Asad Malik',
  role: 'Project supervisor',
  title: 'Lecturer and Cybersecurity Group Leader',
  affiliation: 'Malaysia School of Information Technology, Monash University Malaysia',
  guidance:
    'Guides SecureView on scope, technical direction and evaluation, so the team keeps a coherent security architecture, realistic milestones and a platform that stands up to review.',
  interests: ['Cybersecurity', 'Multimedia forensics', 'DeepFake detection', 'Trustworthy AI'],
}

interface TeamMember {
  name: string
  initials: string
  role: string
  focus: string
  /** Profile URL and the handle shown for it. */
  github: { url: string; handle: string }
  email: string
  /** Tailwind classes, spelled out in full so the compiler can see them. */
  pill: string
  avatar: string
}

const members: TeamMember[] = [
  {
    name: 'Shuoxun Wen',
    initials: 'SW',
    role: 'Project Lead',
    focus: 'Backlog, server and deployment, MySQL, testing and documentation',
    github: { url: 'https://github.com/Waldo0926', handle: 'Waldo0926' },
    email: 'swen0027@student.monash.edu',
    pill: 'bg-amber-600 text-white',
    avatar: 'bg-amber-500/15 text-amber-700 ring-amber-500/30 dark:text-amber-300',
  },
  {
    name: 'Jason Huang',
    initials: 'JH',
    role: 'Backend and APIs',
    focus: 'FastAPI services, authentication, sharing and audit endpoints',
    github: { url: 'https://github.com/jsonrar', handle: 'jsonrar' },
    email: 'jhua0176@student.monash.edu',
    pill: 'bg-blue-600 text-white',
    avatar: 'bg-blue-500/15 text-blue-700 ring-blue-500/30 dark:text-blue-300',
  },
  {
    name: 'Junyan Li',
    initials: 'JL',
    role: 'Frontend and Interface',
    focus: 'Vue pages, product journeys, Education and Help content',
    github: { url: 'https://github.com/jlii0421', handle: 'jlii0421' },
    email: 'jlii0421@student.monash.edu',
    pill: 'bg-emerald-600 text-white',
    avatar: 'bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-300',
  },
  {
    name: 'Tai Chen',
    initials: 'TC',
    role: 'Cryptography',
    focus: 'Browser encryption, file envelope, key wrapping and test vectors',
    github: { url: 'https://github.com/Charter888', handle: 'Charter888' },
    email: 'tche0186@student.monash.edu',
    pill: 'bg-violet-600 text-white',
    avatar: 'bg-violet-500/15 text-violet-700 ring-violet-500/30 dark:text-violet-300',
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
</script>

<template>
  <section class="relative overflow-hidden py-14 md:py-20">
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_8%,color-mix(in_oklab,var(--primary)_12%,transparent),transparent_40%),radial-gradient(circle_at_90%_70%,color-mix(in_oklab,var(--primary)_8%,transparent),transparent_44%)]"
    />

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

      <!-- Supervisor -->
      <div class="mb-16 md:mb-20" data-testid="team-supervisor">
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Supervisor</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-foreground md:text-3xl">Who guides the project</h2>

        <article class="mt-6 grid overflow-hidden rounded-3xl border border-border bg-card shadow-sm md:grid-cols-[17rem_1fr]">
          <div class="relative aspect-[4/5] bg-secondary md:aspect-auto">
            <img
              :src="asadPhoto"
              alt="Portrait of Dr. Asad Malik"
              width="640"
              height="789"
              class="absolute inset-0 h-full w-full object-cover object-top"
              loading="lazy"
            />
          </div>
          <div class="flex flex-col justify-center p-6 md:p-8">
            <span class="inline-flex w-fit items-center rounded-full bg-primary px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary-foreground">
              {{ supervisor.role }}
            </span>
            <h3 class="mt-3 text-2xl font-bold tracking-tight text-foreground md:text-3xl">{{ supervisor.name }}</h3>
            <p class="mt-1 text-base font-medium text-primary">{{ supervisor.title }}</p>
            <p class="text-sm text-muted-foreground">{{ supervisor.affiliation }}</p>

            <p class="mt-5 text-sm leading-relaxed text-foreground md:text-base">{{ supervisor.guidance }}</p>

            <p class="mt-5 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Research interests</p>
            <ul class="mt-2 flex flex-wrap gap-2">
              <li
                v-for="interest in supervisor.interests"
                :key="interest"
                class="rounded-full border border-border bg-secondary/60 px-3 py-1 text-sm text-foreground"
              >
                {{ interest }}
              </li>
            </ul>

            <a
              :href="SUPERVISOR_PROFILE_URL"
              target="_blank"
              rel="noopener noreferrer"
              class="mt-6 inline-flex h-11 w-fit items-center gap-2 rounded-full border border-border px-5 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
            >
              View Monash profile
              <ArrowUpRight class="h-4 w-4" />
            </a>
          </div>
        </article>
      </div>

      <!-- Team -->
      <div data-testid="team-members">
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Development team · Group MCS21</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-foreground md:text-3xl">Meet the people</h2>
        <p class="mt-3 max-w-2xl text-sm text-muted-foreground md:text-base">
          Four builders, one encrypted collaboration platform: each member owns an area, and every area is reviewed by the others.
        </p>

        <ul class="mt-8 grid gap-4 sm:grid-cols-2">
          <li
            v-for="member in members"
            :key="member.name"
            class="flex flex-col rounded-2xl border border-border bg-card p-6 shadow-sm"
            data-testid="team-member"
          >
            <span
              class="flex h-14 w-14 items-center justify-center rounded-2xl text-lg font-bold ring-1"
              :class="member.avatar"
              aria-hidden="true"
            >
              {{ member.initials }}
            </span>
            <h3 class="mt-4 text-lg font-semibold tracking-tight text-foreground">{{ member.name }}</h3>
            <span class="mt-2 inline-flex w-fit rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide" :class="member.pill">
              {{ member.role }}
            </span>
            <p class="mt-3 flex-1 text-sm leading-relaxed text-muted-foreground">{{ member.focus }}</p>

            <div class="mt-5 space-y-1 border-t border-border pt-4 text-sm">
              <a
                :href="member.github.url"
                target="_blank"
                rel="noopener noreferrer"
                class="flex min-h-10 items-center gap-2 rounded-lg px-2 text-foreground transition-colors hover:bg-secondary hover:text-primary"
                :aria-label="`${member.name} on GitHub`"
                data-testid="member-github"
              >
                <Github class="h-4 w-4 shrink-0 text-muted-foreground" />
                <span class="min-w-0 [overflow-wrap:anywhere]">@{{ member.github.handle }}</span>
              </a>
              <a
                :href="`mailto:${member.email}`"
                class="flex min-h-10 items-center gap-2 rounded-lg px-2 text-foreground transition-colors hover:bg-secondary hover:text-primary"
                :aria-label="`Email ${member.name}`"
                data-testid="member-email"
              >
                <Mail class="h-4 w-4 shrink-0 text-muted-foreground" />
                <span class="min-w-0 [overflow-wrap:anywhere]">{{ member.email }}</span>
              </a>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
