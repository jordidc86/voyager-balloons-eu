import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const measurementBootstrap=readFileSync(new URL('../js/google-ads-tracking.js',import.meta.url),'utf8');
function setup(cookie='2.0.0',storage=new Map()) {
 const events={},scripts=[],jar=new Map([['voyager_measurement_v1',cookie]]);
 const document={readyState:'loading',head:{appendChild:s=>scripts.push(s.src)},documentElement:{setAttribute(){}},createElement:()=>({}),getElementById:()=>null,querySelectorAll:()=>[],addEventListener(){}};
 Object.defineProperty(document,'cookie',{get:()=>[...jar].map(([k,v])=>k+'='+v).join('; '),set:s=>{let [k,v]=s.split(';')[0].split('=');if(s.includes('Max-Age=0'))jar.delete(k);else jar.set(k,v)}});
 const location={hostname:'www.voyagerballoons.eu',pathname:'/reservar',href:'https://www.voyagerballoons.eu/reservar?fbclid=valid_click&oppref=oa_click'};
 const window={addEventListener:(n,f)=>events[n]=f,dispatchEvent(){}};
 vm.runInNewContext(measurementBootstrap,{window,document,location,URL,Promise,sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},CustomEvent:class{},setTimeout(){}});
 return {window,scripts,events,jar,storage};
}
const purchase={transaction_id:'vbs-1234567',value:240,currency:'EUR',items:[]};
test('no partner request before explicit consent; old cookie is not consent for Meta',()=>{for(const c of ['2.0.0','1.1.1']){let b=setup(c);b.events['voyager:purchase']({detail:purchase});assert.deepEqual(b.scripts,[]);assert.equal(b.window.fbq,undefined)}});
test('ads-only consent loads both pixels once, forwards click, amounts and matching event ID',()=>{let b=setup('2.0.1');assert.equal(b.scripts.length,2);assert.equal(b.window.voyagerMeasurement.attribution().fbclid,'valid_click');b.events['voyager:purchase']({detail:purchase});b.events['voyager:purchase']({detail:purchase});let oa=b.window.oaiq.q.map(x=>[...x]).filter(x=>x[1]==='order_created');let meta=b.window.fbq.queue.map(x=>[...x]).filter(x=>x[2]==='Purchase');assert.equal(oa.length,1);assert.equal(meta.length,1);assert.equal(oa[0][2].amount,24000);assert.equal(meta[0][3].value,240);assert.equal(oa[0][3].event_id,meta[0][4].eventID)});
test('revocation stops further purchases and removes advertising attribution',()=>{let b=setup('2.0.1');b.window.voyagerMeasurement.choose(false,false);b.events['voyager:purchase']({detail:purchase});assert.equal(b.window.oaiq.q.map(x=>[...x]).some(x=>x[1]==='order_created'),false);assert.equal(b.window.voyagerMeasurement.attribution().fbclid,undefined);assert.ok(b.window.fbq.queue.map(x=>[...x]).some(x=>x[0]==='consent'&&x[1]==='revoke'))});
test('invalid purchase is never sent',()=>{let b=setup('2.0.1');for(const p of [{...purchase,value:0},{...purchase,currency:'USD'},{...purchase,transaction_id:'bad'}])b.events['voyager:purchase']({detail:p});assert.equal(b.window.oaiq.q.map(x=>[...x]).some(x=>x[1]==='order_created'),false)});

test('purchase is not repeated after reloading the receipt in the same session',()=>{const a=setup('2.0.1');a.events['voyager:purchase']({detail:purchase});const b=setup('2.0.1',a.storage);b.events['voyager:purchase']({detail:purchase});assert.equal(b.window.fbq.queue.map(x=>[...x]).filter(x=>x[2]==='Purchase').length,0)});
