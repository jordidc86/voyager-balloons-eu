# Auditoría de presencia en Google

Fecha: 2026-06-18  
Última actualización operativa: 2026-06-19
Sitios revisados:

- Web principal: https://www.voyagerballoons.eu/
- Tienda: https://shop.voyagerballoons.eu/
- WordPress staging antiguo: https://jordidiazcasaubon.wpcomstaging.com/

## Objetivo

Asegurar que Google indexa las páginas nuevas correctas, limpia URLs antiguas, entiende la relación con la tienda y mejora la presencia de Voyager Balloons en Search, Maps, Shopping/Merchant y resultados enriquecidos.

## Cómo asegurar que Google propaga los cambios

No se puede obligar a Google a indexar inmediatamente, pero sí se puede acelerar y controlar el proceso:

1. En Search Console, propiedad de dominio `voyagerballoons.eu`.
2. Enviar sitemap principal:
   - `https://www.voyagerballoons.eu/sitemap.xml`
3. Usar inspección de URL y solicitar indexación para:
   - `https://www.voyagerballoons.eu/`
   - `https://www.voyagerballoons.eu/vuelo-en-globo-segovia`
   - `https://www.voyagerballoons.eu/vuelo-en-globo-segovia-desde-madrid`
   - `https://www.voyagerballoons.eu/actividades-segovia`
   - `https://www.voyagerballoons.eu/seguridad-pilotos`
4. Revisar en Search Console:
   - Página indexada / no indexada.
   - Canonical elegido por Google.
   - Último rastreo.
   - Sitemaps procesados.
   - Errores de datos estructurados.
5. Tras 48-72 horas, buscar:
   - `site:voyagerballoons.eu`
   - `site:voyagerballoons.eu/vuelo-en-globo-segovia`
   - `site:voyagerballoons.eu actividades segovia`

Referencia oficial: Google indica que se puede pedir recrawling mediante sitemap o URL Inspection, pero la recrawl/reindexación puede tardar varios días.  
Fuente: https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl

## Hallazgos públicos actuales

### 1. Google ya ve la home, pero con parámetros `srsltid`

En búsquedas públicas aparece la home varias veces con URLs del tipo:

- `https://www.voyagerballoons.eu/?srsltid=...`

Esto suele venir de enlaces/feeds/campañas o Merchant/Shopping. No es necesariamente un problema si canonical apunta a `/`, pero conviene revisar en Search Console que Google elige:

- Canonical declarada: `https://www.voyagerballoons.eu/`
- Canonical seleccionada por Google: `https://www.voyagerballoons.eu/`

### 2. Hay URLs antiguas indexadas o descubiertas

Google muestra URLs antiguas de WordPress o de la etapa anterior:

- `/refund-policy/`
- `/tag/segovia/`
- `/tag/segovia/page/2/`
- `/segovia-desde-el-aire-paseo-en-globo/`
- `/a-que-altura-vuela-un-globo-curiosidades-que-te-sorprenderan/`
- `/producto/oferta-vuelo-en-globo-en-segovia/`
- `/etiqueta-producto/madrid/`

Estado anterior: muchas terminaban en 404 tras pasar a `www`.  
Acción aplicada: redirects 301 en Netlify hacia páginas equivalentes.

### 3. `shop.voyagerballoons.eu/robots.txt` corregido

Estado anterior: el robots de la tienda devolvía:

```txt
Sitemap: https://voyagerballoons.eu/sitemap.xml
```

Estado actualizado el 2026-06-19: corregido por SFTP en la raíz de WordPress.com. Ahora devuelve `200 OK` y apunta al sitemap nativo de la tienda:

```txt
Sitemap: https://shop.voyagerballoons.eu/wp-sitemap.xml
```

Backup previo guardado temporalmente en `/tmp/voyager-wp-root-backup/robots.txt.before`.

### 4. `shop.voyagerballoons.eu/sitemap.xml` corregido

Estado anterior: el sitemap físico de la tienda listaba URLs del dominio principal antiguo, por ejemplo:

