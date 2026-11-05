"""Paired synthetic stress tests of TwinLab's observational decision policy.

This is an offline simulator study, not a test of physical interventions or a
Meta model.  Run: python robustness.py --cases 120
"""
import argparse
import json
import math
import random

from twin import FAULTS, SIGMA, TESTS, posterior, predict, recommendations

STRATEGIES = ('random', 'cheapest', 'fixed', 'information_gain')
CONDITIONS = ('in_model', 'shifted', 'unknown')
FIXED_ORDER = ('pulse', 'coast', 'reference')
MIN_OBSERVATIONS = 2
CONFIDENCE_THRESHOLD = .90
MAX_RESIDUAL_SIGMA = 3.0


def observation(case_id, fault, condition, test):
    """Common random numbers for each paired policy; shifts are synthetic.

    Shifted retains a known class but perturbs all test means. Unknown is an
    invented extra mechanism, and is deliberately not a fifth trained class.
    """
    if condition not in CONDITIONS or fault not in FAULTS or test not in TESTS:
        raise ValueError('Invalid case')
    noise = random.Random(f'observation:{case_id}:{test}').gauss(0, SIGMA)
    # The mismatch is deliberately smaller than many between-class distances,
    # to include cases where a wrong known diagnosis looks plausible.
    offsets = {
        'in_model': {'pulse': 0., 'coast': 0., 'reference': 0.},
        'shifted': {'pulse': .40, 'coast': -.30, 'reference': .20},
        'unknown': {'pulse': .75, 'coast': .70, 'reference': .70},
    }
    return predict(fault, test) + offsets[condition][test] + noise


def select_test(history, strategy, case_id):
    remaining = [t for t in TESTS if t not in {h['test'] for h in history}]
    if strategy not in STRATEGIES:
        raise ValueError('Unknown policy')
    if not remaining:
        return None
    if strategy == 'fixed':
        return next(t for t in FIXED_ORDER if t in remaining)
    if strategy == 'cheapest':
        return min(remaining, key=lambda t: (TESTS[t]['cost'], t))
    if strategy == 'random':
        # Case and round dependent, reproducible, independent of observations.
        return random.Random(f'policy:{case_id}:{len(history)}').choice(remaining)
    return recommendations(history)[0]['test']


def decision(history):
    """Return best known class or abstain on low confidence or bad model fit.

    Residual is evaluated against the most likely single hypothesis across all
    acquired observations. This is a heuristic, not a calibrated OOD detector.
    """
    probabilities = posterior(history)
    best = max(probabilities, key=probabilities.get)
    residual = max(abs(h['value'] - predict(best, h['test'])) / SIGMA for h in history)
    confident = probabilities[best] >= CONFIDENCE_THRESHOLD
    fit = residual <= MAX_RESIDUAL_SIGMA
    return {'answer': best if confident and fit else None,
            'confidence': probabilities[best], 'max_residual_sigma': residual}


def run_case(case_id, fault, condition, strategy):
    history = []
    while len(history) < len(TESTS):
        test = select_test(history, strategy, case_id)
        history.append({'test': test, 'value': observation(case_id, fault, condition, test)})
        current = decision(history)
        # Require two observations. A contradiction terminates as abstention;
        # an uncertain result may acquire another observation.
        if len(history) >= MIN_OBSERVATIONS:
            if current['answer'] is not None or current['max_residual_sigma'] > MAX_RESIDUAL_SIGMA:
                break
    return {'actual': fault if condition != 'unknown' else 'unknown',
            'answer': current['answer'], 'history': history,
            'cost': sum(TESTS[h['test']]['cost'] for h in history),
            'confidence': current['confidence'],
            'max_residual_sigma': current['max_residual_sigma']}


def evaluate(n=120):
    if n < 1:
        raise ValueError('cases must be positive')
    result = {}
    for condition in CONDITIONS:
        result[condition] = {}
        for policy in STRATEGIES:
            runs = [run_case(i, FAULTS[i % len(FAULTS)], condition, policy) for i in range(n)]
            answered = [r for r in runs if r['answer'] is not None]
            correct = sum(r['answer'] == r['actual'] for r in answered)
            result[condition][policy] = {
                'cases': n, 'answered': len(answered), 'abstained': n-len(answered),
                'coverage': round(len(answered)/n, 4),
                # Unknown is outside the known classes: every answer is a false acceptance.
                'accuracy_on_answered': (round(correct/len(answered), 4)
                                         if answered and condition != 'unknown' else None),
                'unknown_false_acceptances': len(answered) if condition == 'unknown' else None,
                'mean_evidence_cost': round(sum(r['cost'] for r in runs)/n, 4),
                'mean_observations': round(sum(len(r['history']) for r in runs)/n, 4),
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=120)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    print(json.dumps(evaluate(args.cases), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
