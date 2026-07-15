# Auditoría técnica completa - 15 de julio de 2026

## Resultado ejecutivo

Se ha rastreado la web pública de Voyager Balloons y la tienda WooCommerce después de aplicar las correcciones.

| Comprobación | Resultado |
| --- | ---: |
| Sitemaps leídos | 12/12 correctos |
| URLs declaradas en sitemaps | 120 |
| URLs públicas rastreadas | 151 |
| Páginas HTML analizadas | 148 |
| Enlaces internos inspeccionados | 2.937 |
| Enlaces externos encontrados | 603 (20 destinos únicos) |
| Destinos internos rotos | **0** |
| Destinos externos 404/410 | **0** |
| Errores de JSON-LD | **0** |
| Títulos ausentes | **0** |

Los cuatro destinos externos que respondieron `403` (FAI, GetYourGuide, TripAdvisor y Viator) bloquean comprobadores automáticos, pero no están rotos y funcionan para usuarios normales.

## Origen de la alerta de Ahrefs

La alerta principal se reprodujo exactamente. Tres productos enlazaban al archivo de marca:

`https://shop.voyagerballoons.eu/marca/voyager-balloons/`

WooCommerce tenía configurada una base de permalink distinta de la ruta publicada (`brand` frente a `marca`). Ahrefs encontró la ruta durante el intervalo en que respondía 404. La base se ha alineado y la URL devuelve ahora `200`.

También se localizaron estas causas:

- Dos reglas antiguas del plugin Redirection enviaban artículos publicados hacia slugs inexistentes.
- Varios artículos conservaban enlaces de la etapa en la que el contenido comercial vivía en WordPress, antes de pasar las landings SEO al dominio principal.
- Una plantilla antigua mantenía una ruta de viaje de Ávila que ya no existe.
- Dos enlaces globales del pie omitían la barra final y provocaban una redirección en cada página de la tienda.
- Ahrefs conserva el estado de su último rastreo; una reparación no desaparece del informe hasta su siguiente recrawl.

## Correcciones aplicadas

- Reparada la base de enlaces de marcas de WooCommerce (`/marca/`).
- Desactivadas las dos redirecciones que ocultaban artículos válidos y republicados ambos artículos para purgar caché.
- Añadidas redirecciones seguras para cuatro rutas heredadas de la tienda:
  - la landing antigua desde Madrid;
  - las dos variantes antiguas de vuelo en Segovia;
  - la antigua ruta `/trip/avila/`.
- Añadida una redirección en Netlify para `/la-experiencia-de-volar-en-globo/` hacia la landing vigente.
- Corregidos en el pie los enlaces de condiciones y privacidad para apuntar directamente a sus URLs finales. Esta modificación elimina 232 saltos repetidos del grafo interno.
- Instalado el crawler reproducible `scripts/technical-crawl.py` y el comando `npm run seo:crawl`.

## Avisos que permanecen

No quedan errores 4XX internos, pero hay trabajo de higiene SEO en la tienda:

1. **Canonicals en archivos de WordPress:** 54 URLs de etiquetas, categorías, autores, marca y paginaciones no declaran canonical. Hay que decidir cuáles deben indexarse y aplicar canonical o `noindex` de forma coherente.
2. **Meta descriptions:** 46 URLs de tienda tienen descripción corta y 37 larga. La mayoría son archivos y páginas heredadas; no conviene escribir 83 textos a ciegas, sino reducir primero el conjunto indexable.
3. **Enlaces a redirecciones:** quedan 15 destinos redirigidos y 43 relaciones fuente-destino. La mayoría son rutas heredadas o normalización de barra final. No rompen navegación, pero deben sustituirse progresivamente por el destino final.
4. **Jerarquía H1:** 19 páginas de tienda y una ruta redirigida no presentan exactamente un H1. Priorizar home, tienda, blog y páginas comerciales; carrito, checkout y documentos legales no son prioridad SEO.
5. **`noindex`:** los cinco casos detectados son intencionados o correctos: carrito, checkout, legales y dos variantes `replytocom`.

Los tiempos observados durante un crawl no sustituyen Core Web Vitals ni PageSpeed: incluyen la cadencia deliberada del auditor y la protección anti-rastreo de WordPress. El rendimiento debe validarse por separado con datos de campo y pruebas Lighthouse controladas.

## Verificación

Después del despliegue se repitió el rastreo completo con seguimiento de redirecciones y resolución de enlaces relativos contra la URL final. Resultado final:

```text
151 URLs públicas con respuesta 200
0 destinos internos rotos
0 destinos externos 404/410
12 sitemaps válidos
0 errores de schema JSON-LD
```

Ahrefs debería retirar los errores 4XX en el siguiente rastreo. Se puede acelerar desde Site Audit con un recrawl del proyecto, pero no es necesario solicitar indexación en Search Console para una simple corrección de enlaces internos.