- `https://voyagerballoons.eu/`
- `https://voyagerballoons.eu/shop/`
- `https://voyagerballoons.eu/blog/`

Esto era una señal mala para Google y Merchant porque mezclaba tienda WordPress con dominio principal Netlify.

Estado actualizado el 2026-06-19: corregido por SFTP en la raíz de WordPress.com. Ahora `https://shop.voyagerballoons.eu/sitemap.xml` devuelve un sitemap index mínimo que apunta al sitemap real de WordPress:

```xml
<loc>https://shop.voyagerballoons.eu/wp-sitemap.xml</loc>
```

Backup previo guardado temporalmente en `/tmp/voyager-wp-root-backup/sitemap.xml.before`.

### 5. WordPress staging redirige a la tienda

`jordidiazcasaubon.wpcomstaging.com` redirige a `https://shop.voyagerballoons.eu/`. Bien como mitigación. Aun así, debe revisarse que Google no conserve staging como resultado indexable.

## Search Console: auditoría pendiente dentro de cuenta

Estado revisado el 2026-06-18 con la cuenta `voyagerballoonseu@gmail.com`.

### Propiedad principal verificada

Se ha verificado la propiedad de prefijo:

- `https://www.voyagerballoons.eu/`

Método usado:

- Archivo HTML de verificación: `google53c3d717e983d08d.html`
- URL pública comprobada: `https://www.voyagerballoons.eu/google53c3d717e983d08d.html`

Importante: no borrar este archivo, porque Google puede volver a comprobar la verificación.

### Propiedad de dominio verificada

Estado actualizado el 2026-06-19: la propiedad de dominio `voyagerballoons.eu` ya está verificada por DNS en Search Console. Esta propiedad cubre:

- `www.voyagerballoons.eu`
- `shop.voyagerballoons.eu`
- URLs con y sin `www`

No eliminar el TXT DNS de verificación.

### Sitemap principal enviado

Enviado en Search Console:

- `https://www.voyagerballoons.eu/sitemap.xml`
- `https://shop.voyagerballoons.eu/wp-sitemap.xml`

Estado inicial mostrado por Google en algunas vistas:

- `No se ha podido obtener`
- URLs descubiertas: `0`

Comprobación externa:

- Ambos sitemaps públicos responden `200 OK`.
- El contenido XML es válido y accesible.
- Search Console mostró confirmación verde de envío correcto al añadirlos.

Interpretación: al ser una propiedad recién verificada, puede ser un estado temporal de procesamiento. Revisar en 24-48 horas. Si sigue igual, volver a enviarlo y comprobar el informe de sitemaps.

### Indexación solicitada manualmente

Se ha solicitado indexación en URL Inspection para:

- `https://www.voyagerballoons.eu/`
- `https://www.voyagerballoons.eu/blog`
- `https://www.voyagerballoons.eu/vuelo-en-globo-segovia`
- `https://www.voyagerballoons.eu/vuelo-en-globo-segovia-desde-madrid`
- `https://www.voyagerballoons.eu/actividades-segovia`
- `https://www.voyagerballoons.eu/seguridad-pilotos`
- `https://www.voyagerballoons.eu/articulos/vuelo-globo-segovia`
- `https://www.voyagerballoons.eu/articulos/primer-vuelo-globo`
- `https://www.voyagerballoons.eu/articulos/regalar-vuelo-globo`
- `https://www.voyagerballoons.eu/articulos/como-se-dirige-globo`

Estado previo observado:

- `La URL no está en Google`
- `Google no reconoce esta URL`

Estado el 2026-06-19:

- La home `https://www.voyagerballoons.eu/` aparece como `La URL está en Google`.
- La cuota diaria de solicitud manual de indexación se agotó al revisar la tienda.
- Hay una tarea programada para retomar el 2026-06-20 a las 09:00.

Siguiente revisión:

- Esperar 24-72 horas.
- Comprobar si Google elige la canonical declarada.
- Solicitar también la home y `/blog` si no aparecen procesadas con el sitemap.

