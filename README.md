# Notion2API — Free Multi-Account Claude/GPT/Gemini Proxy

Notion'un kendi AI abonelik hesaplarınızı kullanarak **OpenAI uyumlu** bir inference gateway çalıştırın. İstediğiniz kadar Notion hesabı ekleyin, `crax-gpt` benzeri bir sistem kurun — bedava.

Bu repo, **GALIAIS/Notion2API**'nin derlenmiş hâlini + sade bir Python wrapper içerir. Sunucu tarafı Go'da yazılmıştır; Python kısmı sadece hesap yönetimi içindir.

## Özellikler

- **OpenAI uyumlu API** — `/v1/chat/completions`, `/v1/models`, `/v1/responses`
- **Streaming** desteği (SSE)
- **Multi-account pool** — round-robin, fail-over, otomatik session refresh
- **Çoklu model** — Claude Opus 4.7/4.6, Sonnet 4.6, Haiku 4.5, GPT 5.2/5.4, Gemini 3.1 Pro/Flash, Grok 4.5/4.6, Kimi K3
- **WebUI** — `/admin` üzerinden hesap yönetimi
- **Persistent** — SQLite ile durum saklama, cookie'ler diskte
- **Reverse engineering** — Notion'un `/api/v3/getLoginOptions` + `sendTemporaryPassword` + `loginWithEmail` akışını kullanır

## Nasıl Çalışır

```
[Sen] --email--> [n2a-account start]
                     |
                     v
              [n2a-helper] --getLoginOptions--> [Notion]
                     |                            |
                     +--sendTemporaryPassword-----+
                                                     |
                                          [6 haneli kod mail gelir]
                                                     |
[Sen] --code---> [n2a-account verify]                |
                     |                                v
                     +--loginWithEmail + getSpacesInitial
                     |
                     v
              [probe.json (cookies + user_id + space_id)]
                     |
                     v
              [config/accounts dizisine eklenir]
                     |
                     v
              [notion2api server - her istek cookie ile]
```

## Kurulum

### Önkoşullar
- Go 1.25+ (sadece build için)
- Python 3.10+ (hesap yönetimi için, opsiyonel)
- 50 MB disk

### Derleme (kaynak kodu olmadan)

Önceden derlenmiş `bin/n2a-helper` ve `bin/notion2api` binary'leri repoda mevcut. Ekstra derleme gerekmez.

### Kaynak koduyla derleme

```bash
# Hem server hem helper binary'sini build et
make build
# veya:
cd path/to/GALIAIS/Notion2API
go build -o ../notion2api-fork/bin/notion2api ./cmd/notion2api
go build -o ../notion2api-fork/bin/n2a-helper ./cmd/n2a-helper
```

## Hızlı Başlangıç

### 1. Sunucuyu başlat

```bash
./bin/notion2api --config config/config.json
```

Çıktı:
```
[notion2api-go] listening on http://127.0.0.1:8787 default_model=auto
```

API base URL: `http://127.0.0.1:8787/v1`
API key: `config.json` içindeki `api_key` (varsayılan: `change-me-openai-key`)

### 2. Hesap ekle (10 hesap örneği)

```bash
# Her hesap icin:
./scripts/n2a-account.py start user1@gmail.com
# 6 haneli kodu mail'den al
./scripts/n2a-account.py verify user1@gmail.com 123456
# sonraki hesap
./scripts/n2a-account.py start user2@gmail.com
...
```

### 3. OpenAI SDK ile kullan

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8787/v1",
    api_key="change-me-openai-key",
)

resp = client.chat.completions.create(
    model="claude-opus-4.7",
    messages=[{"role": "user", "content": "Merhaba!"}],
)
print(resp.choices[0].message.content)
```

### 4. cURL ile

```bash
curl http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me-openai-key" \
  -d '{
    "model": "claude-opus-4.7",
    "messages": [{"role":"user","content":"Selam"}]
  }'
```

## Konfigürasyon

`config/config.json`:

```json
{
  "host": "127.0.0.1",
  "port": 8787,
  "api_key": "change-me-openai-key",
  "upstream_base_url": "https://www.notion.so",
  "proxy_mode": "off",
  "model_id": "auto",
  "active_account": "user1@gmail.com",
  "admin": {"enabled": true, "password": "admin"},
  "features": {
    "use_web_search": true,
    "ai_surface": "ai_module"
  },
  "session_refresh": {
    "enabled": true,
    "interval_sec": 900
  }
}
```

## Hesap Havuzu

- Tüm hesaplar otomatik round-robin ile kullanılır
- 429/503 hatalarında otomatik sonraki hesaba geçer
- 15 dakikada bir session refresh yapar (cookie'leri yeniler)
- 5 ardışık hata sonrası hesap "dead" olur, otomatik devre dışı kalır

## Modeller

Sistem tüm Notion modellerini destekler (güncel listeyi `/v1/models` ile öğrenin):

| ID | Notion Internal | Aile |
|---|---|---|
| `claude-opus-4.7` | `apricot-sorbet-medium` | anthropic |
| `claude-opus-4.6` | `avocado-froyo-medium` | anthropic |
| `claude-sonnet-4.6` | `almond-croissant-low` | anthropic |
| `claude-haiku-4.5` | `anthropic-haiku-4.5` | anthropic |
| `gpt-5.2` | `oatmeal-cookie` | openai |
| `gpt-5.4` | `oval-kumquat-medium` | openai |
| `gemini-3.1-pro` | `galette-medium-thinking` | gemini |
| `gemini-3-flash` | `gingerbread` | gemini |
| `grok-4.5` | (Notion internal) | xai |
| `kimi-k3` | (Notion internal) | moonshot |

`model: "auto"` → Notion'un default modeli.

## WebUI

`http://127.0.0.1:8787/admin`
- Login: config'deki `admin.password` (varsayılan: `admin`)
- Hesap ekleme/silme, aktif hesap seçme, real-time log

## Docker

```bash
docker compose up -d --build
```

`config/config.json` dosyasını volume olarak mount edin.

## opencode / Continue.dev / Cursor

`opencode.json`'a provider olarak ekle:

```json
{
  "provider": {
    "notion2api": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://127.0.0.1:8787/v1",
        "apiKey": "change-me-openai-key"
      },
      "models": {
        "claude-opus-4.7": { "name": "Claude Opus 4.7" },
        "gpt-5.4": { "name": "GPT-5.4" },
        "gemini-3.1-pro": { "name": "Gemini 3.1 Pro" }
      }
    }
  }
}
```

## Yasal Uyarı

Bu yazılım Notion'un iç API'sini reverse engineer eder ve kullanıcı hesaplarını programatik olarak kullanır. Notion'un hizmet şartlarına aykırı olabilir. Sorumluluk kullanıcıya aittir.

Kendi Notion hesaplarınızla test edin. Üretimde ticari kullanım için Notion'un resmi API'sini (api.notion.com) kullanın.

## Teşekkür

- [GALIAIS/Notion2API](https://github.com/GALIAIS/Notion2API) — Go çekirdek
- [crax-gpt](https://gpt.crax.lol) — ilham kaynağı

## Lisans

MIT
