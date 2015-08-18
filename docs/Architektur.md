\anchor Architektur
Architektur
-----------

\anchor Übersicht
### Übersicht ###
Der TUDChat ist ein Produkt, welches  aus dem „TUDChat Tool“ und den Content-Typen „TUDChat Content“ besteht. Diese sind jeweils entsprechend ihrer Verantwortung getrennt. Dabei ist das einzigartige Tool für die Anbindung an die Datenbank verantwortlich – in dieser Datenbank werden alle Chatsessions bzw. Chaträume und alle Chat-Aktionen (Nachricht schreiben, bearbeiten und löschen) gespeichert und können später abgerufen werden. Eine Instanz von TUDChat Content beziehungsweise das Chatobjekt wiederum übernimmt die eigentliche Chatfunktionalität, also Konfiguration des Chats, Verwaltung der verschiedenen Chaträume und letztlich die Kommunikation der Chatteilnehmer während des Chats.

\anchor TUDChatTool
### TUDChat Tool ###
Das TUDChat Tool verwaltet die Datenbankanbindungen, welche die Chatobjekte für die Persistenz der Chaträume und Chataktionen nutzen. Nach der erfolgreichen Installation (siehe Kapitel Installation in Plone) können für die Plone-Seite hinterlegten MySQL-Verbindungsobjekte (vom Typ 'Z MySQL Database Connection') von den jeweiligen Chatobjekten genutzt werden.

Dies geschieht indem das Chatobjekt vom Tool all jene IDs der MySQL-Verbindungsobjekte abgefragt werden, die innerhalb des Pfades des Chatobjekts bis zum Wurzelverzeichnis der Plone-Seite vorkommen und vom Administrator freigegeben worden sind (getAllowedDbList). Das Chatobjekt verwendet dann im Anschluss die zurückgegebene ID des MySQL-Verbindungsobjekts, um das ChatStorage-Objekt zu erstellen. Mit dem ChatStorage-Objekt lassen sich über ein eindeutiges Interface  (ITUDChatStorage) konkret die Vorgänge zum Abfragen und Speichern durchführen.
![Kommunikation zwischen Chatobjekt und Chat-Tool](sequence.png)

\anchor TUDChatContent
### TUDChat Content ###
Die Instanzen von „TUDChat Content“ bzw. die Chatobjekte kümmern sich um die eigentliche Chatfunktionalität. Im Groben können folgende Aufgabenfelder unterschieden werden:
- Konfiguration des Chatobjekts
- Verwaltung der Chaträume (einrichten, bearbeiten)
- Interne Verwaltung der Benutzer (deren Zustände, Verwarnungen, Verweise/Bann)
- Benutzerinteraktion mittels JSON-Schnittstelle über den Browser

Dabei ist zu beachten, dass alle Konfigurations- bzw. Verwaltungstechnischen Angelegenheiten erst erreichbar sind, wenn man bestimmte Rollen (Admin, ChatModerator) besitzt. Konkrete Anweisungen diesbezüglich sind im Kapitel Installation in Plone nachzulesen.

Es werden nun folgend alle Aufgaben mit ihren bearbeitbaren Aspekten beschrieben.

#### Die Konfiguration des Chatobjekts ####
Alle Chatobjekte liegen einem Schema zugrunde, welches alle für den Moderator (bzw. Administrator) relevanten Attribute beschreibt. Sie bestimmen das Verhalten für alle Chaträume innerhalb des Chatobjekts. Veränderbare Attribute sind:
- Id (Beschreibt die ID des Objektes)
- Titel (Titel des Chatobjektes)
- Begrüßungstext (Text, der bei der Startseite angezeigt wird)
- Datenbank (Auswahl eines MySQL-Verbindungsobjekts)
- Datenbank-Präfix (Da sich mehrere Chatobjekt eine Datenbank teilen können, besteht hier die Möglichkeit einen einzigartigen Präfix für die Tabellen zu wählen.)
- Zeitstempel an Chatnachrichten? 
- Format des Zeitstempels
 - Uhrzeit
 - Uhrzeit (ohne Sekunden)
 - Datum und Uhrzeit
 - Datum und Uhrzeit (ohne Sekunden)
