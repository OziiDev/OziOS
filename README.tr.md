# OziOS

CachyOS paketleri ve KDE Plasma 6 üstüne kurulu, oyun ve günlük kullanım için
Arch tabanlı bir masaüstü sistemi. Sıradan donanımda hızlı olmayı ve önce Arch
öğrenmek istemeyenler için kolay olmayı hedefliyor.

**Durum: erken geliştirme.** Canlı ISO sanal makinede OziOS masaüstüyle
açılıyor. ISO'dan kurulum, Windows katmanı ve paket kurucu henüz bitmedi.
Ayrıntılar: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

- **Plasma üstünde kendi masaüstü:** üst çubuk, yüzen dock, pencere kapatınca
  duran dönen tesseract duvar kâğıdı; terminal, açılış menüsü ve giriş
  ekranında aynı görünüm.
- **Kendini anlatan paket kurucu** (devam ediyor): kurmadan önce paketi
  inceler, Debian/Ubuntu `.deb` paketlerini izole bir kutuda çalıştırır, her
  izole uygulamaya tek tip izin verir.
- **Dosya yöneticisinden Windows programları** (devam ediyor): `.exe` ve `.msi`,
  kendi Windows ISO'nuzdan kurulan bir Windows konuğunda açılır. Windows
  dağıtılmaz.
- **Kendi çekirdek adı** (devam ediyor): CachyOS çekirdek tarifi `linux-ozios`
  adıyla derlenir.

Lisans: bu depodaki kod MIT. KDE, CachyOS ve diğer projelerden türeyen
dosyalar kendi lisanslarını korur.
