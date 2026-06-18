# Auditoría SEO Competitiva - Voyager Balloons Segovia

Fecha: 2026-06-18  
Objetivo: ser una de las opciones más visibles y citables para búsquedas de vuelos en globo, actividades en Segovia, escapadas desde Madrid y regalos experiencia.

## Resumen ejecutivo

Voyager Balloons ya tiene una base técnica bastante mejor que al inicio: robots, sitemap, canonical, schema, páginas indexables limpias y una landing específica para "qué hacer en Segovia". El mayor reto no es Lighthouse, sino autoridad y profundidad comercial frente a competidores con años de señales, reseñas, menciones en agregadores y páginas muy orientadas a "vuelo en globo Segovia".

La oportunidad clara está en posicionarnos como la opción más directa, clara y fácil de reservar:

- Precio de entrada mucho más competitivo: Classic Adventure desde 120 euros frente a competidores que muestran 205 euros.
- Página propia para intención amplia: "qué hacer en Segovia", "actividades en Segovia", "planes desde Madrid".
- Compra directa en subdominio propio.
- Mensaje de regalo fuerte: billetes regalo sin caducidad.

La prioridad ahora es reforzar contenido transaccional, confianza y autoridad externa.

## Competidores observados

### Siempre en las Nubes

Página fuerte para "volar en globo en Segovia". Incluye ficha de zona, duración, hora, qué incluye, opcionales, pilotos, contacto y reserva. Declara vuelo de 1 hora, actividad de unas 3 horas, brindis con cava, picnic, diplomas, vídeo HD, reportaje fotográfico y seguro.

Fortalezas:

- Página muy específica para Segovia.
- Mucha información práctica en una sola URL.
- Enlaces a reserva, indicaciones, pilotos, servicios y FAQs.
- Señales de confianza y teléfono visible.

Debilidades aprovechables:

- Diseño menos moderno.
- Mucha información dispersa.
- No parece tan directa para intención "qué hacer en Segovia" o regalo desde Madrid.

Fuente: https://www.siempreenlasnubes.com/rutas-para-volar-en-globo/globo-rutas-segovia/

### Globos Boreal

Producto WooCommerce muy transaccional. Muestra precio 205 euros, valoraciones, duración total 3 a 4 horas, altura, cava, desayuno, diploma, fotos y vídeo. Tiene reseñas visibles en la ficha.

Fortalezas:

- Página de producto clara.
- Precio y carrito visibles.
- Reseñas en página.
- Mucha autoridad local y menciones históricas.

Debilidades aprovechables:

- La ficha es más tienda que guía.
- Menos narrativa para visitantes de Madrid y compradores de regalo.
- Nosotros podemos competir por claridad, precio y guía editorial.

Fuente: https://globosboreal.com/product/paseo-en-globo-segovia

### Aerodifusión

Muy fuerte en autoridad, antigüedad y precio. La página de Segovia habla de compra/regalo, fechas, niños, recogida, vuelo exclusivo y pack con comida. Muestra adulto 205 euros, infantil 165 euros, privado para dos 975 euros.

Fortalezas:

- Mucha autoridad histórica.
- Estructura por destino.
- Precios claros.
- Argumenta bien Segovia como complemento de visita turística desde Madrid.

Debilidades aprovechables:

- Precio más alto.
- La página mezcla muchas opciones y puede sentirse menos directa.
- Podemos construir mejores páginas por intención concreta: regalos, Madrid, pareja, qué hacer.

Fuente: https://aerodifusion.es/destinos-vuelo-en-globo/vuelo-en-globo-segovia/

### Aerotours

Página de marca amplia con Segovia, Madrid, Aranjuez y Toledo. Destaca experiencia, flota, regalos y 35 años de experiencia.

Fortalezas:

- Marca con recorrido.
- Cobertura geográfica amplia.
- Página con intención regalo y experiencia.

Debilidades aprovechables:

- Menos foco único en Segovia.
- Menos optimizada para una búsqueda local concreta que una landing dedicada.

Fuente: https://aerotours.com/es/

### Turismo de Segovia y agregadores

Turismo de Segovia y TripAdvisor no siempre compiten igual que una operadora directa, pero son fuentes de autoridad que las IA pueden citar. TripAdvisor muestra varias experiencias desde 205 euros y muchas reseñas. Turismo de Segovia refuerza la idea de Segovia como destino top para vuelo en globo.

Fuentes:

- https://turismodesegovia.com/es/turismo-deportivo-y-activo/vuela-en-globo
- https://www.tripadvisor.es/Attractions-g187494-Activities-c61-t213-Segovia_Province_of_Segovia_Castile_and_Leon.html

## Estado técnico actual

### Bien resuelto

- `robots.txt` publicado.
- `sitemap.xml` publicado.
- Canonicals en páginas indexables.
- URLs limpias en canonical y sitemap.
- Home con `LocalBusiness`, `Product`, `Offer`, `FAQPage` y `BreadcrumbList`.
- Landing de actividades con `Article`, `Product`, `ItemList`, `FAQPage` y `BreadcrumbList`.
- Artículos con `Article` y `BreadcrumbList`.
- `exito.html`, `error.html` y legales en `noindex, follow`.
- Dominio sin `www` redirige a `www`.

### Mejoras aplicadas en esta revisión

- Redirecciones 301 desde:
  - `/blog.html` a `/blog`
  - `/actividades-segovia.html` a `/actividades-segovia`
  - `/articulos/:slug.html` a `/articulos/:slug`

