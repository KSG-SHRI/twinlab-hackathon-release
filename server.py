"""Local prototype server. Model calls are opt-in via the Choose or Explain controls."""
import json, os, secrets, threading, time, urllib.request, urllib.error
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from twin import FAULTS, LABELS, TESTS, SIGMA, predict, observe, posterior, recommendations, evaluate, sensitivity
from robustness import decision
from field_replay import FILES, DEFAULT, read_rows, average_c
from condition_coverage import coverage_example

ROOT=Path(__file__).parent
class NoRedirect(urllib.request.HTTPRedirectHandler):
    # Never forward an Authorization header to a redirect target.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_model_opener = urllib.request.build_opener(NoRedirect())

class ModelResponseError(Exception):
    pass

def model_call(payload, key):
    request = urllib.request.Request('https://api.meta.ai/v1/chat/completions',
        data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+key}, method='POST')
    with _model_opener.open(request, timeout=25) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ModelResponseError()
    try:
        result = json.loads(raw)
        content = result['choices'][0]['message']['content']
        if not isinstance(content, str) or len(content) > 4000:
            raise ValueError('Invalid content')
        return content
    except (ValueError, KeyError, IndexError, TypeError):
        raise ModelResponseError() from None

def parse_selection(content, recommendations):
    selected=json.loads(content)
    if not isinstance(selected,dict) or set(selected) != {'test','reason'} or selected['test'] not in [x['test'] for x in recommendations] or not isinstance(selected['reason'],str) or len(selected['reason'])>160:
        raise ValueError('Invalid selection')
    return selected

# Sessions contain only synthetic state. IDs and random seeds never enter model prompts.
# Expiration and a fixed capacity bound the in-memory state; a restart clears it.
SESSION_TTL = 1800
MAX_SESSIONS = 256
_sessions = OrderedDict()
_sessions_lock = threading.Lock()

def new_session():
    now = time.monotonic()
    with _sessions_lock:
        for key in list(_sessions):
            if now - _sessions[key]['created'] > SESSION_TTL:
                del _sessions[key]
        while len(_sessions) >= MAX_SESSIONS:
            _sessions.popitem(last=False)
        token = secrets.token_urlsafe(32)
        _sessions[token] = {'created': now, 'fault': secrets.choice(FAULTS),
                            'seed': secrets.randbits(64), 'history': []}
    return token

def synthetic_state(token, test=None, reveal=False):
    if not isinstance(token, str) or len(token) != 43:
        raise ValueError('Invalid or expired simulation session')
    with _sessions_lock:
        session = _sessions.get(token)
        if session is None or time.monotonic() - session['created'] > SESSION_TTL:
            _sessions.pop(token, None)
            raise ValueError('Invalid or expired simulation session')
        if test is not None:
            if test not in TESTS or any(item['test'] == test for item in session['history']):
                raise ValueError('Invalid or already used test')
            value = observe(session['fault'], test, session['seed'])
            session['history'].append({'test': test, 'value': value})
        history = [item.copy() for item in session['history']]
        answer = session['fault'] if reveal else None
    return history, answer

