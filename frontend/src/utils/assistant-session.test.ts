import { beforeEach, describe, expect, it, vi } from 'vitest'

const store = new Map<string, string>()
let broken = false
vi.stubGlobal('sessionStorage', {
  getItem: (key: string) => {
    if (broken) throw new Error('SecurityError')
    return store.get(key) ?? null
  },
  setItem: (key: string, value: string) => {
    if (broken) throw new Error('QuotaExceededError')
    store.set(key, value)
  },
})

const { MAX_REMEMBERED, readAssistantSession, writeAssistantSession } = await import('./assistant-session')

beforeEach(() => {
  store.clear()
  broken = false
})

describe('the Help assistant session', () => {
  it('starts closed with nothing asked', () => {
    expect(readAssistantSession()).toEqual({ open: false, questions: [] })
  })

  it('remembers whether it was open and what was asked', () => {
    writeAssistantSession({ open: true, questions: [{ question: 'how do I share', answerKey: 'intent:share' }] })

    expect(readAssistantSession()).toEqual({
      open: true,
      questions: [{ question: 'how do I share', answerKey: 'intent:share' }],
    })
  })

  it('keeps only the last few questions', () => {
    const questions = Array.from({ length: MAX_REMEMBERED + 3 }, (_, i) => ({ question: `q${i}`, answerKey: null }))
    writeAssistantSession({ open: false, questions })

    const kept = readAssistantSession().questions
    expect(kept).toHaveLength(MAX_REMEMBERED)
    expect(kept[kept.length - 1]!.question).toBe(`q${MAX_REMEMBERED + 2}`)
  })

  it('ignores anything malformed in storage', () => {
    store.set('help_assistant', '{"open":"yes","questions":[1,{"question":2},{"question":"ok","answerKey":null}]}')
    expect(readAssistantSession()).toEqual({ open: false, questions: [{ question: 'ok', answerKey: null }] })

    store.set('help_assistant', 'not json')
    expect(readAssistantSession()).toEqual({ open: false, questions: [] })
  })

  it('works without storage at all', () => {
    broken = true
    expect(() => writeAssistantSession({ open: true, questions: [] })).not.toThrow()
    expect(readAssistantSession()).toEqual({ open: false, questions: [] })
  })
})