- Textfarbe für Chatmoderator
- Socket-Timeout (in Sekunden) (Zeit, nach dieser der Benutzer automatisch aus dem Chat entfernt wird, wenn er nicht reagiert)
- Aktualisierungsrate (in Sekunden) (Frequenz in der die Benutzer neue Nachrichten bekommen)
- Maximale Nachrichtenlänge 
- Wartezeit zwischen Nachrichten (in Sekunden)
- Bann-Strategie
 - Nur Cookie
 - Nur IP-Adresse
 - Cookie und IP-Adresse

Die Abbildung zeigt eine Beispielkonfiguration für ein Chatobjekt:
![Konfiguration für einen Chat](chat_config.png)

Folgende Templates und Form-Controller sind hierfür relevant:
Aufgabe                      | Template        | Controller
---------------------------- | --------------- | -------------------------------------------------------------------------------------
Chat-Einstellung bearbeiten  | tudchat_edit.pt | TUDChat.py -> post_validate [setzt neuen TUDChatSqlStorage für neue connector_id auf] 

#### Verwaltung der Chaträume (einrichten, bearbeiten) ####
Chaträume bzw. Chat-Sitzungen sind durch folgende Eigenschaften beschrieben:
- Titel
- Beschreibungstext
- Beginn und Ende der Chat-Sitzung
- Passwort (optional)
- Maximale Benutzer (optional)

Folgende Templates und Form-Controller sind hierfür relevant:
Aufgabe                         | Template         | Controller (alle in TUDChat.py)
------------------------------- | ---------------- | -------------------------------
Chat-Sitzung anlegen            | add_session.pt   | addSessionSubmit 
Chat-Sitzungsübersicht anzeigen | edit_sessions.pt | Keiner notwendig 
Chat-Sitzung bearbeiten         | edit_session.pt  | editSessionsSubmit 

#### Interne Verwaltung der Benutzer (deren Zustände, Verwarnungen, Verweise/Bann) ####
Sämtliche Benutzer werden vom Chatobjekt verwaltet. Dies geschieht vollkommen unabhängig von der Datenbankschnittstelle. Es existieren zwei Orte zur Speicherung der Benutzerdaten: Dies sind zum einen das Attribut des Chatobjekts (chat_rooms), um zu wissen, wer sich in welchem Raum mit welchem Zustand befindet, und zum anderen das Session-Objekt, um den Benutzer und seine Anfragen eindeutig zu identifizieren. In beiden Fällen werden die notwendigen Informationen in Dictionaries gespeichert:
Zum Speichern der Benutzer, die sich in den Chaträumen befinden, wird das Attribut chat_rooms mit folgendem Aufbau verwendet:
- chat_rooms (Dictionary, Schlüssel: chat_uid (int)):
 - „chat_users“ (Dictionary, Schlüssel: Benutzername (String) )
  - „ip_address“ (String) –  IP-Adresse
  - „date“ (DateTime) – Zeitstempel, wann der Chatraum betreten wurde
  - „last_message_sent“ (int) – Zeitstempel der zuletzt geschickten Aktion
  - „is_admin“ (Boolean) – hat der Benutzer Adminrechte?
 - „banned_chat_users“ (Dictionary, Schlüssel: Benutzername (String))
  - „reason“ (String) – Grund für das Bannen
  - „ip_address“ (String) – IP-Adresse
 - „warned_chat_users” (Dictionary, Schlüssel: Benutzername (String) )
  - „warning” (String) – Verwarnungstext
 - „kicked_chat_users“ (Liste, Werte: Benutzernamen (String) )

Die genutzten Datenstrukturen haben folgende Teilfunktionalitäten:
- „chat_users“ klärt wann welcher Benutzer den jeweiligen Raum betreten hat, wie der aktuelle Wissensstand im Chat und ob der Nutzer Moderator ist.
- „banned_chat_users“ bestimmt, welche Benutzer unter welcher IP gebannt worden sind.
- „warned_chat_users“ behält eine Verwarnung solange vor, bis der jeweilige Benutzer seine Aktionen abgefragt hat. Nach Erhalt wird diese Verwarnung gelöscht.
- „kicked_chat_users“ hält eine Liste der Benutzernamen, die vom Chat entfernt werden sollen. Wenn ein Benutzer aus dieser Liste seine Aktionen abfragt, wird er entfernt und der Eintrag wird aus der Liste gelöscht.

