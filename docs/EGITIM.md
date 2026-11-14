# OziOS Eğitim: öğretmen kılavuzu

OziOS Eğitim, akıllı tahta ve sınıf bilgisayarları için hazırlanmış ayrı bir
sürümdür. Pardus ETAP değildir ve onun yerine geçtiğini iddia etmez; tahtada
günlük işi görmek için gereken programları hazır getirir. Teknik ayrıntılar için
[EDUCATION.md](EDUCATION.md) (İngilizce).

## Masaüstü

Ekranın altında tek bir çubuk var; düğmeler parmakla ya da kalemle rahat
basılacak kadar büyük. Soldan sağa:

| Düğme | Ne işe yarar |
|---|---|
| Menü | Tüm programlar |
| Ekran kalemi | Ekranda ne varsa üzerine çizer |
| Beyaz tahta | Boş sayfa; sayfalar, görseller ve PDF üzerine not alma |
| Sunum | LibreOffice Impress |
| PDF okuyucu | Okular |
| Sınıf | Öğrenci seçme, grup kurma, zamanlayıcı |
| Tarayıcı | Firefox |
| EBA | Eğitim Bilişim Ağı |
| Dosyalar | Dosya yöneticisi |
| Hesap makinesi | KCalc |
| Yazılım | Program kurma ve güncelleme |

Çubuğun sağında OziOS kontrol düğmesi, sistem tepsisi (ses, ağ ve benzerleri) ve saat bulunur.
Arayüz Türkçedir, klavye Türkçe Q'dur.
Bir yazı alanına dokununca ekran klavyesi açılır. Ekran kilidi ve uyku kapalıdır,
bu yüzden ders ortasında tahta kararmaz.

Başka bir düzene geçmek için bir terminalde `ozi layout default`, geri dönmek
için `ozi layout board` yazılır.

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
- Tahtanın dokunmatik çerçevesi, kalemi ve üreticinin yazılımı denenmedi. Bilgisayara
  sıradan bir USB dokunmatik ekran gibi görünen tahtalar çalışır; üreticinin sürücüsünü
  isteyenler için o sürücü gerekir.
- Eğitim sürümü bir sanal makinede denendi, gerçek bir tahtada henüz denenmedi.
