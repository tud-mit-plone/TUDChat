\anchor Funktionalitäten
Funktionalitäten in Plone
-------------------------

\anchor Nachrichten_senden
### Nachrichten senden ###
Eine der grundlegendsten Funktionalitäten eines Chats ist das Übermitteln und Empfangen von Nachrichten. Das Versenden von Nachrichten wird durch folgenden Aufruf realisiert:
Anfrage	          | Parameter          | Antwort für den Benutzer
----------------- | ------------------ | ------------------------
/sendMessage      | - message (String) | keine 

Bevor die Nachricht in der Datenbank hinterlegt wird und somit für alle Nutzer des Chat-Raums verfügbar wird, erfolgen noch einige Prüfungen: Zuerst wird sichergestellt, dass es sich um einen registrierten Benutzer handelt. Nachdem Laden des Benutzernamens und der Chat-ID wird die „userHeartbeat“-Methode aufgerufen, um zu signalisieren, dass der Benutzer den Chat nicht verlassen hat. Nun wird geprüft, dass die Nachricht nicht leer ist. Anschließend wird ermittelt, ob die Nachricht einen gewissen Zeitabstand zur vorherigen Nachricht einhält. Dieser Zeitabstand kann eingestellt werden und soll eine Nachrichtenüberflutung durch einen einzelnen Benutzer verhindern. Danach wird die Nachricht auf ungültige Zeichen, die nicht der UTF-8-Zeichenkodierung entsprechen, geprüft.

Nun wird die Nachricht gekürzt, falls sie zu lang ist. Die maximale Nachrichtenlänge kann in den Chat-Einstellungen konfiguriert werden. Abschließend wird dann die Nachricht in die Datenbank geschrieben. Handelt es sich um einen Moderator, der diese Nachricht gesendet hat, wird dies bei der Übermittlung an die Datenbank entsprechend gekennzeichnet.

\anchor Nachrichten_anfordern
### Nachrichten anfordern ###
Um die aktuellen Nachrichten vom Server zu erhalten wird vom Browser in einem festgelegten Zeitintervall eine Anfrage geschickt. Diese Anfrage sieht wie folgt aus:
Anfrage	          | Parameter          | Antwort für den Benutzer
----------------- | ------------------ | ------------------------
/getActions       | keine              | JSON-formatierte Daten 

Bevor es zur eigentlichen Abfrage von Nachrichten kommt, werden einige Überprüfungen durchgeführt. Zuerst wird sichergestellt, dass der Benutzer nicht gebannt ist. Im Anschluss erfolgt die Prüfung des Registrierungsstatus. Ist der Benutzer registriert und nicht gebannt, wird geprüft, ob eine Verwarnung oder ein Kick-Befehl für den Benutzer vorliegt. Bei einer Verwarnung wird dem Chat-Anwender der entsprechende Verwarn-Text übermittelt (eine Übermittlung von Nachrichten findet nicht mehr statt). Im Falle eines Kicks erhält der Benutzer lediglich die Information über den Rauswurf und wird vom Chat abgemeldet.

Im Anschluss an die nutzerbezogenen Prüfungen wird eine sogenannte „userHeartbeat“-Methode aufgerufen, welche dem System mitteilt, dass der Nutzer noch aktiv ist. Die Methode „checkForInactiveUsers“ wird direkt danach aufgerufen, um nicht mehr aktive Benutzer vom Chat-Raum zu entfernen. Dies ist beispielsweise dann notwendig, wenn der Browser einfach geschlossen wird und somit keine korrekte Abmeldung erfolgt ist. Danach erfolgt eine Prüfung, ob der Chat-Raum noch aktiv ist. Ist dieser nicht aktiv wird der Benutzer abgemeldet. Wird der Chat-Raum innerhalb der nächste fünf Minuten geschlossen wird der Benutzer darüber informiert (falls er noch nicht darüber informiert wurde).

Der nächste Schritt sieht dann das Abrufen der Nachrichten vor. Dabei werden die entsprechen Parameter, wie im „Datenbank“-Kapitel erläutert, übermittelt. Bevor nun die eigentliche Rückgabe erzeugt wird, werden dem Datenbankergebnis bestimmte Attribute hinzugefügt. Diese werden dann später mit zum Client übertragen und können für bestimmte Darstellungen verwendet werden. Zurzeit werden durch diese Attribute Moderatoren-Aktionen und -Nachrichten gekennzeichnet. Nach diesem Schritt wird dann die eigentliche Rückgabe konstruiert. Diese enthält dann die neuen, bearbeiteten und gelöschten Nachrichten, neue und zu löschende Benutzer und den Status. Das detaillierte Schema dieser Antwort wurde bereits im Abschnitt Benutzerinteraktion über den Browser dargestellt und wird daher an dieser Stelle nicht näher erläutert.

Vor der Rückgabe erfolgen noch einige Aktualisierungen. Sollten Aktionen übermittelt worden sein, wird die letzte Aktion aktualisiert. Die benutzerspezifisch gespeicherte Nutzerliste wird ebenfalls aktualisiert. Diese dient dazu, dem Client nur die Änderungen der Benutzer des Chat-Raums mitzuteilen. Die Session wird nur im Falle von Änderungen gespeichert. Abschließend wird die vorbereitete Rückgabe JSON-kodiert an den Client übermittelt.

