<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
const props = withDefaults(defineProps<{ reverse?: boolean }>(), { reverse: false })
const lane = ref<HTMLElement | null>(null)
let frame = 0, previous = 0, resumeAt = 0, remainder = 0
const hovered = ref(false), focused = ref(false)
let dragging = false, startX = 0, startScroll = 0
function pause() { resumeAt = performance.now() + 3500 }
function down(event: PointerEvent) {
  pause()
  if (event.pointerType !== 'mouse' || event.button !== 0 || !lane.value) return
  dragging = true
  startX = event.clientX
  startScroll = lane.value.scrollLeft
  lane.value.setPointerCapture(event.pointerId)
}
function move(event: PointerEvent) {
  if (dragging && lane.value) lane.value.scrollLeft = startScroll + startX - event.clientX
}
function up() { dragging = false; pause() }
onMounted(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)')
  if (lane.value && !reduced.matches) lane.value.scrollLeft = lane.value.scrollWidth / 3
  function tick(now: number) {
    const el = lane.value
    const elapsed = Math.min(now - previous, 50)
    previous = now
    if (el && !reduced.matches && !hovered.value && !focused.value && !dragging && now > resumeAt) {
      const width = el.scrollWidth / 3
      remainder += elapsed * 0.025
      const step = Math.floor(remainder)
      remainder -= step
      el.scrollLeft += step * (props.reverse ? -1 : 1)
      if (el.scrollLeft < width / 2) el.scrollLeft += width
      if (el.scrollLeft > width * 1.5) el.scrollLeft -= width
    }
    frame = requestAnimationFrame(tick)
  }
  frame = requestAnimationFrame(tick)
})
onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>
<template>
  <div ref="lane" class="feature-lane" tabindex="0" role="region" aria-label="Core Features"
    @mouseenter="hovered = true" @mouseleave="hovered = false" @focusin="focused = true" @focusout="focused = false"
    @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up" @lostpointercapture="up" @wheel.passive="pause" @keydown="pause">
    <slot />
  </div>
</template>
<style scoped>
.feature-lane {
  overflow-x: auto;
  padding-block: 1.25rem;
  cursor: grab;
  scrollbar-width: none;
  touch-action: pan-x pan-y;
}
.feature-lane::-webkit-scrollbar { display: none; }
.feature-lane:active { cursor: grabbing; }
.feature-lane:focus-visible { outline: 2px solid var(--primary); outline-offset: 4px; border-radius: 1rem; }
</style>
