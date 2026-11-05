const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('UI starts a synthetic session and runs the local choice without leaking caller data', async () => {
  const nodes = {};
  const element = id => nodes[id] ||= {textContent:'', innerHTML:'', className:'', disabled:false};
  const document = {getElementById:element, querySelectorAll:() => []};
  const calls = [], history = [];
  const config = {faults:{healthy:'No simulated fault'},tests:{reference:{name:'Reference',description:'Compare',unit:'°C',cost:.4}},meta_configured:false};
  async function fetcher(url, options={}) {
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push({url,body});
    let result;
    if (url==='/api/config') result=config;
    else if (url==='/api/session') result={session:'synthetic-session'};
    else if (url==='/api/coverage-example') {
      const models=[{id:'healthy',label:'No modeled fault',low_prediction:.05,high_prediction:.07}, {id:'conditional_fault',label:'Fault appearing only at high demand',low_prediction:.05,high_prediction:.60}];
      const readings=[{condition:'low',value:.04},{condition:'high',value:.58}];
      result={bound:.10,units:'invented deviation units',reported_symptom:'high demand, unmeasured',stages:[0,1,2].map(n=>({readings:readings.slice(0,n),unobserved_conditions:['low','high'].slice(n),hypotheses:models.map(h=>({...h,compatible:n<2||h.id==='conditional_fault'}))}))};
    }
    else if (url==='/api/diagnose') result={history:[...history],posterior:{healthy:1},recommendations:history.length?[]:[{test:'reference',name:'Reference',information_gain:1,cost:.4}],assessment:null,sensitivity:{bound:1,status:history.length?'single':'no_observations',compatible_faults:['healthy'],hypotheses:[{label:'No simulated fault',compatible:true,residuals:history.map(h=>({test:h.test,unit:'°C',observed:h.value,predicted:0}))}],remaining_test:null}};
    else if (url==='/api/field-data') result={cases:[{date:'171207',condition:'induced infiltration',rows:96,room_mean_c:20,outside_mean_c:4}]};
    else if (url==='/api/choose') result={mode:'local',test:'reference',reason:'Local fallback'};
    else if (url==='/api/observe') { history.push({test:body.test,value:0.1}); result={value:0.1}; }
    else throw Error(`Unexpected endpoint ${url}`);
    return {ok:true,json:async()=>result};
  }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8'),{document,fetch:fetcher,Math,alert:message=>{throw Error(message)}});
  await new Promise(resolve => setImmediate(resolve));
  assert.match(element('handoff').textContent,/SYNTHETIC EXERCISE/);
  assert.equal(element('coverage-high').disabled,true);
  await element('coverage-low').onclick();
  assert.match(element('coverage-result').textContent,/normal low-demand reading does not rule out/);
  assert.match(element('coverage-handoff').textContent,/NOT YET OBSERVED: high demand/);
  assert.equal(element('coverage-high').disabled,false);
  await element('coverage-high').onclick();
  assert.match(element('coverage-result').textContent,/No modeled fault: does not fit/);
  assert.match(element('coverage-result').textContent,/Fault appearing only at high demand: still fits/);
  assert.match(element('coverage-result').textContent,/unmodeled causes remain possible/);
  await element('coverage-reset').onclick();
  assert.match(element('coverage-result').textContent,/None yet/);
  assert.match(element('assessment').textContent,/at least two/);
  await element('field').onclick();
  assert.match(element('field-result').textContent,/induced infiltration/);
  assert.match(element('field-result').textContent,/Do not infer/);
  await element('choose').onclick();
  assert.match(element('handoff').textContent,/Reference: 0\.10/);
  assert.equal(element('choose').disabled,true);
  assert.deepEqual(calls.find(x=>x.url==='/api/choose').body,{session:'synthetic-session'});
  assert.deepEqual(calls.find(x=>x.url==='/api/observe').body,{session:'synthetic-session',test:'reference'});
});