## Search Console: revisión futura

### Propiedades

Debe existir preferentemente una propiedad de dominio:

- `voyagerballoons.eu`

Y, si se gestiona por separado:

- `https://www.voyagerballoons.eu/`
- `https://shop.voyagerballoons.eu/`

### Sitemaps

Comprobar enviados:

- `https://www.voyagerballoons.eu/sitemap.xml`
- sitemap real de tienda en `shop.voyagerballoons.eu`

Comprobar:

- Fecha de última lectura.
- URLs descubiertas.
- Errores.

### Indexación

Revisar:

- Páginas indexadas.
- Páginas no indexadas.
- `404`.
- `Crawled - currently not indexed`.
- `Discovered - currently not indexed`.
- Duplicadas sin canonical seleccionado por el usuario.
- URLs con `srsltid`.

### URL Inspection

Inspeccionar y solicitar indexación para:

- `/vuelo-en-globo-segovia`
- `/vuelo-en-globo-segovia-desde-madrid`
- `/actividades-segovia`
- `/seguridad-pilotos`
- `/sitemap.xml`

Referencia oficial: Search Console permite ver información de la versión indexada, indexabilidad, canonical y datos estructurados.  
Fuente: https://support.google.com/webmasters/answer/9012289

## Google Merchant Center / Shopping

Estado revisado el 2026-06-18 con la cuenta `voyagerballoonseu@gmail.com`.

### Cuenta detectada

- Nombre: `Voyager Balloons EU - vuelos en globo`
- ID: `5530552212`

### Estado actual

- Clics últimos 28 días: `131`
- Variación mostrada: `+59,8%`
- Productos totales: `0`
- Productos aprobados: `0`
- Productos limitados: `0`
- Productos rechazados: `0`
- Productos en revisión: `0`

### Fuentes de producto configuradas

Found by Google:

- Fuente: `voyagerballoons.eu`
- Tipo: tienda online
- Productos: `0`
- Frecuencia: cada 24 horas
- Países mostrados en detalle: `Cambodia, Cameroon, Chile +47`

Provided by you:

- `Content API`, feed label `ES`, idioma inglés, productos `0`, última actualización `-`
- `Content API`, feed label `ES`, idioma español, productos `0`, última actualización `-`

Problema principal: Merchant tiene fuentes creadas, pero no está recibiendo productos. Además, los países aparecen demasiado amplios y no alineados con España como mercado prioritario.

### Hallazgos públicos

La tienda está en WordPress/WooCommerce y existe producto de vuelo desde 120 euros. También aparecen señales externas como GetYourGuide, Viator, Aladinia y Yumping.

### Riesgos actuales

- Sitemap/robots de tienda apuntaban a dominio incorrecto. Corregido el 2026-06-19 por SFTP.
- Posible mezcla de producto en `shop` con páginas antiguas en dominio principal.
- Merchant puede estar leyendo URLs incorrectas si el feed se generó antes del cambio de dominio.
- Falta confirmar si el feed usa:
  - `link`: URL de producto en `shop.voyagerballoons.eu`
  - `image_link`: imagen válida.
  - `price`: 120.00 EUR.
  - `availability`: in_stock.
  - `condition`: new.
  - `brand`: Voyager Balloons.
  - `google_product_category` o categoría adecuada.

### Revisión recomendada en Merchant Center

1. Productos > Diagnóstico.
2. Revisar productos rechazados o con advertencias.
3. Revisar feed principal:
   - Origen del feed.
   - Dominio reclamado.
   - Última actualización.
   - URLs de destino.
4. Revisar configuración de envío si aplica.
5. Revisar política de devoluciones/cancelación.
6. Revisar si el producto debería estar en Merchant.
7. Completar datos de atención al cliente:
   - Website URL: `https://www.voyagerballoons.eu/`
   - Email: `info@voyagerballoons.eu`
   - Teléfono: `+34 921 801 005`
   - Método preferido: teléfono o email, según operación real.
