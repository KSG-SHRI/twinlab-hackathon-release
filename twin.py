"""TwinLab: a deliberately small, inspectable thermal twin and Bayesian diagnosis."""
import math
import random
from itertools import combinations

FAULTS = ('healthy', 'weak_heater', 'leaky_envelope', 'biased_sensor')
LABELS = {'healthy':'No simulated fault', 'weak_heater':'Weak heater', 'leaky_envelope':'Heat leak', 'biased_sensor':'Biased room sensor'}
TESTS = {
    'pulse': {'name':'Heat pulse', 'description':'Heat for four hours and measure the change in the room sensor.', 'unit':'°C change', 'cost':1.0},
    'coast': {'name':'Passive cooling', 'description':'Turn off heat for four hours and measure the room sensor change.', 'unit':'°C change', 'cost':0.65},
    'reference': {'name':'Reference thermometer', 'description':'Compare the room sensor with an independent reference thermometer.', 'unit':'°C difference', 'cost':0.4},
}
SIGMA = .18

def predict(fault, test):
    """Integrate a simple one-zone model, in hourly steps. Relative temperatures matter."""
    if fault not in FAULTS or test not in TESTS:
        raise ValueError('Unknown fault or experiment')
    if test == 'reference':
        return 2.5 if fault == 'biased_sensor' else 0.0
    temperature, ambient = 21.0, 12.0
    loss = .09 if fault == 'leaky_envelope' else .045
    heating = (1.0 if fault == 'weak_heater' else 2.0) if test == 'pulse' else 0.0
    for _ in range(4):
        temperature += heating - loss * (temperature - ambient)
    # Constant sensor bias cancels when taking the difference.
    return temperature - 21.0

def observe(fault, test, seed):
    rng = random.Random(f'{seed}:{test}')
    return round(predict(fault, test) + rng.gauss(0, SIGMA), 3)

def posterior(history):
    logp = {f: math.log(1 / len(FAULTS)) for f in FAULTS}
    for item in history:
        if item['test'] not in TESTS or not math.isfinite(float(item['value'])):
            raise ValueError('Invalid observation')
        for f in FAULTS:
            logp[f] -= .5 * ((float(item['value']) - predict(f, item['test'])) / SIGMA) ** 2
    peak = max(logp.values())
    weights = {f: math.exp(x - peak) for f, x in logp.items()}
    total = sum(weights.values())
    return {f: weights[f] / total for f in FAULTS}

def entropy(prob):
    return -sum(x * math.log2(x) for x in prob.values() if x > 0)

def recommendations(history):
    """Estimate information gain by averaging deterministic normal quantile samples."""
    prior = posterior(history)
    used = {h['test'] for h in history}
    offsets = (-1.65, -1.15, -.84, -.58, -.35, -.12, .12, .35, .58, .84, 1.15, 1.65)
    result = []
    for test, meta in TESTS.items():
        if test in used: continue
        expected = 0.0
        for fault, weight in prior.items():
            if weight < 1e-12: continue
            for z in offsets:
                sample = {'test':test, 'value':predict(fault, test) + SIGMA*z}
                expected += weight * entropy(posterior(history + [sample])) / len(offsets)
        gain = max(0.0, entropy(prior) - expected)
        result.append({'test':test, **meta, 'information_gain':round(gain, 4), 'score':round(gain/meta['cost'], 4)})
    return sorted(result, key=lambda r: (-r['score'], r['test']))

def sensitivity(history):
    """Screen known toy hypotheses under an illustrative +/-1°C reading bound.

    This is a sensitivity comparison, not a probability, calibrated uncertainty,
    unknown-fault detector, or evidence that a real system has this error bound.
    The fixed bound applies to both temperature changes and differences.
    """
    bound = 1.0
    for item in history:
        if item['test'] not in TESTS or not math.isfinite(float(item['value'])):
            raise ValueError('Invalid observation')
    hypotheses = []
    for fault in FAULTS:
        residuals = []
        for item in history:
            predicted = predict(fault, item['test'])
            residual = abs(float(item['value']) - predicted)
            residuals.append({'test': item['test'], 'unit': TESTS[item['test']]['unit'],
                              'observed': float(item['value']), 'predicted': round(predicted, 4),
                              'absolute_residual': round(residual, 4)})
        max_residual = max((abs(float(item['value']) - predict(fault, item['test']))
                            for item in history), default=None)
        hypotheses.append({'fault': fault, 'label': LABELS[fault],
                           'compatible': max_residual is None or max_residual <= bound,
                           'max_abs_residual': round(max_residual, 4) if max_residual is not None else None,
                           'residuals': residuals})
    compatible = [item['fault'] for item in hypotheses if item['compatible']]
    status = ('no_observations' if not history else
              'none' if not compatible else 'single' if len(compatible) == 1 else 'multiple')

    # A pair is separated under this thought experiment if its two +/-1°C
    # prediction ranges do not overlap. First maximize separated pairs, then
    # minimum and total pairwise differences, with a stable alphabetical tie.
    # These are hypothetical predictions, not outcomes of unperformed tests.
    used = {item['test'] for item in history}
    candidates = []
    if len(compatible) >= 2:
        for test in TESTS:
            if test in used:
                continue
            gaps = [abs(predict(a, test) - predict(b, test))
                    for a, b in combinations(compatible, 2)]
            candidates.append({'test': test, 'name': TESTS[test]['name'], 'unit': TESTS[test]['unit'],
                               'separated_pairs': sum(gap > 2 * bound for gap in gaps),
                               'total_pairs': len(gaps), 'min_gap': min(gaps), 'sum_gaps': sum(gaps)})
    candidates.sort(key=lambda x: (-x['separated_pairs'], -x['min_gap'], -x['sum_gaps'], x['test']))
    best = candidates[0] if candidates else None
    if best:
        best['min_gap'] = round(best['min_gap'], 4)
        best['sum_gaps'] = round(best['sum_gaps'], 4)
    return {'bound': bound, 'bound_unit': '°C change or difference', 'status': status,
            'hypotheses': hypotheses, 'compatible_faults': compatible, 'remaining_test': best}

def run(seed, strategy, limit=2):
    fault = random.Random(seed).choice(FAULTS)
    history=[]
    rng = random.Random(seed + 999)
    for _ in range(limit):
        options=recommendations(history)
        if not options: break
        test = options[0]['test'] if strategy == 'active' else rng.choice(options)['test']
        history.append({'test':test,'value':observe(fault,test,seed)})
    p=posterior(history)
    return {'actual': fault, 'prediction':max(p, key=p.get), 'confidence':max(p.values()), 'history':history}

def evaluate(n=200, steps=2):
    result = {}
    for strategy in ('active','random'):
        runs = [run(i, strategy, steps) for i in range(n)]
        result[strategy] = {'correct':sum(r['actual']==r['prediction'] for r in runs), 'total':n, 'accuracy':round(sum(r['actual']==r['prediction'] for r in runs)/n,3)}
    return result
