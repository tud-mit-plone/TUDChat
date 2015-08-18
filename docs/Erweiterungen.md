\anchor Erweiterungsmöglichkeiten
Erweiterungsmöglichkeiten
-------------------------

TUDChat lässt sich einfach erweitern. Dazu ist es hilfreich sich mit der Struktur des TUDChats vertraut zu machen:
![Verzeichnisstruktur des Chats](folders.png)

Für Erweiterungen relevante Dateien und Ordner:
Datei / Ordner                   | Beschreibung
-------------------------------- | -------------------------------------------------------------
/                                | Wurzelverzeichnis 
/config.py                       | Konfiguration des TUDChat –Tools und Content Types. 
/core                            | Implementierung, Interfaces und Schema-Informationen 
/core/InteractionInterface.py    | Schnittstelle die ein TUDChat-Objekt erfüllen muss. 
/core/TUDChat.py                 | Implementierung des Interaktionsinterfaces 
/core/schemata.py                | Beschreibung der veränderlichen Attribute 
/core/PersistenceInterface.py    | Schnittstelle zur persistenten Speicherung. 
/core/TUDChatSqlStorage.py       | Implementierung des Persistenzinterfaces auf Basis von MySQL. 
/core/TUDChatTool.py             | Chat-Tool-Implementation 
/Extensions                      | Installationsroutine (Einstellung der Rechte) 
/skins/.../TUDChat               | Verzeichnis für wichtige Ressourcen 
/skins/…/TUDChat/tud_chat_css    | CSS-Verzeichnis (auch von Dritt-Bibliotheken) 
/skins/…/TUDChat/tud_chat_images | Bilder-Verzeichnis 
/skins/…/TUDChat/tud_chat_js     | JavaScript-Verzeichnis 
/skins_tool                      | Templates für das Chat-Tool 