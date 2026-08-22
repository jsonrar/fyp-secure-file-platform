/**
 * The browser-side mirror of the server password policy.
 *
 * The server in `backend/app/core/security.py` remains the authority: it re-runs
 * every rule here and is the only thing that can reject a password for real. This
 * module exists so the form can name the exact rule that is failing while the user
 * is still typing, instead of trading a round trip for one flattened error string.
 *
 * Keep the two in step. The constants and the messages below are deliberately the
 * same wording the API returns, so a user never sees the rule described two ways.
 * One rule is intentionally not mirrored: the server's common-password deny-list
 * stays on the server, where it can grow into a real breached-password corpus
 * without shipping that corpus to every browser.
 */

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 128
export const PASSWORD_MIN_CHARACTER_CLASSES = 2

/**
 * The encryption passphrase is not a login password. It never reaches the server,
 * it wraps the account key, and losing or guessing it costs the user every file
 * they have encrypted, so it keeps the longer minimum the login password shed.
 */
export const PASSPHRASE_MIN_LENGTH = 15

export type PasswordCharacterClass = 'uppercase' | 'lowercase' | 'number' | 'symbol'

export const PASSWORD_CHARACTER_CLASS_LABELS: Record<PasswordCharacterClass, string> = {
  uppercase: 'uppercase letter',
  lowercase: 'lowercase letter',
  number: 'number',
  symbol: 'symbol',
}

export const PASSWORD_REQUIREMENT_HINT =
  `At least ${PASSWORD_MIN_LENGTH} characters, mixing at least ` +
  `${PASSWORD_MIN_CHARACTER_CLASSES} of: uppercase letters, lowercase letters, numbers, symbols. ` +
  'It must not contain your username or email.'

const UPPERCASE = /\p{Lu}|\p{Lt}/u
const LOWERCASE = /\p{Ll}/u
const NUMBER = /\p{Nd}|\p{Nl}|\p{No}/u

/**
 * Bucket one character the way `unicodedata.category` does on the server: cased
 * letters by case, any numeric character as a number, and everything else -
 * punctuation, symbols, spaces, and caseless scripts - as a symbol.
 */
function classOf(character: string): PasswordCharacterClass {
  if (UPPERCASE.test(character)) return 'uppercase'
  if (LOWERCASE.test(character)) return 'lowercase'
  if (NUMBER.test(character)) return 'number'
  return 'symbol'
}

export function passwordCharacterClasses(password: string): Set<PasswordCharacterClass> {
  const found = new Set<PasswordCharacterClass>()
  for (const character of password.normalize('NFC')) {
    found.add(classOf(character))
  }
  return found
}

/** Mirrors `_MIN_CONTEXT_FRAGMENT_LENGTH`: shorter fragments match honest passwords. */
const MIN_CONTEXT_FRAGMENT_LENGTH = 3

function accountDetailFragments(contextValues: readonly string[]): string[] {
  const fragments = new Set<string>()
  for (const value of contextValues) {
    const normalized = value.normalize('NFC').trim().toLowerCase()
    if (!normalized) continue
    fragments.add(normalized)
    if (normalized.includes('@')) {
      fragments.add(normalized.slice(0, normalized.indexOf('@')))
    }
  }
  return [...fragments].filter((fragment) => fragment.length >= MIN_CONTEXT_FRAGMENT_LENGTH)
}

export interface PasswordPolicyResult {
  /** True once every rule passes, i.e. the form may send this to the server. */
  readonly ok: boolean
  readonly isEmpty: boolean
  readonly length: number
  readonly satisfiedClasses: ReadonlySet<PasswordCharacterClass>
  readonly tooShort: boolean
  readonly tooLong: boolean
  readonly tooFewClasses: boolean
  readonly usesAccountDetails: boolean
  /** The single message to show under the field, or '' when the password passes. */
  readonly message: string
}

export function evaluatePassword(
  password: string,
  contextValues: readonly string[] = [],
): PasswordPolicyResult {
  const normalized = password.normalize('NFC')
  const length = [...normalized].length
  const satisfiedClasses = passwordCharacterClasses(normalized)
  const candidate = normalized.toLowerCase()

  const isEmpty = normalized.length === 0
  const tooShort = !isEmpty && length < PASSWORD_MIN_LENGTH
  const tooLong = length > PASSWORD_MAX_LENGTH
  const tooFewClasses = !isEmpty && satisfiedClasses.size < PASSWORD_MIN_CHARACTER_CLASSES
  const usesAccountDetails =
    !isEmpty &&
    accountDetailFragments(contextValues).some((fragment) => candidate.includes(fragment))

  let message = ''
  if (isEmpty) {
    message = 'Enter a password'
  } else if (tooShort) {
    message = `Use at least ${PASSWORD_MIN_LENGTH} characters (${length} so far).`
  } else if (tooLong) {
    message = `Use at most ${PASSWORD_MAX_LENGTH} characters (${length} so far).`
  } else if (usesAccountDetails) {
    message = 'Do not build your password out of your username or email address.'
  } else if (tooFewClasses) {
    message =
      `Mix at least ${PASSWORD_MIN_CHARACTER_CLASSES} of: uppercase letters, ` +
      'lowercase letters, numbers, symbols.'
  }

  return {
    ok: !isEmpty && !tooShort && !tooLong && !tooFewClasses && !usesAccountDetails,
    isEmpty,
    length,
    satisfiedClasses,
    tooShort,
    tooLong,
    tooFewClasses,
    usesAccountDetails,
    message,
  }
}
