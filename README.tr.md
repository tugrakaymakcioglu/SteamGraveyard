<div align="center">

<img src="docs/images/banner.png" alt="SteamGraveyard - Listeden Kaldırılan Steam Oyunlarını Keşfedin" width="100%" />

# ⚰️ SteamGraveyard (Türkçe)

### Satıştan Kaldırılan, Unutulmuş Steam Oyunlarını, Gizli Demo ve DLC'leri Keşfedin

[![CI](https://github.com/tugrakaymakcioglu/SteamGraveyard/actions/workflows/tests.yml/badge.svg)](https://github.com/tugrakaymakcioglu/SteamGraveyard/actions/workflows/tests.yml)
[![Sürüm 0.1.1](https://img.shields.io/badge/sürüm-0.1.1-66d9ef?style=flat-square)](CHANGELOG.md)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Lisans: MIT](https://img.shields.io/badge/Lisans-MIT-2ea44f.svg?style=flat-square)](LICENSE)
[![Textual TUI](https://img.shields.io/badge/Arayüz-Textual%20TUI-6f42c1?style=flat-square)](https://textual.textualize.io/)
[![SteamDB Entegre](https://img.shields.io/badge/Veri-SteamDB%20Entegre-00ADEE?style=flat-square)](https://steamdb.info/)
[![Windows 1-Tık](https://img.shields.io/badge/Windows-1--Tık%20Başlatıcı%20(.bat)-informational?style=flat-square)](#windows-için-en-kolay-yol)

[English README](README.md) &nbsp;·&nbsp; [Windows Kurulumu](#windows-için-en-kolay-yol) &nbsp;·&nbsp; [Kurulum](#kurulum) &nbsp;·&nbsp; [Hızlı Başlangıç](#hızlı-başlangıç) &nbsp;·&nbsp; [Klavye Kısayolları](#klavye-kısayolları)

</div>

---

Oyunlar mağazalardan kaybolabilir; ancak tarihleri onlarla birlikte kaybolmamalıdır.

SteamGraveyard, yerel bir SQLite veritabanını akıcı ve hızlı bir terminal arayüzüne (TUI) dönüştürür. Araştırmacılar, retro oyun tutkunları ve koleksiyoncular için satıştan kaldırılmış (delisted) Steam oyunlarını, demo paketlerini ve DLC'leri güvenle inceleme imkanı sunar.

> [!IMPORTANT]
> SteamGraveyard, Steam sahiplik, lisans, DRM veya ödeme sistemlerini **asla atlatmaz**. Yalnızca resmi Steam istemcisinin desteklediği `steam://` bağlantılarını açar.

---

## 📸 Ekran Görüntüleri & Tur

<p align="center">
  <img src="docs/images/quick-tour.gif" alt="SteamGraveyard Hızlı Tur" width="960">
</p>

---

## 🚀 Kurulum

### Windows İçin En Kolay Yol
1. [En son Windows ZIP paketini indirin](https://github.com/tugrakaymakcioglu/SteamGraveyard/releases/latest/download/SteamGraveyard-Windows.zip).
2. ZIP'i bir klasöre çıkartın.
3. `START_STEAM_GRAVEYARD.bat` dosyasına çift tıklayın.

### GitHub Üzerinden Kurulum
```bash
python -m pip install "git+https://github.com/tugrakaymakcioglu/SteamGraveyard.git@v0.1.1"
steam-graveyard
```

---

## ⚡ Hızlı Başlangıç

```bash
# Terminal arayüzünü açın
steam-graveyard

# TUI açmadan doğrudan arama yapın
steam-graveyard search "lawbreakers"

# Bilinen bir AppID'yi inceleyin
steam-graveyard game 350280

# Yerel veritabanını dışa aktarın (JSON / CSV / SQLite)
steam-graveyard export
```

### ⌨️ Klavye Kısayolları

| Tuş | Eylem |
| --- | --- |
| `↑` / `↓` | Oyunlar arasında gezin |
| `Ctrl+S` | Canlı aramayı aç |
| `Enter` | Seçili oyunu aç veya Steam'e resmi komut gönder |
| `C` | Doğrulanmış Steam URI adresini panoya kopyala |
| `D` | SteamDB sayfasını tarayıcıda aç |
| `S` | Resmi Steam Mağaza sayfasını aç |
| `Esc` | Arama veya detaydan ana kataloğa dön |
| `Q` | Çıkış |

---

## 📄 Lisans

MIT Lisansı. Detaylar için [LICENSE](LICENSE) dosyasına bakın.
