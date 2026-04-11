# code.friend — AI Code Transpiler

AI-powered code transpiler. Convert between 21 languages. Powered by Claude.

---

## 🗂 Project Structure

```
codefriend-backend/    ← Python FastAPI server (has your API key)
  main.py
  requirements.txt
  Procfile
  railway.toml
  render.yaml
  .env.example
  .gitignore

codefriend-frontend/   ← Static HTML (deploy anywhere)
  index.html
```

---

## STEP 1 — Get Your Anthropic API Key (5 min)

1. Go to **https://console.anthropic.com**
2. Sign up / log in
3. Click **"API Keys"** in the left sidebar
4. Click **"Create Key"** → name it anything → click **"Add"**
5. **COPY THE KEY IMMEDIATELY** — it starts with `sk-ant-api03-...`
   Anthropic only shows it once. Paste it somewhere safe.
6. Go to **"Billing"** → add at least **$5** (required for the API to work)

---

## STEP 2 — Deploy the Backend on Render (free)

### Option A: Render (recommended, free tier)

1. Create account at **https://render.com**
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Push the `codefriend-backend/` folder to a GitHub repo
5. Render will auto-detect Python → set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Under **"Environment Variables"** add:
   - Key: `ANTHROPIC_API_KEY`
   - Value: `sk-ant-api03-YOUR_KEY_HERE`
7. Click **Deploy** — you'll get a URL like `https://codefriend-api.onrender.com`

### Option B: Railway (also free)

1. Go to **https://railway.app**
2. New Project → Deploy from GitHub repo
3. Add environment variable: `ANTHROPIC_API_KEY` = your key
4. Railway auto-detects everything via `railway.toml`
5. You'll get a URL like `https://codefriend-api.up.railway.app`

---

## STEP 3 — Deploy the Frontend

The frontend is a single HTML file. Deploy it anywhere:

### Netlify (easiest — drag & drop)
1. Go to **https://netlify.com/drop**
2. Drag `index.html` onto the page
3. Done — you get a live URL instantly

### GitHub Pages
1. Push `index.html` to a GitHub repo
2. Settings → Pages → Deploy from branch → main
3. Your app is live at `https://yourusername.github.io/reponame`

### Vercel
```bash
npx vercel --static index.html
```

---

## STEP 4 — Connect Frontend to Backend

1. Open your deployed frontend URL
2. In the top header, paste your backend URL:
   `https://codefriend-api.onrender.com`
3. Click **"ping"** — it should show **"connected"** ✓
4. Start transpiling!

The URL is saved in your browser automatically.

---

## Features

- ⟳ **Transpile** — convert code between 21 languages
- 💡 **Explain** — AI explains what your code does
- 🔍 **Review** — AI reviews your code for bugs & issues
- 📟 **Terminal** — simulates execution output
- 💬 **Chat** — floating AI coding assistant
- 📋 **History** — last 60 transpilations saved locally
- ⌨️ **Shortcuts** — Ctrl+Enter to transpile, Ctrl+D to clear

## Supported Languages

Python, JavaScript, TypeScript, Java, C++, C, Go, Rust, Ruby,
PHP, Swift, Kotlin, C#, Bash, R, Lua, Dart, Scala, Haskell, Elixir, SQL

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/transpile` | Transpile code |
| POST | `/explain` | Explain code |
| POST | `/review` | Code review |
| POST | `/simulate` | Simulate execution |
| POST | `/chat` | Chat with AI |

---

## Cost

Claude Sonnet 4 pricing (approximate):
- ~$3 per million input tokens
- ~$15 per million output tokens
- A typical transpile = ~500–1500 tokens total
- **$5 credit ≈ thousands of transpilations**

---

## Security Notes

- Your API key lives ONLY on the backend server as an env variable
- Users of your app never see or need the API key
- Set `ALLOWED_ORIGINS` env var to your frontend domain in production:
  `ALLOWED_ORIGINS=https://yourapp.netlify.app`
