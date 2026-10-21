# Deploying CraftX3D Studio

This guide takes you from your local project folder to a fully live site:
GitHub → Render (hosting) → Railway (database) → Cloudinary (images) →
Google login → Razorpay (payments).

Do the sections in order — each one needs the previous one done first.

---

## 1. Push the code to GitHub

1. Create a new **empty** repository on GitHub (no README, no .gitignore — you already have one).
2. In your project folder (the one with `manage.py` in it), run:

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

3. **Double-check `.env` is NOT in the repo.** Run `git status` before your first commit — if you see `.env` listed, add it to `.gitignore` first:

   ```
   .env
   db.sqlite3
   __pycache__/
   *.pyc
   staticfiles/
   media/
   ```

   Your API keys live in `.env` — if that file gets pushed to a public repo, anyone can use your Razorpay/Google/Cloudinary accounts. `.env.example` (no real values) is safe to commit; `.env` itself never is.

---

## 2. Set up the database — Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project → Provision PostgreSQL.**
3. Once it's created, click into the Postgres service → **Variables** tab → copy the value of `DATABASE_URL` (it looks like `postgresql://postgres:xxxx@xxxx.railway.app:5432/railway`).
4. Keep this tab open — you'll paste this into Render in step 4.

That's it — Railway just hosts the database itself; your Django app doesn't run on Railway.

---

## 3. Set up image storage — Cloudinary

Render's disk is wiped every time you redeploy, so uploaded product photos and customer customization photos need to live somewhere permanent.

