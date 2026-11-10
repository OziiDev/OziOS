# OziShell (masaüstü)

Hedef: Hyprland'dan daha akıcı/güzel animasyon, KDE kadar kolay kullanım.

## Karar
Sıfırdan compositor yazmıyoruz (yıllarca sürer, sürücü/HDR/çoklu monitör/erişilebilirlik sorunları çıkar). **KDE Plasma 6 + KWin** üstüne OziOS katmanı:
- KWin kendi animasyon efektlerini GPU'da çalıştırır; Hyprland'a göre eksik olan "güzel" kısmı efekt + tema ile kapanır.
- Kolaylık hazır gelir: ayar paneli, çoklu monitör, giriş ekranı, bildirimler, erişilebilirlik.

## Katmanlar
1. **Global tema + renk şeması + ikonlar** (`look-and-feel` paketi: `ozi-theme`)
2. **KWin efektleri açık gelir:** bulanıklık (blur), wobbly windows, magic lamp (küçültme), kayan geçişler, genel bakış; animasyon süresi ayarlı (`defaults/kdeglobals`, `defaults/kwinrc`)
3. **Panel/dock düzeni:** altta ortalı yüzen dock, üstte ince durum çubuğu (Plasma panel layout script)
4. **Karşılama uygulaması** + Windows katmanı widget'ı (Windows durumu, tek tık "Windows penceresi aç")
5. İleride: topluluk efektleri (Burn My Windows vb.) paket olarak; lisansları kontrol edilerek eklenir.

## Sonraki adım (isteğe bağlı, uzun vade)
Quickshell (QML) ile tamamen özel bir kabuk, KWin üstünde çalışır; Plasma'nın altyapısını koruyup görünümü tamamen değiştirir.

## Durum
`defaults/` içindeki anahtar adları Plasma 6'da **doğrulanmadı**; CachyOS KDE ISO'sunda `kreadconfig6` ile kontrol edilecek.