8. Limitar países de venta/listing a España salvo que haya una estrategia real para otros mercados.
9. Reconectar WooCommerce/Google Listings con `shop.voyagerballoons.eu`, no con el dominio principal antiguo.

Nota: Google Merchant está pensado para productos y servicios vendibles online. Las experiencias/tickets pueden funcionar, pero conviene asegurarse de que las políticas y landing pages coinciden exactamente con el feed.

Referencia oficial: Google exige que landing pages y datos de producto coincidan, y recomienda structured data con precio, disponibilidad, moneda y condición.  
Fuentes:

- https://support.google.com/merchants/answer/4752265
- https://support.google.com/merchants/answer/7052112
- https://developers.google.com/search/docs/appearance/structured-data/merchant-listing

## Google Business Profile / Maps

Estado revisado el 2026-06-18.

### Estado actual observado

- Perfil gestionado desde la cuenta actual.
- Nombre visible: `Voyager Balloons EU - Paseos en Globo`
- Categoría visible: `Agencia de excursiones en globo en España`
- Valoración: `4,9/5`
- Reseñas: `364`
- Interacciones mostradas: `1.314`
- Perfil indica `18 reseñas nuevas`.
- Google indica que las fotos se añadieron por última vez hace `262 días`.
- Website visible: `https://voyagerballoons.eu/`
- Teléfono visible: `605 08 74 78`
- Dirección visible: `C. 3 de Abril, 40003 Segovia`
- Horario visible: `Abierto las 24 horas`
- Opciones de reserva visibles:
  - Sitio oficial: `https://voyagerballoons.eu/shop`, 120 euros, 3h
  - Tripadvisor
  - Viator

### Riesgos detectados

1. Dirección pública visible, aunque no hay atención presencial.
2. Teléfono visible como `605 08 74 78`, cuando ese número se definió como WhatsApp; para llamadas debería figurar `921 801 005`.
3. Web visible sin `www`, aunque la web final trabaja en `https://www.voyagerballoons.eu/`.
4. Enlace de reserva oficial apunta a `/shop` en el dominio principal, en vez de `https://shop.voyagerballoons.eu/`.
5. Fotos desactualizadas para una actividad muy visual.
6. Reseñas nuevas pendientes de leer/responder.
7. Horario `24 horas` puede crear expectativas operativas si no hay atención telefónica real 24/7.

### Qué revisar

1. Nombre:
   - `Voyager Balloons EU`
   - No añadir keywords artificiales tipo "Vuelos en Globo Segovia" si no forman parte del nombre real.
2. Categoría primaria:
   - Actividad turística / Agencia de turismo / Servicio de vuelo en globo, según opciones disponibles.
3. Área de servicio:
   - Segovia.
   - Madrid como origen de visitantes, no como sede si no hay atención allí.
4. Dirección:
   - No mostrar dirección física si no hay atención presencial.
5. Teléfono:
   - +34 921 801 005 para llamadas.
   - WhatsApp +34 605 087 478 si GBP permite mensajería.
6. Web:
   - `https://www.voyagerballoons.eu/vuelo-en-globo-segovia`
   - O home si Google no acepta URL profunda.
7. Fotos:
   - Globo real.
   - Pasajeros.
   - Alcázar/Segovia desde el aire.
   - Equipo.
   - No usar solo imágenes genéricas.
8. Reseñas:
   - Pedir reseñas reales tras cada vuelo.
   - Responder reseñas con detalle.
   - No incentivar reseñas con descuentos o regalos.
9. Posts:
   - Publicar 1 vez por semana:
     - fechas disponibles.
     - vuelo regalo.
     - consejos de ropa.
     - qué hacer en Segovia después del vuelo.

### Acciones recomendadas en Business Profile

