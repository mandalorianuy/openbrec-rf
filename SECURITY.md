# Security Policy

OpenBREC RF es un proyecto de sensing defensivo para pruebas autorizadas. El repositorio oficial no acepta implementaciones de deauthentication, jamming, evil twin, phishing, credential capture, cracking, payload interception, emulación celular ni transmisión SDR de campo.

## Reportes
Reportar vulnerabilidades de forma privada al equipo mantenedor antes de publicar detalles. Incluir versión, perfil, impacto, reproducción mínima y mitigación propuesta.

## Privacidad
- Metadata-only por defecto.
- HMAC por incidente para identificadores radio.
- Retención corta y borrado verificable.
- BFI biométrico fuera del perfil operativo inicial.
- Datasets reales requieren revisión y consentimiento.


## UAS safety boundary
OpenBREC is not flight-control software. Vulnerabilities that could trigger payload release, falsify pose, bypass operator confirmation or command an aircraft are critical.

## RF quieting boundary
Report any behavior that could unintentionally suppress emergency communications or infer absence of victims from radio silence.

## RuView/model supply chain
Pin commits, verify hashes and treat model files as untrusted inputs. A parser failure must fail closed and visibly.
