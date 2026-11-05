"""Bounded toy-model stress cases; no external data or requests."""
import unittest
from twin import FAULTS, posterior, predict, sensitivity
from server import Handler


class SensitivityTests(unittest.TestCase):
    def test_concentrated_posterior_can_hide_plausible_alternatives(self):
        # One synthetic coast result; this is not an accepted final diagnosis.
        history = [{'test': 'coast', 'value': -2.5}]
        self.assertGreater(posterior(history)['leaky_envelope'], .999)
        result = sensitivity(history)
        self.assertEqual(result['status'], 'multiple')
        self.assertEqual(set(result['compatible_faults']), set(FAULTS))
        self.assertEqual(result['bound'], 1.0)
        self.assertEqual(result['remaining_test']['test'], 'reference')
        self.assertEqual(result['remaining_test']['separated_pairs'], 3)
        self.assertEqual(result['remaining_test']['total_pairs'], 6)
        self.assertEqual(result['remaining_test']['unit'], '°C difference')
        self.assertEqual(result['hypotheses'][0]['residuals'][0]['unit'], '°C change')

    def test_empty_single_none_and_inclusive_boundary(self):
        self.assertEqual(sensitivity([])['status'], 'no_observations')
        result = sensitivity([{'test': 'pulse', 'value': predict('weak_heater', 'pulse')}])
        self.assertEqual(result['status'], 'single')
        self.assertEqual(result['compatible_faults'], ['weak_heater'])
        self.assertIsNone(result['remaining_test'])
        result = sensitivity([{'test': 'pulse', 'value': 20.0}])
        self.assertEqual(result['status'], 'none')
        self.assertIsNone(result['remaining_test'])
        self.assertIn('healthy', sensitivity([{'test':'reference', 'value':1.0}])['compatible_faults'])
        self.assertNotIn('healthy', sensitivity([{'test':'reference', 'value':1.0001}])['compatible_faults'])

    def test_all_observations_and_remaining_tests(self):
        history = [{'test':'coast', 'value':-2.5}, {'test':'reference', 'value':0.0}]
        result = sensitivity(history)
        self.assertNotIn('biased_sensor', result['compatible_faults'])
        self.assertEqual(result['remaining_test']['test'], 'pulse')
        history.append({'test':'pulse', 'value':predict('healthy', 'pulse')})
        self.assertIsNone(sensitivity(history)['remaining_test'])

    def test_invalid_observation_rejected(self):
        for item in ({'test':'coast','value':float('nan')}, {'test':'invalid','value':0}):
            with self.assertRaises(ValueError):
                sensitivity([item])

    def test_example_endpoint_is_fixed_and_local(self):
        handler = Handler.__new__(Handler)
        handler.path = '/api/challenge-example'
        replies = []
        handler.reply = replies.append
        handler.do_GET()
        example = replies[0]
        self.assertEqual(example['history'], [{'test':'coast', 'value':-2.5}])
        self.assertGreater(example['posterior']['leaky_envelope'], .999)
        self.assertEqual(example['sensitivity']['status'], 'multiple')
        self.assertEqual(len(example['sensitivity']['compatible_faults']), 4)


if __name__ == '__main__':
    unittest.main()
