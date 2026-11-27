"""Persistent bezel identifiers and menu translations, without rendering dependencies."""
MODES=('none','auto','egypt','greece','solar')
LABELS=('Aucun','Automatique','Égyptien','Grec','Éclipse solaire')
TEXTS=('Cadre d’écran',*LABELS,'Décor adapté aux marges de l’écran.')
ROWS={
 'en':('Screen bezel','None','Automatic','Egyptian','Greek','Solar eclipse','Artwork fitted to the screen margins.'),
 'de':('Bildschirmrahmen','Keiner','Automatisch','Ägyptisch','Griechisch','Sonnenfinsternis','Dekor für die Bildschirmränder.'),
 'es':('Marco de pantalla','Ninguno','Automático','Egipcio','Griego','Eclipse solar','Decoración adaptada a los márgenes.'),
 'it':('Cornice schermo','Nessuna','Automatica','Egizia','Greca','Eclissi solare','Decorazione adattata ai margini.'),
 'pt':('Moldura do ecrã','Nenhuma','Automática','Egípcia','Grega','Eclipse solar','Decoração adaptada às margens.'),
 'nl':('Schermrand','Geen','Automatisch','Egyptisch','Grieks','Zonsverduistering','Decoratie aangepast aan de schermranden.'),
 'pl':('Ramka ekranu','Brak','Automatyczna','Egipska','Grecka','Zaćmienie Słońca','Dekoracja dopasowana do brzegów ekranu.'),
 'cs':('Rámeček obrazovky','Žádný','Automatický','Egyptský','Řecký','Zatmění Slunce','Dekorace přizpůsobená okrajům obrazovky.'),
 'ro':('Rama ecranului','Fără','Automată','Egipteană','Greacă','Eclipsă solară','Decor adaptat marginilor ecranului.'),
 'hu':('Képernyőkeret','Nincs','Automatikus','Egyiptomi','Görög','Napfogyatkozás','A képernyő széléhez igazított díszítés.'),
 'tr':('Ekran çerçevesi','Yok','Otomatik','Mısır','Yunan','Güneş tutulması','Ekran kenarlarına uyarlanan süsleme.'),
 'sv':('Skärmram','Ingen','Automatisk','Egyptisk','Grekisk','Solförmörkelse','Dekor anpassad till skärmens kanter.'),
 'da':('Skærmramme','Ingen','Automatisk','Egyptisk','Græsk','Solformørkelse','Dekoration tilpasset skærmens kanter.'),
 'nb':('Skjermramme','Ingen','Automatisk','Egyptisk','Gresk','Solformørkelse','Dekor tilpasset skjermens kanter.'),
 'fi':('Näytön kehys','Ei mitään','Automaattinen','Egyptiläinen','Kreikkalainen','Auringonpimennys','Näytön reunoihin sovitettu koriste.'),
 'is':('Skjáumgjörð','Engin','Sjálfvirk','Egypsk','Grísk','Sólmyrkvi','Skraut lagað að jöðrum skjásins.'),
 'ru':('Рамка экрана','Нет','Автоматически','Египетская','Греческая','Солнечное затмение','Оформление по краям экрана.'),
 'bg':('Рамка на екрана','Без','Автоматична','Египетска','Гръцка','Слънчево затъмнение','Украса, съобразена с краищата на екрана.'),
 'sr':('Оквир екрана','Без','Аутоматски','Египатски','Грчки','Помрачење Сунца','Украс прилагођен ивицама екрана.'),
}


def theme_for(mode,level):
    if mode=='auto':return 'greece' if 5<=level<=8 else 'egypt'
    return mode if mode in ('egypt','greece','solar') else None
