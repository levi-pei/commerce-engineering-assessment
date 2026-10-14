# Variant PDP Frontend

From `app/frontend`:

```bash
npm install
npm run dev
npm test
npm run build
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Variant resolution is pure domain logic in `src/variants.ts`; request handling is isolated in `src/api.ts`; `App.tsx` coordinates UI state.

The product images were generated with an AI image tool for this assessment and contain no customer or third-party data.
