# Deploy the frontend

## Cloudflare Pages: drag and drop

1. Set your backend origin in `frontend/.env.local`:

   ```env
   VITE_API_BASE_URL=https://YOUR-SPACE.hf.space
   ```

2. Inside `frontend`, run `npm ci` once, then `npm run build`.
3. Drag the resulting **`dist` folder** onto Cloudflare Pages Direct Upload.

That is the complete upload workflow. `dist` includes the SPA redirects and all compiled assets. Do not upload the raw source folder or `node_modules`: Cloudflare drag-and-drop serves prebuilt files and does not run npm builds. Build again after changing the backend URL; setting variables in the Pages dashboard cannot change an existing local build.

For automatic builds from source, connect the Git repository to Pages: root `frontend`, Node `24`, command `npm run build`, output `dist`, and set the same `VITE_API_BASE_URL` in Pages build settings.

On Hugging Face set `CORS_ORIGINS` to the exact Pages origin. Keep provider keys only in Hugging Face Secrets. See [hosted setup](../docs/HOSTED_DEPLOYMENT.md), [local/Docker setup](../README.md), and [Cloudflare Direct Upload documentation](https://developers.cloudflare.com/pages/get-started/direct-upload/).
