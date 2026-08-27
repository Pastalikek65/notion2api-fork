# Notion2API Fork

A simplified, pre-compiled fork of [GALIAIS/Notion2API](https://github.com/GALIAIS/Notion2API) with a Python CLI for account management.

## Quick Start

```bash
# 1. Start the server
./bin/notion2api --config config/config.json

# 2. Add accounts (in another terminal)
./scripts/n2a-account.py start you@gmail.com
# check your email for the 6-digit code
./scripts/n2a-account.py verify you@gmail.com 123456

# 3. Use as OpenAI-compatible API
curl http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me-openai-key" \
  -d '{"model":"claude-opus-4.7","messages":[{"role":"user","content":"hi"}]}'
```

See [README.md](README.md) for full documentation.
