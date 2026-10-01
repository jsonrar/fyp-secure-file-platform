import { describe, expect, it } from 'vitest'

import { COMPARISON, STORY_SCENES } from './security-story'

describe('the explainer story', () => {
  it('runs in the order the animation draws it, each scene once', () => {
    expect(STORY_SCENES.map((s) => s.id)).toEqual([
      'pick', 'encrypt', 'wrap', 'upload', 'share', 'open', 'tamper',
    ])
  })

  it('gives every scene a title, an explanation and a reason it matters', () => {
    for (const scene of STORY_SCENES) {
      expect(scene.title.length).toBeGreaterThan(5)
      expect(scene.body.length).toBeGreaterThan(40)
      expect(scene.why.length).toBeGreaterThan(10)
    }
  })

  it('names the real mechanisms rather than vague promises', () => {
    const text = STORY_SCENES.map((s) => `${s.body} ${s.why}`).join(' ')
    for (const term of ['AES-256-GCM', 'RSA-OAEP', 'SHA-256', 'passphrase', 'backup', 'recovery key']) {
      expect(text).toContain(term)
    }
    // Sharing is account to account; there are no share links in the product.
    expect(STORY_SCENES.find((s) => s.id === 'share')!.why).toContain('no public link')
  })

  it('compares every row on both sides', () => {
    expect(COMPARISON.length).toBeGreaterThanOrEqual(4)
    for (const row of COMPARISON) {
      expect(row.ordinary && row.secureview && row.question.endsWith('?')).toBeTruthy()
    }
  })
})
