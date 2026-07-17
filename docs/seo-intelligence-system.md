# Voyager SEO Intelligence

## Objetivo operativo

Mantener una vigilancia continua y accionable de la web, tienda, posicionamiento, demanda, competidores y autoridad de Voyager Balloons. El sistema prioriza reservas directas y evita convertir cada variación SEO en trabajo manual.

## Principios

1. Los datos propios de Search Console, GA4 y WooCommerce prevalecen sobre estimaciones externas.
2. Una alerta debe incluir impacto, evidencia y acción; si no permite decidir, no debe interrumpir.
3. Los chequeos no ejecutan JavaScript de Analytics ni crean pedidos, por lo que las pruebas sintéticas no contaminan conversiones.
4. El monitor se ejecuta fuera de la web y no participa en la respuesta al usuario.
5. Detección y almacenamiento son automáticos. Los cambios comerciales/editoriales requieren aprobación; las reparaciones técnicas seguras pueden automatizarse después de validarlas.
6. Las consultas de pago tienen un presupuesto mensual máximo y su coste real queda registrado por ejecución.
7. Una señal de vida externa debe avisar si el worker deja de ejecutarse; un sistema de vigilancia no puede depender solo de vigilarse a sí mismo.
8. Una ejecución que permanezca dos horas en estado `running` se recupera como fallida y vuelve a ser elegible para reintento; ninguna fuente debe quedar congelada tras una caída del proceso.

## Cobertura actual

| Trabajo | Frecuencia | Cobertura |
| --- | ---: | --- |
| `health` | 6 horas | 14 URLs estratégicas, precios, canonical, noindex, redirecciones y tiempo de respuesta |
| `commerce` | 6 horas | Ficha → añadir al carrito → carrito → checkout para los 5 productos publicados |
| `gsc` | diaria | Clics, impresiones, CTR, posición, páginas y consultas; compara 7 días contra 7 días |
| `indexing` | semanal | Inspección de las 12 URLs estratégicas indexables, canonical elegido, rastreo, obtención y sitemap |
| `ga4` | diaria | Sesiones, eventos e ingresos orgánicos (7 días), atribución por canal/host (28 días) y embudo WooCommerce evaluado solo con datos posteriores a su reparación |
| `rank` | diaria/semanal | 29 keywords estratégicas ES/EN/PT más hasta 6 consultas comerciales descubiertas en Search Console, ubicación, móvil, top 100 y competidores SERP |
| `local_visibility` | semanal | Posición móvil del Perfil de Empresa en 5 consultas/ubicaciones de Segovia, Madrid y Bragança |
| `ai_visibility` | semanal | 7 preguntas comerciales en ChatGPT, Gemini y Perplexity; menciones, citas y fuentes competidoras |
| `technical` | semanal | 151 URLs, enlaces, sitemaps, metadatos, canonical, H1 y JSON-LD |
| `tracking` | diaria | Etiquetas Google, atribución cross-domain y eventos WooCommerce `add_to_cart`/`begin_checkout`/`purchase` |
| `pagespeed` | semanal | Rendimiento, accesibilidad, SEO, LCP y CLS en móvil/escritorio; conserva los tests SEO concretos y los selectores afectados |
| `competitors` | semanal | Títulos, H1, precios y cambios de páginas de 7 competidores/canales |
| `backlinks` | mensual | Enlaces/menciones ganados y relaciones contactadas del sistema de outreach |
| `backlink_gap` | mensual | Dominios relevantes que enlazan a varios competidores directos pero no a Voyager |
| `digest` | semanal | Informe único con score 0–100, impacto, horizonte, esfuerzo, destino, evidencia y alertas abiertas |

El conjunto de keywords crece a partir de Search Console sin convertir el monitor en una lista incontrolada. Cada ejecución semanal puede guardar hasta 20 candidatas no branded y activar como máximo 6 consultas comerciales adicionales. Se excluyen páginas técnicas, parámetros, carrito, checkout, taxonomías y marcas competidoras. Las 29 iniciales siguen siendo el núcleo comercial estable.

