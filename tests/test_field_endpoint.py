import unittest
from unittest.mock import patch
from server import Handler

class FieldEndpointTests(unittest.TestCase):
    def test_public_replay_summaries_are_local_and_labeled(self):
        handler=Handler.__new__(Handler)
        handler.path='/api/field-data'
        responses=[]
        handler.reply=lambda obj,status=200: responses.append((status,obj))
        with patch('server.model_call', side_effect=AssertionError('model must not be invoked')):
            handler.do_GET()
        status, result=responses[0]
        self.assertEqual(status,200)
        self.assertIn('induced faults',result['source'])
        self.assertEqual(len(result['cases']),4)
        self.assertEqual(sum(case['rows'] for case in result['cases']),384)
        self.assertTrue(all(case['room_mean_c'] is not None for case in result['cases']))

if __name__=='__main__': unittest.main()