\anchor Nachrichten_bearbeiten_und_löschen
### Nachrichten bearbeiten und löschen ###
Aufgrund der sehr ähnlichen Vorgehensweise der Methoden zum Löschen und Bearbeiten einer Nachricht, werden diese hier gemeinsam beschrieben. Schließt ein Moderator solche Aktionen ab werden diese Anfragen übermittelt:
Anfrage	          | Parameter                                        | Antwort für den Benutzer
----------------- | ------------------------------------------------ | ------------------------
/editMessage      | - message_id (Integer) <br />- message (String)  | keine 
/deleteMessage    | - message_id (Integer)                           | keine 

Der einzige wesentliche Unterschied beim Methodenaufruf besteht beim „message“-Parameter der „editMessage“-Methode. Dieser existiert bei der „deleteMessage“-Methode nicht, weil beim Löschen einer Nachricht kein neuer Nachrichtentext notwendig ist.

Zu Beginn beider Funktionen wird geprüft, ob es sich beim aufrufenden Benutzer um einen Moderator handelt. Ist dies nicht der Fall, wird die Bearbeitung sofort abgebrochen. Andernfalls wird durch den Aufruf der „userHeartbeat“-Methode signalisiert, dass der Benutzer die Chat-Sitzung nicht verlassen hat. Im Falle der „editMessage“-Funktion wird zur Fortsetzung noch geprüft, ob der „message“-Parameter übergeben wurde. Abschließend wird dann die entsprechende Aktion in die Datenbank geschrieben.

\anchor Benutzer_verwarnen
### Benutzer verwarnen ###
Benutzer könnten aufgrund eventuellen Fehlverhaltens verwarnt werden. Dadurch wählt der Moderator einen Button neben dem Benutzernamen (dargestellt als gelbes Warndreieck).

Durch Klicken dieses Buttons und der Eingabe eines Verwarnungstextes, wird folgende Anfrage gestellt:
Anfrage	          | Parameter                                        | Antwort für den Benutzer
----------------- | ------------------------------------------------ | ------------------------
/warnUser         | - user (String) <br />- warning (String)         | keine 

Dadurch wird ein Eintrag in das interne Dictionary bei dem Schlüssel „warned_chat_users“ angelegt, wodurch dieser beim nächsten Zyklus als verwarnter Benutzer erkannt werden wird. Nach Auslieferung der Verwarnung, wird diese aus dem Chatobjekt entfernt.

\anchor Benutzer_vom_Chat_entfernen_und_sperren
### Benutzer vom Chat entfernen und sperren ###
Um einen Benutzer zu entfernen, erreicht ein Moderator in der Oberfläche einen Button neben dem jeweiligen Benutzernamen (dargestellt als rotes X). Um den Benutzer permanent zu sperren, steht analog ein weiterer Button (rote Fahne) zur Verfügung. Letztlich wird durch das Benutzen dieser Buttons eine der zwei folgenden Anfragen an das Chatobjekt gestellt:
Anfrage	          | Parameter                                        | Antwort für den Benutzer
----------------- | ------------------------------------------------ | ------------------------
/kickUser         | - user (String)                                  | keine 
/banUser          | - user (String) <br />- reason (String)          | keine 

Für das einfache Entfernen aus dem Chat wird einfach die Information beibehalten, dass der Benutzer noch zu entfernen ist.  Dies geschieht im internen Dictionary chat_rooms über den Schlüssel “kicked_chat_users“ als neuer Eintrag in die Liste. Sobald der Benutzer neue Aktionen abfragen  (/getActions) sollte, wird er aus dieser Liste erkannt und entfernt.

Falls der Benutzer permanent entfernt werden soll, geschieht analog ein Eintrag in dasselbe Dictionary, allerdings im Schlüsesel „banned_chat_users“ als neues Dictionary, bei welchem IP-Adresse des Benutzers und der Grund gespeichert werden. Der Benutzer wird anschließend im nächsten Zyklus entfernt.

Falls er sich jetzt wieder einloggen möchte, wird dies gemäß der aktuellen Ban-Strategie erst gar nicht zugelassen. Die Ban-Strategie kann folgende Werte annehmen:
Anfrage               | Bedeutung
--------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Nur Cookie            | Dadurch werden zwei Cookies im Browser des Nutzers gesetzt (tudchat_is_banned, tudchat_ban_reason), die jeweils für 1 Jahr vorhalten. Dieses Verfahren scheitert allerdings, wenn der Nutzer weiß, wie er seine Cookies löscht bzw. diese generell verbietet. 
Nur IP-Adresse        | Über die IP-Adresse wird fortan der gebannte Nutzer erkannt. Dies kann aber potenziell zu Problemen führen, wenn sich mehrere Nutzer dieselbe IP-Adresse teilen. 
IP-Adresse und Cookie | Hier werden beide Verfahren kombiniert. 

Es sollte dabei nicht unerwähnt bleiben, dass beide Verfahren Schwächen aufweisen und kein perfekter Schutz existieren kann.