"""Exercise model boundaries without network access or real credentials."""
import io, json, os, unittest
from email.message import Message
from types import SimpleNamespace
from unittest.mock import patch
import server
from server import Handler

class Response:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, *args):
        return json.dumps({'choices':[{'message':{'content':'{"test":"reference","reason":"Most information per cost"}'}}]}).encode()

class HandlerTests(unittest.TestCase):
    def setUp(self):
        with server._sessions_lock: server._sessions.clear()
    def request(self,path,body,headers=None):
        h=Handler.__new__(Handler); h.path=path; h.server=SimpleNamespace(server_port=18547)
        h.headers=Message(); h.headers['Host']='127.0.0.1:18547'; h.headers['Content-Type']='application/json'
        for name, value in (headers or {}).items(): h.headers.replace_header(name,value) if name in h.headers else h.headers.__setitem__(name,value)
        raw=json.dumps(body).encode(); h.headers['Content-Length']=str(len(raw)); h.rfile=io.BytesIO(raw)
        replies=[]; h.reply=lambda obj,status=200: replies.append((status,obj)); h.do_POST(); return replies[0]
    def session(self): return self.request('/api/session',{})[1]['session']
    def test_only_server_generated_state_reaches_model(self):
        token=self.session(); self.assertEqual(self.request('/api/observe',{'session':token,'test':'pulse'})[0],200)
        requests=[]
        def fake(req,timeout): requests.append(json.loads(req.data)); return Response()
        with patch.dict(os.environ,{'MODEL_API_KEY':'dummy-test-key'}), patch.object(server._model_opener,'open',fake):
            status,result=self.request('/api/choose',{'session':token})
        self.assertEqual(status,200); self.assertEqual(result['test'],'reference')
        payload=requests[0]; self.assertEqual(payload['max_tokens'],512)
        self.assertEqual(payload['response_format']['type'],'json_schema')
        user=json.loads(payload['messages'][1]['content'])
        self.assertEqual(set(user),{'posterior','hypotheses','observations','measurement_sigma','available_experiments'})
        self.assertEqual(user['observations'],self.request('/api/diagnose',{'session':token})[1]['history'])
        self.assertEqual(user['measurement_sigma'], server.SIGMA)
        self.assertEqual(user['hypotheses'], server.LABELS)
        self.assertEqual([c['test'] for c in user['available_experiments']], ['coast','reference'])
        for candidate in user['available_experiments']:
            self.assertEqual(set(candidate), {'test','name','description','unit','cost','predictions'})
            self.assertEqual(candidate['predictions'], {f: server.predict(f, candidate['test']) for f in server.FAULTS})
        encoded = json.dumps(user)
        for forbidden in ('information_gain', 'score', 'recommendation', 'seed', token):
            self.assertNotIn(forbidden, encoded)
        self.assertNotIn(token,json.dumps(payload)); self.assertNotIn('seed',json.dumps(payload))
    def test_candidate_order_is_not_local_ranking(self):
        token = self.session()
        captured = []
        def model(payload, key):
            captured.append(payload)
            return '{"test":"reference","reason":"Compare the reference"}'
        with patch.dict(os.environ, {'MODEL_API_KEY':'dummy-test-key'}), patch.object(server, 'model_call', side_effect=model):
            status, result = self.request('/api/choose', {'session':token})
        self.assertEqual((status,result['mode']), (200,'meta'))
        user = json.loads(captured[0]['messages'][1]['content'])
        supplied = [item['test'] for item in user['available_experiments']]
        local = [item['test'] for item in server.recommendations([])]
        self.assertEqual(supplied, list(server.TESTS))
        self.assertNotEqual(supplied, local)
        self.assertEqual(captured[0]['response_format']['json_schema']['schema']['properties']['test']['enum'], supplied)
    def test_invalid_or_used_selection_falls_back_to_local_recommendation(self):
        token = self.session()
        self.assertEqual(self.request('/api/observe', {'session':token,'test':'pulse'})[0], 200)
        history = self.request('/api/diagnose', {'session':token})[1]['history']
        expected = server.recommendations(history)[0]['test']
        for content in ('{"test":"pulse","reason":"already used"}',
                        '{"test":"not-a-test","reason":"invalid"}',
                        '{"test":"reference","reason":"ok","extra":1}', 'not json'):
            with self.subTest(content=content), patch.dict(os.environ, {'MODEL_API_KEY':'dummy-test-key'}), patch.object(server, 'model_call', return_value=content):
                status,result = self.request('/api/choose', {'session':token})
                self.assertEqual((status,result['mode'],result['test']), (200,'local',expected))
                self.assertEqual(self.request('/api/diagnose', {'session':token})[1]['history'], history)
    def test_caller_history_and_unknown_session_rejected_before_model(self):
        token=self.session()
        with patch.dict(os.environ,{'MODEL_API_KEY':'dummy-test-key'}), patch.object(server._model_opener,'open',side_effect=AssertionError('network called')):
            for endpoint in ('/api/choose','/api/explain'):
                self.assertEqual(self.request(endpoint,{'session':token,'history':[{'test':'pulse','value':12.345678}]})[0],400)
                self.assertEqual(self.request(endpoint,{'session':'A'*43})[0],400)
            self.assertEqual(self.request('/api/observe',{'session':token,'test':'pulse','seed':1})[0],400)
            self.assertEqual(self.request('/api/observe',{'session':token,'test':None})[0],400)
    def test_normal_simulation_does_not_call_network(self):
        with patch.dict(os.environ,{},clear=True), patch.object(server._model_opener,'open',side_effect=AssertionError('network called')):
            token=self.session()
            for test in ('pulse','reference'): self.assertEqual(self.request('/api/observe',{'session':token,'test':test})[0],200)
            status,result=self.request('/api/diagnose',{'session':token}); self.assertEqual(status,200)
            self.assertEqual(len(result['history']),2); self.assertIsNotNone(result['assessment'])
            self.assertEqual(self.request('/api/observe',{'session':token,'test':'pulse'})[0],400)
            self.assertEqual(self.request('/api/choose',{'session':token})[1]['mode'],'local')
            self.assertEqual(self.request('/api/explain',{'session':token})[1]['mode'],'local')
            self.assertIn(self.request('/api/reveal',{'session':token})[1]['fault'],server.FAULTS)
    def test_session_lifetime_and_capacity_are_bounded(self):
        token=self.session()
        with patch('server.time.monotonic',return_value=server._sessions[token]['created']+server.SESSION_TTL+1):
            self.assertEqual(self.request('/api/diagnose',{'session':token})[0],400)
        with patch('server.MAX_SESSIONS',2):
            old=self.session(); self.session(); self.session()
            self.assertEqual(self.request('/api/diagnose',{'session':old})[0],400); self.assertEqual(len(server._sessions),2)
    def test_explanation_contains_only_synthetic_server_state(self):
        token=self.session(); self.request('/api/observe',{'session':token,'test':'pulse'})
        requests=[]
        def fake(req,timeout): requests.append(json.loads(req.data)); return Response()
        with patch.dict(os.environ,{'MODEL_API_KEY':'dummy-test-key'}), patch.object(server._model_opener,'open',fake):
            self.assertEqual(self.request('/api/explain',{'session':token})[0],200)
        payload=requests[0]
        user=json.loads(payload['messages'][1]['content'])
        self.assertEqual(set(user),{'posterior','recommendations','observations'})
        self.assertEqual(user['observations'],self.request('/api/diagnose',{'session':token})[1]['history'])
        self.assertNotIn(token,json.dumps(payload)); self.assertNotIn('seed',json.dumps(payload))
    def test_cross_origin_and_invalid_host_blocked_before_network(self):
        token=self.session()
        with patch.dict(os.environ,{'MODEL_API_KEY':'dummy-test-key'}), patch.object(server._model_opener,'open',side_effect=AssertionError('network called')):
            for headers in ({'Origin':'https://example.invalid'}, {'Host':'example.invalid'}, {'Content-Type':'text/plain'}):
                self.assertEqual(self.request('/api/choose',{'session':token},headers)[0],400)
    def test_no_redirect_and_malformed_model_response(self):
        self.assertIsNone(server.NoRedirect().redirect_request(None,None,302,'',{},'https://example.invalid'))
        class InvalidResponse(Response):
            def read(self,*args): return b'{"choices": []}'
        token=self.session()
        with patch.dict(os.environ,{'MODEL_API_KEY':'dummy-test-key'}), patch.object(server._model_opener,'open',return_value=InvalidResponse()):
            status,result=self.request('/api/explain',{'session':token})
        self.assertEqual(status,502); self.assertNotIn('dummy-test-key',str(result))
if __name__=='__main__': unittest.main()
