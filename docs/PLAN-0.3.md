# OziOS 0.3 "Akış" planı

İstek: KDE Plasma gibi görünmesin; Hyprland kadar güzel, Plasma kadar kolay olsun; pencere
animasyonları ve yeni arayüzler gelsin. Plan kendi kendine onaylandı (kullanıcı öyle istedi).

## Neyin üstüne kuruluyor

KWin 6.7.4 + Plasma 6.7.4 (Qt 6.11). Pencere yöneticisi değişmiyor: Hyprland'ın kendisi
yazılımsal çizimde ve eski donanımda kötü çalışır, ayar dosyası ister, sistem ayarları,
ekran, ağ, ses gibi kolaylıkları yoktur. Onun yerine Hyprland'ı güzel yapan şeyler KWin'in
üstüne kuruluyor:

| Hyprland'da | OziOS 0.3'te |
|---|---|
| Yuvarlak köşeli pencereler, renkli kenarlık | Kendi pencere çerçevemiz `org.ozios.decoration` (C++, KDecoration3). KWin pencerenin içeriğini de yuvarlatır; kenarlığı KWin'in çizgisi (outline) çizer, köşede kırılmaz. Etkin pencerede tema renginde kenar ve hafif ışıltı. |
| Yaylanan açılış/kapanış | `ozios_motion` daha canlı ayarlarla. |
| Pencere yer/boyut değişince süzülme | Yeni `ozios_morph` efekti: büyütme, küçültme, döşeme, yarıya yaslama — eski yerden yenisine akar. KWin'in kendi büyütme efektinin yerini alır. |
| Küçültme | Yeni `ozios_minimize`: pencere dock'taki simgesine süzülür. |
| Çalışma alanları kayarak değişir | KWin slide, araları açık; Meta+1…4. |
| Otomatik döşeme (dwindle), boşluklar | Yeni KWin betiği `ozios-tiling`: Meta+T aç/kapa, Meta+F pencereyi serbest bırak, sürükleyerek yer değiştir. Varsayılan kapalı (kolay kullanım), tek tuş uzakta. |
| Waybar adaları | Üstte üç yüzen ada: solda başlatıcı + çalışma alanları, ortada saat, sağda hızlı ayarlar + tepsi. Yeni uygulamacıklar `org.ozios.workspaces`, `org.ozios.clock`. |
| Ayar dosyası | Yok: yeni **Görünüm** uygulaması (`ozi-look`) ve `ozi look` komutu: hazır stiller (Akıcı, Döşeme, Hafif), köşe, kenar, boşluk, animasyon hızı, bulanıklık, döşeme. |
| Kısayol ezberi | Meta+K ile kısayol kartı (`ozi-keys`). |

## Sıra

1. Pencere çerçevesi (en çok görünen parça), VM'de derle, dene.
2. Efektler: morph, minimize, açılış/kapanış ayarı, slide ayarı.
3. Üst adalar + çalışma alanları + saat.
4. Döşeme betiği (testleri QJSEngine ile, gerçek KWin'de deneme).
5. Görünüm uygulaması, `ozi look`, kısayol kartı, varsayılan kısayollar.
6. Paket (`ozios-decoration` derlenir), remaster, check-image, testler, belgeler, 0.3.0,
   ISO, kurulum testi, ekran görüntüleri.

## Durum (21 Kasım 2026)

1–5 bitti ve gerçek KWin 6.7.4'te (VirtualBox, yazılımsal çizim) denendi: çerçeve, akış ve
küçültme efektleri, üç ada, dört masaüstü ve kısayolları, kaymada duran duvar kâğıdı, döşeme
(aç/kapa, yeni pencere, serbest bırakma, sürükleyip yer değiştirme, kenardan boyutlandırma),
Görünüm uygulaması Türkçe ve Döşeme stili. 6'da paket, remaster, check-image, testler ve
belgeler hazır; 0.3.0 ISO'su VM'de derlenip denenecek.

## Riskler ve önlemler

- Derlenmiş çerçeve KDecoration3'e bağlı. Yalnız genel API kullanılır; yüklenemezse KWin
  Breeze'e döner. Plasma'nın yeni bir ana sürümü (6.7 → 6.8) gelince pacman kancası
  (`decoration-guard`) eklentiyi kenara koyar, o Plasma için derlenmiş paket gelince geri
  koyar; `ozi doctor` derlendiği sürümle kurulu sürümü karşılaştırır. Paket ISO'da her
  x86-64 işlemci için derlenir (CachyOS'un `-march=native` ayarı kullanılmaz).
- Üçlü üst panel Plasma'da mümkün ama yeni; VM'de denenir, olmazsa tek tam çubuğa dönülür.
- Yazılımsal çizimde (VM) hafif profil kalır: ışıltı ve bulanıklık kapalı, animasyonlar açık.
- Kilit ekranı değiştirilmiyor: bozulursa oturum açılamaz.
