# Modelo TCO y auditoría de supuestos

**Fecha de revisión de fuentes**: 2026-11-11  
**Horizonte para fórmulas**: 12 meses (365 días cuando se calcule electricidad)  
**Moneda de trabajo**: EUR, salvo precios de proveedor expresados en USD  
**Estado**: modelo de escenarios; no es factura, cotización ni coste real del proyecto.

## Auditoría de las cifras publicadas

| Afirmación anterior | Comprobación | Estado y tratamiento |
|---|---|---|
| VPS: 24 €/mes; 288 €/año | `24 × 12 = 288` | Aritmética correcta. No hay proveedor, SKU, región, IVA, compromiso ni cotización que confirme el precio y el tamaño 2 vCPU/4 GB. |
| ngrok: 8 €/mes; 96 €/año | `8 × 12 = 96` | Aritmética correcta, precio no confirmado. La página actual muestra planes/consumo distintos; no respalda esa tarifa. |
| Backups: 18,50 €/año | No se especifica almacenamiento, GB-mes, operaciones, redundancia o proveedor | No verificable; retirar del coste confirmado. |
| Netlify: 0 € | Existe plan gratuito en página consultada | Solo precio nominal del plan. La página actual usa créditos/uso; no confirma que la carga estimada permanezca dentro de cuota. |
| Hardware: 900 € amortizados a 2 años = 450 €/año | `900 / 2 = 450` | Aritmética correcta; precio, vida útil, residual e impuestos son supuestos no cotizados. |
| Electricidad: 45 W × 24 × 365 = 394,2 kWh; a 0,30 €/kWh = 118,26 € | Ambas operaciones correctas | Precio de energía y consumo sostenido no medidos ni ligados a ubicación/contrato; solo escenario. |
| Fibra local: 30 €/mes = 360 €/año | `30 × 12 = 360` | Aritmética correcta; no hay ISP, tarifa, IP fija o SLA citado. |
| Trabajo: 24 h × 50 € = 1.200 €; 48 h × 50 € = 2.400 € | Productos correctos | Horas y tarifa son hipótesis, no parte de una hoja de horas o nómina observada. |
| Ingesta: 1.440 × 80 KB/día y ~42 GB/año | Con KB/GB decimales: 42,048 GB/año | Correcto bajo tamaño fijo de 80 KB/respuesta y una descarga cada minuto; el tamaño real debe medirse desde respuestas/compression. |
| Egress API: 250 MB/día y 91 GB/año | `250 MB × 365 = 91,25 GB` | Conversión correcta; 50 usuarios concurrentes y bytes por respuesta no se midieron. Implica ~3,47 KB por cada uno de 72.000 requests/día. |
| Totales: cloud 1.602,50 €/año; local 3.373,26 €/año | Suma de los componentes no verificados descritos en el documento anterior | Aritmética correcta bajo esos supuestos, no TCO confirmado. Mensual cloud 133,54 €; mensual local 281,11 € redondeado comercialmente (valor exacto 281,105 €). |
| Cloud 52% más barato; personal 75% del coste | `(3373,26−1602,50)/3373,26 = 52,49%`; `1200/1602,50 = 74,88%` | Cocientes aritméticamente correctos, pero heredan supuestos no verificados; retirar como conclusión operativa. |
| 100M filas × 212 B = 21,2 GB; 10,4 GB de índices; +30% ≈42 GB | `21,2 + 10,4 = 31,6 GB`; `31,6 × 1,3 = 41,08 GB`, redondeado a 42 | La multiplicación se verifica; tamaños de fila/índices y margen no se midieron ni derivan del DDL completo. No usar como dimensionamiento. |

## Referencias externas consultadas

Fuentes consultadas el **2026-11-11**; los precios, planes y páginas pueden
cambiar. Ninguna referencia es una oferta aceptada para esta arquitectura.

| Componente | Referencia y dato que respalda | Lo que no respalda |
|---|---|---|
| VPS / cómputo | [Hetzner Cloud](https://www.hetzner.com/cloud/): la página mostraba categorías desde 5,49 €/mes y 5,99 €/mes (excl. IVA), y General Purpose dedicado desde 36,99 €/mes. | No acredita 24 €/mes para una VM de 2 vCPU/4 GB/80 GB ni disponibilidad de un SKU/ubicación concretos. Hay que seleccionar SKU y sumar IPv4/backup/IVA según proceda. |
| Túnel | [ngrok Pricing](https://ngrok.com/pricing): la página listaba Free a $0 con crédito único y Pay-as-you-go con $20 de crédito mensual incluido, además de cuotas de transferencia/requests indicadas en la página. | No confirma el antiguo “Pro 8 €/mes” ni un coste anual de 96 €. El coste real depende del plan y uso medido. |
| Hosting frontend | [Netlify Pricing](https://www.netlify.com/pricing/): página consultada indicaba Free $0/300 créditos, Personal $9/mes y Pro $20/mes, con costes de uso por créditos. | No confirma un límite universal de 100 GB/mes ni coste cero para tráfico/deploys ilimitados. Debe calcularse consumo contra créditos y tarifas vigentes. |
| Electricidad UE | [Eurostat, Electricity price statistics](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Electricity_price_statistics): extracción publicada en octubre 2026; precios H1 2026 varían por país y clase de consumidor (p. ej. banda hogar y no hogar se publican separadamente). | No es tarifa contratada en la ubicación del servidor. Los 0,30 €/kWh siguen siendo un supuesto de escenario, no media universal ni gasto del proyecto. |

## Modelo que debe rellenarse para una estimación aplicable

Calcular por escenario, fecha, región, IVA y moneda fijados:

```text
TCO_12m =
  12 × (compute_month + managed_storage_month + tunnel_month
        + frontend_month + domain_month + monitoring_month)
  + storage_gb_month × storage_rate
  + egress_gb × egress_rate
  + request_units × request_rate
  + (power_watts / 1000) × hours_on × electricity_rate
  + hardware_capex / useful_life_years
  + maintainer_hours × loaded_hourly_rate
```

Registrar como mínimo: SKU/region y captura o exportación del calculador;
GB-mes/retención y política de backup; requests, bytes/respuesta, usuarios y
egress medidos; potencia media con vatímetro; tarifa eléctrica/ISP y SLA
locales; dominio, impuestos, cambio USD/EUR y fecha; horas reales o escenarios
de mantenimiento con coste laboral cargado. No sumar dos veces un coste
incluido (p. ej. electricidad en tarifa de nube o bandwidth dentro de créditos).
Separar un escenario base de límites de cuota y un escenario de pico.

Los free tiers reducen o difieren cargos mientras se cumplen sus condiciones;
no garantizan capacidad, SLA, persistencia, límites ni coste marginal cero en
producción.