class Handler(BaseHTTPRequestHandler):
    def reply(self, obj, status=200):
        body=json.dumps(obj, allow_nan=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        routes={'/':('static/index.html','text/html'), '/app.js':('static/app.js','text/javascript'), '/style.css':('static/style.css','text/css')}
        if self.path in routes:
            path, mime=routes[self.path]; body=(ROOT/path).read_bytes(); self.send_response(200); self.send_header('Content-Type',mime+'; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path == '/api/config': self.reply({'faults':LABELS,'tests':TESTS,'meta_configured':bool(os.getenv('MODEL_API_KEY'))})
        elif self.path == '/api/evaluate': self.reply(evaluate())
        elif self.path == '/api/coverage-example': self.reply(coverage_example())
        elif self.path == '/api/challenge-example':
            # Fixed illustrative case, generated locally and independent of sessions.
            history = [{'test': 'coast', 'value': -2.5}]
            self.reply({'history': history, 'posterior': posterior(history), 'sensitivity': sensitivity(history)})
        elif self.path == '/api/field-data':
            try:
                rows = read_rows(DEFAULT)
                cases = []
                for filename, condition in FILES.items():
                    subset = [row for row in rows if row['source_file'] == filename]
                    inside, n_inside = average_c(subset, 'T_Room_106_Avg')
                    outside, n_outside = average_c(subset, 'T_out_Avg')
                    cases.append({'date':filename[:6], 'condition':condition, 'rows':len(subset),
                                  'room_mean_c':inside, 'outside_mean_c':outside,
                                  'valid_room':n_inside, 'valid_outside':n_outside})
                self.reply({'source':'DOE curated test fault dataset; public research facility; induced faults', 'cases':cases})
            except (OSError, ValueError, KeyError):
                self.reply({'error':'The public dataset extract is missing or invalid.'},503)
        else: self.send_error(404)
    def do_POST(self):
        try:
            host=self.headers.get('Host', '')
            port=self.server.server_port
            if host not in (f'127.0.0.1:{port}', f'localhost:{port}'):
                raise ValueError('Invalid host')
            origin=self.headers.get('Origin')
            if origin is not None and origin != f'http://{host}':
                raise ValueError('Invalid origin')
            if self.headers.get_content_type() != 'application/json':
                raise ValueError('JSON content type required')
            size=int(self.headers.get('Content-Length','0'))
            if size < 1 or size > 20000: raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data, dict): raise ValueError('Invalid request')
            allowed = {'/api/session': set(), '/api/observe': {'session','test'},
                       '/api/diagnose': {'session'}, '/api/choose': {'session'},
                       '/api/explain': {'session'}, '/api/reveal': {'session'}}
            if self.path not in allowed or set(data) != allowed[self.path]:
                raise ValueError('Invalid request fields')
            if self.path == '/api/session':
                self.reply({'session':new_session()}); return
            if self.path == '/api/observe' and (not isinstance(data['test'], str) or data['test'] not in TESTS):
                raise ValueError('Invalid test')
            history, answer = synthetic_state(data['session'], data.get('test') if self.path == '/api/observe' else None, self.path == '/api/reveal')
            if self.path == '/api/reveal': self.reply({'fault':answer}); return
            p=posterior(history); rec=recommendations(history)
            if self.path == '/api/diagnose': self.reply({'history':history,'posterior':p,'recommendations':rec,'assessment':decision(history) if len(history) >= 2 else None,'sensitivity':sensitivity(history)}); return
            if self.path == '/api/observe': self.reply({'value':history[-1]['value']}); return
            if self.path == '/api/choose':
                if not rec: raise ValueError('No experiments remain')
                key=os.getenv('MODEL_API_KEY')
                if not key:
                    self.reply({'mode':'local','test':rec[0]['test'], 'reason':'Local information-gain fallback; no model was called.'}); return
                # Build this independently of the local recommendation ordering. Muse
                # receives the synthetic model's evidence and predictions, not the
                # calculated information gains or local recommendation.
                used = {item['test'] for item in history}
                candidates = [{'test': test, 'name': meta['name'], 'description': meta['description'],
                               'unit': meta['unit'], 'cost': meta['cost'],
                               'predictions': {fault: predict(fault, test) for fault in FAULTS}}
                              for test, meta in TESTS.items() if test not in used]
                context = {'posterior': p, 'hypotheses': LABELS, 'observations': history,
                           'measurement_sigma': SIGMA, 'available_experiments': candidates}
                payload={'model':os.getenv('META_MODEL','muse-spark-1.3'),'messages':[{'role':'system','content':'Compare the supplied predictions, probabilities, measurement noise, and relative costs. Choose the next simulated experiment that could help distinguish the hypotheses. Return ONLY JSON with exactly the keys test and reason. The test must be one of the available test IDs provided. Keep reason under 160 characters. Never suggest real-world equipment operations.'},{'role':'user','content':json.dumps(context)}],'max_tokens':512,'reasoning_effort':'low','response_format':{'type':'json_schema','json_schema':{'name':'experiment_selection','strict':True,'schema':{'type':'object','properties':{'test':{'type':'string','enum':[r['test'] for r in candidates]},'reason':{'type':'string'}},'required':['test','reason'],'additionalProperties':False}}}}
                content=model_call(payload,key)
                try:
                    selected=parse_selection(content, rec)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    self.reply({'mode':'local','test':rec[0]['test'],'reason':'Model output was invalid; local information-gain fallback selected the test.'}); return
                self.reply({'mode':'meta','test':selected['test'],'reason':selected['reason']}); return
            if self.path == '/api/explain':
                key=os.getenv('MODEL_API_KEY')
                if not key: self.reply({'mode':'local','text':'No API key is configured. The recommended test is selected by the local information-gain calculation, not an AI model.'}); return
                payload={'model':os.getenv('META_MODEL','muse-spark-1.3'),'messages':[{'role':'system','content':'Explain only the supplied simulated diagnostic results in 2 concise sentences. This is a toy model, not advice for real building equipment. Do not invent facts or recommend physical actions.'},{'role':'user','content':json.dumps({'posterior':p,'recommendations':rec,'observations':history})}],'max_tokens':512,'reasoning_effort':'low'}
                content=model_call(payload,key)
                self.reply({'mode':'meta','text':content}); return
            self.send_error(404)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e: self.reply({'error':str(e)},400)
        except (urllib.error.URLError, TimeoutError, OSError, ModelResponseError): self.reply({'error':'Meta request failed. Check connectivity and your configuration.'},502)

if __name__=='__main__':
    port = int(os.getenv('TWINLAB_PORT', '18547'))
    server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'TwinLab is running at http://127.0.0.1:{port}',flush=True)
    server.serve_forever()
