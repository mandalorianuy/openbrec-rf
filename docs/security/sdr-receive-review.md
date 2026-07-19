# Review de seguridad — recepción SDR (`sdr-receive-profile`)

- Fecha: 2026-07-19
- Alcance: addon experimental `sdr-receive-profile` (decodificación 406 MHz Cospas-Sarsat, DF con array coherente, ocupación de espectro; diseño contractual, sin runtime)
- Autoridad: ADR-004, modos regulatorios de la spec (`receive_only`, `conducted_only`, `jurisdiction_validated`), red lines de ADR-0001
- Base de evidencia: `docs/research/rf-sensing-state-of-the-art.md` §9 y §12
- Veredicto: aceptado como diseño `specified`; ningún perfil SDR ejecutable queda habilitado

## Alcance

Revisión de diseño del perfil de recepción SDR. El caso de uso life-safety central es la decodificación de balizas 406 MHz (ELT/EPIRB/PLB) y la dirección de llegada con array coherente; el DF y la ocupación de espectro apoyan awareness del incidente.

## Amenazas

| ID | Amenaza | Precondiciones | Impacto |
|---|---|---|---|
| SDR-T1 | TX activo en campo: presión para transmitir (prueba, respuesta, interferencia) fuera de banco autorizado. | Hardware SDR capaz de TX; perfil que no fije receive-only. | Violación regulatoria, interferencia perjudicial, daño a otros servicios de emergencia. |
| SDR-T2 | Demodulación de tráfico de terceros: el mismo receptor que decodifica 406 MHz puede sintonizar comunicaciones privadas. | Perfil amplio sin restricción; operador sin guía. | Intercepción ilícita de contenido (UY: orden judicial; §2511), violación de privacidad. |
| SDR-T3 | Baliza falsa o replay: una señal 406 MHz fabricada o retransmitida genera un falso distress. | Actor con TX; ausencia de verificación por doctrina (registro Cospas-Sarsat, corroboración). | Desvío de recursos de rescate. |
| SDR-T4 | Falsa confianza en DF: un bearing con multipath de escombro se presenta como localización. | Error angular no medido; UI que muestre punto en vez de sector con incertidumbre. | Búsqueda mal dirigida. |

## Controles

- **Contrato `sdr-receive-profile`**: `mode: receive_only_in_field` como const — en campo el perfil nunca transmite; cualquier TX de prueba exige `allowed_only_if_regulatory_mode: conducted_only` y `authorized_bench_required: true` (banco autorizado con carga fantasma o recinto medido). `demodulate_third_party_traffic: false` como const.
- **406 MHz como señal pública de distress**: la recepción de balizas Cospas-Sarsat cae del lado pasivo de la línea legal (§2511(2)(g) exceptúa comunicaciones de socorro "readily accessible to the general public"); la coordinación con doctrina CAP/ICAO está en la guía `sdr-beacons.md` — el SDR se coordina con esa doctrina, no la reemplaza.
- **Incertidumbre declarada**: DF con error angular medido por geometría; el perfil declara `array_type: coherent_array` y los casos de uso cerrados; ningún resultado es localización confirmada (pipeline de evidencia del core).
- **Coherencia con red lines**: sin TX activo en SDR en la fase inicial (ADR-0001); sin funciones ofensivas.

## Riesgo residual

- Un implementador con SDR capaz de TX puede ignorar el perfil; el control contractual no bloquea hardware. La mitigación es de gobernanza (perfil, review, SOP) y queda pendiente de runtime.
- La falsificación de balizas no se descarta por contrato; la verificación por registro y doctrina es procedimental, no técnica.
- Cero rescates atribuidos a SDR open-source: la utilidad operacional real es `unverified`.

## Declaración de madurez

Review de **diseño** sobre perfil `specified`. Decodificación 406 MHz y DF con array coherente son `bench-validated` comunitarios; el uso en SAR operacional es `unverified`. Nada de esta review habilita runtime, hardware ni campo.
