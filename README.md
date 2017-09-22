# sagabot

## Wstęp

Stworzyłem tego bota na potrzeby Discorda Sasuga-san@Ganbaranai (AKA OdA). 
Główną funkcjonalnością bota jest czytanie profilów MyAnimeList i wyliczanie "powerlevelu". 
Obliczanie odbywa się na podstawie **Completed**, czyli skończonych bajek i **Days**, czyli sumarycznej ilości czasu poświęconej na oglądanie bajek. 

## Wzór

Poniżej techniczne szczegóły dla zainteresowanych tym, jak bot właściwie liczy XP i level. 
XP jest liczone według poniższego wzoru:

```
xp = int(round(days_number * completed_number * factor * score_factor, 0))
```
gdzie `factor` to `60/13`, a `score_factor` to kara za odchylenie od średniej ocen:
```
middle = norm(5, 2).pdf(5) # prawdopodobieństwo wylosowania 5 z rozkładu normalnego o średniej 5 i wariancji 2
score_factor = norm(5, 2).pdf(meanscore_number) / middle # j.w, ale wylosowania średniej ocen z profilu 
```
W przypadku, gdy średnia ocen z profilu to 5, ten czynnik wynosi 1 - w przeciwnym razie maleje. 
Po przemnożeniu wszystkiego XP jest zaokrąglone do pełnej liczby, a typ zmiennej zostaje zmieniony na liczbę całkowitą (żeby nie było zbędnego rozwinięcia dziesiętnego przy podawaniu liczby przez bota). 

Poziom wyliczany jest na podstawie ramek XP, które podane są w pliku `levels.csv` wewnątrz tego repozytorium. 

## Polecenia

`!malbind <nazwa profilu MAL>` - przypisuje użytkownikowi Discord podany profil na MAL. 
`!mal` - dla przypisanego użytkownikowi profilu wylicza XP oraz level i przypisuję rolę na serwerze zależnie od levela. 
`!malcheck <nazwa profilu MAL>` - dla podanej nazwy profilu zwraca statystyki takie, jak `!mal`. Działa także na nieprzypisanych profilach - dla przypisanych już profilów pobiera statystyki z bazy danych, nie z MALa. 
`!malfind <zapytanie>` - znajduje bajkę na MALu i podaje informacje o niej oraz link do wpisu na MALu. 

