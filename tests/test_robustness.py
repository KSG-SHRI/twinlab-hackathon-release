import unittest

from robustness import (CONDITIONS, STRATEGIES, decision, evaluate, observation,
                        run_case, select_test)
from twin import FAULTS, TESTS, predict


class RobustnessTests(unittest.TestCase):
    def test_same_case_observations_are_policy_independent(self):
        for condition in CONDITIONS:
            for test in TESTS:
                self.assertEqual(observation(7, 'healthy', condition, test),
                                 observation(7, 'healthy', condition, test))
        runs = [run_case(7, 'healthy', 'shifted', p) for p in STRATEGIES]
        for run in runs:
            for item in run['history']:
                self.assertEqual(item['value'], observation(7, 'healthy', 'shifted', item['test']))
            self.assertEqual(len({h['test'] for h in run['history']}), len(run['history']))

    def test_policies_use_valid_unused_tests(self):
        history = [{'test': 'reference', 'value': 0.0}]
        for policy in STRATEGIES:
            self.assertIn(select_test(history, policy, 2), ('pulse', 'coast'))
        with self.assertRaises(ValueError):
            select_test(history, 'invalid', 2)

    def test_abstains_on_clear_mismatch(self):
        history = [{'test': t, 'value': predict('healthy', t) + 10} for t in TESTS]
        self.assertIsNone(decision(history)['answer'])
        self.assertGreater(decision(history)['max_residual_sigma'], 3)

    def test_consistent_known_case_answers_correctly(self):
        for fault in FAULTS:
            history = [{'test': t, 'value': predict(fault, t)} for t in TESTS]
            self.assertEqual(decision(history)['answer'], fault)

    def test_evaluation_counts_and_determinism(self):
        result = evaluate(8)
        self.assertEqual(result, evaluate(8))
        for condition in CONDITIONS:
            for policy in STRATEGIES:
                stats = result[condition][policy]
                self.assertEqual(stats['answered'] + stats['abstained'], 8)
                self.assertGreaterEqual(stats['mean_evidence_cost'], .4 + .65)
                self.assertLessEqual(stats['mean_evidence_cost'], 2.05)
                if condition == 'unknown' and stats['answered']:
                    self.assertEqual(stats['unknown_false_acceptances'], stats['answered'])
                    self.assertIsNone(stats['accuracy_on_answered'])
        with self.assertRaises(ValueError):
            evaluate(0)


if __name__ == '__main__':
    unittest.main()
