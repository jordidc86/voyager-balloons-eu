# Sistema de backlinks y colaboraciones

Este sistema permite prospectar, priorizar y preparar outreach para conseguir menciones y enlaces de calidad hacia Voyager Balloons. Tras probar acciones locales con baja disposicion, la prioridad pasa a medios nacionales, guias internacionales, blogs de viaje con audiencia en Madrid/Espana y plataformas globales de experiencias.

No envia emails automaticamente. Genera borradores para aprobarlos antes de contactar.

## Principios

- Prioridad: autoridad nacional/internacional y demanda de visitantes de Madrid por encima de volumen local.
- Objetivo: reforzar autoridad para busquedas como "vuelo en globo Segovia", "paseo en globo Segovia", "que hacer en Segovia" y "regalo experiencia Madrid".
- Seguridad SEO: evitar compra masiva de enlaces, intercambios artificiales y directorios de baja calidad.
- Si hay compensacion clara, tratarlo como colaboracion patrocinada y aceptar `rel="sponsored"` o `nofollow` cuando corresponda.
- Nunca pedir "enlace follow a cambio de vuelo". La propuesta debe ser editorial, util y honesta.

## Archivos

- `data/backlinks/opportunities.csv`: base principal de oportunidades.
- `data/backlinks/private_contacts.example.csv`: ejemplo para crear una base privada no versionada.
- `data/backlinks/discovery-queries.csv`: busquedas para descubrir oportunidades nuevas.
- `data/backlinks/competitors.json`: competidores usados para rastrear menciones.
- `data/backlinks/candidate_urls.txt`: URLs candidatas para escanear.
- `data/backlinks/link_audit.csv`: estado del ultimo control de enlaces publicados.
- `templates/outreach/*.md`: plantillas por tipo de contacto.
- `scripts/backlink-outreach.js`: motor local de scoring, borradores, escaneo y auditoria.
- `data/backlinks/media-pack/`: textos, checklist, lote piloto y carpeta para fotos editoriales.

Los borradores y reportes generados se guardan en `data/backlinks/drafts/` y `data/backlinks/reports/`. Estan ignorados por Git para no subir contactos o mensajes sensibles.

Las fotos del media pack se dejan en `data/backlinks/media-pack/photos/raw/`. Tambien estan ignoradas por Git.

## Flujo recomendado

1. Anadir oportunidades a `data/backlinks/opportunities.csv`.
2. Ejecutar scoring:

```bash
npm run backlinks:score
```

3. Revisar el ranking generado en `data/backlinks/reports/`.
4. Generar borradores de la tanda:

```bash
npm run backlinks:draft
```

5. Revisar los borradores en `data/backlinks/drafts/`.
6. Preparar o revisar el media pack de fotos.
7. Aprobar manualmente los mensajes que se van a enviar.
8. Tras enviar, actualizar `status` en `opportunities.csv` a `sent`.
9. Si responden, marcar `replied`; si se consigue enlace o mencion, marcar `won`.
10. Auditar enlaces vivos:

```bash
npm run backlinks:audit
```

## Estados

- `new`: oportunidad sin cualificar.
- `qualified`: oportunidad validada para preparar contacto.
- `drafted`: borrador preparado.
- `approved`: aprobado para envio.
- `sent`: enviado.
- `replied`: hubo respuesta.
- `won`: enlace, mencion o colaboracion conseguida.
- `lost`: descartado.
- `do_not_contact`: no contactar.

## Tipos utiles

- `travel_blog`
- `international_travel_blog`
- `travel_guide`
- `international_travel_guide`
- `media_blog`
- `national_media`
- `local_media`
- `institutional_directory`
- `marketplace_directory`
- `tour_marketplace`
- `affiliate_platform`
- `gift_marketplace`
- `experience_platform`
- `creator`
- `owned_social`
- `partner`

## Paginas destino

- `https://www.voyagerballoons.eu/vuelo-en-globo-segovia`
- `https://www.voyagerballoons.eu/paseo-en-globo-segovia`
- `https://www.voyagerballoons.eu/regalar-vuelo-en-globo-segovia`
- `https://www.voyagerballoons.eu/vuelo-en-globo-segovia-desde-madrid`
- `https://www.voyagerballoons.eu/actividades-segovia`