1. Convertir la ficha a negocio de área de servicio si no hay atención presencial, ocultando la dirección exacta.
2. Cambiar teléfono principal a `+34 921 801 005`.
3. Añadir WhatsApp/mensajería con `+34 605 087 478` si Google lo permite.
4. Actualizar web a `https://www.voyagerballoons.eu/` o a `https://www.voyagerballoons.eu/vuelo-en-globo-segovia`.
5. Actualizar enlace de reservas a `https://shop.voyagerballoons.eu/`.
6. Subir fotos nuevas cada semana durante 30 días.
7. Responder las 18 reseñas recientes con texto específico y natural.
8. Usar el enlace de "Pedir una reseña" en el email postvuelo.
9. Publicar posts semanales orientados a:
   - vuelo en globo en Segovia,
   - regalo para pareja/familia,
   - escapada desde Madrid,
   - actividad de amanecer,
   - qué hacer en Segovia.

Referencia oficial: Google pide información precisa y actualizada en Business Profile.  
Fuente: https://support.google.com/business/answer/3038177

## Actualización operativa 2026-06-19

### Google Business Profile

Acciones realizadas en el perfil `Voyager Balloons EU - Paseos en Globo`:

- Teléfono principal cambiado a `+34 921 801 005`.
- Web cambiada a `https://www.voyagerballoons.eu/`.
- Dirección pública ocultada. El perfil queda como negocio sin ubicación pública y con área de servicio `Segovia, España`.
- Descripción actualizada para reforzar:
  - vuelo al amanecer en Segovia,
  - vistas del Alcázar, Catedral y sierra,
  - más de 25 años de experiencia volando en globo,
  - escapadas desde Madrid,
  - brindis con cava tras el aterrizaje.
- Enlaces de reserva:
  - añadido `https://shop.voyagerballoons.eu/`;
  - marcado como enlace preferido;
  - se mantiene `wa.me` como canal adicional.
- Actividad `Paseo en Globo en Segovia` actualizada:
  - URL: `https://shop.voyagerballoons.eu/`;
  - descripción enfocada a Segovia, Alcázar, Catedral, sierra, regalo, Madrid y brindis con cava;
  - idioma cambiado a `Spanish`;
  - duración `3 h`;
  - precio `120 EUR`;
  - sin seleccionar `Cancelación gratuita`.
- Servicios añadidos bajo la categoría `Agencia de excursiones en globo`:
  - `Vuelo en globo en Segovia`
  - `Paseo en globo para regalo`
  - `Vuelo en globo para parejas`
  - `Vuelos en globo para grupos`
  - `Actividad de empresa en globo`
- Cada servicio quedó con descripción propia.
- Publicación antigua con precio `180 EUR` editada y enviada a revisión como oferta vigente:
  - título nuevo previsto: `Vuelos en globo en Segovia desde 120 EUR`;
  - enlace de canje: `https://shop.voyagerballoons.eu/`;
  - fecha de fin: `31/12/2026`.

Estado: Google marcó varios cambios como pendientes de revisión. Plazos mostrados:

- Actividad: hasta 20 minutos.
- Servicios: hasta 1 día.
- Publicación: enviada a revisión.
- Teléfono, web, descripción y dirección: pendientes de revisión en el perfil.

### Search Console

Propiedad trabajada:

- `https://www.voyagerballoons.eu/`

La propiedad de dominio `voyagerballoons.eu` ya está verificada por DNS. Cubre tanto `www.voyagerballoons.eu` como `shop.voyagerballoons.eu`.

Sitemap:

- `https://www.voyagerballoons.eu/sitemap.xml` comprobado externamente con `200 OK`.
- `robots.txt` comprobado externamente con `200 OK`.
- Search Console seguía mostrando `No se ha podido obtener`, pero el sitemap se reenvió y Google confirmó: `Se ha enviado el sitemap correctamente`.

Indexación:

- La home `https://www.voyagerballoons.eu/` ya aparece como `La URL está en Google`.
- Para la home se solicitó reindexación tras los cambios de schema/canonical/contenido.
- Search Console detecta en la home:
  - HTTPS válido.
  - Fragmentos de productos: 1 elemento válido con problemas no críticos.
  - Fichas de comerciantes: 1 elemento válido con problemas no críticos.
