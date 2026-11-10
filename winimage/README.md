# Windows imaj üretici (M3)

Amaç: kullanıcının kendi Windows ISO'sundan, yerelde, debloat'lı ve otomatik kurulumlu qcow2 üretmek. Hazır modifiye ISO dağıtılmaz.

## Girdi
- Resmi Windows ISO (kullanıcı verir) + `virtio-win.iso`

## Yapılacak
1. `autounattend.xml`: yerel kullanıcı (parola kurulumda sorulur/üretilir, düz metin saklanmaz), OOBE atla, RDP aç, virtio sürücü yolu.
2. Debloat: **IveMalfunctioned/Win10Debloated** reposundaki `DeCrapify.ps1`, `tweaks.reg` ve OOBE preset XML'i referans alınır. Lisansı repoda belirtilmemiş: kopyalamadan önce yazardan izin/lisans netleştir, yoksa kendi betiğimizi yaz.
3. virtio sürücülerini (ağ, depolama, GPU) imaja enjekte et.
4. `qemu-img` + libvirt ile VM oluştur, ilk açılışta RemoteApp için gerekli kayıt defteri ayarlarını uygula.
5. Windows 10 desteği bitti (Ekim 2025): varsayılanı Windows 11 yap, 10'u isteğe bağlı bırak.

## Not
Elindeki Win10Debloated ISO'sunu şimdilik VM'de prototip için kullan.
