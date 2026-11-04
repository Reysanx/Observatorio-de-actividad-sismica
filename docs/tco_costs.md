# INFORME DE COSTE TOTAL DE PROPIEDAD (TCO) Y VIABILIDAD ECONÓMICA
## Observatorio de Actividad Sísmica · Resultado de Aprendizaje 1 (RA1)

> **Materia:** Sistemas de Big Data & Inteligencia Artificial  
> **Criterio de Evaluación:** Criterio 5 — Reflexión Crítica y Análisis Financiero de Producción (Sobresaliente 9–10)  
> **Entregable:** E-07 (`docs/tco_costs.md`)

---

## 1. Introducción y Metodología TCO

El análisis de **Coste Total de Propiedad (*Total Cost of Ownership - TCO*)** permite evaluar de forma rigurosa la viabilidad económica y operativa de una arquitectura de Big Data. Un error común en proyectos académicos y de ingeniería temprana consiste en asumir que utilizar la capa gratuita (*Free Tier*) de proveedores cloud equivale a operar a "coste cero".

En este informe se cuantifican todos los vectores de coste reales para un horizonte temporal de **1 año (365 días)** bajo dos escenarios de producción:
1. **Escenario A: Arquitectura Cloud Híbrida / Desacoplada (Producción actual del proyecto)** — Backend en servidor dedicado/VPS con túnel ngrok reservado y Frontend estático en Netlify CDN.
2. **Escenario B: Despliegue 100% On-Premise / Servidor Local Corporativo** — Hardware dedicado local con enlace simétrico de fibra y SAI (*UPS*).

---

## 2. Desglose Detallado de Costes Operativos (1 Año)

```
+---------------------------------------------------------------------------------------------------------+
|                                  MATRIZ COMPARATIVA DE COSTES ANUALES (TCO)                             |
+------------------------------------+----------------------------------+---------------------------------+
| Categoría de Coste                 | Escenario A: Cloud / Híbrido     | Escenario B: On-Premise Local   |
+------------------------------------+----------------------------------+---------------------------------+
| 1. Cómputo e Infraestructura       | 288,00 € (VPS 2 vCPU, 4GB RAM)   | 450,00 € (Amortización hardware)|
| 2. Consumo Eléctrico               | Incluido en el VPS               | 118,26 € (45W @ 0,30 €/kWh)     |
| 3. Conectividad y Red (Egress)     | 96,00 € (ngrok Pro / Dominio)    | 360,00 € (Línea IP fija simét.) |
| 4. Almacenamiento y Backups S3     | 18,50 € (Postgres + Snapshots)   | 45,00 € (Discos NAS RAID 1)     |
| 5. Frontend & CDN (Netlify)        | 0,00 € (Tráfico dentro de cuota) | 0,00 € (Nginx local)            |
| 6. Mantenimiento Humano (DevOps)   | 1.200,00 € (24h/año @ 50 €/h)    | 2.400,00 € (48h/año @ 50 €/h)   |
+------------------------------------+----------------------------------+---------------------------------+
| TOTAL COSTE ANUAL (TCO)            | **1.602,50 € / año**             | **3.373,26 € / año**            |
| Coste Operativo Mensual Equivalente| **133,54 € / mes**               | **281,10 € / mes**              |
+------------------------------------+----------------------------------+---------------------------------+
```

---

### Detalle de los Vectores de Coste

#### 1. Cómputo (CPU y Memoria)
* **Escenario Cloud:** Instancia VPS equilibrada (tipo *Hetzner CPX21* o *AWS t3.medium* con reserva anual) con 2 vCPU dedicadas, 4 GB de RAM y 80 GB de almacenamiento NVMe. Capaz de ejecutar holgadamente los 5 contenedores Docker (`broker`, `almacenamiento`, `productor`, `consumidor` y `api`).
  $$\text{Coste mensual: } 24,00 \text{ €} \times 12 = \mathbf{288,00 \text{ €}}$$
* **Escenario On-Premise:** Mini-servidor / Workstation de bajo consumo (tipo Intel Core i5 / AMD Ryzen 5, 16 GB RAM, 512 GB SSD NVMe). Coste de adquisición: 900,00 €. Amortización lineal a 2 años:
  $$\text{Amortización anual: } \frac{900,00 \text{ €}}{2} = \mathbf{450,00 \text{ €}}$$

#### 2. Consumo Eléctrico
* En la nube, el coste energético está absorbido en la tarifa plana del proveedor.
* En local, un equipo encendido en régimen 24/7 con una carga media del 35% consume de forma continua $\approx 45 \text{ W}$:
  $$\text{Energía anual} = \frac{45 \text{ W} \times 24 \text{ h/día} \times 365 \text{ días}}{1.000} = 394,2 \text{ kWh}$$
  Aplicando un precio medio industrial/doméstico europeo de $0,30 \text{ €/kWh}$ (incluyendo impuestos y término de potencia):
  $$\text{Coste Eléctrico} = 394,2 \text{ kWh} \times 0,30 \text{ €/kWh} = \mathbf{118,26 \text{ € / año}}$$

