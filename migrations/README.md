# Migraciones

Esquema de las cuatro destinaciones de disposición (`ingress_units`, `accepted_event_log`, `review_quarantine`, `evidence_vault`, `rejection_ledger`, `audit_events`).

## Fuente de verdad

- **`postgresql/0001_m0_disposition.sql`** es la fuente de verdad de las cuatro destinaciones de disposición. Es la migración que aplica el runtime (`apps/fusion-worker` vía `openbrec/postgres_disposition.py`) y la que valida el gate `postgres-disposition`.
- **`postgresql/0002_fusion_results.sql`** es la fuente de verdad del read model del pipeline: `observations` y `fusion_results` en JSON canónico más columnas de filtrado. La aplica y escribe el worker (`openbrec/fusion_store.py`) y la lee la API (`GET /v1/observations`, `GET /v1/fusion-results`). No guarda material cifrado ni contenido crudo: solo payloads ya validados por contrato.
- **`0001_m0_disposition.sql`** (raíz de este directorio) es una variante **SQLite solo para tests y replay local** (`openbrec/disposition.py`, store efímero en memoria/archivo temporal). No se despliega.

## Diferencias intencionales entre variantes

No son drift accidental: reflejan los dialectos y el alcance de cada store.

- Dialecto: `INTEGER PRIMARY KEY AUTOINCREMENT` vs `BIGSERIAL`; `BLOB` vs `BYTEA`; `INTEGER` vs `BIGINT`.
- `key_id` en `review_quarantine` y `evidence_vault`: existe **solo en PostgreSQL** porque el runtime soporta rotación de claves (`openbrec/keyring.py`, `OPENBREC_MASTER_KEY_ID`) y necesita registrar con qué clave se cifró cada unidad. La variante SQLite deriva una única clave por incidente con HKDF (`DispositionStore._key`) sin rotación, así que no la necesita. Si en el futuro el store SQLite gana rotación, hay que agregar `key_id` y alinear el `UNIQUE(incident_id, key_id, nonce)`.

## Reglas

- Toda columna o tabla nueva nace primero en `postgresql/` y se documenta aquí.
- La variante SQLite solo cambia para sostener los gates de replay/privacidad; no agrega capacidades que el runtime no tenga.
