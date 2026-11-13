# OziOS

CachyOS paketleri ve KDE Plasma 6 üstüne kurulu, oyun ve günlük kullanım için
Arch tabanlı bir masaüstü sistemi. Sıradan donanımda hızlı olmayı ve önce Arch
öğrenmek istemeyenler için kolay olmayı hedefliyor.

**Durum: erken geliştirme.** Canlı ISO sanal makinede OziOS çekirdeği ve
masaüstüyle açılıyor; paket kurucu `.deb`, AppImage ve Arch paketleri için
çalışıyor. Windows katmanı gerçek bir konukta henüz çalıştırılmadı ve gerçek
donanımda hiçbir şey denenmedi. Ayrıntılar: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

- **Plasma üstünde kendi masaüstü:** üst çubuk, yüzen dock, pencere kapatınca
  duran dönen tesseract duvar kâğıdı; terminal, açılış menüsü ve giriş
  ekranında aynı görünüm.
- **Kendini anlatan paket kurucu:** kurmadan önce paketi inceler,
  Debian/Ubuntu `.deb` paketlerini izole bir kutuda, AppImage dosyalarını bir
  kum havuzunda çalıştırır, AUR paketlerini atılabilir bir kapta derler, her
  izole uygulamaya tek tip izin verir.
- **Dosya yöneticisinden Windows programları** (devam ediyor): `.exe` ve `.msi`,
  kendi Windows ISO'nuzdan kurulan bir Windows konuğunda açılır. Windows
  dağıtılmaz.
- **Kendi çekirdeği:** CachyOS çekirdek tarifi `linux-ozios` adıyla derlenir
  ve bu depodan yayımlanır. İmajda ve kurulan sistemde CachyOS çekirdeği,
  programı ya da görseli yok.
- **Akıllı tahtalar için Eğitim sürümü:** tahta düzeni, ekran kalemi, beyaz
  tahta, Türkçe varsayılanlar. Ayrıntılar: [docs/EDUCATION.md](docs/EDUCATION.md).

Lisans: bu depodaki kod MIT. KDE, CachyOS ve diğer projelerden türeyen
dosyalar kendi lisanslarını korur.
