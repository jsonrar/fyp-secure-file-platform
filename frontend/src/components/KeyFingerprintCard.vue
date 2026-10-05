<script setup lang="ts">
import { KeyRound } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { keyApi } from '@/api/key_api'
import { formatFingerprint } from '@/crypto/fingerprint'
import { publicKeyFingerprint } from '@/crypto/primitives'

const { t } = useI18n()
const fingerprint = ref('')
const failed = ref(false)

// Computed here from the public key itself, the same way a sender's share dialog computes it,
// so the two can be compared without trusting the server's copy of the number.
onMounted(async () => {
  try {
    const pem = (await keyApi.myBundle()).data.data.key.public_key_pem
    fingerprint.value = formatFingerprint(await publicKeyFingerprint(pem))
  } catch {
    failed.value = true
  }
})
</script>

<template>
  <div class="rounded-xl border border-border bg-card p-6" data-testid="own-key-fingerprint">
    <h2 class="flex items-center gap-2 text-lg font-semibold text-foreground">
      <KeyRound class="h-5 w-5 text-primary" />
      {{ t('settings.fingerprintTitle') }}
    </h2>
    <p class="mt-2 reading-measure text-sm text-muted-foreground">{{ t('settings.fingerprintBody') }}</p>
    <p v-if="fingerprint" translate="no" class="mt-4 font-mono text-lg tracking-wide text-foreground">{{ fingerprint }}</p>
    <p v-else-if="failed" class="mt-4 text-sm text-destructive">{{ t('settings.fingerprintError') }}</p>
    <p v-else class="mt-4 text-sm text-muted-foreground">{{ t('settings.fingerprintLoading') }}</p>
  </div>
</template>