## Severidad

- **P0:** compra rota, 5XX, producto no disponible, página comercial noindex, sitemap crítico caído.
- **P1:** 4XX, canonical incorrecto, caída significativa de clics o conversiones, posición estratégica perdida, backlink ganado retirado.
- **P2:** rendimiento degradado confirmado, cambio competidor, keyword ausente, enlace externo roto, oportunidad de CTR.
- **P3:** información y observación sin impacto inmediato.

P0/P1 nuevos o reabiertos se notifican inmediatamente. P2/P3 aparecen en el informe semanal. Una alerta que deja de reproducirse se marca `resolved` automáticamente. El score de prioridad combina severidad, cercanía a la reserva y evidencia cuantitativa; sirve para ordenar trabajo y no debe interpretarse como una previsión garantizada de ingresos.

## Almacenamiento

PostgreSQL en producción y SQLite en desarrollo. Tablas iniciales:

- `job_runs`: estado, duración, resumen y error de cada trabajo.
- `metrics`: series temporales de Search Console, GA4, PageSpeed y chequeos.
- `alerts`: alerta deduplicada, primera/última aparición y resolución.
- `page_snapshots`: estado e identidad de páginas propias y competidoras.
- `keyword_rankings`: posición, URL, ubicación, dispositivo y top de la SERP.
- `keyword_candidates`: consultas comerciales descubiertas en Search Console, estado de activación, landing, mercado y demanda observada.
- `local_rankings`: posición en Maps, perfil detectado, CID, reseñas y competidores visibles.
- `ai_visibility_observations`: respuesta, modelo, mención, cita, fuentes y competidores por pregunta controlada.

No se guardan contraseñas en el repositorio. Los secretos deben vivir como variables privadas de Railway.

## Ejecución local

```bash
python3 -m venv .venv-seo-monitor
.venv-seo-monitor/bin/pip install -r requirements-seo-monitor.txt
.venv-seo-monitor/bin/python -m seo_monitor doctor
.venv-seo-monitor/bin/python -m seo_monitor run health
.venv-seo-monitor/bin/python -m seo_monitor run commerce
.venv-seo-monitor/bin/python -m seo_monitor run local_visibility
.venv-seo-monitor/bin/python -m seo_monitor run ai_visibility
.venv-seo-monitor/bin/python -m seo_monitor run backlink_gap
.venv-seo-monitor/bin/python -m seo_monitor run technical
.venv-seo-monitor/bin/python -m seo_monitor run indexing
.venv-seo-monitor/bin/python -m seo_monitor report
```

Para ejecutar una pasada única con todos los trabajos que estén vencidos:

```bash
.venv-seo-monitor/bin/python -m seo_monitor tick
```

El modo continuo local también existe:

```bash
.venv-seo-monitor/bin/python -m seo_monitor worker
```

## Integraciones operativas

### Google

La cuenta de servicio está conectada como lectora a:

1. Search Console, propiedad de dominio `voyagerballoons.eu`.
2. GA4, propiedad que recibe los eventos de web y tienda.

El JSON vive en `GOOGLE_SERVICE_ACCOUNT_JSON` y el ID numérico en `GA4_PROPERTY_ID` dentro de Railway. La cuenta no necesita permisos de edición.

### DataForSEO

La cuenta pay-as-you-go y sus credenciales están activas. El monitor usa SERP orgánica, Google Maps, demanda de keywords, brecha de dominios y respuestas de ChatGPT/Gemini/Perplexity con búsqueda web. El coste real de cada tarea se guarda como métrica y el inventario se limita a las consultas aprobadas.

