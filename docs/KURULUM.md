# OziOS kurulumu

OziOS henüz erken aşamada. Sanal makinede (VirtualBox, UEFI) kuruldu ve açıldı;
gerçek donanımda henüz denenmedi. Bilgisayardaki önemli dosyalarının yedeğini al.

## Gerekenler

- UEFI kipinde açılan 64 bit bir bilgisayar. BIOS kipi denenmedi.
- En az 4 GB bellek ve OziOS için en az 25 GB disk.
- 8 GB ya da daha büyük bir USB bellek.
- Kurulum sırasında internet. Kurucu sistemi çalışırken indirir (yaklaşık 2 GB);
  kablo ya da canlı masaüstünden bağlanabileceğin bir Wi-Fi ağı gerekir.
  İndirme sırasında bağlantı bir süre koparsa kurucu onu bekler ve kaldığı
  yerden devam eder. İndirilen sistemin Plasma'sı ortamdakinden yeniyse kurucu
  OziOS pencere çerçevelerini o Plasma için de derler; bu bir iki dakika ekler.

## 1. ISO'yu USB belleğe koy

Önce sağlama toplamını karşılaştır; `.sha256` dosyası ISO'nun yanında durur.

```
sha256sum -c ozios-<sürüm>-<tarih>-x86_64.iso.sha256
```

Sonra şunlardan biri:

- **Ventoy.** `.iso` dosyasını Ventoy belleğine kopyala. Başka bir şey gerekmez.
- **Windows.** Rufus, "DD imajı" kipinde.
- **Linux.** `sudo dd if=ozios-....iso of=/dev/sdX bs=4M status=progress oflag=sync`;
  `/dev/sdX` USB bellektir. Bellekteki her şey silinir.

## 2. Bellekten başlat

Bilgisayarı yeniden başlat ve açılış menüsünü aç (çoğunlukla açılır açılmaz F12,
F9, Esc ya da F2). USB belleği UEFI kipinde seç. Bir iki dakika içinde OziOS
masaüstü gelir. Bu noktada bilgisayarda hiçbir şey değişmemiştir: etrafa bakabilir,
ağa bağlanabilir, kapatıp çıkabilirsin.

## 3. Kur

Karşılama penceresinde **Kur** düğmesi var. Kurucu sırayla şunları sorar:

1. Dil.
2. Saat için bulunduğun yer.
3. Klavye düzeni.
4. Disk. "Diski sil" bütün diski OziOS'a verir ve üzerindeki her şeyi siler.
   Başka bir sistemi korumak için elle bölümlemeyi seç ve ne yaptığını bil;
   Windows'un yanına kurulum denenmedi.
5. Masaüstü: Plasma'da bırak.
6. Ek paketler: varsayılanlar yeterli.
7. Adın, kullanıcı adın ve parolan.
8. Özet. Burada **Kur**'a basıp onaylayana kadar diske hiçbir şey yazılmaz.

Kurulum 30 ile 60 dakika sürer; çoğu indirmedir. Bittiğini söylediğinde yeniden
başlat ve belleği çıkar.

## 4. İlk açılış

Oluşturduğun kullanıcıyla giriş yap. Karşılama penceresi yeniden açılır; oradan:

- **Oyunlar**, Steam'i, oyun modunu ve ekran kartına uyan grafik kitaplıklarını
  kurar (terminalde `ozi gaming` aynısını yapar ve önce listeyi gösterir).
- **Yazılım edin**, program kurar ve paketleri sisteme girmeden önce inceler.
- Terminalde `ozi doctor` kurulumu denetler ve bulduklarının nasıl düzeltileceğini
  söyler; `ozi update` sistemi günceller ve önce bir anlık görüntü alır.

## Bir şey ters giderse

- Kurucu bir hatayla durursa: yazıyı not et, sonra Karşılama penceresinden yeniden
  başlat. Yarıda kalan bir kurulum tekrarlanabilir.
- Bilgisayar sonradan diskten açılmazsa: yeniden bellekten başlat, bir terminal aç
  ve `ozi report` çalıştır. Adlar ve adresler silinmiş bir metin dosyası yazar;
  onu <https://github.com/OziiDev/OziOS/issues> adresindeki bir kayda ekleyebilirsin.

English: [INSTALL.md](INSTALL.md)
