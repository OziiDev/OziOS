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
| Temalar | `branding/OziOS.colors`, `branding/themes/`, `branding/konsole/` (`tools/make-themes.py` yazar) | Camgöbeği, Kutup Işığı, Kor, Nane, Gül, Ayaz (açık). `ozi theme <ad>` veya kontrol panelindeki renk yuvarlakları; çubuk, dock, açılır pencereler, duvar kâğıdı, pencere çerçeveleri ve terminal birlikte değişir; OziOS uygulamaları açılırken seçili temayı alır. |
| Duvar kâğıdı `org.ozios.tesseract` | `wallpaper/org.ozios.tesseract` | Dönen tesseract, nefes alır gibi parlayan ışık, yukarı süzülen ışık zerrecikleri; renkleri temadan. Bir pencere masaüstünü kapatınca tamamen durur. |
| Kontrol `org.ozios.control` | `plasmoids/org.ozios.control` | Tema, oyun modu, efekt seviyesi, düzen, Windows misafiri, güncellemeler. |

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
- Uygulamalar: `OZIOS_THEME=frost python3 tools/qml-shot.py apps/ozi-welcome shot:x.png`.

## Durum

Plasma oturumunda henüz çalıştırılmadı. Testler (`tests/test_desktop.py`) şunları
doğrular: üretilen dosyalar üreticileriyle aynı, çerçeve parçalarının geometrisi doğru,
temaların kontrastı yeterli, KWin efekti KWin'in betik API'sinin bir taklidinde doğru
animasyonları istiyor, QML dosyaları dengeli ve yalnızca Qt/Plasma modüllerini içe aktarıyor.
İlk iş: VM'de bir Plasma oturumunda açıp `journalctl --user -b | grep -i qml` çıktısına bakmak.