- El informe de páginas todavía indica que los datos se están procesando.

URLs no reconocidas por Google y enviadas a cola de indexación prioritaria:

- `https://www.voyagerballoons.eu/blog`
- `https://www.voyagerballoons.eu/articulos/vuelo-globo-segovia`
- `https://www.voyagerballoons.eu/articulos/primer-vuelo-globo`
- `https://www.voyagerballoons.eu/articulos/regalar-vuelo-globo`
- `https://www.voyagerballoons.eu/articulos/como-se-dirige-globo`

Acción pendiente:

- Revisar en 24-72 horas si el sitemap pasa de `No se ha podido obtener` a procesado.
- Revisar si las URLs anteriores pasan de `Google no reconoce esta URL` a `URL en Google`.
- No retirar el TXT DNS de verificación de la propiedad de dominio.

### WordPress / tienda

Comprobaciones realizadas:

- `https://jordidiazcasaubon.wpcomstaging.com/` devuelve `301` a `https://shop.voyagerballoons.eu/`. Esto mitiga el resultado antiguo de Google con staging y debería hacer que desaparezca tras nuevo rastreo.
- En WordPress, `WordPress Address (URL)` y `Site Address (URL)` están en `https://shop.voyagerballoons.eu`.
- `https://shop.voyagerballoons.eu/wp-sitemap.xml` existe, responde `200 OK` y lista URLs correctas de `shop.voyagerballoons.eu`.

Problema corregido el 2026-06-19:

- `https://shop.voyagerballoons.eu/robots.txt` estaba apuntando a:

```txt
Sitemap: https://voyagerballoons.eu/sitemap.xml
```

- `https://shop.voyagerballoons.eu/sitemap.xml` listaba URLs antiguas de `https://voyagerballoons.eu/...`.

Interpretación:

- La tienda tiene un sitemap nativo correcto en `wp-sitemap.xml`.
- El sitemap/robots antiguo no es solo caché: tras limpiar caché de WordPress.com respondió `MISS` y mantuvo `Last-Modified` de marzo de 2026.
- Se confirmó que eran archivos físicos heredados en la raíz del hosting WordPress.com.
- No conviene poner el sitio completo en noindex porque rompería la tienda.
- WPCode Lite muestra editor de archivos, pero la edición de `robots.txt` es función Pro.
- Se accedió por SFTP tras el reset autorizado por el propietario.

Acción aplicada:

1. Backup de archivos antiguos en `/tmp/voyager-wp-root-backup/`.
2. `robots.txt` actualizado para apuntar a:

```txt
Sitemap: https://shop.voyagerballoons.eu/wp-sitemap.xml
```

3. `sitemap.xml` actualizado como sitemap index que apunta a `https://shop.voyagerballoons.eu/wp-sitemap.xml`.
4. Verificación externa:
   - `https://shop.voyagerballoons.eu/robots.txt` responde `200 OK`.
   - `https://shop.voyagerballoons.eu/sitemap.xml` responde `200 OK`.
   - `https://shop.voyagerballoons.eu/wp-sitemap.xml` responde `200 OK`.
5. La propiedad de dominio ya está verificada y `wp-sitemap.xml` ya se ha enviado en Search Console.

### Correcciones aplicadas en la tienda

Aplicado el 2026-06-19 en WooCommerce:

- Producto principal actualizado:
  - Antes: `Vuelo en globo al amanecer en segovia`
  - Ahora: `Vuelo en globo al amanecer en Segovia`
- Eliminadas referencias a `picnic`, `pícnic` y desayuno en la ficha pública.
- Descripción corta actual:

```txt
De 45 a 60 minutos de vuelo y brindis con cava al acabar la experiencia.
```

