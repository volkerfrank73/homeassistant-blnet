# BLNET für Home Assistant

Custom Integration für das **BL-NET** von Technische Alternative (TA). Sie liest
über die Weboberfläche des BL-NET die Werte des angeschlossenen Reglers
(z. B. UVR1611) und kann dessen digitale Ausgänge schalten. Optional liest sie
zusätzlich über den TA-Port (Direktport) Werte, die die Weboberfläche nicht
zeigt.

Die Kommunikation läuft über die Bibliothek
[pyblnet-async](https://github.com/volkerfrank73/pyblnet-async).

## Funktionen

| Plattform | Inhalt |
|---|---|
| `sensor` | Analoge Werte (Temperaturen u. a.), Einheit und Name kommen vom BL-NET. Werte in °C erhalten die Geräteklasse Temperatur. |
| `binary_sensor` | Digitale Eingänge, nur lesend. |
| `switch` | Pro digitalem Ausgang zwei Schalter, siehe unten. |

Neue Kanäle, die das BL-NET später meldet, werden automatisch ergänzt.

### Datenquelle: Weboberfläche, TA-Port oder beides

Unter *Konfigurieren* → **Datenquelle**:

| Datenquelle | Inhalt |
|---|---|
| Nur Weboberfläche (Standard) | wie oben |
| Weboberfläche und TA-Port | wie oben, dazu vom TA-Port nur, was im Web fehlt: Eingänge wie Durchfluss, Wärmemengenzähler und Ausgänge, die das Web nicht listet |
| Nur TA-Port | alle Werte über den TA-Port, **nur lesend**: keine Schalter, Ausgänge als `binary_sensor` |

Zusätzliche Entitäten über den TA-Port:

| Plattform | Inhalt | unique_id |
|---|---|---|
| `sensor` | Eingänge mit Messwert (Temperatur, Durchfluss in L/h, …) | `blnet_sensor_blnet analog <n>`, wie die Web-Sensoren |
| `binary_sensor` | digitale Eingänge, nur im Modus „Nur TA-Port“ und nur mit Namen (siehe unten) | `blnet_digital_input_<n>`, wie im Web |
| `sensor` | Wärmemengenzähler, nur aktive: Leistung (kW) und Wärmemenge (kWh, `total_increasing`, für das Energie-Dashboard geeignet) | `blnet_direct_heat_meter_<n>_power`, `…_energy` |
| `binary_sensor` | Schaltzustand der Ausgänge A1–A13 (mit Web nur die dort nicht gelisteten) | `blnet_direct_output_<n>` |

Eingänge behalten beim Wechsel zwischen Weboberfläche und TA-Port ihre
`unique_id` und damit Entity-ID und Verlauf. Die Schalter gibt es nur mit der
Weboberfläche; im Modus „Nur TA-Port“ bleiben sie in der Registry stehen und
sind nicht verfügbar.

Fällt der TA-Port bei „Weboberfläche und TA-Port“ aus, werden nur seine
Entitäten `unavailable`. Unterstützt ist nur der Logging-Modus CAN. Der
TA-Port ist eine eigene Verbindung und kollidiert nicht mit der Sitzung der
Weboberfläche.

### Namen der Eingänge und Ausgänge

Der TA-Port liefert keine Namen. Im Feld **Namen** steht je Zeile ein Eingang
oder Ausgang:

```text
S1 = Temperatur Kollektor
S2 = Heizpumpe Freigabe
A6 = Heizkreis Pumpe
```

Beim ersten Öffnen ist das Feld mit den Namen der Weboberfläche vorbelegt. Die
Namen gelten für alle Entitäten, auch die aus der Weboberfläche; ohne Eintrag
gilt der Name der Weboberfläche bzw. ein Standardname wie „Durchfluss S16“.
Eine in Home Assistant umbenannte Entität behält ihren Namen.

Eine UVR1611 meldet digitale Eingänge am TA-Port so, dass ein ausgeschalteter
Eingang nicht von einem unbenutzten zu unterscheiden ist. Im Modus „Nur
TA-Port“ werden digitale Eingänge deshalb nur angelegt, wenn sie hier einen
Namen haben.

### Datenspeicher nach Abruf löschen

Die Option **Datenspeicher des BL-NET nach Abruf löschen** löscht nach jedem
erfolgreichen Abruf über den TA-Port die im BL-NET aufgezeichneten Daten (wie
die Option `reset` von pyblnet). Diese Daten nutzt z. B. Winsol; sie lassen
sich nicht wiederherstellen. Nach einem fehlgeschlagenen Abruf wird nichts
gelöscht. Standard: aus.

## Installation

### HACS (empfohlen)

1. HACS → Menü → *Benutzerdefinierte Repositories*
2. Repository `https://github.com/volkerfrank73/homeassistant-blnet`,
   Kategorie *Integration* hinzufügen.
3. *BLNET* herunterladen und Home Assistant neu starten.

### Manuell

Den Ordner `custom_components/blnet` nach `/config/custom_components/blnet`
kopieren und Home Assistant neu starten.

## Einrichtung

*Einstellungen → Geräte & Dienste → Integration hinzufügen → BLNET*

| Feld | Bedeutung |
|---|---|
| Host | IP-Adresse oder Hostname des BL-NET |
| Passwort | Passwort der Weboberfläche, leer lassen, wenn keines gesetzt ist |
| Port | Port der Weboberfläche, Standard `80` |
| CAN-Knoten | optional (1–62), leer = aktiver Knoten des Geräts |
| Abfrageintervall | in Sekunden, Standard `60`, mindestens `15` |

Über *Konfigurieren* lassen sich später Abfrageintervall, Datenquelle,
TA-Port (Standard des BL-NET `40000`), Namen und das Löschen des Datenspeichers
einstellen. Beim Speichern wird der TA-Port geprüft, sofern er genutzt wird.

**Hinweis:** Das BL-NET erlaubt nur eine Sitzung gleichzeitig. Ist die
Weboberfläche anderswo geöffnet, schlägt die Anmeldung fehl.

### Umstieg von der YAML-Konfiguration

Eine vorhandene YAML-Konfiguration der älteren BLNET-Integration wird beim Start
einmalig als Config-Entry importiert:

```yaml
blnet:
  resource: http://192.168.0.250
  password: !secret blnet_password
  web_port: 80
  can_node: 1
  scan_interval: 60
```

Die `unique_id`s der Entitäten entsprechen der alten Integration, Entity-IDs,
Namen und Registry-Einstellungen bleiben dadurch erhalten. Nach dem
erfolgreichen Import kann der `blnet:`-Block aus der `configuration.yaml`
entfernt werden. Schlägt der Import fehl, steht der Grund im Log; die
Integration dann über die Oberfläche hinzufügen.

## Entwicklung

```bash
python -m venv .venv
source .venv/bin/activate
pip install pytest-homeassistant-custom-component \
  "pyblnet-async @ git+https://github.com/volkerfrank73/pyblnet-async@v0.2.0"
pytest
```

Neue Versionen werden als GitHub-Release mit Tag `vX.Y.Z` veröffentlicht; die
Version in `custom_components/blnet/manifest.json` muss dazu passen.

## Lizenz

[MIT](LICENSE)
