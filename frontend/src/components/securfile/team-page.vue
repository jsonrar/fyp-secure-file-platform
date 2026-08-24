<script setup lang="ts">
import { ChevronDown, Code, LockKeyhole, Palette, Server } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { CSSProperties } from 'vue'

const members = [
  {
    name: 'Wen Shuoxun',
    role: 'Testing Engineer',
    icon: Palette,
    initials: 'WS',
    bio: 'Designs user-first security workflows and plans product strategy.',
  },
  {
    name: 'Chen Tai',
    role: 'Encryption Engineer',
    icon: LockKeyhole,
    initials: 'CT',
    bio: 'Builds encryption modules and ensures secure key management.',
  },
  {
    name: 'Li Junyan',
    role: 'Frontend Developer',
    icon: Code,
    initials: 'LJ',
    bio: 'Develops responsive interfaces and interaction experiences.',
  },
  {
    name: 'Jason Huang',
    role: 'Backend Engineer',
    icon: Server,
    initials: 'JH',
    bio: 'Maintains APIs, file pipelines, and system reliability.',
  },
]

const TITLE_END = 0.3
const CAROUSEL_IN = 0.14
const CAROUSEL_READY = 0.38
const SPACING = 90
const ENTRY_ANGLE = 0
const EXIT_ANGLE = 180
const CLOCK_4 = 30
const SNAP_COMMIT = 0.72
const SNAP_IDLE_MS = 130

const trackRef = ref<HTMLElement | null>(null)
const progress = ref(0)
const viewportW = ref(1280)
let frame = 0
let snapTimer = 0
let unlockTimer = 0
let snapping = false
let lockedCard = -1
let reduceMotion = false

function clamp(value: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value))
}

function updateProgress() {
  const track = trackRef.value
  if (!track) return
  const total = track.offsetHeight - window.innerHeight
  if (total <= 0) {
    progress.value = 0
    return
  }
  progress.value = clamp(-track.getBoundingClientRect().top / total)
}

function onFrame() {
  frame = 0
  updateProgress()
}

function requestFrame() {
  if (frame) return
  frame = window.requestAnimationFrame(onFrame)
}

function onResize() {
  viewportW.value = window.innerWidth
  requestFrame()
}

const titleLeave = computed(() => clamp(progress.value / TITLE_END))
const titleStyle = computed((): CSSProperties => {
  const t = titleLeave.value
  return {
    opacity: String(1 - t),
    transform: `translate3d(0, ${-t * 56}px, ${-t * 480}px) scale(${1 - t * 0.28})`,
    filter: `blur(${t * 8}px)`,
    pointerEvents: t > 0.85 ? 'none' : 'auto',
  }
})

const carouselEnter = computed(() =>
  clamp((progress.value - CAROUSEL_IN) / (CAROUSEL_READY - CAROUSEL_IN)),
)

const spinMax = SPACING * members.length + 80

function trackMetrics() {
  const track = trackRef.value
  if (!track) return null
  const total = track.offsetHeight - window.innerHeight
  if (total <= 0) return null
  return { track, total }
}

function spinToProgress(spin: number) {
  return CAROUSEL_READY + (spin / spinMax) * (1 - CAROUSEL_READY)
}

function cardFrontProgress(index: number) {
  return spinToProgress(index * SPACING + 90)
}

function scrollToProgress(p: number) {
  const metrics = trackMetrics()
  if (!metrics) return
  const top = metrics.track.offsetTop + metrics.total * clamp(p)
  if (Math.abs(window.scrollY - top) < 6) return
  snapping = true
  window.clearTimeout(snapTimer)
  window.clearTimeout(unlockTimer)
  window.scrollTo({ top, behavior: 'smooth' })
}

function settleSnap() {
  if (reduceMotion || snapping) return

  const p = progress.value
  const firstCard = cardFrontProgress(0)
  const lastCard = cardFrontProgress(members.length - 1)
  const raw = (carouselSpin.value - 90) / SPACING

  if (p < firstCard) {
    lockedCard = -1
    return
  }

  if (p > lastCard) {
    const leave = (p - lastCard) / Math.max(0.001, 1 - lastCard)
    if (leave >= SNAP_COMMIT) {
      lockedCard = members.length
      return
    }
    lockedCard = members.length - 1
    scrollToProgress(lastCard)
    return
  }

  if (lockedCard < 0 || lockedCard >= members.length) {
    lockedCard = Math.round(clamp(raw, 0, members.length - 1))
  }

  const delta = raw - lockedCard
  if (delta >= SNAP_COMMIT && lockedCard < members.length - 1) lockedCard += 1
  else if (delta <= -SNAP_COMMIT && lockedCard > 0) lockedCard -= 1
  else if (delta <= -SNAP_COMMIT && lockedCard === 0) {
    lockedCard = -1
    return
  }

  scrollToProgress(cardFrontProgress(lockedCard))
}