- La página pública del producto ya no contiene `picnic`, `pícnic` ni `desayuno`.
- El schema `Product` del producto principal ya refleja la descripción con brindis de cava.
- Se creó el snippet WPCode `SEO canonical tags tienda` para intentar añadir canonical tags en WordPress.
  - Verificado: el producto principal emite canonical correcto.
  - Pendiente: home/categoría de tienda no reciben canonical con WPCode Lite; resolver con Rank Math bien configurado o corrección a nivel hosting/tema.

### Merchant Center

Intento de acceso:

- URL oficial usada: `https://accounts.google.com/Login?service=merchants`.
- Google pidió verificación de identidad/passkey para `voyagerballoonseu@gmail.com`.

Estado: bloqueado hasta que el propietario complete la verificación en navegador.

Qué revisar al entrar:

- Website URL de atención al cliente.
- Teléfono `+34 921 801 005`.
- Email `info@voyagerballoons.eu`.
- Dominio reclamado y método de verificación.
- Fuentes de datos con 0 productos.
- Países de destino del feed.
- Si WooCommerce/Google Listings sigue enviando URLs antiguas.
- Si conviene usar Merchant para experiencias o limitarlo a producto regalo/ticket con landing y políticas muy consistentes.

### SERP pública y competidores

Hallazgo importante:

- Google aún muestra resultados antiguos de `jordidiazcasaubon.wpcomstaging.com`, pero el dominio ya redirige 301 a `shop.voyagerballoons.eu`.

Competidores visibles para búsquedas de vuelo en globo Segovia:

- Siempre en las Nubes.
- Globos Boreal.
- Aerodifusión.
- Aerotours.
- TripAdvisor, Viator, Yumping, Aladinia y otros agregadores.

Oportunidades detectadas:

- Reforzar la diferencia de precio `desde 120 EUR` frente a competidores que muestran importes cercanos a `205 EUR`.
- Mantener páginas de contenido y landings muy claras para:
  - `vuelo en globo Segovia`,
  - `paseo en globo Segovia`,
  - `vuelo en globo desde Madrid`,
  - `regalar vuelo en globo Segovia`,
  - `actividades en Segovia`.
- Conseguir enlaces/citas externas en blogs turísticos y medios locales.
- Acelerar reseñas y fotos en Google Business Profile.

## Prioridad de acciones

### Urgente

1. Revisar el 2026-06-20 si Search Console ya procesó los sitemaps enviados.
2. Retomar solicitud de indexación manual cuando se renueve la cuota diaria.
3. Revisar canonical seleccionado por Google.
4. Revisar feed y diagnósticos de Merchant Center.
5. Corregir canonical de home/categorías de tienda con Rank Math, tema o SFTP/SSH.

### Esta semana

1. Revisar y limpiar URLs antiguas en Search Console.
2. Configurar Google Business Profile sin dirección pública si no hay atención presencial.
3. Añadir enlace de reseña de Google al proceso post-vuelo.
4. Completar datos de atención al cliente en Merchant.
5. Revisar que Google Business Profile aprueba teléfono, web, dirección oculta y enlace de reservas.

### 30 días

1. Conseguir reseñas reales en Google y plataformas.
2. Publicar fotos reales en Business Profile.
3. Responder todas las reseñas nuevas.
4. Conseguir que Merchant reciba al menos los productos/experiencias principales desde WooCommerce.
5. Revisar Search Console semanalmente: rendimiento, consultas, páginas indexadas y sitemaps.
6. Monitorizar queries en Search Console.
7. Crear report mensual: clicks, impresiones, CTR, posición media, reservas orgánicas.

## Accesos pendientes

Ya se ha podido revisar Search Console, Business Profile y WordPress/WooCommerce con la cuenta actual. Para completar las correcciones que dependen de plataformas externas faltan estos accesos o acciones:

- Verificación de identidad/passkey en Merchant Center para revisar feed, productos y políticas.
- Google Ads si se quiere optimizar campañas, extensiones y conversiones.
- Site Kit en WordPress si está conectado a Analytics/Search Console.

Con eso se pueden cerrar feed de Merchant, medición de conversiones y consistencia completa entre ficha, tienda y web principal.