#### 3. Tráfico de Red y Conectividad
* **Ingesta (Ingress):**
  * Peticiones a USGS cada 60 s: $1.440 \text{ peticiones/día} \times \approx 80 \text{ KB/feed} \approx 115 \text{ MB/día} \approx \mathbf{42 \text{ GB/año}}$.
  * El tráfico entrante en los proveedores de nube es habitualmente gratuito ($0,00 \text{ €}$).
* **Salida a Clientes (Egress API):**
  * Estimando 50 usuarios concurrentes en el panel Angular con sondeos cada 60 s: $\approx 250 \text{ MB/día} \approx \mathbf{91 \text{ GB/año}}$.
  * En la arquitectura con túnel ngrok reservado comercial (licencia Pro con dominio personalizado y sin límites de peticiones por minuto):
    $$\text{ngrok Pro: } 8,00 \text{ €/mes} \times 12 = \mathbf{96,00 \text{ € / año}}$$
* En la alternativa local se requiere una línea de fibra comercial con IP fija estática y SLA de disponibilidad de 4 horas ($\approx 30,00 \text{ €/mes} \times 12 = 360,00 \text{ €}$).

#### 4. Coste Humano y DevOps (El mayor componente del TCO)
* **Error habitual:** Contabilizar únicamente las facturas de infraestructura ignorando el tiempo de ingeniería necesario para mantener el sistema operativo, seguro y actualizado.
* **Escenario Cloud:**
  * Estimación de 2 horas al mes dedicadas a: aplicación de parches de seguridad del sistema operativo, rotación de certificados TLS, auditoría de logs de cuarentena y verificación de backups.
  $$\text{Coste Humano} = 24 \text{ h} \times 50,00 \text{ €/h} = \mathbf{1.200,00 \text{ € / año}}$$
* **Escenario On-Premise:**
  * Requiere además supervisión física del hardware, gestión del sistema de alimentación ininterrumpida (SAI), ventilación, y resolución presencial de incidencias por cortes de luz o proveedor de fibra ($\approx 4 \text{ h/mes} = 48 \text{ h/año} = \mathbf{2.400,00 \text{ €}}$).

---

## 3. Discusión Crítica: La Falacia del "Coste Cero" de la Capa Gratuita (*Free Tier Fallacy*)

Durante el diseño de arquitecturas cloud para proyectos académicos o pruebas de concepto (*PoC*), existe la tentación de proclamar que la solución tiene un coste de $0,00 \text{ €}$ apoyándose en capas gratuitas (Netlify Starter, Supabase Free, AWS Free Tier de 12 meses, ngrok Free).

En este proyecto se defiende formalmente que **dicha suposición es inviable para un entorno de producción real** debido a las siguientes razones técnicas y financieras:

1. **Límites Abruptos de Tráfico y Cortes de Servicio:**
   * La capa gratuita de ngrok impone límites estrictos de peticiones por minuto (40 RPM) y muestra una página intermedia de aviso (`ngrok-skip-browser-warning`) que bloquea las peticiones REST no preparadas.
   * La capa gratuita de Netlify tiene un límite de 100 GB de ancho de banda mensual. Un pico de tráfico por un terremoto de gran magnitud viralizado agotaría la cuota en horas, provocando la suspensión inmediata del sitio (*HTTP 402 Payment Required*).

2. **Riesgo de Facturación Descontrolada (*Billing Spikes*):**
   * En proveedores cloud públicos (AWS/GCP), el tráfico saliente (*egress*) fuera de la cuota gratuita se factura a precios prohibitivos ($\approx 0,09 \text{ \$/GB}$). Si una API es indexada por rastreadores o sufre un ataque de denegación de servicio (*DoS*), el coste puede dispararse a miles de dólares en cuestión de días sin previo aviso humano.

3. **Inexistencia de Acuerdos de Nivel de Servicio (SLA):**
   * Ningún proveedor garantiza disponibilidad en servicios gratuitos. Para un observatorio sísmico donde la frescura del dato y la alerta temprana son críticas, la caída del broker o de la base de datos sin soporte 24/7 convierte el sistema en un juguete no operativo.

4. **Persistencia Efímera y Desconexión por Inactividad:**
   * Plataformas PaaS gratuitas (como Render o Fly.io en sus planes base) suspenden los contenedores tras 15 minutos de inactividad (*cold start* de hasta 40 segundos). Un broker Kafka no puede tolerar suspensiones, ya que provocaría la expulsión de consumidores del grupo (*rebalance storm*) y acumulación inmanejable de lag.

---

## 4. Conclusiones y Recomendación para Producción

1. **La arquitectura híbrida implementada (Docker Compose en VPS + Netlify CDN) es la óptima:** Presenta un TCO un **52% inferior** a mantener un servidor físico local, eliminando los riesgos de cortes domésticos y garantizando una disponibilidad $> 99,9\%$.
2. **El coste operativo real es de $\approx 133,54 \text{ €/mes}$**, donde el 75% corresponde a tiempo de ingeniería y mantenimiento preventivo, y solo el 25% a infraestructura de máquinas y red.
3. El desacoplamiento entre el frontend en CDN y el backend en Docker permite absorber picos masivos de visitantes sin incrementar el coste de los servidores de datos.

