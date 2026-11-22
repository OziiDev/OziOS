# OziOS 0.4 "Öz" planı: kendi masaüstümüz

İstek (22 Kasım 2026): Plasma'nın üstüne kurulan masaüstü her Plasma sürümünde bir yerden
bozuluyor (çerçeveler 6.8'de yeniden derlenmek zorunda kaldı, kapatma ekranı kabuğa taşındı,
efektler KWin'in betik API'sine bağlı). Masaüstü sıfırdan, OziOS'un kendi kodu olacak.
Uzun sürmesi kabul.

Geliştirme artık doğrudan OziOS kurulu bilgisayarda: VM yok. Bilgisayar: i5-5200U (4 iş
parçacığı), 12 GB, Intel HD 5500 (ekran buna bağlı) + GeForce 930M (Optimus), Plasma 6.8.3,
Qt 6.12, Rust 1.100, wlroots 0.20, quickshell 0.3.2 depoda.

## 1. Mimari

Üç parça, aralarında tek bir sözleşme (IPC):

```
 ┌───────────────────────────── oturum: "OziOS" (SDDM'de) ─────────────────────────────┐
 │                                                                                     │
 │  oziwm  (Rust, Smithay)            ozi-shell  (PyQt6 + QML)          uygulamalar    │
 │  ─ ekran, girdi, pencereler        ─ üç ada, dock, başlatıcı          Dolphin,       │
 │  ─ çerçeveler, gölge, bulanıklık   ─ kontrol merkezi, bildirimler     Firefox,       │
 │  ─ animasyonlar, döşeme            ─ kilit ekranı, kapatma ekranı     ozi-look ...   │
 │  ─ çalışma alanları, Alt+Tab       ─ duvar kâğıdı (tesseract)                        │
 │        ▲                                   ▲                                         │
 │        └──── $XDG_RUNTIME_DIR/oziwm.sock ──┘  (JSON satırları: komut + olay akışı)   │
 │                                                                                     │
 │  ozi / ozi-pkg (Python, var olan)  ─ ayarlar, temalar, paketler: değişmiyor          │
 └─────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Pencere yöneticisi `oziwm`: Rust + Smithay (öneri)

| Seçenek | Artı | Eksi |
|---|---|---|
| **Rust + Smithay** (öneri) | Bellek hatası derleyicide yakalanır: "buglu olmasın" isteğinin en büyük kısmı bu. Çizim tamamen bizde (kendi GLES gölgelendiricilerimiz): yuvarlak köşe, ışıltılı kenar, gölge, bulanıklık, yaylanan animasyonlar Hyprland gibi. niri aynı kütüphaneyle yazılmış, çalışan örnek olarak okunabilir. | İlk derleme ağır (bu bilgisayarda 5–10 dk), sonrakiler hızlı. Daha çok kod. |
| C + wlroots 0.20 (+ scenefx) | Donanım, XWayland, protokoller hazır; hızlı derlenir. | Sahne grafiği köşe/bulanıklık/animasyonda sınırlı (Hyprland bu yüzden wlroots'tan ayrıldı); C'de bellek hataları bizim. |

Seçim kullanıcıda; plan Smithay'e göre yazıldı. wlroots seçilirse aşamalar aynı kalır,
yalnız Aşama 3 (görünüm) daha zayıf olur.

Kurallar:
- `unsafe` yok (Smithay'in içi hariç). Panik olursa oturum SDDM'e döner, günlük
  `~/.local/state/oziwm/` altına yazılır, `ozi doctor` gösterir.
- Ayar dosyası yok: ayarlar `ozi look` / Görünüm uygulamasından, IPC ile anında gelir;
  diske `~/.config/ozios/wm.json` olarak `ozi` yazar.
- Çerçeveler sunucu tarafında (xdg-decoration). KDecoration eklentisi (`ozios-decoration`)
  ve "Plasma değişince yeniden derle" mekanizması bu oturumda gereksizleşir.
- XWayland: `xwayland-satellite` (depoda 0.8.3) ayrı süreç olarak; Steam, eski programlar.
- Yalnız Intel'de çizilir; NVIDIA oyunlar için `prime-run` ile kalır.

### 1.2 Kabuk `ozi-shell`: PyQt6 + QML + layer-shell-qt

İlk plan Quickshell'di. Yerine OziOS uygulamalarının zaten kullandığı yol seçildi:
PyQt6 + QML, her pencere layer-shell-qt ile bir katman yüzeyi. Yeni bağımlılık yok,
0.x bir API'ye bağlanılmıyor ve bütün mantık (uygulama listesi, arama, dock, ses,
pil, ağ, görünüm ayarları) Qt'siz düz Python'da (`python/ozipkg/shell.py`), yani
`unittest` ile her yerde denenebilir. Pencere listesi ve olaylar `oziwm.sock`'tan gelir.

Parçalar (`shell/qml/`): duvar kâğıdı (arka katman, dönen tesseract, iki renkli ışık),
üst çubuk (üç ada: Ozi + öndeki pencere, saat, ağ/ses/pil), dock (sabitlenenler +
çalışanlar, büyüyen simgeler), başlatıcı (Super'e tek basış, arama, güç), hızlı panel
(ses, ağ, pil ve görünüm: tema, ışıltı, köşe, hareket; kaydırıcı oynarken bütün
pencere çerçeveleri canlı değişir).

### 1.3 Kalanlar (yeniden yazılmayanlar)

Giriş ekranı SDDM (OziOS teması var; "OziOS" oturumu `session/ozios.desktop`),
dosya yöneticisi Dolphin, ayar arka uçları
NetworkManager / PipeWire / BlueZ / power-profiles-daemon, portal: xdg-desktop-portal-gtk
(dosya seçici) + kendi ekran görüntüsü/paylaşımı (Aşama 6). Plasma oturumu kurulu kalır:
OziOS oturumu kararlı olana kadar yedek.

## 2. Aşamalar

Her aşama kendi başına çalışan bir şeyle ve testlerle biter; bir sonrakine o zaman geçilir.

**Aşama 0 — Devir ve iskelet**
- Kod `~/Projeler/OziOS`, CachyOS.iso ve `.kernel-pkgs/` yanında (yapıldı, sha256 tuttu).
- `oziwm/` (cargo çalışma alanı), `shell/` (QML), `docs/IPC.md` (sözleşme).
- Deneme: `oziwm --nested` şimdiki masaüstünde pencere olarak açılır, içinde Konsole çalışır.
- Derleme ayarı: `CARGO_BUILD_JOBS=3`, `nice`; bağımlılıklar `opt-level=2`, bizim kod hızlı
  derlensin diye `1` (bilgisayar bir kez ısınıp kapanmıştı).

**Aşama 1 — Çekirdek (iç içe pencerede)**
- xdg-shell, klavye (Türkçe Q/F, xkb), fare, odak, taşıma/boyutlandırma, katman kabuğu,
  pano + birincil seçim, sürükle-bırak, imleç şekilleri, kesirli ölçek.
- Yüzen (stacking) pencereler, Meta tuş kısayolları, çıkış: Meta+Shift+Esc.

**Aşama 2 — Gerçek donanım**
- DRM/KMS + libseat + libinput; ekran tak/çıkar, VT değiştirme (Ctrl+Alt+F3 her zaman
  çalışır), uyku/uyanma, dokunmatik yüzey jestleri.
- `/usr/share/wayland-sessions/ozios.desktop` → SDDM'de "OziOS (deneme)". Çökerse SDDM'e döner.
- Kare saati: titreşimsiz (vsync), boşta sıfır kare (pil).

**Aşama 3 — Görünüm motoru** (en çok görünen kısım)
- Kendi çerçevelerimiz: yuvarlak köşe (içerik de), etkin pencerede iki renkli ışıltılı kenar,
  ortalı başlık, yuvarlak düğmeler; renkler temadan.
- Gölge, katmanların arkasında bulanıklık (dual kawase, yarı çözünürlükte).
- Animasyon motoru: yay (spring) eğrileri; açılış/kapanış, büyütme/döşeme akışı, dock'a
  küçültme, çalışma alanı kayması. `ozi effects off` hepsini kapatır.
- Hafif profil (yazılımsal çizim / zayıf GPU): bulanıklık kapalı, kısa animasyonlar.

**Aşama 4 — Pencere yönetimi**
- Dört çalışma alanı (Meta+1…4), döşeme (0.3'teki sarmal algoritma Rust'a taşınır,
  Meta+T/Meta+F, sürükleyince yer değişir), kenara yaslama, Alt+Tab canlı önizlemeli,
  tam ekran.
- XWayland (xwayland-satellite), oyunlar: işaretçi kilidi, göreli işaretçi, yırtılma izni.

**Aşama 5 — Kabuk** (Aşama 1'den itibaren paralel)
- Üç ada çubuk, dock (yaylanan simgeler, çalışan ışığı), başlatıcı (Meta), kontrol merkezi,
  bildirimler, ses/parlaklık göstergesi (OSD), tepsi, saat + MPRIS, kapatma ekranı,
  kilit ekranı (PAM), tesseract duvar kâğıdı. Görünüm ve tema aynı `ozi theme`'den.

**Aşama 6 — Sistem**
- Ekran görüntüsü ve ekran paylaşımı (ext-image-copy-capture + portal + PipeWire),
  polkit ajanı, boşta kararma/kilit/uyku (ext-idle-notify), gece ışığı (gamma),
  ekran ayarları (çözünürlük, ölçek, yerleşim; wlr-output-management), klavye/dokunmatik
  yüzey ayarları, pano geçmişi (data-control).

**Aşama 7 — Paket, varsayılan oturum, ISO**
- `ozios-desktop` paketi (oziwm + ozi-shell), `ozi doctor` denetimleri, Welcome güncellemesi.
- OziOS oturumu varsayılan; Plasma isteğe bağlı paket.
- ISO bu bilgisayarda derlenir (VM'siz `iso/remaster.sh`; `tools/build-iso-in-vm.sh`'in
  VM'e bağlı kısımları ayrılır). Calamares ile gerçek kurulum denemesi.

## 3. Nasıl denenecek (VM'siz)

- **Birim testleri**: döşeme, animasyon eğrileri, yerleşim, IPC ayrıştırma (`cargo test`).
- **Başsız (headless) testler**: oziwm ekransız başlar, test istemcileri pencere açar,
  durum IPC'den sorulur, kareler PNG olarak karşılaştırılır. CI'da da çalışır.
- **İç içe**: Plasma oturumunun içinde pencere olarak, her gün.
- **Gerçek oturum**: SDDM'den "OziOS (deneme)". Kilitlenirse Ctrl+Alt+F3 → `pkill oziwm`.
- Var olan 588 Python/QML testi korunur; Plasma'ya bağlı olanlar Plasma oturumuna aittir.

## 4. Riskler

| Risk | Önlem |
|---|---|
| Ekran kilitlenir, kullanıcı masaüstsüz kalır | Plasma oturumu yerinde; OziOS oturumu "deneme" adıyla, varsayılan değil; TTY her zaman açık. |
| Optimus / iki GPU karmaşası | Yalnız Intel'de çizim; NVIDIA'ya dokunulmaz. |
| Qt veya layer-shell-qt değişir | Kabuk yalnız Qt Quick ve layer-shell-qt QML modülünü kullanır; mantık Qt dışında. |
| Derleme bilgisayarı ısıtır | 3 iş, `nice`; uzun derlemeler arka planda. |
| İş çok büyük | Aşamalar kendi başına kullanılabilir; Aşama 5 (kabuk) KWin'de de çalıştığından tek başına bile kazanç. |