function scheduleSnap() {
  if (snapping || reduceMotion) return
  window.clearTimeout(snapTimer)
  snapTimer = window.setTimeout(settleSnap, SNAP_IDLE_MS)
}

const carouselSpin = computed(() => {
  const t = clamp((progress.value - CAROUSEL_READY) / (1 - CAROUSEL_READY))
  return t * spinMax
})

const carouselStageStyle = computed((): CSSProperties => {
  const t = carouselEnter.value
  return {
    opacity: String(t),
    transform: `translate3d(0, ${(1 - t) * 48}px, ${(1 - t) * 280}px) scale(${0.84 + t * 0.16})`,
    pointerEvents: t > 0.4 ? 'auto' : 'none',
  }
})

const radius = computed(() => {
  if (viewportW.value < 640) return 220
  if (viewportW.value < 1024) return 380
  return 560
})

const clock4 = {
  x: Math.cos((CLOCK_4 * Math.PI) / 180),
  y: Math.sin((CLOCK_4 * Math.PI) / 180),
}

function cardTheta(index: number) {
  return ENTRY_ANGLE - index * SPACING + carouselSpin.value
}

const activeIndex = computed(() => {
  let best = 0
  let bestDist = Number.POSITIVE_INFINITY
  members.forEach((_, index) => {
    const dist = Math.abs(cardTheta(index) - 90)
    if (dist < bestDist) {
      bestDist = dist
      best = index
    }
  })
  return best
})

function cardStyle(index: number): CSSProperties {
  const theta = cardTheta(index)
  const R = radius.value
  const overshootScale = R * 2.2

  let x = 0
  let y = 0
  let z = 0

  if (theta >= ENTRY_ANGLE && theta <= EXIT_ANGLE) {
    const rad = (theta * Math.PI) / 180
    const arc = Math.cos(rad) * R
    x = arc * clock4.x
    y = arc * clock4.y
    z = Math.sin(rad) * R
  } else if (theta < ENTRY_ANGLE) {
    const overshoot = ((ENTRY_ANGLE - theta) / 90) * overshootScale
    x = clock4.x * (R + overshoot)
    y = clock4.y * (R + overshoot)
    z = -overshoot * 0.2
  } else {
    const overshoot = ((theta - EXIT_ANGLE) / 90) * overshootScale
    x = -clock4.x * (R + overshoot)
    y = -clock4.y * (R + overshoot)
    z = -overshoot * 0.2
  }

  const depth = clamp((z + R) / (2 * R))
  const scale = 0.68 + depth * 0.42
  let opacity = 0
  if (theta >= -8 && theta <= 188) {
    const edge = theta < 18 ? clamp((theta + 8) / 26) : theta > 162 ? clamp((188 - theta) / 26) : 1
    opacity = (0.4 + depth * 0.6) * edge
  }

  const tiltY = (-x / R) * 24
  const tiltX = (y / R) * 14

  return {
    transform: `translate3d(${x}px, ${y}px, ${z}px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale(${scale})`,
    opacity: String(opacity),
    zIndex: Math.round(depth * 100),
    filter: `blur(${(1 - depth) * 1.1}px)`,
    pointerEvents: opacity > 0.2 ? 'auto' : 'none',
  }
}

function goToMember(index: number) {
  lockedCard = index
  scrollToProgress(cardFrontProgress(index))
}

function onScroll() {
  requestFrame()
  if (snapping) {
    window.clearTimeout(unlockTimer)
    unlockTimer = window.setTimeout(() => {
      snapping = false
    }, 180)
    return
  }
  scheduleSnap()
}

function onWheel() {
  if (!snapping) scheduleSnap()
}

onMounted(() => {
  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  viewportW.value = window.innerWidth
  updateProgress()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('wheel', onWheel, { passive: true })
  window.addEventListener('touchend', scheduleSnap, { passive: true })
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('touchend', scheduleSnap)
  window.removeEventListener('resize', onResize)
  window.clearTimeout(snapTimer)
  window.clearTimeout(unlockTimer)
  if (frame) window.cancelAnimationFrame(frame)
})
</script>

