# Help-page videos

Recorded from the real product, not mocked, by `frontend/scripts/record-walkthroughs.mjs`:

| File | What it shows |
| --- | --- |
| `how-it-works.mp4` | The animated explainer (`/how-it-works?present`), seven scenes at eight seconds each |
| `encrypt-upload.mp4` | Sign in, choose a file, pick the cipher, Start Encryption, the encrypted preview |
| `share-open.mp4` | Share with another account, then that account decrypts it with its own passphrase |

Each has a `.jpg` poster. The accounts are made up (`sam`, `alex`, `@example.com`) on a disposable
local stack; passwords and passphrases are masked by the page and were throwaway values.

To re-record after a UI change, start a local stack (API, MySQL, `npx vite`), seed two accounts with
`backend/scripts/seed_test_account.py`, put their credentials in a JSON file
`{ "sam": {username, password, passphrase}, "alex": {...} }`, then from `frontend/`:

```bash
node scripts/record-walkthroughs.mjs --base http://localhost:5173 --accounts accounts.json --out public/videos
```

`--only encrypt-upload,share-open` re-records just those. `share-open` expects the file that
`encrypt-upload` uploads. Needs ffmpeg on PATH. Check the result frame by frame before committing.