Zur Identifikation wird das für jeden Benutzer existierende Session-Objekt (REQUEST.session) mit folgendem Aufbau verwendet: 
- „user_properties“ (Dictionary, Schlüssel: hier folgende Werte (String)):
 - „name“ (String) – Registrierter Benutzername
 - „chat_room“ (int) – Chatraum (aka chat_uid)
 - „user_list“ (Liste von Strings) – Bekannte Benutzer (initial leer) 
 - „start_action“ (int) –Letzte Aktion zum Zeitpunkt des Betretens des Chatsraums Erste erhaltene Aktion im Chat
 - „last_action“ (int) – Zuletzt erhaltene Aktion im Chat
 - „chat_room_check“ (int) – Zeitstempel, um jede Minute zu prüfen, ob der Chat ausläuft.
 - „chatInactiveWarning“ (Boolean) – Benutzer wurde informiert, dass der Chat ausläuft?

Durch die Angaben im Session-Objekt wird außerdem für den Benutzer festgelegt, welche Antworten über die JSON-Schnittstelle zu erwarten sind, zum Beispiel, welche anderen Chatteilnehmer oder Nachrichten neu sind. Der Benutzer wird grundsätzlich nur über Änderungen informiert, die sich seit dem Zeitpunkt des Betretens des Chats (start_action) ergeben haben.

#### Benutzerinteraktion über den Browser ####
Nachdem sich ein Benutzer für einen Raum angemeldet hat, beginnt die Interaktion mit dem Chatobjekt mittels der JSON-Schnittstelle über den Browser. 

Das Page-Template, welches den Chatraum aufbaut, räumt abhängig von der Rolle des Benutzers andere Möglichkeiten ein. Während beispielsweise Benutzer mit der Anonymous-Rolle nur Nachrichten schreiben und Aktionen empfangen können, ist es Benutzern mit den Rollen Administrator oder ChatModerator darüber hinaus möglich, Nachrichten zu bearbeiten und/oder zu löschen und andere Benutzer zu verwarnen oder (dauerhaft) zu entfernen. Dies geschieht, indem unterschiedliche CSS- und JavaScript-Dateien eingebunden werden und damit die Oberfläche verändert wird.

Folgende Dateien sind dafür essentiell für den Client (ausgenommen sind Dritt-Bibliotheken):
Datei                      | Aufgabe(n)                                                                                                          | Alle / Nur Benutzer / Moderator
-------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------
TUDChat_view.pt            | Login-Seite. Raumauswahl.                                                                                           | Alle 
chat.pt                    | Struktur des Chats.                                                                                                 | Alle 
tud_chat.js                | Funktionalität für Nachrichten senden, Aktionen empfangen und interpretieren.                                       | Alle 
tud_chat.css               | Grundlegender Look.                                                                                                 | Alle 
tud_chat_user.js           | Einfache Implementierung der Funktionen zur Erzeugung von Nachrichten- und Teilnehmereinträgen.                     | Nur Benutzer 
tud_chat_admin.js          | Erweitert Nachrichten- und Teilnehmereinträge mit Admin-Buttons und liefert die dazugehörige Logik zur Interaktion. | Nur Moderator 
tud_chat_admin.css         | Notwendiges CSS für die Moderatoren-Elemente.                                                                       | Nur Moderator 
tud_chat_additional.css.py | Generierte CSS, die Farben und andere Details aus der Chat-Konfiguration liefern kann.                              | Alle 

Daneben werden weitere jQuery-Bibliotheken verwendet, um die Chatfunktionalität zu gewährleisten:
- jquery.notification.js  (für Popups, die im Gegensatz zu den Standardpopups nicht blockieren)
- jquery.ba-dotimeout.min.js (komfortablere Timeout-Erweiterung)

Die verwendeten Grafiken unterstehen der Lizenz „Creative Commons Attribution (by)“  und wurden von Bdate Kaspar/Franziska Sponsel erstellt .

Relevante Variablen aus der Chatkonfiguration werden direkt in das Template als globale JavaScript-Variablen zur Verfügung gestellt (z.B.:  die Blockzeit zwischen den Nachrichten). 

Der Teilnehmer informiert sich periodisch über seinen Status und holt neue Aktionen ab. Auf der Clientseite werden diese Eingaben anschließend interpretiert.  Die Ausgabe ist ein JSON-Objekt, bestehend aus einer zwingenden Status-Property („status“), welches aus einem Code als Integer und einem für den Benutzer verständlichen Nachricht besteht, der gegebenenfalls verwendet werden kann.