1. Sign up at [cloudinary.com](https://cloudinary.com) (free tier is enough to start).
2. On your Cloudinary Dashboard home page, find **API Environment variable** — it looks like:
   ```
   CLOUDINARY_URL=cloudinary://123456789012345:AbCdEfGhIjKlMnOpQrStUvWxYz@your-cloud-name
   ```
3. Copy that whole line — you'll paste it into Render in step 4.

---

## 4. Deploy to Render

1. Go to [render.com](https://render.com) and sign in with GitHub.
2. **New → Web Service**, then pick the GitHub repo you pushed in step 1.
3. Fill in:
   - **Name:** anything, e.g. `craftix3d-studio`
   - **Region:** closest to your customers (e.g. Singapore for India)
   - **Branch:** `main`
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn craftix3d.wsgi:application`
   - **Instance Type:** Free is fine to start
4. Before clicking create, scroll to **Environment Variables** and add every one of these (values from the sections above / below):

   | Key | Value |
   |---|---|
   | `SECRET_KEY` | a long random string — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DEBUG` | `False` |
   | `USE_SQLITE` | `False` |
   | `DATABASE_URL` | the Railway Postgres URL from step 2 |
   | `CLOUDINARY_URL` | the Cloudinary URL from step 3 |
   | `RAZORPAY_KEY_ID` | from step 5 below |
   | `RAZORPAY_KEY_SECRET` | from step 5 below |
   | `GOOGLE_CLIENT_ID` | from step 6 below |
   | `GOOGLE_CLIENT_SECRET` | from step 6 below |
   | `STAFF_ADMIN_USERNAME` | e.g. `admin` — creates your manage-portal login automatically |
   | `STAFF_ADMIN_PASSWORD` | a strong password |

   You can add Razorpay/Google values later and redeploy — the site works without them, it'll just show "payment not configured" / hide the Google button until they're set.

5. Click **Create Web Service**. Render will build and deploy — watch the logs for errors. First deploy takes a few minutes.
6. Once live, your site is at `https://<your-app-name>.onrender.com`.
7. **Create your manage-portal staff login.** The free Render plan doesn't include shell access, so this is done automatically during every build using two environment variables:
   - Add `STAFF_ADMIN_USERNAME` (e.g. `admin`) and `STAFF_ADMIN_PASSWORD` (a strong password) to Render's Environment Variables, then redeploy.
   - `build.sh` runs `python manage.py create_staff_admin` on every deploy, which creates that login if it doesn't exist yet, or resets its password if it does. It's safe to leave these two variables set permanently.
   - Log in at `https://<your-app-name>.onrender.com/manage/login/` with those credentials.
   - To change the password later, just update `STAFF_ADMIN_PASSWORD` in Render and redeploy — it'll reset automatically.
   - This is a separate system from Django's own `/admin/` — if you also want that (and have a paid plan with shell access), use `python manage.py createsuperuser` from the Shell tab instead.

---

## 5. Set up Razorpay (online payments)

1. Sign up at [dashboard.razorpay.com](https://dashboard.razorpay.com).
2. Start in **Test Mode** (top-left toggle) — you can place test orders with fake cards before going live.
3. Go to **Settings → API Keys → Generate Test Key**. Copy the **Key ID** and **Key Secret**.
4. Add these to Render as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`, then redeploy (Render → Manual Deploy → Deploy latest commit, or it auto-redeploys when you save env vars).
5. Test a payment on your live site using [Razorpay's test cards](https://razorpay.com/docs/payments/payments/test-card-upi-details/) (e.g. card `4111 1111 1111 1111`, any future expiry, any CVV).
6. When ready for real payments: complete Razorpay's KYC/activation, switch to **Live Mode**, generate **Live** API keys, and replace the values in Render with the `rzp_live_...` keys.

---

## 6. Set up Google login

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create a new project (or use an existing one).
2. **APIs & Services → OAuth consent screen** — set it up as "External", fill in app name/support email, add your Render domain under authorized domains (`onrender.com` while testing, or your custom domain later).
3. **APIs & Services → Credentials → Create Credentials → OAuth Client ID.**
   - Application type: **Web application**
   - **Authorized redirect URIs**, add exactly:
     ```
     https://<your-app-name>.onrender.com/accounts/google/login/callback/
     ```
     (Use your actual Render URL — this must match exactly, including the trailing slash.)
4. Copy the **Client ID** and **Client Secret**.
5. Add these to Render as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, then redeploy.
6. Test: go to your site's login page and click **Continue with Google** — it should take you to Google's real consent screen now.

If you later add a custom domain, add a second redirect URI for that domain too (Google allows multiple).

---

## 7. Set up order confirmation emails (optional)

Customers automatically get an emailed order confirmation/invoice once payment is confirmed. This is optional — the site works fully without it, since customers can always view their invoice on the site (My Orders → view order). Skip this section if you don't need it yet.

**Important — uses Brevo's API, not SMTP.** Render's free tier blocks outbound SMTP traffic (ports 25/465/587) entirely, so a normal SMTP setup won't work unless you're on a paid Render instance. This project uses Brevo's HTTPS API instead, which works fine on the free tier since it's just a regular web request, not raw SMTP.

1. Sign up at [brevo.com](https://www.brevo.com) (free tier: 300 emails/day, permanently — plenty for most small stores).
2. In Brevo, go to **Settings (gear icon) → SMTP & API → API Keys tab** (not the SMTP tab).
3. Click **Generate a new API key**, name it, and copy the value shown — you won't be able to see it again after leaving the page.
4. **Verify your sender email** — Settings → Senders & IP → Senders → add and verify the email address you'll use in `DEFAULT_FROM_EMAIL` below (Brevo emails you a confirmation link). Emails won't send until this is done.
5. Add to Render:
   ```
   BREVO_API_KEY=<your API key from Brevo>
   DEFAULT_FROM_EMAIL=CraftX3D <supportcraftx3dstudio@gmail.com>
   ```
6. Save → Render redeploys automatically.
7. Test it: place a real (or test-mode) order and complete payment — the customer should receive a confirmation email within a few seconds. You can also manually resend any order's confirmation email anytime from **Manage Portal → Orders → [order] → ✉️ Resend Email** — if it fails, that page shows a diagnostic code explaining exactly why.

**What happens if you hit Brevo's free daily limit (300 emails):** that day's 301st+ email(s) simply won't send — nothing else breaks. The order itself is unaffected, and the customer can still view their invoice on the site. The counter resets at midnight. If you outgrow 300/day, Brevo's paid plans start affordably.

---

## 8. Custom domain (optional)

1. In Render → your service → **Settings → Custom Domain** → add your domain, follow Render's DNS instructions (usually a CNAME record).
2. Once it's live on your domain, add it to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` env vars on Render, e.g.:
   - `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
   - `CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`
3. Add the same domain's callback URL to Google Cloud Console (step 6.3).

---

## 9. Making changes after you're live

Every time you want to push an update:

```bash
git add .
git commit -m "describe your change"
git push
```

Render automatically redeploys on every push to `main` (if auto-deploy is on, which is the default).

---

## Troubleshooting

- **"DisallowedHost" error** → your domain isn't in `ALLOWED_HOSTS`. Add it in Render's env vars.
- **Images disappear after a redeploy** → `CLOUDINARY_URL` isn't set, so it's using Render's temporary disk. Set it and re-upload.
- **"CSRF verification failed" on checkout/login** → add your real domain to `CSRF_TRUSTED_ORIGINS`.
- **Google login redirects to an error page** → the redirect URI in Google Cloud Console doesn't exactly match your Render URL — check for `http` vs `https` and the trailing slash.
- **Payment page says "not configured"** → `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` aren't set or are wrong — check Render's env vars.
- **Order confirmation emails aren't sending** → without `BREVO_API_KEY` set, this is expected — the site just skips sending (no error, no broken orders). If you've set it and it's still not sending, use the **"✉️ Resend Email"** button on any order in Manage Portal → Orders — it shows the exact error. A `TimeoutError` specifically used to mean "using SMTP on Render's free tier" (SMTP ports are blocked there) — this project now uses Brevo's HTTPS API instead, which isn't affected by that block, so a timeout at this point more likely means a genuine network issue. A `401`/`403` error means your API key is wrong; check it's copied from Brevo's **API Keys** tab, not the SMTP tab (those are two different kinds of keys). Also confirm your sender email is verified in Brevo (Settings → Senders & IP → Senders).
- **Build fails with `Pillow` / `KeyError: '__version__'` or similar package build errors** → Render picked a Python version too new for the pinned package versions (this happened when Render defaulted to Python 3.14). The repo includes a `.python-version` file pinning Python 3.12.7 — make sure it's present at the project root (same level as `manage.py`) and committed to git. If Render still doesn't pick it up, set the environment variable `PYTHON_VERSION=3.12.7` directly in Render's dashboard and redeploy.
- **`ModuleNotFoundError: No module named 'shop3d'` (or any name other than `craftix3d`) at startup** → your Render **Start Command** points to the wrong Python module. This project's settings package is `craftix3d`, so the Start Command must be exactly:
  ```
  gunicorn craftix3d.wsgi:application --bind 0.0.0.0:$PORT --workers 2
  ```
  Fix it under Render → your service → **Settings → Start Command**. This field is typed manually in the dashboard and isn't read from the repo, so a typo here won't show up until you check. A `render.yaml` is included in the repo with the correct value — if you ever recreate the service via **New → Blueprint** instead of **New → Web Service**, Render will read the correct command from that file automatically instead of you typing it by hand.

