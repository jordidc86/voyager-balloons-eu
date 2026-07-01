(function () {
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
        'shop.voyagerballoons.eu'
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

  ['pointerdown', 'keydown', 'touchstart', 'scroll', 'wheel'].forEach(function (eventName) {
    window.addEventListener(eventName, loadOnInteraction, {
      once: true,
      passive: true,
      capture: true
    });
  });

  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href*="shop.voyagerballoons.eu"]');
    if (!link || loaded) return;

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
