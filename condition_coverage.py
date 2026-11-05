"""Fixed synthetic illustration of why a normal reading may miss a conditional fault.

This is a separate toy scenario, not the thermal simulator and not real equipment.
The units, thresholds, fault patterns and observations are all invented.
"""

BOUND = 0.10  # invented absolute tolerance in deviation units
MODELS = {
    'healthy': {'label': 'No modeled fault', 'low': 0.05, 'high': 0.07},
    'conditional_fault': {'label': 'Fault appearing only at high demand', 'low': 0.05, 'high': 0.60},
}
READINGS = (
    {'condition': 'low', 'value': 0.04},
    {'condition': 'high', 'value': 0.58},
)


def coverage_stage(count):
    """Compare observations with fixed predictions; compatibility is not probability."""
    if type(count) is not int or not 0 <= count <= len(READINGS):
        raise ValueError('Invalid number of observations')
    readings = [dict(item) for item in READINGS[:count]]
    hypotheses = []
    for key, model in MODELS.items():
        matches = all(abs(r['value'] - model[r['condition']]) <= BOUND + 1e-12 for r in readings)
        hypotheses.append({'id': key, 'label': model['label'], 'low_prediction': model['low'],
                           'high_prediction': model['high'], 'compatible': matches})
    return {'readings': readings, 'hypotheses': hypotheses,
            'observed_conditions': [r['condition'] for r in readings],
            'unobserved_conditions': [c for c in ('low', 'high') if c not in {r['condition'] for r in readings}]}


def coverage_example():
    return {'bound': BOUND, 'units': 'invented deviation units',
            'reported_symptom': 'A simulated complaint reports a problem at high demand; it has no numerical measurement.',
            'stages': [coverage_stage(n) for n in range(len(READINGS) + 1)]}
