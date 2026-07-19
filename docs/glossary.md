# Glosario

Términos clave de OpenBREC. Los identificadores de contrato se conservan en inglés; la definición normativa de cada uno vive en la [Open Spec](open-spec/README.md) y en [`schemas/`](../schemas/).

## Contratos y envelopes

- **envelope (`TransportEnvelope`):** unidad que viaja por cualquier bearer conservando identidad, prioridad, autenticidad, deduplicación y semántica. El transporte mueve envelopes; no entiende su contenido.
- **overlay:** la capa OpenBREC por encima de los transportes. OpenBREC no define radio propia: es un overlay sobre bearers reemplazables.
- **bearer:** transporte físico/lógico que mueve envelopes (Meshtastic, MeshCore, Reticulum, LoRaWAN, carry bundle). Se considera no confiable para identidad y aceptación.
- **carry bundle:** fallback de transporte por medio físico (alta latencia, sin RF) para particiones prolongadas.
- **adapter:** componente versionado que conecta un bearer, sensor o fuente de energía con el overlay, fijando upstream y límites. Nace `unverified`.
- **`HumanMessage`:** mensaje del plano humano (texto breve, estado, SOS, ubicación) con lifecycle append-only que distingue recepción técnica de aceptación operativa.
- **`Observation`:** dato de sensor o beacon con timestamp, zona, provenance, unidad, incertidumbre, health y sensores ausentes declarados.
- **fusion result (`FusionResult`):** salida de la fusión determinística: un indicio con confianza y fuentes, o `abstained` con razones. Nunca confirma presencia ni ausencia.
- **`VictimRecord`:** registro de persona localizada/extraída/trasladada, creado sólo por confirmación humana, con revisiones append-only y triage START opcional.
- **`actor_device_binding`:** vínculo verificable `actor_id` ↔ `device_id` con atestación Ed25519; base de la identidad por incidente.

## Evidencia y operación

- **abstención (abstention):** producir `unknown` ante evidencia insuficiente en lugar de inferir. Regla normativa, no fallo.
- **provenance:** registro de origen y cadena de custodia de cada dato: quién/qué lo produjo, cuándo y con qué incertidumbre.
- **handling policy:** política declarada de acceso, retención y disposición de datos sensibles o de distress.
- **evidence pack:** paquete que vincula un claim físico a una combinación exacta (versión, configuración, hardware, entorno, protocolo, resultados, límites). Única vía para elevar a `bench-validated` o `field-validated`.
- **replay:** ejecución determinística desde fixtures/journals grabados que reproduce decisiones del pipeline sin hardware.
- **gate:** verificador ejecutable de la spec (`openbrec.verify <gate>`); los 8 gates componen la conformidad de `1.0.0-draft.1`.
- **receipt:** comprobante determinístico de una ejecución (comando, SHA, resultado) que sustenta un claim `simulated`.
- **ResponseCell:** celda operativa mínima autónoma: varios operadores, gateway local, persistencia y beacons opcionales.
- **plano humano / máquina / evidencia / federación:** los cuatro planos operativos. Humano: mensajería y SOS. Máquina: energía, health, telemetría. Evidencia: journals, provenance, replay, review. Federación: sincronización eventual entre niveles, cada uno operativo sin el superior.

## Estados de evidencia

- **`specified`:** contrato y criterios definidos; no implica ejecución.
- **`simulated`:** ejecutado con datos o entorno sintético reproducible.
- **`bench-validated`:** ensayado físicamente en banco para la configuración declarada.
- **`field-validated`:** ensayado en campo bajo el perfil y condiciones declarados.
- **`unsupported`:** fuera del contrato o deliberadamente no soportado.
- **`unverified`:** sin evidencia suficiente para asignar otro estado.
