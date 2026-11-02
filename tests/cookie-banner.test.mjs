import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../js/google-ads-tracking.js',import.meta.url),'utf8');
function browser(cookie='',path='/',host='www.voyagerballoons.eu') {
 const jar=new Map(cookie?[['voyager_measurement_v1',cookie]]:[]),docEvents={},events={},scripts=[],nodes=[],storage=new Map();
 let focused;
 class Element {
  constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.listeners={};this.hidden=false;this.style={};}
  setAttribute(k,v){this[k]=v;}
  appendChild(e){this.children.push(e);nodes.push(e);if(e.tagName==='script'&&e.src)scripts.push(e.src);return e;}
  addEventListener(n,f){this.listeners[n]=f;}
  focus(){focused=this;}
  click(){this.listeners.click?.();}
  set innerHTML(s){this.html=s;this.buttons=[...s.matchAll(/<button[^>]*data-choice="([^"]+)"[^>]*>([^<]+)<\/button>/g)].map(m=>{const e=new Element('button');e.dataset.choice=m[1];e.textContent=m[2];return e;});}
  querySelectorAll(s){return s==='button'?this.buttons||[]:[];}
  querySelector(s){return this.querySelectorAll(s)[0]||null;}
 }
 const document={readyState:'loading',head:new Element('head'),body:new Element('body'),documentElement:new Element('html'),createElement:t=>new Element(t),getElementById:id=>nodes.find(e=>e.id===id)||null,querySelectorAll:()=>[],addEventListener(n,f){(docEvents[n]??=[]).push(f);}};
 Object.defineProperty(document,'cookie',{get:()=>[...jar].map(([k,v])=>k+'='+v).join('; '),set:s=>{let[k,v]=s.split(';')[0].split('=');if(s.includes('Max-Age=0'))jar.delete(k);else jar.set(k,v);}});
 const location={hostname:host,pathname:path.split('?')[0],href:'https://'+host+path};
 const window={location,addEventListener(n,f){(events[n]??=[]).push(f);},dispatchEvent(e){events[e.type]?.forEach(f=>f(e));}};
 const context={window,document,location,URL,Promise,sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},CustomEvent:class{constructor(type,o){this.type=type;this.detail=o.detail;}},setTimeout(){}};
 vm.runInNewContext(source,context);
 docEvents.DOMContentLoaded.forEach(f=>f());
 return {window,document,jar,scripts,panel:document.getElementById('voyager-consent-panel'),settings:document.getElementById('voyager-consent-settings'),focused:()=>focused};
}
test('first visit shows exactly Accept and Reject, with optional tags blocked',()=>{
 const b=browser();assert.equal(b.panel.hidden,false);assert.deepEqual(b.panel.buttons.map(x=>x.textContent),['Aceptar','Rechazar']);assert.doesNotMatch(b.panel.html,/checkbox|Configurar|Guardar elección/);assert.match(b.panel.html,/Lo de las cookies… tú decides/);assert.equal(b.scripts.length,0);
});
test('reject persists denied consent, hides notice, and stays denied on return',()=>{
 const b=browser();b.panel.buttons[1].click();assert.equal(b.jar.get('voyager_measurement_v1'),'2.0.0');assert.equal(b.panel.hidden,true);assert.equal(b.scripts.length,0);assert.equal(browser(b.jar.get('voyager_measurement_v1')).panel.hidden,true);
});
test('accept grants both categories, hides notice, and persists across shop navigation',()=>{
 const b=browser();b.panel.buttons[0].click();assert.equal(b.jar.get('voyager_measurement_v1'),'2.1.1');assert.equal(b.panel.hidden,true);assert.ok(b.scripts.some(s=>s.includes('googletagmanager')));assert.ok(b.scripts.some(s=>s.includes('openai')));assert.ok(b.scripts.some(s=>s.includes('facebook')));assert.equal(browser(b.jar.get('voyager_measurement_v1'),'/regalar','tienda.voyagerballoons.eu').panel.hidden,true);
});
test('reopen and reject withdraws an existing choice without missing checkbox errors',()=>{
 const b=browser('2.1.1');b.settings.click();assert.equal(b.panel.hidden,false);assert.equal(b.focused(),b.panel.buttons[0]);b.panel.buttons[1].click();assert.equal(b.jar.get('voyager_measurement_v1'),'2.0.0');assert.equal(JSON.stringify(b.window.voyagerMeasurement.consent()),'{"analytics":false,"ads":false}');
});
test('previous granular choices are preserved until the visitor chooses again',()=>{
 for(const c of ['2.0.0','2.0.1','2.1.0','2.1.1']){const b=browser(c);assert.equal(b.panel.hidden,true);assert.equal(b.jar.get('voyager_measurement_v1'),c);}
});
test('English page and shop use translated buttons and working canonical policy link',()=>{
 for(const [p,h] of [['/en/','www.voyagerballoons.eu'],['/regalar?lang=en','tienda.voyagerballoons.eu']]){const b=browser('',p,h);assert.deepEqual(b.panel.buttons.map(x=>x.textContent),['Accept','Reject']);assert.equal(b.panel.children[0].href,'https://www.voyagerballoons.eu/legales#cookies');}
});

test('homepage reviews use the shared choice, never show a second banner, and load only once',()=>{
 const events={},docEvents={},scripts=[],note={hidden:false},widget={hidden:false},placeholder={dataset:{cookieSrc:'https://elfsightcdn.com/platform.js',cookieDefer:'true'}};
 let accepted=false;
 const document={getElementById:()=>null,querySelector:s=>s==='.reviews-consent-note'?note:s.startsWith('[class^=')?widget:null,querySelectorAll:s=>s==='script[data-cookie-src]'?[placeholder]:[],addEventListener(n,f){docEvents[n]=f;},createElement:()=>({}),body:{appendChild:s=>scripts.push(s.src)}};
 const window={voyagerMeasurement:{consent:()=>({ads:accepted})},addEventListener(n,f){events[n]=f;}};
 vm.runInNewContext(readFileSync(new URL('../js/script.js',import.meta.url),'utf8'),{window,document,IntersectionObserver:class{observe(){}}});
 docEvents.DOMContentLoaded();assert.equal(scripts.length,0);assert.equal(widget.hidden,true);
 accepted=true;events['voyager:consent']();events['voyager:consent']();assert.equal(scripts.length,1);assert.equal(note.hidden,true);assert.equal(widget.hidden,false);
 accepted=false;events['voyager:consent']();assert.equal(widget.hidden,true);assert.equal(note.hidden,false);
 assert.doesNotMatch(readFileSync(new URL('../index.html',import.meta.url),'utf8'),/class="cookie-banner"/);
});
