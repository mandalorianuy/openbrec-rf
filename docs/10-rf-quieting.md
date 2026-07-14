# RF Quieting: cortinas, carpas y recintos de atenuación

## Objetivo

Reducir interferencia externa o separar emisiones propias durante una medición específica. No se usa para afirmar ausencia de víctimas ni para bloquear comunicaciones de manera prolongada.

## Diseños

### A. Cortina sectorial

Dos o tres paneles conductores colocados entre una fuente urbana dominante y el sector. Es la primera opción porque pesa menos, conserva acceso y permite comparar orientaciones.

### B. Carpa parcial

Estructura plegable con paredes conductoras y techo, sin piso. Útil para gateway, calibración o enlaces controlados.

### C. Recinto completo

Paredes, techo, piso, costuras y feedthroughs conductivos. Solo laboratorio o equipamiento; su montaje y medición son más exigentes.

## Medición

Cada configuración genera un `IsolationProfile`:

- banda/frecuencia;
- atenuación mediana y percentiles;
- posición Tx/Rx;
- polarización;
- costuras abiertas/cerradas;
- piso y feedthrough;
- fotografías y hash de configuración;
- fecha y operador.

## Reglas BREC

- mantener comunicación de seguridad independiente;
- anunciar ventana de quieting;
- medir baseline antes y después;
- abortar si interfiere coordinación o dispositivos críticos;
- nunca envolver un sector con posible víctima sin análisis de impacto;
- registrar toda observación bajo `isolation_profile_id`.

## Referencias comerciales y técnicas

- Portable shielded enclosures: https://select-fabricators.com/portable-shielded-enclosures/
- TitanRF fabric: https://mosequipment.com/products/titanrf-faraday-fabric
- IEEE Std 299: métodos de medición de efectividad de blindaje.
