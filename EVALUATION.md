# Synthetic robustness evaluation

Run `python robustness.py --cases 120` from this directory; run the test suite with `python -m unittest discover -s tests -v`. This is deterministic and makes no network or model API calls. The script compares policies, not Meta model performance.

## Setup

The comparison uses the same 120 synthetic cases for each policy within each condition, evenly cycling through four known faults. For a given case and test, all policies receive the same simulated measurement and random noise, even when they acquire tests in a different order. Three conditions are tested:

- **In model:** observations are generated from the same predictions and Gaussian noise assumed by the diagnostic model. This intentionally favors that model and is not independent validation.
- **Shifted:** observations for a known fault have fixed offsets of +0.40, −0.30 and +0.20 °C for pulse, coast and reference, respectively, plus the original noise. The original fault remains the label, even though the data generator now disagrees with the model.
- **Unknown:** a hypothetical unmodeled mechanism adds +0.75, +0.70 and +0.70 °C to those measurements, respectively, on top of a known-fault base. This is one hand-designed unknown, not a representative population of unknown faults. Every known-class diagnosis in this condition counts as a false acceptance.

Each policy sees at least two observations and at most three. The policies select unused tests randomly, by lowest assigned cost, in a fixed pulse/coast/reference order, or by TwinLab's expected information gain per cost. They share the same stopping and abstention rules: after two observations, stop when the posterior is at least 0.90 and all residuals for its most likely known fault are within three assumed standard deviations, or stop and abstain when a residual exceeds that limit; otherwise acquire the remaining test. The thresholds and shifts are illustrative choices, not calibrated or independently selected. The residual rule can miss an unknown that happens to resemble a known fault. Reported evidence costs are arbitrary simulator units (pulse 1.0, coast 0.65, reference 0.4), not dollars, time or physical intervention costs.

## Results on 120 cases per condition

Coverage is the fraction receiving a known-fault answer. Accuracy is correct answers divided by answered known-class cases; it excludes abstentions and does **not** mean accuracy on all cases. For unknown cases, any answer is a false acceptance. Mean cost includes abstained cases. Rounded values:

| Condition | Policy | Answered / 120 | Accuracy when answered | Unknown false acceptances | Mean evidence cost |
|---|---|---:|---:|---:|---:|
| In model | Random | 120 | 100% | — | 1.618 |
| In model | Cheapest | 120 | 100% | — | 1.550 |
| In model | Fixed | 119 | 100% | — | 1.850 |
| In model | Information gain | 119 | 100% | — | 1.313 |
| Shifted | Random | 91 | 100% | — | 1.598 |
| Shifted | Cheapest | 97 | 100% | — | 1.517 |
| Shifted | Fixed | 86 | 100% | — | 1.800 |
| Shifted | Information gain | 94 | 100% | — | 1.313 |
| Unknown | Random | 3 | — | 3 | 1.415 |
| Unknown | Cheapest | 2 | — | 2 | 1.083 |
| Unknown | Fixed | 2 | — | 2 | 1.657 |
| Unknown | Information gain | 4 | — | 4 | 1.313 |

For the particular in-model cases, information gain used fewer cost units on average; it did not achieve higher accuracy among answered cases, and it abstained once while random and cheapest did not. Under the one unknown shift, all methods falsely accepted some cases, including 4 of 120 for information gain. Do not generalize these figures to other fault mechanisms, buildings, experts, intervention costs, or field outcomes. The in-model faults are well separated by design, and the 120 cases share just four base fault types and one noise model; they are not 120 independent buildings.

Pulse and coast are represented here only as readings produced by a toy equation. The simulated outcomes do not validate whether, how, or when to perform interventions on a real building. No physical system, external dataset, licensed technician, model API, actual diagnosis, safety procedure, energy savings, or monetary benefit was tested. A sound follow-up would use held-out, appropriately licensed field data and separate equipment/site splits; test multiple unknowns and sensor failures; pre-register thresholds and metrics; and obtain expert review before any operational claims. Observational datasets cannot establish unobserved intervention outcomes by themselves.
