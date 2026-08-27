# Notion2API — CLI Launcher + Account Manager

OpenAI uyumlu API **Claude, GPT, Gemini, Grok, Kimi** modellerini tek portta sunar.

## 🚀 Quick Start

```bash
./n2a-cli   # interaktif menü açılır
```

## 📋 Komutlar

| Komut | Açıklama |
|-------|----------|
| `./n2a-cli` | Menü |
| `./n2a-cli start` | Server başlat |
| `./n2a-cli stop` | Server durdur |
| `./n2a-cli status` | Durum + hesaplar |
| `./n2a-cli accounts` | Hesapları listele |
| `./n2a-cli add <email>` | Hesap ekle (kod mail gelir) |
| `./n2a-cli add-verify <email> <kod>` | Kodu gir |
| `./n2a-cli remove <email>` | Hesap sil |

## 🔧 Kurulum

```bash
./n2a-cli start          # server başlat
./n2a-cli add mail@ornek.com  # hesap ekle
```

## 🧩 opencode.json

```json
{
  "providers": {
    "notion2api": {
      "baseUrl": "http://127.0.0.1:8787/v1",
      "models": {
        "claude-opus-4.7": { "model": "claude-sonnet-4.7", "tool_call": true, "reasoning": true },
        "claude-sonnet-4.6": { "model": "claude-sonnet-4.6", "tool_call": true },
        "gpt-5.4": { "model": "gpt-5.4", "tool_call": true, "vision": true },
        "gemini-3.1-pro": { "model": "gemini-3.1-pro", "tool_call": true, "vision": true }
      }
    }
  }
}
```

## 🗂 Dosya Yapısı

```
.
├── n2a-cli              # Ana CLI/TUI
├── bin/
│   ├── notion2api       # Go server (25 MB)
│   └── n2a-helper       # Go CLI (22 MB)
├── scripts/
│   └── n2a-account.py   # Python account helper
├── config/
│   └── n2a-config.json  # Konfigürasyon
├── README.md
├── Makefile
└── LICENSE
```

Made by Kaku Dev
