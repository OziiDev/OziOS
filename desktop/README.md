# OziOS kabuğu (masaüstü)

Hedef: canlı hissettiren, akıcı animasyonlu ama zayıf donanımda da hafif bir masaüstü;
KDE kadar kolay kullanım.

## Karar

Sıfırdan compositor (KWin'in yerine geçen pencere yöneticisi) yazılmıyor: derlenmiş kod
ister, sürücü, çoklu monitör, HDR ve erişilebilirlik işi yıllar sürer. Onun yerine
**KWin + plasmashell altyapısı korunuyor, görünen her şey OziOS'un oluyor**:

| Parça | Nerede | Ne yapar |
|---|---|---|
| Dock `org.ozios.dock` | `plasmoids/org.ozios.dock` | Sabitlenen programlar ve açık pencereler. Simgeler fareye doğru yaylanarak büyür, basınca çöker, program açılırken zıplar, dikkat isteyen pencere halka halka nabız atar, çalışanın altında ışık yanar. |
| Başlatıcı `org.ozios.launcher` | `plasmoids/org.ozios.launcher` | Meta tuşu açar. Saate göre selamlama, arama (uygulama, ayar, dosya, hesap), kategori çipleri, açılınca sırayla akarak gelen uygulama ızgarası, kilitle/çıkış/yeniden başlat/kapat. |
| Plasma stili `ozios` | `plasma-style/ozios` (`tools/make-plasma-style.py` yazar) | Çubuk, dock ve tüm açılır pencerelerin çerçevesi: yuvarlak köşeli koyu cam, ince vurgu kenarı. Renkleri o anki renk şemasından alır. |
| Pencere hareketi `ozios_motion` | `kwin/effects/ozios_motion` | Pencereler derinlikten hafif bir yaylanmayla yükselerek açılır, içe çekilip kaybolarak kapanır. KWin'in kendi açılış/kapanış efektinin yerini alır. |
| Pencere değiştirici `org.ozios.switcher` | `kwin/tabbox/org.ozios.switcher` | Alt+Tab: açık pencerelerin canlı resimleri tek sırada; seçili olan vurgu renginde öne çıkar, sıra onu ortada tutacak şekilde kayar. |
| Temalar | `branding/OziOS.colors`, `branding/themes/`, `branding/konsole/` (`tools/make-themes.py` yazar) | Camgöbeği, Kutup Işığı, Kor, Nane, Gül, Ayaz (açık). `ozi theme <ad>` veya kontrol panelindeki renk yuvarlakları; çubuk, dock, açılır pencereler, duvar kâğıdı, pencere çerçeveleri ve terminal birlikte değişir; OziOS uygulamaları açılırken seçili temayı alır. |
| Duvar kâğıdı `org.ozios.tesseract` | `wallpaper/org.ozios.tesseract` | Dönen tesseract, nefes alır gibi parlayan ışık, yukarı süzülen ışık zerrecikleri; renkleri temadan. Bir pencere masaüstünü kapatınca tamamen durur. |
| Kontrol merkezi `org.ozios.control` | `plasmoids/org.ozios.control` | Üstte hızlı ayarlar: Wi-Fi (ağın adıyla), Bluetooth, gece ışığı, rahatsız etme, oyun modu kutucukları (açıkken vurgu renklerinde) ve ses kaydırıcısı; bilgisayarda olmayan (Wi-Fi kartı yoksa Wi-Fi) gösterilmez. Altında tema, efekt seviyesi, düzen, Windows misafiri, güncellemeler. Her şey `ozi quick` / `ozi status` / `ozi theme` ile. |
| Pencere çerçevesi `org.ozios.decoration` | `decoration` (C++, paketi `packages/ozios-decoration`) | Yuvarlak köşeli pencereler (programın içi de); etkin pencerede vurgu renginde kenar ve temanın iki renginde ışıltı, ötekilerde soluk kenar; ortalı başlık, üstüne gelince yanan yuvarlak düğmeler. Plasma'nın yeni ana sürümü gelince `decoration-guard` çerçeveleri paketle gelen kaynaktan o bilgisayarda yeniden derler (`decoration-rebuild`, bir iki dakika); derleyemezse eklentiyi kenara koyar, KWin o arada Breeze çizer. |
| Pencere akışı `ozios_morph` | `kwin/effects/ozios_morph` | Büyütme, geri alma, döşeme: pencere eski yerinden yenisine akar (boyut, yer, geçiş). KWin'in kendi büyütme efektinin yerini alır. |
| Küçültme `ozios_minimize` | `kwin/effects/ozios_minimize` | Pencere dock'taki simgesine süzülür, oradan geri çıkar. |
| Döşeme `ozios-tiling` | `kwin/scripts/ozios-tiling` | Meta+T masaüstünü yarımlar sarmalında döşer (kenarda 12, arada 10 piksel); her yeni pencere kullanılanın yarısını alır. Sürükleyince yer değişir, kenardan çekince çizgi kayar; Meta+F pencereyi serbest bırakır. |
| Masaüstleri `org.ozios.workspaces` | `plasmoids/org.ozios.workspaces` | Soldaki adada dört masaüstü ışık olarak: kullanılan vurgu renklerinde hap, pencereli olanlar dolu nokta. Tık veya tekerlek değiştirir; Meta+1…4. |
| Saat `org.ozios.clock` | `plasmoids/org.ozios.clock` | Ortadaki adada saat ve tarih; tıklayınca takvim. Bir çalarda müzik çalarken (MPRIS) ada büyür: vurgu renginde üç çubuk ve şarkının adı; tıklayınca durur. Takvimin altında kapak, geri, durdur, ileri. Müzik kısmı ayrı yüklenir (`NowPlaying.qml`): Plasma'nın özel modülü değişirse saat yerinde kalır. |
| Kapatma ekranı | `look-and-feel/org.ozios.desktop/contents/logout` | Çıkış, yeniden başlatma, kapatma: masaüstü mürekkep rengine kararır, temanın iki renginde yumuşak bir ışık; üstte saat, tarih ve "Görüşmek üzere", altta sırayla yükselen büyük kutucuklar (kilitle, uyku, derin uyku, yeniden başlat, kapat, oturumu kapat). Seçili olan vurgu renklerinde dolar ve parlar; oklar ve Enter, Esc ya da boşluğa tık geri döner. Bir program tek bir şey istediyse (yeniden başlatma gibi) yalnız o gelir ve 30 saniye geri sayar; bir tuş sayımı durdurur. Bekleyen güncellemeler sarı noktalı ayrı kutucuktur. Çizimler simge temasından değil, kendi çizgileri. Plasma 6.8'den sonra bu ekran masaüstü kabuğundan okunur: yalnız bu ekranı taşıyan `shell/org.ozios.desktop` paketi yalnız kapatma ekranına adlandırılır (`apply-branding.sh`), masaüstü Plasma'nınki kalır; Plasma ekranı reddederse kendi ekranını gösterir. |
| Görünüm `ozi-look` | `apps/ozi-look` | Hazır stiller (Akıcı, Döşeme, Hafif) ve tek tek ayarlar: köşe, kenar, ışıltı, başlık çubuğu, boşluk, döşeme, hız, bulanıklık; her değişiklik hemen görünür. `ozi-look --keys` Meta+K kısayol kartıdır. |

## Optimizasyon kuralları

- Hareket eden her şey dönüşüm (scale/translate) veya saydamlık: GPU'da, CPU'yu yormaz.
  Dock fare hareket ederken boyut değiştirmez, bu yüzden panel yeniden yerleşmez.
- Duvar kâğıdı animasyonları zamanlayıcı değil animator (render thread) kullanır ve
  bir pencere masaüstünü kapatınca durur.
- Kullanıcının animasyon hızı ayarı (`ozi effects off` → 0) tüm OziOS hareketlerini kapatır.
- Yazılımsal çizimde (VirtualBox, llvmpipe) `apply-branding.sh` hafif profili seçer:
  bulanıklık ve wobbly kapalı, duvar kâğıdı durağan.

## Plasma olmadan görmek ve denemek

- `python3 tools/shell-preview.py out/preview --all-themes`: dock, başlatıcı, arama, kontrol
  paneli ve duvar kâğıdının her temada resmi, ayrıca hepsi bir arada `showcase-<tema>.png`.
  Gerçek QML dosyaları, Plasma'nın yerine `tools/plasma_stubs.py` taklitleriyle yüklenir;
  çerçeveler `tools/plasma_style.py` ile Plasma'nın çizdiği gibi SVG'den çizilir.
- `python3 tools/shell-drive.py`: uygulamacıklara gerçek fare ve klavye olaylarıyla tıklar,
  yazar, üstüne gelir ve Plasma'dan ne istediklerini JSON olarak yazar.
- `python3 tools/fake-mpris.py`: bir Plasma oturumunda müzik çalıyormuş gibi yapan sahte bir
  çalar (MPRIS); saatin müzik kısmını gerçek bir çalar olmadan denemek için.
- Uygulamalar: `OZIOS_THEME=frost python3 tools/qml-shot.py apps/ozi-welcome shot:x.png`.

## Durum

Gerçek bir Plasma oturumunda (VirtualBox, 3D kapalı, yazılımsal çizim) denendi: dock,
başlatıcı (arama, kategoriler, Enter ile açma), kontrol paneli ve tema değişimi, Alt+Tab,
pencere hareketi ve gölgeler çalışıyor; plasmashell OziOS için QML hatası vermiyor.
Hafif profilde boştaki masaüstü işlemcinin yüzde birinden azını kullanıyor.

0.3'te ayrıca: çerçeve, akış ve küçültme, üç ada ve dört masaüstü, döşeme (Meta+T, Meta+F,
sürükleme, boyutlandırma) ve Görünüm uygulaması KWin 6.7.4'te denendi.

