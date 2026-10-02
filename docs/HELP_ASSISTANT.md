# Help assistant

The round button at the bottom right of every page opens the **Help assistant** (Issue #146).
It answers "how do I…", "how does it work…" and "why not Google Drive / WhatsApp / email…"
with a short summary, numbered steps for a how-to, and links into the product.

It is called the Help assistant everywhere, never an agent or AI: the security agent
(Admin → Security agent) is the project's agent, and the names keep the two apart.

## How it answers

There is no language model and no network call. Everything runs in the visitor's browser:

1. The question is normalised: lowercased, punctuation stripped, a light stemmer
   (share/shared/sharing meet), synonyms folded together (send → share, lost → forgot,
   e2e → end-to-end), and a word the content never uses is corrected to the nearest one it
   does (one typo, two in a long word).
2. It is scored with BM25 against every answer the assistant knows. A word pair that also
   appears in one of an intent's sample questions adds a little, and asking one of those
   questions word for word adds more.
3. The best answer is shown with the next two as "Was this not it?". If the best score is
   low, or the answer shares less than half of the question's weight, the reply is
   "I'm not sure" with the closest three and links to Help and Contact us.

The answers come from, in this order of preference:

| Source | File | Linked to |
| --- | --- | --- |
| Curated intents | `frontend/src/data/assistant/intents.ts` | their own links |
| Knowledge articles | `frontend/src/data/education/knowledge.ts` | `/education?article=<id>#article-<id>` |
| Algorithm pages | `frontend/src/data/education/algorithms.ts` | `/education?algorithm=<id>#algorithm-detail` |
| Explainer scenes and comparison | `frontend/src/data/security-story.ts` | `/how-it-works` |
| Picture guide steps | `frontend/src/data/workflow-guide.ts` | `/#how-it-works` |

The sources are read, not copied, so editing an Education article changes what the assistant
says. The matcher is `frontend/src/utils/assistant-search.ts`, a pure module with unit tests
beside it.

Questions are not stored on any server or logged. The panel remembers whether it was open and
the last five questions in `sessionStorage`, which ends with the tab.

## Adding an intent

Add an entry to `ASSISTANT_INTENTS` in `frontend/src/data/assistant/intents.ts`:

```ts
{
  id: 'export-files',              // unique, kebab-case
  group: 'using',                  // 'using' | 'how' | 'compare'
  title: 'Can I download all my files at once?',
  phrasings: [                     // at least three ways people actually ask it
    'can I download all my files at once',
    'export everything',
    'bulk download',
  ],
  keywords: ['export', 'bulk', 'all', 'everything', 'zip'],
  summary: 'Two to four sentences that answer the question on their own.',
  steps: ['Only when it is a how-to.', 'Name each control as the interface labels it.'],
  links: [{ label: 'My Files', to: '/files' }],   // one to three product links
},
```

Then run `cd frontend && npx vitest run src/utils/assistant-search.test.ts`. The tests fail if:

- any of the intent's phrasings (or its title) finds a different answer: add words to
  `keywords`, or reword a phrasing that is really a different question;
- a link is not a real route, anchor, article, algorithm or video;
- the summary is not two to four sentences, or there are no product links or more than three.

A word the questions use but the content does not can be taught in `SYNONYMS` in
`assistant-search.ts`. Add a realistic question for it to the "realistic questions" list in
the test, typos included.

### Comparisons

An intent in the `compare` group must cite every claim it makes about another product with a
`kind: 'source'` link to that product's own documentation, and the test only accepts sources on
the hosts it lists. Say what is different, never that SecureView is "more secure", and keep its
limits in the answer (a recipient keeps a copy they already downloaded).

## Deep links it relies on

- `/help?video=<id>#videos` opens the Help page on that video (`frontend/src/data/help-videos.ts`).
- `/education?article=<id>#article-<id>` opens the Knowledge Base on that article.
- `/education?algorithm=<id>#algorithm-detail` opens the Algorithm Explorer on that algorithm.

## Not in this version

A server-side rewording layer (for example Zhipu `glm-4-flash`, fed only the retrieved answer
text) is a separate decision, because it would send the visitor's question to a third party.
Answering questions about the visitor's own files or account is out of scope. When the language
switch (#74) lands, the intents become translatable strings too.