Esto reduce duplicidad y alinea enlaces internos, canonical, sitemap y URLs públicas.

## Brechas frente a competidores

### 1. Falta una landing comercial pura para "vuelo en globo Segovia"

La home ataca "vuelos en globo en Segovia", pero los competidores tienen URLs específicas muy transaccionales. Necesitamos una página dedicada:

- `/vuelo-en-globo-segovia`
- H1 exacto: "Vuelo en globo en Segovia"
- Precio desde 120 euros.
- Duración, hora, qué incluye, condiciones meteorológicas, niños, regalo, vuelo privado.
- CTA arriba, medio y final.
- Schema `Product`, `Offer`, `FAQPage`, `BreadcrumbList`.

Prioridad: P0.

### 2. Falta una página "vuelo en globo desde Madrid"

Muchos visitantes buscan escapadas desde Madrid. Competidores mencionan recogida o distancia. Aunque no ofrezcamos traslado ahora, podemos posicionar:

- "Vuelo en globo en Segovia desde Madrid"
- Cómo organizar la escapada.
- Horarios al amanecer.
- Plan recomendado después del vuelo.
- Para quién encaja.

Prioridad: P0.

### 3. Falta prueba social propia visible sin depender de cookies

Las reseñas de Elfsight solo aparecen si el usuario acepta cookies externas. Google e IA pueden no verlas. Necesitamos una sección HTML propia con reseñas reales seleccionadas, enlazando a la fuente cuando sea posible.

No usar `aggregateRating` salvo que tengamos una fuente verificable y visible.

Prioridad: P0.

### 4. Falta autoridad de entidad

Los competidores tienen señales de antigüedad, pilotos, certificaciones, menciones institucionales o agregadores. Voyager necesita una página de confianza:

- `/seguridad-pilotos`
- Quiénes somos.
- Experiencia real: más de 25 años volando.
- Pilotos, permisos, seguros, seguridad meteorológica.
- Qué pasa si se cancela.
- Fotos reales del equipo y globos.

Prioridad: P1.

### 5. Blog insuficiente para dominar long-tail

Tenemos cuatro artículos más la guía de actividades. Para superar competidores y aparecer en respuestas de IA, hacen falta clusters:

- Precio vuelo en globo Segovia.
- Vuelo en globo Segovia desde Madrid.
- Regalar vuelo en globo en Segovia.
- Vuelo en globo para parejas en Segovia.
- Qué ver en Segovia después de volar en globo.
- Mejor época para volar en globo en Segovia.
- ¿Da miedo volar en globo?
- Vuelo privado en globo para dos en Segovia.

Prioridad: P1.

### 6. Faltan menciones externas y distribución

Para ser "los mejores" en SEO local no basta con la web. Necesitamos señales externas:

- Google Business Profile optimizado y con reseñas constantes.
- Menciones en Turismo de Segovia, blogs locales, prensa, experiencias regalo y directorios turísticos.
- TripAdvisor/Viator/GetYourGuide/Smartbox si interesan como canales, aunque priorizando que la web directa tenga mejor margen.
- Enlaces desde artículos sobre "qué hacer en Segovia".

Prioridad: P0/P1.

## Plan de trabajo priorizado

### Próximos 7 días

1. Crear `/vuelo-en-globo-segovia` como landing comercial principal.
2. Crear `/vuelo-en-globo-segovia-desde-madrid`.
3. Añadir reseñas reales en HTML visible.
4. Añadir bloque de confianza en home: precio desde 120 euros, más de 25 años volando, seguridad, reprogramación por meteorología.
5. Revisar la tienda WordPress para que el producto tenga título, meta description, schema y canonical correctos.

### Próximos 30 días

1. Publicar 4 artículos long-tail:
   - Precio vuelo en globo Segovia.
   - Regalar vuelo en globo en Segovia.
   - Mejor época para volar en globo.
   - Qué hacer en Segovia después de un vuelo en globo.
2. Crear página de seguridad/pilotos.
3. Montar proceso de solicitud de reseñas tras vuelo.
4. Optimizar Google Business Profile con fotos reales, posts y preguntas frecuentes.
5. Conseguir 3-5 menciones/enlaces locales.

### 60-90 días

1. Crear cluster completo de regalos, parejas, empresas y vuelos privados.
2. Trabajar comparativas editoriales: "vuelo en globo vs otras actividades en Segovia".
3. Mejorar activos visuales: fotos reales comprimidas en WebP/AVIF, alt text descriptivo.
4. Crear versiones en inglés si el volumen turístico internacional lo justifica.

## KPIs recomendados

- Impresiones y clics en Search Console para:
  - vuelo en globo Segovia
  - volar en globo Segovia
  - paseo en globo Segovia
  - qué hacer en Segovia
  - actividades en Segovia
  - regalo vuelo globo Segovia
  - vuelo globo Segovia desde Madrid
- CTR por página.
- Reservas directas desde orgánico.
- Consultas WhatsApp desde orgánico.
- Posición media de `/vuelo-en-globo-segovia` y `/actividades-segovia`.
- Reseñas nuevas por mes.

## Conclusión

La web ya tiene una base técnica sólida. Para superar competidores hay que pasar de "web correcta" a "máquina de intención": una página para cada búsqueda rentable, confianza visible, reseñas rastreables y autoridad local externa.

La siguiente pieza más importante es crear la landing específica `/vuelo-en-globo-segovia`. Esa debería ser la página que Google y las IA entiendan como la respuesta directa cuando alguien busca reservar un vuelo en globo en Segovia.
