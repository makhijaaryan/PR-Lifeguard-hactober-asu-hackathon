# PR Lifeguard web app

The Next.js frontend for PR Lifeguard: the landing page (`app/page.tsx`) and the app with its Triage and Insights tabs (`app/app/page.tsx`).

It talks to the FastAPI server at `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` to use a different address. To run both together, use `./dev.sh` from the repo root. To run only the frontend:

```bash
npm install
npm run dev     # http://localhost:3000
npm run lint
npm run build
```

See the [main README](../README.md) and [CONTRIBUTING.md](../CONTRIBUTING.md) for the full setup.
