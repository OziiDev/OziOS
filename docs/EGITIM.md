# OziOS Eğitim: öğretmen kılavuzu

OziOS Eğitim, akıllı tahta ve sınıf bilgisayarları için hazırlanmış ayrı bir
sürümdür. Pardus ETAP değildir ve onun yerine geçtiğini iddia etmez; tahtada
günlük işi görmek için gereken programları hazır getirir. Teknik ayrıntılar için
[EDUCATION.md](EDUCATION.md) (İngilizce).

## Masaüstü

OziOS'un kendi masaüstü açılır: üstte ince bir çubuk, altta büyük simgeli bir
dock. Dock'ta soldan sağa:

| Simge | Ne işe yarar |
|---|---|
| Uygulamalar | Tüm programlar (yazarak aranır) |
| Ekran kalemi | Ekranda ne varsa üzerine çizer |
| Beyaz tahta | Xournal++: boş sayfa, görseller, PDF üzerine not alma |
| Sunum | LibreOffice Impress |
| Sınıf | Öğrenci seçme, grup kurma, zamanlayıcı |
| Tarayıcı | Firefox (PDF'leri de açar) |
| EBA | Eğitim Bilişim Ağı |
| Dosyalar | Ozi Dosyalar |
| Hesap makinesi | Hesap makinesi |
| Mağaza | Program kurma ve güncelleme |

Dock'taki simgeler sürüklenerek yer değiştirir; sağ tık (ya da basılı tutma)
ile sabitlenir veya kaldırılır. Arayüz Türkçedir, klavye Türkçe Q'dur. Ekran
kilidi ve uyku kapalıdır, bu yüzden ders ortasında tahta kararmaz; imleç
büyüktür.

## Dokunma ve ekran klavyesi

- **Parmakla:** dokunmak tıklamaktır. Firefox'ta ve programlarda parmakla
  kaydırılır, iki parmakla yakınlaştırılır. Pencere başlığından tutup
  sürüklenir, başlıktaki düğmeler parmakla basılır.
- **Ekran klavyesi:** bir yazı alanına parmakla dokununca kendiliğinden açılır,
  alanın dışına dokununca kapanır. Çubuktaki klavye düğmesiyle her zaman
  açılıp kapatılır. Açıkken pencereler yukarı kayar, yazılan yer görünür
  kalır. Türkçe Q düzenindedir (ı, ğ, ü, ş, ö, ç, İ); **&123** sembolleri, iki
  kez **⇧** büyük harf kilidini açar.
- **Kalem:** tahtanın kalemi bilgisayara kalem olarak bağlanıyorsa fare gibi
  çalışır; kalemin düğmesi sağ tıktır.

## Ekran kalemi

Kalem açılınca ekranın altında bir araç çubuğu belirir.

- **Araçlar:** kalem, fosforlu kalem, çizgi, ok, kutu, daire, silgi, lazer,
  spot ışığı. Silgi, dokunduğu çizginin tamamını siler.
- **Lazer:** kırmızı bir nokta ve kısa süre sonra silinen bir iz bırakır; sunum
  sırasında bir yeri göstermek içindir.
- **Spot ışığı:** ekranı karartır, yalnızca işaretçinin çevresi aydınlık kalır.
- **Renk ve kalınlık:** altı renk, üç kalınlık.
- **Geri al** son çizgiyi geri alar (Ctrl+Z), **Temizle** hepsini siler (Delete).
- **Kaydet**, çizimi ekran görüntüsü olmadan, saydam bir PNG olarak
  `Resimler/ozi-pen` klasörüne yazar.
- **Ekranı kullan**, dokunuşları altındaki programa geçirir; çizimler ekranda
  kalır. Tekrar çizmek için **Çiz** düğmesine basılır. Esc tuşu ikisi arasında
  geçiş yapar.
- Araç çubuğu boş bir yerinden tutulup sürüklenerek taşınır.

Kalem şimdilik tek işaretçiyle çalışır: iki parmakla aynı anda iki çizgi
çizilmez.

## Beyaz tahta

Xournal++ açılır. Sayfa ekleyebilir, görsel yerleştirebilir, bir PDF'i açıp üzerine
yazabilirsin. Çalışmayı kaydedersen dosya olarak saklanır; PDF olarak da
dışa aktarılabilir.

## Sınıf

Sınıf uygulaması dört bölümden oluşur.

1. **Öğrenciler:** ilk açılışta bir sınıf adı verilir (örneğin `5-A`), sonra her
   satıra bir isim yazılıp **Kaydet**'e basılır. Listeler hesabına özeldir. Bir
   sınıfı silmek için **Sınıfı sil**'e iki kez basmak gerekir.
2. **Seç:** rastgele bir öğrenci seçer. Herkes bir kez seçilmeden kimse ikinci kez
   seçilmez; tur bitince yenisi kendiliğinden başlar. **Yeni tur** istediğin zaman
   baştan başlatır. Boşluk tuşu da seçer.
3. **Gruplar:** grup sayısını ayarla, **Grupları oluştur**'a bas. Gruplar, kişi
   sayıları en fazla bir fark edecek şekilde karıştırılır.
4. **Zamanlayıcı:** 1 ile 180 dakika arası geri sayım yapar. Süre dolunca ses çalar
   ve ekrandaki yazı yanıp söner. Boşluk tuşu başlatır ve durdurur.

## Tahta Köprüsü

Dock'taki **Tahta Köprüsü** tahtada iki QR kod gösterir. Telefonlar tahtayla aynı
Wi-Fi'da olmalı; hiçbir uygulama kurulmaz, internet gerekmez.

- **Öğretmen kodu:** telefonu tahtanın kumandası yapar: önceki ve sonraki slayt,
  sunumu başlat, karart, bitir; dokunmatik fare (dokun = tıkla, iki parmak = sağ
  tık); tahtanın canlı görüntüsü; **Bu tahtayı paylaş**. Kodda rastgele bir
  anahtar vardır: okuttuktan sonra **Kodu gizle**'ye bas, öğrenciler göremesin.
- **Öğrenci kodu:** bugün paylaşılan tahtalar ve ekran kalemiyle kaydedilen
  çizimler listelenir; dokununca telefona iner. **Hepsini tek PDF olarak indir**
  bütün dersi tek dosya yapar.
- Okulda Wi-Fi yoksa **Tahtanın kendi Wi-Fi'ı** tahtayı bir erişim noktası
  yapar; ağ adı ve şifresi ile bir Wi-Fi QR kodu çıkar. O sırada tahtanın kendi
  interneti kesilir.
- Paylaşılanlar `Belgeler/Ders Notları` klasöründe durur (**Notlar klasörü**).
- Telefonlar yalnız yerel ağdan, yalnız 8765-8784 portlarından bağlanabilir;
  güvenlik duvarı (ufw) gerisini kapalı tutar.

## Kısıtlı ve yetkili mod

Tahta her açılışta **kısıtlı** modda başlar: dersler her zamanki gibi çalışır ama
terminal, ayarlar, mağaza, kurulum ve yönetici yetkileri kapalıdır. Wi-Fi'a
bağlanmak, USB bellek takmak, ses ve kapatma çalışır.

- **Öğretmen modu** uygulamasında öğretmen şifresi yazılınca **yetkili** moda
  geçilir; bir sonraki açılışa kadar her şey açıktır. **Kısıtlı moda dön** hemen
  kilitler.
- İlk şifre `ogretmen`dir. Yetkili moddayken **Yeni öğretmen şifresi** ile
  değiştir. Şifre beş kez yanlış yazılırsa 30 saniye beklemek gerekir.

## Dondurma

Yetkili modda **Tahtayı dondur** açılınca masaüstü ve dosyalar o anki hâliyle
kaydedilir ve her açılışta bu hâline döner: öğrencilerin masaüstüne bıraktığı,
sildiği ya da değiştirdiği her şey ertesi sabah eski hâlindedir. Ders notları
(`Belgeler/Ders Notları` ve `Resimler/ozi-pen`) korunur. Tahtayı yeniden
düzenledikten sonra **Bu hâli dondurulmuş hâl olarak kaydet**'e bas.

## OziOS turu

**OziOS turu** uygulamasında Ozi-chan ekranın altından Eğitim sürümünü anlatır ve
her bölümde ilgili programı kendisi açar. Konuşma balonuna dokunmak durdurur,
oklar ileri ve geri götürür, × bitirir. Tanıtım USB'sinde
(`ozios-tanitim-edu-*.iso`) tur masaüstü açılınca kendiliğinden başlar ve
sürekli döner.

## Güncelleme

Hoş Geldin'deki **Şimdi güncelle** (ya da terminalde `ozi update`, yetkili modda)
önce sistemin anlık kopyasını alır, sonra günceller ve sistemin açılabildiğini
denetler. Bir şey bozulduysa yeniden başlatmadan önce kendiliğinden eski hâline
döner.

## Bir şey ters giderse

- Bir terminalde `ozi doctor` kurulumu denetler ve bulduğu her sorun için ne
  yapılacağını söyler.
- `ozi report` hata bildirimine eklenecek bir metin raporu yazar. Hiçbir yere
  gönderilmez; kullanıcı adı, adresler ve seri numaraları dosyaya yazılmadan önce
  silinir.
- `ozi clean` diskte yer açılabilecek yerleri gösterir; `--yes` ile temizler.

## Sınırlar

- Birçok tahtayı tek yerden yönetmek (uzaktan güncelleme, uzaktan kilit, sınıf
  hesapları) yoktur; her tahta kendi bilgisayarıdır.
- Dokunma, ekran klavyesi ve pencere sürükleme bir test masaüstünde parmak
  dokunuşları taklit edilerek denendi; gerçek bir tahtada henüz denenmedi.
  Bilgisayara sıradan bir USB dokunmatik ekran gibi görünen tahtalar (çoğu
  tahta böyledir) çalışır; üreticinin sürücüsünü isteyen eski tahtalar için o
  sürücü gerekir.
- Birden çok ekran bağlıysa dokunma ilk ekrana eşlenir.
