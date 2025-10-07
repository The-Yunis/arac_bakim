# Araç Bakım Kayıtları Yönetim Sistemi 

Modern PyQt6 tabanlı araç bakım takip uygulaması. Araçlarınızın bakım geçmişini, kilometre takibini ve gelecek bakım planlarını yönetmenizi sağlar.

## 🚗 Özellikler

- **Araç Yönetimi**: Araç ekleme, düzenleme ve silme
- **Bakım Kayıtları**: Detaylı bakım geçmişi takibi
- **Kilometre Takibi**: Araç kilometrelerini kaydetme ve analiz
- **Bakım Planlama**: Gelecek bakım tarihlerini planlama
- **Excel İçe/Dışa Aktarma**: Verilerinizi Excel formatında yedekleme
- **Modern Arayüz**: Kullanıcı dostu PyQt6 arayüzü
- **Veritabanı**: SQLite ile güvenli veri saklama

## 📋 Gereksinimler

- Python 3.8+
- PyQt6
- pandas
- openpyxl
- requests
- PyGithub

## 🚀 Kurulum

1. Repository'yi klonlayın:
```bash
git clone https://github.com/kullaniciadi/arac_bakim.git
cd arac_bakim
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın:
```bash
python bakim_gui.py
```

## 📖 Kullanım

### Araç Ekleme
1. "Araçlar" sekmesine gidin
2. "Yeni Araç Ekle" butonuna tıklayın
3. Araç bilgilerini doldurun
4. "Kaydet" butonuna tıklayın

### Bakım Kaydı Ekleme
1. "Bakım Kayıtları" sekmesine gidin
2. "Yeni Bakım Ekle" butonuna tıklayın
3. Bakım detaylarını doldurun
4. "Kaydet" butonuna tıklayın

### Excel İçe Aktarma
1. "Veri Yönetimi" sekmesine gidin
2. "Excel'den İçe Aktar" butonuna tıklayın
3. Excel dosyasını seçin
4. Sütun eşleştirmelerini yapın

## 🗂️ Proje Yapısı

```
arac_bakim/
├── bakim_gui.py          # Ana uygulama dosyası
├── requirements.txt       # Python bağımlılıkları
├── bakim_kayitlari.db     # SQLite veritabanı
└── README.md             # Bu dosya
```

## 🔧 Geliştirme

Projeyi geliştirmek için:

1. Repository'yi fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Push edin (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## 📞 İletişim

Proje hakkında sorularınız için issue açabilirsiniz.
