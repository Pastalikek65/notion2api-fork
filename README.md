# Notion2API — Multi-Account AI Proxy + TUI

OpenAI uyumlu API ile **Claude, GPT, Gemini** modellerini Notion AI üzerinden tek portta sunar.
Çoklu hesap yönetimi, Textual TUI, admin dashboard.

## 🚀 Quick Start

```bash
./n2a-cli           # Textual TUI (önerilen)
./n2a-cli --menu    # fallback Rich menü
```

## 📋 TUI Kullanımı

Klavye kısayolları: `D` Dashboard, `A` Accounts, `S` Server, `M` Models, `R` Refresh, `Q` Quit

| Ekran | İçerik |
|-------|--------|
| **Dashboard** | Server durumu, aktif hesap, account özeti, hızlı aksiyonlar |
| **Accounts** | Hesap listesi, ekle/çıkar/aktifleştir/test et |
| **Server** | Start/stop/restart, healthz detayı |
| **Models** | Tüm modeller listesi, test |

## 📋 CLI Komutları

| Komut | Açıklama |
|-------|----------|
| `./n2a-cli` | Textual TUI |
| `./n2a-cli start` | Server başlat |
| `./n2a-cli stop` | Server durdur |
| `./n2a-cli status` | Durum + hesaplar |
| `./n2a-cli accounts` | Hesapları listele |
| `./n2a-cli add <email>` | Hesap ekle (kod mail gelir) |
| `./n2a-cli add-verify <email> <kod>` | Kodu gir |
| `./n2a-cli remove <email>` | Hesap sil |

## 🔧 Hesap Ekleme (TUI ile)

1. `./n2a-cli` ile TUI'yi aç
2. `A` ile Accounts tab'a geç
3. Email gir → **Add** → kodu bekle → gir → aktif
4. Veya Dashboard'da **➕ Add Account** butonu

## 🗂 Dosya Yapısı

```
.
├── n2a-cli              # Ana CLI (TUI'yi açar)
├── tui.py               # Textual TUI (Python)
├── .venv/               # Python venv (textual, requests)
├── bin/
│   ├── notion2api       # Go server (17 MB)
│   └── n2a-helper       # Go helper
├── config/
│   └── n2a-config.json  # Konfigürasyon
├── probe_files/         # Session cookie'leri
├── Makefile
└── README.md
```

## 📡 API

```
POST /v1/chat/completions  — OpenAI uyumlu
GET  /v1/models            — model listesi
GET  /healthz              — server durumu
```

## ⚠️ Notion Free Plan

Notion AI ücretsiz planda **75 kullanım/ay** (hesap başına). Kota dolunca `premium-feature-unavailable`.
Yeni bir hesap ekleyerek devam edebilirsiniz (`./n2a-cli` ile TUI → Accounts → Add).

Made by Kaku Dev