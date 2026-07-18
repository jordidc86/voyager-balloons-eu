# Activación de Voyager SEO Intelligence

## Trabajo mínimo de Jordi

El código, las comprobaciones, las prioridades y el informe ya están preparados. Para pasar de validación local a vigilancia continua hacen falta estas autorizaciones externas.

### 1. Railway

- Autorizar la creación de un servicio cron `voyager-seo-monitor` y una base PostgreSQL dentro del proyecto existente `zealous-creativity`, entorno `production`.
- Coste: el propio de una réplica pequeña y la base gestionada. No se creará nada hasta tener autorización expresa.
- El SMTP corporativo ya existe en Railway y puede reutilizarse mediante referencias privadas, sin volver a compartir la contraseña. El monitor ya es compatible con los nombres `SMTP_USER` y `SMTP_APP_PASSWORD` de los servicios actuales.

### 2. Google Search Console y GA4

- Crear una cuenta de servicio de Google de solo lectura.
- Añadir su email como usuario de lectura en la propiedad de dominio `voyagerballoons.eu` de Search Console.
- Añadir el mismo email como lector en la propiedad GA4 de Voyager.
- Guardar en Railway el JSON de la cuenta y el ID numérico de GA4.

Con esto se activan: consultas, páginas, países, dispositivos, oportunidades de CTR, inspección de indexación, landings orgánicas, eventos clave, compras e ingresos.

### 3. DataForSEO

- La cuenta pay-as-you-go y sus credenciales API ya están configuradas en Railway.
- Completar la verificación del correo de DataForSEO antes de la primera consulta.
- Techo configurado: **8 USD/mes**, **1 USD por módulo y ejecución** y aviso a **0,75 USD**. Al alcanzarlo, el sistema detiene automáticamente las consultas de pago.

Con esto se activan: rankings P0 diarios hasta posición 20, rankings secundarios semanales hasta posición 100, cinco búsquedas de Google Maps, observaciones de buscadores IA escalonadas y seis cruces mensuales de backlinks entre competidores.

### 4. PageSpeed Insights

- Crear una API key restringida a PageSpeed Insights API.
- Guardarla en Railway.

La cuota pública sin clave ya está agotada, por lo que la clave propia es necesaria para medir diez páginas en móvil y escritorio sin depender de una cuota compartida.

### 5. Alertas y vigilancia

- Confirmar el correo que recibirá alertas P0/P1 e informe semanal. Valor provisional recomendado: `info@voyagerballoons.eu`.
- Crear una URL privada de *heartbeat* en Better Uptime o Healthchecks.io y guardarla como `SEO_MONITOR_HEARTBEAT_URL`. Solo se confirma después de un ciclo limpio.

## Trabajo que hará Codex después de las autorizaciones

1. Servicio cron y PostgreSQL ya creados en Railway; el proceso se ejecuta cada 6 horas y permanece apagado entre pasadas para minimizar consumo.
2. Variables privadas, Google, PageSpeed y alertas ya configuradas sin mostrar secretos.
3. Una única réplica desplegada, con build, arranque, persistencia y envío de informes verificados.
4. Tras verificar DataForSEO, ejecutar la tanda inicial controlada y contrastar SERP, Maps, IA y backlinks con el crédito de prueba.
5. Enviar una alerta sintética controlada y comprobar deduplicación y resolución.
6. Entregar el primer informe real priorizado por impacto en reservas directas.
7. Ajustar umbrales tras 2-4 semanas de línea base para reducir ruido y detectar tendencias reales.

## Cadencia operativa

- Cada 6 horas: disponibilidad y cinco recorridos de compra.
- Diaria: Search Console, GA4 y rankings orgánicos.
- Semanal: indexación, PageSpeed, crawl, competidores, Maps e IA.
- Semanal: baseline de dominios enlazantes, enlaces nuevos/perdidos y brecha frente a competidores.
- Inmediata: email para incidencias P0/P1 nuevas o reabiertas.
- Semanal: un único informe ejecutivo con acciones P2/P3 y oportunidades.
