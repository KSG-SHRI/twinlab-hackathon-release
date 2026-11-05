import unittest
from twin import FAULTS, TESTS, predict, observe, posterior, recommendations, evaluate
from server import parse_selection

class ThermalTwinTests(unittest.TestCase):
    def test_physics_and_sensor_offset(self):
        self.assertGreater(predict('healthy','pulse'), predict('weak_heater','pulse'))
        self.assertLess(predict('leaky_envelope','coast'),predict('healthy','coast'))
        self.assertEqual(predict('healthy','pulse'), predict('biased_sensor','pulse'))
        self.assertEqual(predict('biased_sensor','reference'),2.5)
    def test_bayes_localizes_exact_observations(self):
        for fault in FAULTS:
            h=[{'test':t,'value':predict(fault,t)} for t in TESTS]
            p=posterior(h)
            self.assertEqual(max(p,key=p.get),fault)
            self.assertAlmostEqual(sum(p.values()),1)
    def test_observation_reproducible(self):
        self.assertEqual(observe('weak_heater','pulse',42),observe('weak_heater','pulse',42))
        self.assertNotEqual(observe('weak_heater','pulse',42),observe('weak_heater','pulse',43))
    def test_selection_avoids_repeats_and_reacts_to_data(self):
        self.assertEqual(recommendations([])[0]['test'],'reference')
        history=[{'test':'reference','value':predict('healthy','reference')}]
        r=recommendations(history)
        self.assertNotIn('reference',[x['test'] for x in r])
        self.assertEqual(r[0]['test'],'pulse')
    def test_evaluation_is_reproducible_and_counts_correctly(self):
        a=evaluate(40,2); self.assertEqual(a,evaluate(40,2))
        self.assertEqual(a['active']['total'],40)
        self.assertGreaterEqual(a['active']['correct'],a['random']['correct'])
    def test_rejects_invalid_model_actions(self):
        allowed=[{'test':'pulse'}]
        self.assertEqual(parse_selection('{"test":"pulse","reason":"test"}', allowed)['test'],'pulse')
        for raw in ('not json', '{"test":"coast","reason":"test"}', '{"test":"pulse","reason":"test","extra":1}', '{"test":"pulse","reason":123}'):
            with self.assertRaises(ValueError): parse_selection(raw, allowed)
    def test_rejects_invalid_observation(self):
        with self.assertRaises(ValueError): posterior([{'test':'reference','value':float('nan')}])

if __name__=='__main__': unittest.main()
