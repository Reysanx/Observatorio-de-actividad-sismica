# Modelo de costes TCO

> **Estado de evidencia (2026-11-11):** Las cifras detalladas que aparecían en
> versiones anteriores eran un escenario aritmético con precios y cargas sin
> fuente/cotización. No representan facturas del proyecto ni un coste anual
> verificado. La auditoría, fuentes oficiales, fecha de consulta y formulario de
> supuestos se mantienen en
> [specs/005-benchmarks-y-tco-reproducibles/tco-model.md](../specs/005-benchmarks-y-tco-reproducibles/tco-model.md).

## Lectura correcta de la estimación anterior

Las operaciones aritméticas se comprobaron: el escenario cloud `1.602,50
€/año` suma `288 + 96 + 18,50 + 1.200`; el escenario local `3.373,26 €/año`
suma `450 + 118,26 + 360 + 45 + 2.400`. Las multiplicaciones individuales de
amortización, electricidad, horas de mantenimiento, ingesta y egress también
son reproducibles con los datos asumidos.

Sin embargo, no hay factura, SKU/región, oferta de ISP, medición de potencia,
backup, dominio, uso de API, hoja de horas o tarifa laboral que confirme esos
inputs. Por tanto, los totales, los `133,54 €/mes` y `281,10 €/mes`, el ahorro
del 52% y la proporción de coste humano son **cálculos condicionales, no
resultados confirmados**. El mensual local exacto es `3.373,26 / 12 =
281,105 €` y debe redondearse según la regla contable elegida.

Las páginas de planes actuales tampoco respaldan ciertos límites publicados
anteriormente: las páginas consultadas de Netlify presentan un sistema de
créditos (no un límite universal de 100 GB), y ngrok presenta planes/créditos
distintos del antiguo “Pro 8 €/mes”. El precio mínimo anunciado de un proveedor
no confirma un SKU con capacidad suficiente para los cinco contenedores.

## Componentes a estimar antes de declarar un TCO

1. **Cómputo y almacenamiento**: SKU, región, sistema operativo, disco,
   snapshots/backups, retención, redundancia, impuestos y compromiso.
2. **Red y SaaS**: tráfico egress medido, número/tamaño de respuestas, requests,
   proveedor de túnel, dominio, plan/CDN, cuotas y tarifas por exceso.
3. **Operación local**: vatios medios medidos, horas de encendido, tarifa
   eléctrica e ISP con la ubicación, SAI y mantenimiento.
4. **Trabajo humano**: horas observadas o rango por tarea y tarifa cargada
   (salario, impuestos y beneficios) explícitos.
5. **Ventana y moneda**: 12 meses, fecha de precios, moneda, tipo de cambio e
   IVA; no sumar por separado conceptos incluidos en otra tarifa.

Para referencias fechadas, auditoría de cada número histórico, fórmulas y
plantilla de cálculo, consultar el [modelo TCO de la spec 005](../specs/005-benchmarks-y-tco-reproducibles/tco-model.md).

Los planes gratuitos pueden servir para pruebas bajo cuotas, condiciones y
disponibilidad limitadas; no demuestran coste marginal cero, capacidad o SLA
de producción.
