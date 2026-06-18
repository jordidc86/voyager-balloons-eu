# Auditoría de presencia en Google

Fecha: 2026-06-18  
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

### 3. `shop.voyagerballoons.eu/robots.txt` apunta al sitemap equivocado

El robots de la tienda devuelve:

```txt
Sitemap: https://voyagerballoons.eu/sitemap.xml
```

Esto es incorrecto para la tienda. Debería apuntar a un sitemap propio de `shop.voyagerballoons.eu`, por ejemplo:

```txt
Sitemap: https://shop.voyagerballoons.eu/sitemap.xml
```

O, mejor, el sitemap real generado por WordPress/WooCommerce si existe.

### 4. `shop.voyagerballoons.eu/sitemap.xml` contiene URLs del dominio principal antiguo

El sitemap de la tienda lista URLs como:

- `https://voyagerballoons.eu/`
- `https://voyagerballoons.eu/shop/`
- `https://voyagerballoons.eu/blog/`

Esto es una señal mala para Google y Merchant porque mezcla tienda WordPress con dominio principal Netlify.

Acción recomendada en WordPress:

- Regenerar sitemap con el dominio `shop.voyagerballoons.eu`.
- Excluir posts/páginas que no sean productos o contenido útil de tienda.
- Asegurar canonical de productos a `shop.voyagerballoons.eu`.

### 5. WordPress staging redirige a la tienda

`jordidiazcasaubon.wpcomstaging.com` redirige a `https://shop.voyagerballoons.eu/`. Bien como mitigación. Aun así, debe revisarse que Google no conserve staging como resultado indexable.

## Search Console: auditoría pendiente dentro de cuenta

Necesito acceso o pantalla compartida para revisar:

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

### Hallazgos públicos

La tienda está en WordPress/WooCommerce y existe producto de vuelo desde 120 euros. También aparecen señales externas como GetYourGuide, Viator, Aladinia y Yumping.

### Riesgos actuales

- Sitemap/robots de tienda apuntan a dominio incorrecto.
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

Nota: Google Merchant está pensado para productos y servicios vendibles online. Las experiencias/tickets pueden funcionar, pero conviene asegurarse de que las políticas y landing pages coinciden exactamente con el feed.

Referencia oficial: Google exige que landing pages y datos de producto coincidan, y recomienda structured data con precio, disponibilidad, moneda y condición.  
Fuentes:

- https://support.google.com/merchants/answer/4752265
- https://support.google.com/merchants/answer/7052112
- https://developers.google.com/search/docs/appearance/structured-data/merchant-listing

## Google Business Profile / Maps

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

Referencia oficial: Google pide información precisa y actualizada en Business Profile.  
Fuente: https://support.google.com/business/answer/3038177

## Prioridad de acciones

### Urgente

1. En Search Console, enviar sitemap principal.
2. Solicitar indexación de las 4 páginas estratégicas.
3. Revisar canonical seleccionado por Google.
4. Corregir robots/sitemap de `shop.voyagerballoons.eu`.
5. Revisar feed y diagnósticos de Merchant Center.

### Esta semana

1. Revisar y limpiar URLs antiguas en Search Console.
2. Configurar Google Business Profile sin dirección pública si no hay atención presencial.
3. Añadir enlace de reseña de Google al proceso post-vuelo.
4. Alinear WordPress/WooCommerce con `shop.voyagerballoons.eu`.

### 30 días

1. Conseguir reseñas reales en Google y plataformas.
2. Publicar fotos reales en Business Profile.
3. Monitorizar queries en Search Console.
4. Crear report mensual: clicks, impresiones, CTR, posición media, reservas orgánicas.

## Acceso necesario para auditoría privada

Para completar la auditoría dentro de Google necesito que abras o me des acceso a:

- Google Search Console.
- Google Merchant Center.
- Google Business Profile.
- Google Ads si hay campañas activas.
- Site Kit en WordPress si está conectado.

Con eso puedo revisar diagnósticos reales, feeds, index coverage, errores de Merchant, consultas, páginas con impresiones, rich results y problemas de propiedad.