El presupuesto queda limitado a **8 USD/mes** y cada módulo tiene además un máximo de **1 USD por ejecución**. Se avisa si una ejecución alcanza **0,75 USD**. Las palabras P0 se consultan a diario hasta posición 20; las secundarias, semanalmente hasta posición 100. Las preguntas P0 de visibilidad IA se revisan semanalmente y las secundarias cada 28 días. Los límites se ajustan en `thresholds.dataforseo_monthly_budget_usd`, `thresholds.dataforseo_run_budget_usd` y las claves de cadencia relacionadas. `DATAFORSEO_ENABLED=false` permite pausar todas las consultas pagadas sin eliminar credenciales ni generar fallos. Al alcanzar cualquiera de los límites, la tanda se detiene sin borrar alertas previas ni repetir consultas innecesarias.

### PageSpeed

La API key restringida a PageSpeed Insights API está configurada en `PAGESPEED_API_KEY`. Los datos CrUX de origen se deduplican: si Chrome solo dispone de datos agregados para toda la tienda, se genera una alerta de origen y no una copia por cada producto.

### Alertas

Configurar SMTP y `SEO_ALERT_EMAIL_TO`. El remitente previsto es `info@voyagerballoons.eu`; el destinatario puede ser el correo personal de Jordi, el corporativo o ambos. El monitor acepta tanto `SMTP_USER`/`SMTP_APP_PASSWORD`, ya usados por Voyager, como `SMTP_USERNAME`/`SMTP_PASSWORD`, y soporta STARTTLS e implicit TLS.

El 17 de julio se verificó que los servicios actuales de Railway ya disponen de `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` y contraseña de aplicación. Se reutilizarán mediante referencias privadas; Jordi no debe volver a compartir ese secreto.

### Vigilancia del monitor

Crear un monitor de tipo *dead man's switch* (por ejemplo, Better Uptime o Healthchecks.io) y guardar su URL privada en `SEO_MONITOR_HEARTBEAT_URL`. El cron solo confirma la señal tras un ciclo sin fallos; si deja de ejecutarse o algún trabajo falla persistentemente, el proveedor externo avisa aunque Railway, SMTP o el proceso hayan caído.

## Despliegue actual

Proyecto Railway `zealous-creativity`, entorno `production`:

- servicio cron `voyager-seo-monitor` usando `Dockerfile.seo-monitor`, ejecutado cada 6 horas y apagado entre pasadas;
- PostgreSQL persistente con histórico de ejecuciones, métricas, rankings, snapshots y alertas;
- secretos privados de Google, DataForSEO, PageSpeed y SMTP;
- una única ejecución cron para evitar trabajos duplicados.

## Criterios de aceptación de la primera versión

1. Dos ciclos consecutivos de `health` y `commerce` sin falsos positivos.
2. Crawl completo con 0 destinos internos rotos y 0 errores JSON-LD.
3. Search Console y GA4 importan datos reales de dos periodos comparables.
4. Las keywords devuelven posición y top 10 competidor para las tres lenguas.
5. Una alerta sintética P0 llega por email una sola vez y se resuelve tras desaparecer.
6. Un reinicio del worker conserva histórico y no duplica trabajos.
7. El informe semanal distingue acciones urgentes, estratégicas y observacionales.

## Estado del 18 de julio de 2026

