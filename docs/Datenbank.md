\anchor Datenbank
Datenbank
---------

![Datenbankstruktur](tables.png)

Die Chat-Anwendung verwendet die zwei Relationen „action“ und „session“. Durch die Angabe eines Präfixes ist es möglich, dass mehrere Chat-Objekte dieselbe Datenbank verwenden. Bei der Wahl eines Präfixes wird geprüft, ob Relationen mit diesem Präfix bereits existieren, um in diesem Fall den Präfix abzulehnen.

Die Relation „session“ speichert alle Sitzungen eines Chat-Objekts. In der „actions“-Relation sind alle Nachrichten und Aktionen bezüglich der Nachrichten zu den Chat-Sessions gespeichert. Folgende Tabelle beschreibt die Spalten der beiden Relationen.

Spalte	    | Beschreibung
----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
id          | Es wird die eindeutige ID der Sitzung gespeichert. 
name        | Es wird der Name der Chat-Sitzung gespeichert. 
description | Es wird eine Beschreibung für die Chat-Sitzung gespeichert. 
password    | Es wird das Passwort der Chat-Sitzung gespeichert. Ist dieses Feld leer, so hat die betreffende Sitzung kein Passwort. 
max_user    | Es wird die Anzahl der maximalen Benutzer für die Chat-Sitzung gespeichert. Ist dieses Feld leer, so gibt es keine Beschränkung der Benutzerzahl. 
start       | Es wird der Startzeitpunkt der Chat-Sitzung gespeichert. Vorher kann dem Chat nicht beigetreten werden. 
end         | Es wird der Endzeitpunkt der Chat-Sitzung gespeichert. Nach diesem Zeitpunkt kann der Chat nicht mehr betreten werden. Benutzer, welche sich noch im Chat befinden, werden nach diesem Zeitpunkt des Chats verwiesen. 

Spalte   | Beschreibung
-------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
id       | Es wird die eindeutige ID der Aktion gespeichert. 
chat_uid | Die Aktion wird einer konkreten Chat-Sitzung zugeordnet. 
date     | Es wird der Zeitpunkt der Aktion gespeichert. 
user     | Es wird der Benutzer, von welchem die Aktion ausging, gespeichert. 
action   | Es wird der Typ der Aktion gespeichert. Mögliche Typen sind das Hinzufügen, Bearbeitung oder Löschen einer Nachricht. 
content  | Es wird der Nachrichteninhalt gespeichert. Dabei handelt es sich entweder um eine gesendete Nachricht oder um die aktualisierte Nachricht, falls eine Nachricht bearbeitet wurde. 
target   | Falls eine Nachricht bearbeitet oder gelöscht wurde, wird hier die ID dieser  betreffenden Nachricht gespeichert. 

Die Interaktion mit der Datenbank wird durch die TUDChatSqlStorage-Klasse realisiert. In ihr befinden sich neben den Definitionen, welche zur Erzeugung der Tabellen notwendig sind, auch alle Abfragen, die zum Anfordern von Informationen aus der Datenbank notwendig sind. Die Funktion zum Abfragen der Chat-Nachrichten weist eine erhöhte Komplexität auf und wird daher detaillierter beschrieben.

Als Eingabe für diese Abfrage werden drei Parameter übermittelt. Der Parameter „chat_uid“ enthält die ID des aktuellen Chat-Raums, damit auch nur Aktionen aus diesem Raum zurückgegeben werden. Der zweite Parameter namens „last_action“ enthält die letzte Aktion des Nutzers. Dadurch wird sichergestellt, dass nur Aktionen angezeigt werden, die neuer sind als die bisher übermittelten Aktionen. Abschließend existiert noch der Parameter „start_action“. Er enthält die Aktions-ID, welche beim Betreten des Chat-Raums, die letzte Aktion darstellt. Dies dient dazu, dem Benutzer keine Aktionen zuzusenden, welche sich auf Nachrichten vom dem Betreten des Chat-Raums beziehen. Wird beispielsweise eine ältere Nachricht von einem Zeitpunkt, als der Nutzer noch nicht im Chat war, gelöscht, so kann durch diesen Parameter die Aktion für den konkreten Benutzer ignoriert werden. Die resultierenden Ergebnisspalten der Abfrage werden durch folgende Tabelle charakterisiert:

Spalte   | Beschreibung
-------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
id       | Es wird die eindeutige ID der Aktion ausgegeben. Es handelt sich um eine aufsteigend inkrementierte Zahl. Neue Aktionen haben also eine höhere ID als ältere Aktionen. 
action   | Es wird ausgegeben, ob die Nachricht hinzugefügt, bearbeitet oder gelöscht wird. 
date     | Es wird der Zeitpunkt der ursprünglichen Nachricht ausgegeben. 
user     | Es wird der Benutzer ausgeben, welcher die Nachricht ursprünglich erzeugt hat. 
message  | Es wird die hinzugefügte oder geänderte Nachricht ausgegeben. 
target   | Bei Moderatoren-Aktionen steht in diesem Feld die ID der Aktion auf welche sich die Moderation-Aktion bezieht. 
a_action | Bei Moderatoren-Aktionen steht in diesem Feld, ob eine bestehende Nachricht bearbeitet oder gelöscht wurde. 
a_name   | Bei Moderatoren-Aktionen steht in diesem Feld durch welchen Moderator die Aktion ausgelöst wurde. 
u_action | Bei Moderatoren-Aktionen steht in diesem Feld, welche Aktion durch den ursprünglichen Benutzer ausgeführt wurde. 

Realisiert wird das Abfrageergebnis durch vier verbundene „select“-Blöcke:
1. Zuerst werden die Nachrichten abgefragt, welche seit der letzten Nutzer-Abfrage neu hinzugekommen sind. Es werden die Nachrichten herausgefiltert, für die bereits eine neuere Aktion existiert (beispielsweise weil die Nachricht bearbeitet wurde).
2. In diesem Block werden Aktionen für bearbeitete oder gelöschte Nachrichten ermittelt. Dabei wird der „start_action“-Parameter verwendet, um sich nur auf Nachrichten zu beziehen, welche beim Betreten des Chat-Raums bereits gesendet wurden. Sollte eine Nachricht mehrfach bearbeitet worden sein, wird nur die letzte Bearbeitung berücksichtigt. Durch eine zweifache Verknüpfung mit der Nachrichten-Tabelle können Informationen zur ursprünglichen Nachricht und zur Moderatoren-Aktion gewonnen werden.
3. Dieser Block verhält sich sehr ähnlich zum vorherigen Block. Im Unterschied zu diesem behandelt dieser Block aber geänderte Nachrichten, bei denen der Nutzer die ursprüngliche Nachricht noch nicht erhalten hat. Für die spätere Bearbeitung ist diese Unterscheidung wichtig, da in diesem Fall eine neue Nachricht hinzugefügt werden muss. Besonders beim Neuladen der Seite, wo eine bestimmte Menge von Nachrichten abgefragt wird, kann dieser Block zum Einsatz kommen.
4. Abschließend wird die höchste Aktions-ID des Chat-Raums zurückgegeben, welche als Grundlage für den „last_action“-Parameter dient.

Nach der Abarbeitung dieser Blöcke wird das Ergebnis aufsteigend nach den IDs sortiert und zurück geliefert.