## Tanda piloto

Primera tanda recomendada tras el pivote:

- 10 medios/guias nacionales o internacionales: Traveler, Guia Repsol, National Geographic Viajes, Lonely Planet, Rough Guides, Fodor's, PlanetWare, European Best Destinations.
- 10 plataformas globales o afiliadas: GetYourGuide, Viator, Klook, Musement, Tiqets, Headout, Fever, HelloTickets.
- 10 blogs o medios orientados a escapadas desde Madrid y experiencias en Espana.

Criterio de exito a 30 dias:

- 30 contactos cualificados.
- 20 mensajes aprobados y enviados.
- 5-8 respuestas positivas.
- 3-5 enlaces o menciones conseguidos.
- 0 envios sin aprobacion.
- 0 enlaces dudosos aceptados por volumen.

## Como descubrir oportunidades nuevas

Usar `data/backlinks/discovery-queries.csv` como lista de busquedas manuales o semiautomaticas. Cuando se encuentre una URL prometedora, anadirla a `data/backlinks/candidate_urls.txt` y ejecutar:

```bash
npm run backlinks:scan
```

El escaneo detecta menciones de competidores, enlaces actuales a Voyager y el tipo probable de oportunidad. Despues hay que pasar las mejores filas a `opportunities.csv`.

## Como importar contactos propios

Para bases sensibles de instagramers, agencias o clientes, crear un archivo no versionado:

```bash
cp data/backlinks/private_contacts.example.csv data/backlinks/private_contacts.csv
```

Ese archivo queda ignorado por Git. De momento se usa como staging manual: las mejores oportunidades se copian a `opportunities.csv` cuando esten listas para entrar en el pipeline.

## Auditoria mensual

Una vez al mes:

1. Ejecutar `npm run backlinks:audit`.
2. Revisar `data/backlinks/link_audit.csv`.
3. Comprobar si el enlace existe, anchor usado y atributo `rel`.
4. Medir en Search Console impresiones, clics y consultas de las paginas destino.
5. Subir prioridad a partners que generen trafico real o buenas respuestas.

## Ofertas recomendadas

- Medios nacionales/internacionales: recurso editorial con fotos reales, datos utiles y angulo "Segovia desde Madrid al amanecer".
- Guias de viaje: propuesta de actualizacion para contenidos sobre day trips from Madrid, things to do in Segovia y experiencias singulares en Espana.
- Plataformas internacionales: ficha precisa y optimizada, priorizando visibilidad internacional y reservas incrementales sin canibalizar la web directa.
- Blogs/medios: recurso editorial con fotos reales, datos utiles y angulo "Segovia desde el aire".
- Creadores: colaboracion con experiencia y contenido, priorizando quienes tengan web/blog ademas de Instagram.
- Directorios: alta o correccion de ficha con NAP, descripcion, fotos y URL canonica.
- Partners existentes: corregir enlace hacia la landing adecuada.

## Enfoque actual

No perseguir de forma activa acciones locales en Segovia salvo que exista una relacion personal clara o una oportunidad ya caliente. Esas oportunidades quedan como referencia o baja prioridad. El trabajo comercial debe concentrarse en:

- Captar demanda internacional de "day trip from Madrid".
- Entrar en listas de "things to do in Segovia/Spain".
- Conseguir menciones en medios nacionales con autoridad.
- Crear o mejorar fichas en plataformas globales cuando aporten visibilidad real.
- Usar contenidos visuales propios como diferencial: Segovia desde el aire, amanecer, Alcazar, Catedral, sierra y experiencia premium.

## Media pack

Carpeta principal:

`data/backlinks/media-pack/`

Contenido:

- `README.md`: instrucciones de fotos.
- `photo-manifest.csv`: inventario de fotos con alt text y permisos.
- `copy/company-boilerplate-es.md`: descripcion en espanol.
- `copy/company-boilerplate-en.md`: descripcion en ingles.
- `copy/editorial-angles.md`: angulos editoriales.
- `batches/batch-01-national-international.csv`: tanda inicial.
- `checklist-before-send.md`: control antes de enviar.

Las fotos originales deben ir en:

`data/backlinks/media-pack/photos/raw/`
