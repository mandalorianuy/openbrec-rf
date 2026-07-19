> ⚠️ Documento histórico — corresponde a la encarnación Wi-Fi-CSI previa del proyecto. Sin autoridad normativa. Ver [docs/legacy/README.md](README.md).

# Diseño de antenas externas

## Principio
La antena es parte del sensor y debe registrarse y calibrarse. Más ganancia no implica automáticamente más precisión.

## Kit recomendado
- omni dual-band de 3–5 dBi para inventario general;
- panel/patch de 8–12 dBi para sectorización;
- biquad 2.4 GHz para CSI direccional de bajo costo;
- log-periódica para SDR de banda amplia;
- dos antenas iguales por radio MIMO;
- trípode, brújula/inclinómetro y marcas de azimut;
- coaxial corto de baja pérdida, adaptadores SMA/RP-SMA y alivio mecánico.

## Reglas
- minimizar cable; el coaxial largo puede anular la ganancia;
- registrar polarización y orientación;
- calibrar combinación radio-cable-antena;
- no usar amplificadores de potencia;
- LNAs solo en recepción y con filtros adecuados;
- mantener separación y geometría MIMO del fabricante;
- en escombros, comparar omni y direccional antes de concluir.