Öğrenilenler:
- KWin'in `reconfigure` çağrısı çalışan bir efektin ayarlarını yeniden okumaz; efekte adıyla
  sorulur (`org.kde.kwin.Effects.reconfigureEffect slide`).
- Yüzen panel yalnız kendi kalınlığını ayırır, çizildiği yer daha aşağıdadır; döşeme boşluğu
  adanın görünen kenarından ölçülür.
- KWin pencere kenarını opak çizer; soluk kenar saydamlıkla değil, karışık bir renkle yapılır.
- Derlenmiş eklenti `-march=native` ile derlenirse başka işlemcide KWin'i düşürebilir; paket
  bu yüzden genel x86-64 için derlenir.
- KWin yazılımsal çizimde bütün animasyonları kapatır; OziOS bunu
  `/usr/lib/environment.d/60-ozios-animations.conf` ile açık tutar.
- Qt Quick her değişiklikte bütün pencereyi yeniden çizer. Duvar kâğıdındaki hareket
  bu yüzden tek bir saate bağlıdır (saniyede 25 kare); hafif profilde durur.
- Blur yokken yarı saydam açılır pencereler okunmaz; Plasma stilinin normal takımı opaktır.

Testler (`tests/test_desktop.py`) ayrıca şunları doğrular: üretilen dosyalar üreticileriyle
aynı, çerçeve parçalarının geometrisi doğru, temaların kontrastı yeterli, KWin efekti KWin'in
betik API'sinin bir taklidinde doğru animasyonları istiyor, QML dosyaları dengeli ve yalnızca
Qt/Plasma modüllerini içe aktarıyor.
