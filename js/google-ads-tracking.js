(function () {
  if (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === '[::1]' ||
    window.location.hostname.endsWith('.localhost')
  ) {
    return;
  }

  var GTAG_ID = 'GT-55NTF5CN';
  var ADS_ID = 'AW-11564692382';
  var loaded = false;
  var scheduled = false;

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () {
    window.dataLayer.push(arguments);
  };

  function configureGtag() {
    window.gtag('set', 'linker', {
      domains: [
        'voyagerballoons.eu',
        'www.voyagerballoons.eu',
        'tienda.voyagerballoons.eu'
      ],
      accept_incoming: true,
      decorate_forms: true
    });

    window.gtag('js', new Date());
    window.gtag('config', GTAG_ID);
    window.gtag('config', ADS_ID);
  }

  function loadGtag() {
    if (loaded) return;
    loaded = true;

    var script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GTAG_ID);
    document.head.appendChild(script);

    configureGtag();
  }

  function scheduleGtag() {
    if (scheduled) return;
    scheduled = true;

    var afterLoad = function () {
      window.setTimeout(function () {
        if ('requestIdleCallback' in window) {
          window.requestIdleCallback(loadGtag, { timeout: 1500 });
        } else {
          loadGtag();
        }
      }, 4200);
    };

    if (document.readyState === 'complete') {
      afterLoad();
    } else {
      window.addEventListener('load', afterLoad, { once: true });
    }
  }

  function loadOnInteraction() {
    loadGtag();
  }

  function storefrontUrl(link) {
    var source;
    try { source = new URL(link.href, window.location.href); } catch (_error) { return ''; }
    if (source.hostname !== 'shop.voyagerballoons.eu') return '';
    var legacyPath = source.pathname.toLowerCase();
    var legacyProduct = source.searchParams.get('add-to-cart');
    var label = (link.textContent || '').toLowerCase();
    if (legacyPath.indexOf('braganza') !== -1 || legacyPath.indexOf('braganca') !== -1) {
      return 'https://www.aosabordovento.net/voo-de-balao-braganca';
    }
    // Private flights are not yet available in the new Segovia checkout.
    if (legacyPath.indexOf('privado') !== -1 || legacyPath.indexOf('private') !== -1) return '';
    if (legacyPath.indexOf('segovia-comfort') !== -1 || legacyProduct === '4164') return 'https://tienda.voyagerballoons.eu/reservar?producto=comfort';
    if (label.indexOf('regal') !== -1 || window.location.pathname.indexOf('regalar') !== -1) return 'https://tienda.voyagerballoons.eu/regalar';
    return 'https://tienda.voyagerballoons.eu/reservar?producto=classic';
  }

  function updateLegacyStoreLinks() {
    document.querySelectorAll('a[href*="shop.voyagerballoons.eu"]').forEach(function (link) {
      var destination = storefrontUrl(link);
      if (destination) link.href = destination;
    });
  }

  function decorateStorefrontAttribution(link) {
    var destination;
    try { destination = new URL(link.href, window.location.href); } catch (_error) { return; }
    if (destination.hostname !== 'tienda.voyagerballoons.eu') return;

    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(function (field) {
      var value = new URL(window.location.href).searchParams.get(field);
      if (value && !destination.searchParams.has(field)) destination.searchParams.set(field, value);
    });

    var referrerHost = '';
    try { referrerHost = document.referrer ? new URL(document.referrer).hostname.toLowerCase() : ''; } catch (_error) {}
    if (!destination.searchParams.has('utm_source') && referrerHost) {
      if (/(^|\.)google\./.test(referrerHost)) {
        destination.searchParams.set('utm_source', 'google');
        destination.searchParams.set('utm_medium', 'organic');
      } else if (/(^|\.)bing\.com$/.test(referrerHost)) {
        destination.searchParams.set('utm_source', 'bing');
        destination.searchParams.set('utm_medium', 'organic');
      }
    }
    destination.searchParams.set('vb_landing_path', window.location.pathname || '/');
    if (referrerHost) destination.searchParams.set('vb_referrer_host', referrerHost);
    link.href = destination.toString();
  }

  updateLegacyStoreLinks();

  ['pointerdown', 'keydown', 'touchstart', 'scroll', 'wheel'].forEach(function (eventName) {
    window.addEventListener(eventName, loadOnInteraction, {
      once: true,
      passive: true,
      capture: true
    });
  });

  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href*="tienda.voyagerballoons.eu"], a[href*="shop.voyagerballoons.eu"]');
    if (!link) return;
    var legacyDestination = storefrontUrl(link);
    if (legacyDestination) link.href = legacyDestination;
    decorateStorefrontAttribution(link);
    if (loaded) return;

    event.preventDefault();
    loadGtag();

    window.setTimeout(function () {
      if (link.target === '_blank') {
        window.open(link.href, '_blank', 'noopener,noreferrer');
      } else {
        window.location.href = link.href;
      }
    }, 180);
  }, true);

  scheduleGtag();
})();