Grundsätzlich sind alle Antworten, die mit JSON dargestellt werden, wie folgt strukturiert:

    {
      'status':{ 
        'code': integer,              // Statuscode als Integer
        'message': string             // Menschenlesbare Nachricht
      },
      ...                             // .. Abhängig vom Status können hier
                                      //    mehr Properties erscheinen.
    }

Der Status-Code kann folgende Werte annehmen:
Status-Code        | Bedeutung                                             | Konsequenz
------------------ | ----------------------------------------------------- | -------------------------------
OK (0)             | Alles in Ordnung.                                     | Empfangene Aktionen werden interpretiert. 
NOT_AUTHORIZED (1) | Benutzer ist nicht autorisiert.                       | Benutzer wird zum Chat-Eingang verwiesen. 
KICKED (2)         | Benutzer soll entfernt werden.                        | Benutzer wird entfernt. 
BANNED (3)         | Benutzer soll permanent entfernt werden.              | Benutzer wird unter Angabe eines Grundes permanent entfernt. 
LOGIN_ERROR (4)    | Es gab einen Fehler beim Login.                       | Benutzer wird über den Grund informiert, warum der Login scheiterte und verbleibt auf der Login-Seite. 
WARNED (5)         | Benutzer soll verwarnt werden.                        | Benutzer erhält eine Verwarnung als Popup. 
CHAT_WARN (6)      | Benutzer soll dezent (im Chatfenster) gewarnt werden. | Benutzer erhält eine Warnung als Nachricht in einem Popup. 

Das Chatobjekt kann nur einen Status pro Antwort liefern. Je nach Status haben gewisse Antworten Vorrang und erreichen den Benutzer eher als andere. Die Sortierung nach der Nachrichten eines gewissen Status ausgeliefert werden ist: BANNED, NOT_AUTHORIZED, WARNED, KICKED, OK.

Es ist zu beachten, dass nur bei der Anfrage /getActions  und dem „OK“-Status die Antwort um weitere Properties erweitert wird. Die erweiterte Antwort hat folgende Struktur:

    {
      'status':{ 
        'code': integer,                       // Statuscode als Integer
        'message': string                      // Menschenlesbare Nachricht
      },
      'messages':{				
        'new': [ {                             // Liste von neuen Nachrichten (optional)
          'id': integer,                       // ID der Nachricht
          'date': string,                      // Lesbares Datum
          'name': string,                      // Verfasser der Nachricht
          'message': string,                   // Eigentliche Nachricht
          'attributes':[                       // Liste von Attributen
            attr1,                             // Attribut 1 als JavaScript-Objekt
            attr2,                             // Attribut 2 als JavaScript-Objekt
            ...                                // .. weitere Attribute
          ],				
        }, ... ],                              // .. weitere neue Nachrichten
        'to_delete': [ {                       // Liste zu löschende Nachrichten (optional)
          'id': integer,                       // ID der Nachricht
          'date': string,                      // Lesbares Datum
          'name': string,                      // Verfasser der Nachricht
          'attributes':[                       // Liste von Attributen
            attr1,                             // Attribut 1 als JavaScript-Objekt
            attr2,                             // Attribut 2 als JavaScript-Objekt
            ...                                // .. weitere Attribute
          ],		
        }, ... ],                              // .. weitere zu löschende Nachrichten
       'to_edit': [ {                          // Liste von bearbeiteten Nachrichten(optional)
          'id': integer,                       // ID der zu bearbeitenden Nachricht
          'date': string,                      // Lesbares Datum
          'name': string,                      // Verfasser der Nachricht
          'message': string,                   // Bearbeitete Nachricht
          'attributes':[                       // Liste von Attribut
            attr1,                             // Attribut 1 als JavaScript-Objekt
            attr2,                             // Attribut 2 als JavaScript-Objekt
            ...                                // .. weitere Attribute
          ],
        }, ... ],                              // .. weitere zu bearbeitende Nachrichten
      },
      'users':{
        'new': [ {                             // Liste von neu hinzuzufügenden Benutzern 
          'name': string,                      // Name des neuen Benutzers
          'is_admin': boolean,                 // Ist der Nutzer Moderator?
        } ... ],                               // .. weitere hinzuzufügende Benutzer
        'to_delete': [                         // Liste von zu löschenden Benutzern
          string,
          string,
          ...
        ]
      }
    }

Dieses JSON-Objekt wird sukzessive verarbeitet und entsprechend werden die Nachrichten- und Teilnehmer-Listen des Clients aktualisiert.