
(function(){
  if(!/^(www\.)?voyagerballoons\.eu$|^tienda\.voyagerballoons\.eu$/.test(location.hostname) || window.voyagerMeasurement) return;
  var tagId='GT-55NTF5CN',analyticsId='G-4FT0KG5TKT',adsId='AW-11564692382',target='AW-11564692382/Dz2nCLDQgLwcEJ7nvIor';
  var cookieName='voyager_measurement_v1',loaded=false,pending=null,sent={},chosen=false;
  var consent={analytics:false,ads:false};
  var ids={},idsRequested=false,identityGeneration=0,identityWaiters=[];
  function identityState(){if(document.documentElement)document.documentElement.setAttribute('data-voyager-ga4-identity',!consent.analytics?'denied':ids.clientId&&ids.sessionId?'ready':'pending');}
  function finishIdentityWaiters(){
    if(!consent.analytics||(ids.clientId&&ids.sessionId))identityWaiters.splice(0).forEach(function(done){done();});
  }
  function refreshIds(force){
    if(!consent.analytics||(idsRequested&&!force))return;idsRequested=true;
    var generation=identityGeneration;identityState();
    window.gtag('get',analyticsId,'client_id',function(v){if(generation===identityGeneration&&consent.analytics&&/^[0-9]{1,20}\.[0-9]{1,20}$/.test(String(v)))ids.clientId=String(v);identityState();finishIdentityWaiters();});
    window.gtag('get',analyticsId,'session_id',function(v){if(generation===identityGeneration&&consent.analytics&&/^[0-9]{1,20}$/.test(String(v)))ids.sessionId=String(v);identityState();finishIdentityWaiters();});
  }
  function readyIdentifiers(timeoutMs){
    if(!consent.analytics)return Promise.resolve({});
    load();refreshIds(true);
    return new Promise(function(resolve){
      var finished=false;
      function done(){if(finished)return;finished=true;identityWaiters=identityWaiters.filter(function(f){return f!==done;});resolve(consent.analytics?Object.assign({},ids):{});}
      identityWaiters.push(done);finishIdentityWaiters();
      setTimeout(done,Math.min(2000,Math.max(0,Number(timeoutMs)||1500)));
      setTimeout(function(){if(!finished&&consent.analytics)refreshIds(true);},400);
    });
  }
  window.dataLayer=window.dataLayer||[];
  window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};
  window.gtag('consent','default',{analytics_storage:'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
  window.gtag('set','ads_data_redaction',true);
  var raw=document.cookie.split(';').map(function(x){return x.trim();}).find(function(x){return x.indexOf(cookieName+'=')===0;});
  if(raw){var parts=raw.slice(cookieName.length+1).split('.');if(parts.length===3&&parts[0]==='2'&&/^[01]$/.test(parts[1])&&/^[01]$/.test(parts[2])){chosen=true;consent={analytics:parts[1]==='1',ads:parts[2]==='1'};}}
  function update(){window.gtag('consent','update',{analytics_storage:consent.analytics?'granted':'denied',ad_storage:consent.ads?'granted':'denied',ad_user_data:consent.ads?'granted':'denied',ad_personalization:consent.ads?'granted':'denied'});}
  function load(){
    if(loaded||!(consent.analytics||consent.ads))return;
    loaded=true;
    window.gtag('set','linker',{domains:['voyagerballoons.eu','www.voyagerballoons.eu','tienda.voyagerballoons.eu'],accept_incoming:true,decorate_forms:true});
    window.gtag('js',new Date());window.gtag('config',tagId);window.gtag('config',adsId,{allow_enhanced_conversions:false});refreshIds();
    var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(tagId);s.onload=function(){refreshIds(true);};document.head.appendChild(s);
  }
  function openaiClick(){
    var name='voyager_openai_click_v1',suffix='; Domain=voyagerballoons.eu; Path=/; SameSite=Lax; Secure';
    function clear(){document.cookie=name+'=; Max-Age=0'+suffix;}
    function valid(v){return typeof v==='string'&&v.length>0&&v.length<=2048&&!/[\u0000-\u0020\u007f]/.test(v)&&encodeURIComponent(v).length<=3800;}
    if(!consent.ads){clear();return '';}
    var incoming=new URL(location.href).searchParams.get('oppref');
    if(valid(incoming)){
      var current=document.cookie.split(';').map(function(v){return v.trim();}).find(function(v){return v.indexOf(name+'=')===0;});
      var encoded=encodeURIComponent(incoming);
      if(!current||current.slice(name.length+1)!==encoded)document.cookie=name+'='+encoded+'; Max-Age=2592000'+suffix;
      return incoming;
    }
    try{
      var stored=document.cookie.split(';').map(function(v){return v.trim();}).find(function(v){return v.indexOf(name+'=')===0;});
      var value=stored?decodeURIComponent(stored.slice(name.length+1)):'';
      return valid(value)?value:'';
    }catch(e){clear();return '';}
  }
  function acquisition(){
    var data={},url=new URL(location.href),key='voyager_measurement_attribution_v1';
    try{data=JSON.parse(sessionStorage.getItem(key)||'{}');}catch(e){}
    if(!data||typeof data!=='object'||Array.isArray(data))data={};
    var fields=consent.analytics?['utm_source','utm_medium','utm_campaign','utm_content','utm_term']:[];
    if(consent.ads)fields=fields.concat(['gclid','gbraid','wbraid','fbclid']);
    if(consent.analytics&&url.searchParams.get('utm_source')&&['utm_source','utm_medium','utm_campaign','utm_content'].some(function(k){return (url.searchParams.get(k)||'')!==(data[k]||'');}))data={};
    fields.forEach(function(k){var v=url.searchParams.get(k);if(v&&!data[k])data[k]=v.replace(/[\u0000-\u001f\u007f]/g,'').slice(0,500);});
    Object.keys(data).forEach(function(k){if(fields.indexOf(k)<0)delete data[k];});
    try{if(fields.length)sessionStorage.setItem(key,JSON.stringify(data));else sessionStorage.removeItem(key);}catch(e){}
    var oppref=openaiClick();if(oppref)data.oppref=oppref;
    return data;
  }
  function deliver(channel,name,params){
    var key='voyager_purchase_'+channel+'_'+params.transaction_id;
    try{if(sessionStorage.getItem(key)==='sent')return;}catch(e){}
    if(sent[key])return;sent[key]=true;load();
    window.gtag('event',name,Object.assign({},params,{event_callback:function(){try{sessionStorage.setItem(key,'sent');}catch(e){}}}));
  }

  var partnerLoaded=false,partnerReady={openai:false,meta:false};
  function partnerConsent(){
    try{if(window.oaiq)window.oaiq('consent',consent.ads);}catch(e){}
    try{if(window.fbq)window.fbq('consent',consent.ads?'grant':'revoke');}catch(e){}
    if(!consent.ads||partnerLoaded)return;
    partnerLoaded=true;
    if(!window.oaiq){var q=function(){q.q.push(arguments);};q.q=[];window.oaiq=q;
      var o=document.createElement('script');o.async=true;o.onload=function(){partnerReady.openai=true;if(pending)partnerPurchase(pending);};o.src='https://bzrcdn.openai.com/sdk/oaiq.min.js';document.head.appendChild(o);}
    window.oaiq('consent',true);window.oaiq('init',{pixelId:'1Ctd288nhCPeqfiwRb9eXp'});
    window.oaiq('measure','page_viewed',{type:'contents'},{opt_out:true});
    if(!window.fbq){var f=function(){f.callMethod?f.callMethod.apply(f,arguments):f.queue.push(arguments);};
      f.queue=[];f.push=f;f.loaded=true;f.version='2.0';window.fbq=f;window._fbq=f;
      var m=document.createElement('script');m.async=true;m.onload=function(){partnerReady.meta=true;if(pending)partnerPurchase(pending);};m.src='https://connect.facebook.net/en_US/fbevents.js';document.head.appendChild(m);}
    window.fbq('consent','grant');window.fbq('set','autoConfig',false,'231034488264198');
    window.fbq('init','231034488264198');window.fbq('trackSingle','231034488264198','PageView');
  }
  function partnerPurchase(p){
    if(!consent.ads)return;partnerConsent();
    // A queued SDK command is not delivery. Keep a failed/blocked load retryable
    // on receipt reload; each provider is independent. This records dispatch,
    // never an acknowledgement from Meta/OpenAI.
    ['openai','meta'].forEach(function(provider){
      if(!partnerReady[provider])return;
      var key='voyager_purchase_dispatched_'+provider+'_'+p.transaction_id;
      try{if(sessionStorage.getItem(key)==='dispatched')return;}catch(e){}
      if(sent[key])return;
      try{
        if(provider==='openai')window.oaiq('measure','order_created',{type:'contents',amount:Math.round(p.value*100),currency:p.currency},{event_id:p.transaction_id,opt_out:true});
        else window.fbq('trackSingle','231034488264198','Purchase',{value:p.value,currency:p.currency},{eventID:p.transaction_id});
        sent[key]=true;
        try{sessionStorage.setItem(key,'dispatched');}catch(e){}
      }catch(e){/* Leave this provider retryable; do not suppress the other. */}
    });
  }

  function purchase(p){
    if(!p||!/^vbs-[A-Za-z0-9]{5,12}$/.test(p.transaction_id)||!Number.isFinite(p.value)||p.value<=0||p.currency!=='EUR'||!Array.isArray(p.items))return;
    pending=p;partnerPurchase(p);
    if(consent.analytics&&p.server_ga4!==true){var gaPayload=Object.assign({},p,{send_to:analyticsId});delete gaPayload.server_ga4;deliver('ga4','purchase',gaPayload);}
    if(consent.ads)deliver('ads','conversion',{send_to:target,transaction_id:p.transaction_id,value:p.value,currency:p.currency});
  }
  function choose(analytics,ads){
    chosen=true;consent={analytics:!!analytics,ads:!!ads};
    document.cookie=cookieName+'=2.'+(analytics?'1':'0')+'.'+(ads?'1':'0')+'; Domain=voyagerballoons.eu; Path=/; Max-Age=15552000; SameSite=Lax; Secure';
    update();acquisition();if(!analytics){identityGeneration++;ids={};idsRequested=false;finishIdentityWaiters();try{sessionStorage.removeItem('voyager_attribution_v1');}catch(e){}}else if(loaded)refreshIds();
    var p=document.getElementById('voyager-consent-panel');if(p)p.hidden=true;
    partnerConsent();identityState();window.dispatchEvent(new CustomEvent('voyager:consent',{detail:consent}));load();if(pending)purchase(pending);
  }
  window.voyagerMeasurement={consent:function(){return Object.assign({},consent);},attribution:acquisition,identifiers:function(){return consent.analytics?Object.assign({},ids):{};},readyIdentifiers:readyIdentifiers,choose:choose};
  window.voyagerTrack=function(name,params){if(!consent.analytics)return false;load();window.gtag('event',name,params||{});return true;};
  window.addEventListener('voyager:purchase',function(e){purchase(e.detail);});
  update();acquisition();identityState();partnerConsent();
  function mount(){
    var en=location.pathname.indexOf('/en/')===0||new URL(location.href).searchParams.get('lang')==='en';
    var style=document.createElement('style');style.textContent='#voyager-consent-panel{position:fixed;inset:auto 12px 12px;z-index:10000;max-width:620px;margin:auto;padding:16px;background:#fff;color:#202020;box-shadow:0 2px 18px #0003;border:1px solid #ddd;border-radius:6px;font:14px/1.5 Arial,sans-serif}#voyager-consent-panel[hidden]{display:none}#voyager-consent-panel p{margin:0 0 10px}#voyager-consent-panel label{display:inline-flex;align-items:center;gap:6px;margin:0 16px 10px 0}#voyager-consent-panel input{width:18px;height:18px}#voyager-consent-panel .choices{display:flex;flex-wrap:wrap;gap:8px}#voyager-consent-panel button{background:#fff;color:#222;border:1px solid #555;border-radius:4px;padding:9px 12px;min-height:44px;font:inherit;cursor:pointer}#voyager-consent-settings{display:block;margin:12px auto;padding:8px;background:transparent;color:inherit;border:0;text-decoration:underline;font:12px Arial,sans-serif;cursor:pointer}';document.head.appendChild(style);
    var panel=document.createElement('section');panel.id='voyager-consent-panel';panel.setAttribute('aria-label',en?'Cookie preferences':'Preferencias de cookies');panel.hidden=chosen;
    panel.innerHTML='<p>'+(en?'We use optional cookies to understand visits and measure advertising with Google, OpenAI and Meta. You can reject them and book normally.':'Usamos cookies opcionales para entender las visitas y medir la publicidad con Google, OpenAI y Meta. Puedes rechazarlas y reservar con normalidad.')+'</p><label><input type="checkbox" id="vb-consent-analytics">'+(en?'Analytics':'Analítica')+'</label><label><input type="checkbox" id="vb-consent-ads">'+(en?'Advertising':'Publicidad')+'</label><div class="choices"><button type="button" data-choice="reject">'+(en?'Reject all':'Rechazar todas')+'</button><button type="button" data-choice="save">'+(en?'Save choice':'Guardar elección')+'</button><button type="button" data-choice="accept">'+(en?'Accept all':'Aceptar todas')+'</button></div>';
    var policy=document.createElement('a');policy.href=en?'https://www.voyagerballoons.eu/en/legal#cookies':'https://www.voyagerballoons.eu/legales#cookies';policy.textContent=en?'Cookie policy':'Política de cookies';policy.style.cssText='display:inline-block;margin-top:10px;color:#202020;text-decoration:underline';panel.appendChild(policy);
    document.body.appendChild(panel);
    panel.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){var a=b.dataset.choice;choose(a==='accept'||a==='save'&&panel.querySelector('#vb-consent-analytics').checked,a==='accept'||a==='save'&&panel.querySelector('#vb-consent-ads').checked);});});
    var settings=document.createElement('button');settings.id='voyager-consent-settings';settings.type='button';settings.textContent=en?'Cookie preferences':'Preferencias de cookies';settings.addEventListener('click',function(){panel.hidden=false;panel.querySelector('#vb-consent-analytics').checked=consent.analytics;panel.querySelector('#vb-consent-ads').checked=consent.ads;panel.querySelector('button').focus();});document.body.appendChild(settings);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else setTimeout(mount,0);
  ['pointerdown','keydown','touchstart'].forEach(function(n){window.addEventListener(n,load,{once:true,passive:true,capture:true});});
  function schedule(){setTimeout(function(){if('requestIdleCallback'in window)window.requestIdleCallback(load,{timeout:2000});else load();},12000);}
  if(document.readyState==='complete')schedule();else window.addEventListener('load',schedule,{once:true});
})();(function () {
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

    var acquisition = window.voyagerMeasurement ? window.voyagerMeasurement.attribution() : {};
    destination.searchParams.delete('oppref');
    Object.keys(acquisition).forEach(function (field) {
      var value = acquisition[field];
      if (value && !destination.searchParams.has(field)) destination.searchParams.set(field, value);
    });

    var referrerHost = '';
    try { referrerHost = document.referrer ? new URL(document.referrer).hostname.toLowerCase() : ''; } catch (_error) {}
    if (window.voyagerMeasurement && window.voyagerMeasurement.consent().analytics && !destination.searchParams.has('gclid') && !destination.searchParams.has('gbraid') && !destination.searchParams.has('wbraid') && !destination.searchParams.has('utm_source') && referrerHost) {
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
  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href*="tienda.voyagerballoons.eu"], a[href*="shop.voyagerballoons.eu"]');
    if (!link) return;
    var legacy = storefrontUrl(link);
    if (legacy) link.href = legacy;
    decorateStorefrontAttribution(link);
    // Navigation never waits for an analytics request.
  }, true);
})();
