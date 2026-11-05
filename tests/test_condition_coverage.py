import unittest
from unittest.mock import patch
from server import Handler
from condition_coverage import coverage_stage, coverage_example


class CoverageScenarioTests(unittest.TestCase):
    def test_low_demand_cannot_rule_out_conditional_fault(self):
        stage = coverage_stage(1)
        self.assertEqual(stage['readings'], [{'condition': 'low', 'value': 0.04}])
        self.assertEqual(stage['unobserved_conditions'], ['high'])
        self.assertTrue(all(h['compatible'] for h in stage['hypotheses']))

    def test_high_demand_changes_compatibility_under_explicit_assumptions(self):
        example = coverage_example()
        self.assertEqual(example['bound'], .10)
        stage = example['stages'][2]
        self.assertEqual(stage['unobserved_conditions'], [])
        self.assertEqual({h['id']: h['compatible'] for h in stage['hypotheses']},
                         {'healthy': False, 'conditional_fault': True})
        for h in stage['hypotheses']:
            calculated = all(abs(r['value'] - h[r['condition'] + '_prediction']) <= example['bound']
                             for r in stage['readings'])
            self.assertEqual(h['compatible'], calculated)

    def test_endpoint_is_local_and_does_not_call_model(self):
        handler = Handler.__new__(Handler)
        handler.path = '/api/coverage-example'
        results = []
        handler.reply = lambda result, status=200: results.append((status, result))
        with patch('server.model_call', side_effect=AssertionError('model must not be invoked')):
            handler.do_GET()
        self.assertEqual(results[0][0], 200)
        self.assertEqual(results[0][1], coverage_example())

    def test_stage_bounds_are_checked(self):
        for invalid in (-1, 3, True, '1'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                coverage_stage(invalid)


if __name__ == '__main__':
    unittest.main()
