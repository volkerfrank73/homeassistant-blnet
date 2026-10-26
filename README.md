# BLNET für Home Assistant

Custom Integration für das **BL-NET** von Technische Alternative (TA). Sie liest
über die Weboberfläche des BL-NET die Werte des angeschlossenen Reglers
(z. B. UVR1611) und kann dessen digitale Ausgänge schalten.

Die Kommunikation läuft über die Bibliothek
[pyblnet-async](https://github.com/volkerfrank73/pyblnet-async).

## Funktionen

| Plattform | Inhalt |
|---|---|
| `sensor` | Analoge Werte (Temperaturen u. a.), Einheit und Name kommen vom BL-NET. Werte in °C erhalten die Geräteklasse Temperatur. |
| `binary_sensor` | Digitale Eingänge, nur lesend. |
| `switch` | Pro digitalem Ausgang zwei Schalter, siehe unten. |

Neue Kanäle, die das BL-NET später meldet, werden automatisch ergänzt.

### Schalter der digitalen Ausgänge

Für jeden Ausgang gibt es zwei Schalter. Beide tragen den Namen des Ausgangs
aus dem BL-NET; Home Assistant hängt deshalb an die Entity-ID des zweiten ein
Suffix an.

- **Ausgang** (unique_id `blnet_switch_<n>`): schaltet den Ausgang ein oder aus
  und setzt ihn dabei in den Handbetrieb.
- **Automatik** (unique_id `blnet_mode_switch_<n>`): *Ein* gibt den Ausgang an
  den Regler zurück (AUTO). *Aus* wechselt in den Handbetrieb und behält den
  aktuellen Schaltzustand bei.

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

Das Abfrageintervall lässt sich später über *Konfigurieren* ändern.

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
  "pyblnet-async @ git+https://github.com/volkerfrank73/pyblnet-async@v0.1.1"
pytest
```

Neue Versionen werden als GitHub-Release mit Tag `vX.Y.Z` veröffentlicht; die
Version in `custom_components/blnet/manifest.json` muss dazu passen.

## Lizenz

[MIT](LICENSE)
