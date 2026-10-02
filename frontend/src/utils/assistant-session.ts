/**
 * What the Help assistant remembers: whether it is open and the last few questions.
 *
 * `sessionStorage` only, so it lasts while the tab is open and never outlives it, and is never
 * sent anywhere. Each question keeps the key of the answer it was shown, so a "did you mean"
 * choice comes back as the answer that was picked rather than whatever the words match first.
 */
const KEY = 'help_assistant'

/** Enough to keep the thread across a page change; a long log is noise in a small panel. */
export const MAX_REMEMBERED = 5

export interface RememberedQuestion {
  question: string
  /** The answer shown, or null when the reply was "not sure" or empty. */
  answerKey: string | null
}

export interface AssistantSession {
  open: boolean
  questions: RememberedQuestion[]
}

const EMPTY: AssistantSession = { open: false, questions: [] }

export function readAssistantSession(): AssistantSession {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return EMPTY
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return EMPTY
    const { open, questions } = parsed as Record<string, unknown>
    return {
      open: open === true,
      questions: Array.isArray(questions)
        ? questions
            .filter(
              (q): q is RememberedQuestion =>
                Boolean(q) &&
                typeof (q as RememberedQuestion).question === 'string' &&
                ((q as RememberedQuestion).answerKey === null || typeof (q as RememberedQuestion).answerKey === 'string'),
            )
            .slice(-MAX_REMEMBERED)
        : [],
    }
  } catch {
    // A private window, blocked storage, or something else in this key: start fresh.
    return EMPTY
  }
}

export function writeAssistantSession(session: AssistantSession): void {
  try {
    sessionStorage.setItem(
      KEY,
      JSON.stringify({ open: session.open, questions: session.questions.slice(-MAX_REMEMBERED) }),
    )
  } catch {
    // Storage unavailable: the assistant still works, it just forgets on reload.
  }
}
