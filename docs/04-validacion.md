# Plan de validación

## Etapas
1. Cámara/entorno controlado sin escombros.
2. Muros simples de ladrillo, hormigón y metal.
3. Caja de escombros instrumentada con maniquí, dispositivos y actuadores respiratorios.
4. Campo BREC de entrenamiento con operadores ciegos al ground truth.
5. Comparación con canes, acústica, cámara y radar comercial.

## Métricas
- sensibilidad por tipo de evidencia;
- tasa de falsos positivos por hora;
- error de zona/posición;
- tiempo a primer indicio;
- estabilidad frente a movimiento de rescatistas;
- robustez tras cambio de antena y geometría;
- disponibilidad y autonomía;
- tasa de abstención correcta;
- tiempo de despliegue y carga cognitiva.

## Diseño experimental
Separar entrenamiento y prueba por día, configuración de escombros, operador y posición de nodos. No aceptar resultados basados solo en random split.