<template>
  <section ref="trackRef" class="team-scroll-track relative">
    <div class="team-scene sticky top-0 h-svh overflow-hidden">
      <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,color-mix(in_oklab,var(--primary)_16%,transparent),transparent_58%)]" />

      <div class="team-perspective relative mx-auto flex h-full items-center justify-center">
        <div class="team-title absolute inset-0 z-20 flex flex-col items-center justify-center text-center px-4" :style="titleStyle">
          <p class="mb-5 text-xs font-semibold uppercase tracking-[0.35em] text-primary">SecureView</p>
          <h1 class="max-w-5xl text-5xl font-bold leading-[0.92] tracking-tight text-foreground sm:text-7xl md:text-8xl lg:text-[7.5rem]">
            Development
            <span class="block text-primary">Team</span>
          </h1>
          <p class="mt-8 max-w-2xl text-base text-muted-foreground md:text-xl">
            Four people. One encrypted collaboration platform.
          </p>
          <div class="mt-12 flex flex-col items-center gap-2 text-muted-foreground" :style="{ opacity: String(1 - titleLeave * 2) }">
            <span class="text-xs uppercase tracking-[0.28em]">Scroll to meet us</span>
            <ChevronDown class="h-5 w-5 animate-bounce" />
          </div>
        </div>

        <div class="team-carousel relative z-10 h-full w-full" :style="carouselStageStyle">
          <div class="pointer-events-none absolute left-0 right-0 top-32 z-20 text-center md:top-36">
            <p class="mb-2 text-xs font-semibold uppercase tracking-[0.32em] text-primary">The crew</p>
            <h2 class="text-3xl font-bold text-foreground md:text-5xl">Meet the team</h2>
          </div>

          <div class="team-ring absolute inset-0">
            <article
              v-for="(member, index) in members"
              :key="member.name"
              class="team-card absolute left-1/2 top-1/2"
              :class="{ 'team-card-active': activeIndex === index }"
              :style="cardStyle(index)"
            >
              <div class="flex h-full items-stretch gap-6 md:gap-8">
                <div class="flex shrink-0 flex-col items-start justify-between">
                  <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-xl font-bold text-primary md:h-20 md:w-20 md:text-2xl">
                    {{ member.initials }}
                  </div>
                  <div class="rounded-xl bg-primary/10 p-2.5">
                    <component :is="member.icon" class="h-5 w-5 text-primary md:h-6 md:w-6" />
                  </div>
                </div>
                <div class="flex min-w-0 flex-1 flex-col justify-center">
                  <h3 class="text-2xl font-semibold tracking-tight text-foreground md:text-4xl">{{ member.name }}</h3>
                  <p class="mt-2 text-sm font-medium text-primary md:text-lg">{{ member.role }}</p>
                  <p class="mt-4 text-sm leading-relaxed text-muted-foreground md:text-lg">{{ member.bio }}</p>
                </div>
              </div>
            </article>
          </div>

          <div class="absolute bottom-8 left-0 right-0 z-20 flex flex-col items-center">
            <div class="flex items-center gap-3">
              <button
                v-for="(member, index) in members"
                :key="`${member.name}-dot`"
                class="h-2.5 rounded-full transition-all"
                :class="activeIndex === index ? 'w-8 bg-primary' : 'w-2.5 bg-border hover:bg-muted-foreground/40'"
                :aria-label="`Show ${member.name}`"
                @click="goToMember(index)"
              />
            </div>
            <p class="mt-4 text-sm text-muted-foreground">{{ members[activeIndex].name }} · {{ members[activeIndex].role }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.team-scroll-track {
  height: 560vh;
}

.team-perspective {
  perspective: 1600px;
  perspective-origin: 50% 48%;
  transform-style: preserve-3d;
}

.team-title,
.team-carousel,
.team-ring,
.team-card {
  transform-style: preserve-3d;
  will-change: transform, opacity;
}

.team-card {
  width: min(92vw, 30rem);
  height: 20rem;
  margin-left: calc(min(92vw, 30rem) / -2);
  margin-top: -10rem;
  padding: 1.75rem 2rem;
  border: 1px solid var(--border);
  border-radius: 1.75rem;
  background: color-mix(in oklab, var(--card) 92%, transparent);
  backdrop-filter: blur(16px);
  box-shadow: 0 24px 60px color-mix(in oklab, var(--foreground) 8%, transparent);
}

.team-card-active {
  border-color: color-mix(in oklab, var(--primary) 45%, var(--border));
}

@media (min-width: 1024px) {
  .team-card {
    width: 34rem;
    height: 22rem;
    margin-left: -17rem;
    margin-top: -11rem;
    padding: 2.25rem 2.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .team-scroll-track {
    height: auto;
  }

  .team-scene {
    position: relative;
    height: auto;
    overflow: visible;
  }

  .team-title,
  .team-carousel,
  .team-card {
    position: static !important;
    transform: none !important;
    opacity: 1 !important;
    filter: none !important;
    margin: 0 auto 1.5rem !important;
  }

  .team-ring {
    position: relative;
    display: grid;
    height: auto;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
    gap: 1.5rem;
    padding: 2rem 1rem 6rem;
  }

  .team-carousel {
    height: auto;
  }
}
</style>