- Crawl productivo: 151 URLs, 12 sitemaps, 2.937 enlaces internos, 0 destinos rotos, 0 errores JSON-LD.
- Prueba de compra completa: clásico, oferta, privado, Comfort y Bragança llegan correctamente hasta checkout con formulario y medios de pago visibles.
- Configuración calibrada para `/cart/` y `/checkout/`; el checkout vacío redirige legítimamente al carrito.
- Dos ciclos de salud completados: 14/14 URLs disponibles. El segundo ciclo abrió una alerta P2 por respuesta sostenida del checkout cercana a 3 segundos, pendiente de contrastar con PageSpeed/CrUX.
- Base histórica, deduplicación, resolución y reporting implementados y probados localmente.
- Inspección automática de indexación preparada para 12 URLs indexables prioritarias mediante Search Console URL Inspection API.
- Observatorios preparados: 5 consultas locales en Google Maps y 21 respuestas IA controladas por ciclo (7 preguntas × 3 proveedores).
- Cruce mensual de enlaces preparado sobre 4 competidores directos, filtrado por relevancia, autoridad, spam y enlaces `dofollow`.
- Validación productiva repetida: 14/14 URLs, 5/5 compras, 151 páginas, 2.937 enlaces internos, 0 enlaces rotos y 0 errores de schema.
- Medición validada en navegador: el salto web → producto Comfort queda decorado con `_gl`; las dos propiedades comparten `GT-55NTF5CN`/`AW-11564692382` y WooCommerce declara `add_to_cart` y `purchase`.
- Control diario de integridad Analytics: valida etiquetas, linker, eventos declarados y que WP Rocket no retrase el listener WooCommerce de Site Kit.
- Tests locales: 75/75 correctos antes del siguiente despliegue.
- Protección operativa añadida: techo de 8 USD/mes, 1 USD por ejecución y aviso a 0,75 USD para DataForSEO; las consultas secundarias se difieren automáticamente para evitar gasto repetido.
- Google, GA4, PageSpeed, SMTP, Railway, PostgreSQL y DataForSEO están desplegados y verificados con datos reales.
- Primera inteligencia de demanda: 10 keywords con datos y 9 oportunidades fuera del top 10 por 0,0252 USD en la ejecución del 17 de julio.
- Calibración de ruido: una variación aislada de ranking ya no escala a P1; Maps requiere tres observaciones; el estado indeterminado de Search Console es P2; carrito se valida por producto y URL; CrUX de tienda se deduplica por origen.
- El informe y las alertas urgentes incluyen score 0–100, impacto sobre reservas, horizonte, esfuerzo, destino, potencial basado en evidencia y acción recomendada.
- Auditoría GA4 de 28 días: `purchase` registra 2 compras y 480 €, y el canal se conserva al entrar en la tienda. Se corrigió la causa probable del `add_to_cart` ausente excluyendo solo el listener WooCommerce de Site Kit del retraso de WP Rocket; el monitor comprobará diariamente que siga cargando de inmediato.
- `begin_checkout` se emite mediante un snippet JavaScript seguro en el checkout, después de que Site Kit esté disponible y respetando el consentimiento. La integridad publicada pasa 9/9 comprobaciones. Para no mezclar el fallo antiguo con el código reparado, el embudo se evalúa desde el 17 de julio y solo genera alerta tras dos días completos y 50 sesiones de tienda.
- Los tres avisos urgentes iniciales de Maps y de `segovia balloon ride` se cerraron tras recalibrar el ruido: Maps requiere tres ausencias consecutivas y se trata como P2; una caída orgánica solo escala a P1 cuando la referencia histórica y una segunda observación degradada la confirman.
- DataForSEO detectó una canibalización inglesa real: para `segovia balloon ride` Google mostraba `/en/` en lugar de `/en/hot-air-balloon-segovia`. La home inglesa se ha reorientado como selector de destinos España/Portugal y la landing dedicada conserva la intención exacta de Segovia, con sitemap y fuentes para IA actualizados.
- La propiedad recibe tráfico de `localhost`/`127.0.0.1`; el script propio ya no carga en esos hosts y el monitor mantiene la contaminación histórica como aviso separado hasta que salga de la ventana de 28 días.
- Descubrimiento real de Search Console validado: 20 candidatas comerciales detectadas en 28 días, 6 activadas como inventario dinámico y 2 oportunidades de CTR, sin incorporar búsquedas branded, marcas competidoras ni URLs técnicas.
- PageSpeed completo revalidado: 20/20 pruebas correctas a nivel de proveedor. CrUX confirma que el principal problema real de la tienda es TTFB (p75 3,13 s), con INP y CLS correctos; la ficha Bragança obtiene SEO 92 por controles de cantidad de Astra implementados como enlaces no rastreables.
