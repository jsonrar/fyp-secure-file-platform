# Help-page videos

English | [简体中文](README.zh-CN.md)

Recorded from the real product, not mocked, by `frontend/scripts/record-walkthroughs.mjs`:

| File | What it shows |
| --- | --- |
| `how-it-works.mp4` | The animated explainer (`/how-it-works?present`), seven scenes at eight seconds each |
| `encrypt-upload.mp4` | Sign in, choose a file, pick the cipher, Start Encryption, the timed encryption steps and byte comparison, the encrypted preview |
| `share-open.mp4` | Share with another account after checking their key fingerprint, that account decrypts it with its own passphrase, then files it in a folder of its own |

Each has a `.jpg` poster. The accounts are made up (`sam`, `alex`, `@example.com`) on a disposable
local stack; passwords and passphrases are masked by the page and were throwaway values.
All three were re-recorded on 2026-10-05 after the "Sealed" redesign (sidebar, centred headers, two-column Settings, the new sign-in page). The captions are English; the videos have no sound. The caption, outline and sign-in helpers are shared with the
presentation's backup video in `frontend/scripts/lib/video.mjs`.

To re-record after a UI change, start a local stack (API, MySQL, `npx vite`), seed two accounts with
`backend/scripts/seed_test_account.py`, put their credentials in a JSON file
`{ "sam": {username, password, passphrase}, "alex": {...} }`, then from `frontend/`:

```bash
node scripts/record-walkthroughs.mjs --base http://localhost:5173 --accounts accounts.json --out public/videos
```

`--only encrypt-upload,share-open` re-records just those. `share-open` expects the file that
`encrypt-upload` uploads. Needs ffmpeg on PATH. Check the result frame by frame before committing.
