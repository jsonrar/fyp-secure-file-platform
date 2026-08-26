import { fileApi } from '@/api/file_api'
import { unwrapData } from '@/api/types'

/**
 * Resolve file ids to their original filenames, from the browser.
 *
 * The audit response carries `file_id` and no filename, so the records page labelled every
 * group `File #<uuid>`. Resolving it client-side was the agreed call, so this does that --
 * but not naively one request per row.
 *
 * `GET /files` returns up to 100 summaries in a single call and covers essentially every
 * file a person has audit entries for, so that runs first and the per-file lookups are only
 * for what it missed. A user with eight files costs one request rather than eight.
 */
const LIST_PAGE_SIZE = 100

/** Enough to hide latency without opening fifty sockets at once for a stale page. */
const LOOKUP_CONCURRENCY = 4

/** Resolved names live as long as the page. Audit rows are re-read far more often than
 *  filenames change, and a filename cannot change at all: the AAD binds it. */
const cache = new Map<string, string>()

export function forgetFileNames(): void {
  cache.clear()
}

async function lookupOne(fileId: string): Promise<void> {
  try {
    const file = unwrapData(await fileApi.getFile(fileId))
    if (file?.original_filename) cache.set(fileId, file.original_filename)
  } catch {
    // A deleted file, or one whose access was revoked, has no name to offer any more. The
    // caller falls back to the id rather than dropping the record: what happened to a file
    // is worth showing even once the file is gone.
  }
}

async function drain(ids: string[]): Promise<void> {
  const queue = [...ids]
  const workers = Array.from({ length: Math.min(LOOKUP_CONCURRENCY, queue.length) }, async () => {
    for (let next = queue.shift(); next !== undefined; next = queue.shift()) {
      await lookupOne(next)
    }
  })
  await Promise.all(workers)
}

export async function resolveFileNames(fileIds: Iterable<string>): Promise<Map<string, string>> {
  const wanted = new Set<string>()
  for (const id of fileIds) {
    if (id && id !== 'unknown' && !cache.has(id)) wanted.add(id)
  }

  if (wanted.size > 0) {
    // The single list call first: one request usually answers all of them.
    try {
      const page = unwrapData(
        await fileApi.listFiles({ page: 1, page_size: LIST_PAGE_SIZE }),
      )
      for (const item of page?.items ?? []) {
        if (item?.file_id) cache.set(item.file_id, item.original_filename)
      }
    } catch {
      // Listing is an optimisation, not a requirement; fall through to per-file lookups.
    }

    await drain([...wanted].filter((id) => !cache.has(id)))
  }

  const resolved = new Map<string, string>()
  for (const id of fileIds) {
    const name = cache.get(id)
    if (name) resolved.set(id, name)
  }
  return resolved
}

/** What to show when the name could not be resolved. Short enough to read, still unique. */
export function fallbackFileLabel(fileId: string): string {
  if (!fileId || fileId === 'unknown') return 'Unknown file'
  return `File ${fileId.slice(0, 8)}`
}
