# TwinLab

**An experiment-planning workbench for diagnosing hidden faults in a simulated room.** A one-zone thermal model generates readings; a Bayesian diagnostic engine updates four possible causes; a deterministic information-gain calculation ranks the next experiment. All equipment, readings, effects and benchmark results are simulated. This is a research prototype, not a system for real building diagnosis or control.

## Run

Requires Python 3.10 or later, no dependencies.

```bash
python server.py
```

Open http://127.0.0.1:18547. Click **New mystery**, run tests, inspect the probability bars and observation log, then reveal the answer. The benchmark compares the active policy with random test selection over 200 paired seeds. Internet is not required for local mode. The interface uses local system fonts.

Run checks:

```bash
python -m unittest discover -s tests -v
node --test tests/ui.test.cjs  # optional UI smoke test; requires Node.js
```

## How it works

The model starts at 21°C with ambient temperature of 12°C. For each of four one-hour steps it uses `temperature += heat - loss * (temperature - ambient)`. Nominal heating adds 2°C per hour and nominal heat loss coefficient is 0.045/h. Faults change the heater to 1°C/hour, double heat loss to 0.09/h, or add a 2.5°C constant sensor bias; the fourth state is no fault. A reference thermometer compares sensor and reference, while heat pulse and passive cooling observe temperature changes, so a constant bias cancels. Measurements have independent seeded Gaussian noise (σ = 0.18°C). Parameters are illustrative, not calibrated physical equipment specifications.

The inference engine evaluates Gaussian likelihoods for each fault with equal priors. For each unused test, it estimates expected posterior entropy with twelve fixed normal quantile samples for each hypothesis; it divides expected information gain by a relative cost. Test costs and noise are illustrative. A baseline chooses tests randomly without replacement, using paired fault/noise seeds. Ties in the most likely diagnosis break in the fixed fault ordering. The benchmark is **in distribution**: the generator and inference model share the same assumptions. It demonstrates mechanics, not performance on actual equipment, populations, weather, or sensor failures.

## Optional Meta Muse explanation

Set `MODEL_API_KEY` in the environment before starting the server (optionally set `META_MODEL`, default `muse-spark-1.3`). The **Let Muse choose & run a test** button sends current simulated probabilities, observations, and each unused test’s predictions for the modeled hypotheses to `https://api.meta.ai/v1/chat/completions` and asks the model to choose an available test. The model does not receive the local information-gain scores or recommendation; the server validates the JSON and allowed test ID before the simulator runs it. Invalid model outputs fall back to the local information-gain choice. The separate explanation button also makes a model request. **No API request is made automatically**; every click can incur usage. No key is exposed to the browser. With no key, the button clearly returns a local explanation. The simulator, numeric ranking, and benchmark never depend on the model; Muse can select the next test when explicitly requested. A valid selection is not proof that it is optimal or that the explanation is correct; model selection has not been benchmarked against the local policy. The separate explanation request includes local recommendations. The prototype does not enforce an account-wide dollar cap; use the provider's billing controls and monitor usage before using a key. Model endpoints accept only an opaque server-generated session identifier; observations and fault parameters are generated and stored on the server, never accepted from the caller. Session identifiers, seeds and hidden faults are not included in model prompts. Sessions expire after 30 minutes, are limited to 256 in memory, and are cleared on restart; unexpected request fields are rejected. Do not use real personal or building data. Meta receives the account credentials and normal network metadata with a request; review the provider’s terms. The adapter uses a 512-token output ceiling, low reasoning effort, and a constrained JSON schema. A synthetic selection was tested in the Meta playground, but this exact API adapter has not been exercised with a live key.

## Research and design context

- [U.S. DOE, buildings data and analysis](https://www.energy.gov/cmei/buildings/data-and-analysis-buildings-sector-innovation): the scale of building energy use motivates the simulated domain.
- [NREL, Innovations in Sensors and Controls for Building Energy Management](https://docs.nrel.gov/docs/fy20osti/75601.pdf): examples include sensor drift and equipment/control faults.
- [Closed-loop AI framework for interpretable materials design](https://arxiv.org/abs/2509.18604): a research example of hypothesis-driven experimentation; TwinLab does not reproduce its method or claim comparable results.
- [A sober look at LLMs for material discovery](https://arxiv.org/abs/2402.05015): motivation to evaluate against simple baselines and avoid claiming scientific gains from model text alone.
- [Meta Model API chat-completions quickstart](https://dev.meta.ai/docs/cookbook/quickstart-chat-completions): API URL, authentication and Muse Spark model.

## Limits and next steps

Real equipment has many interacting faults, controls, weather variations, occupancy changes, sensor placement issues, and costs and safety constraints not represented here. Real deployment requires validated physical models, real-world datasets, field testing with qualified engineers and strict safety controls. Better research would compare against additional active diagnostic baselines under model mismatch and sensor noise unknown to the diagnostic engine. Muse-generated text is not verified; never treat it as a diagnosis or instruction.

## Robustness and abstention

Run `python robustness.py` to compare four policies across familiar, shifted, and unknown synthetic cases; see [EVALUATION.md](EVALUATION.md). After two observations, the interface displays a model-dependent candidate or abstains when confidence or model-fit checks fail. The abstention rule is a heuristic, not a calibrated guarantee.

## Challenge the model

The sensitivity panel asks which known hypotheses remain compatible if every simulated reading may differ from its predicted temperature change or difference by up to an illustrative ±1°C. It shows each prediction and observation, and counts how many pairs of compatible hypotheses could be separated by non-overlapping assumed ranges in each remaining experiment. The reported candidate maximizes that pair count, with deterministic tie breaks. The bound is invented, not measured or calibrated; compatible does not mean true, and an unknown fault may also fit. This screen does not replace the existing probabilistic assessment or guarantee that a future observation will separate causes. The fixed confidence-trap example uses one synthetic cooling observation of −2.5°C: the fixed-noise model gives a heat leak over 99.9%, while all four known hypotheses fit the wider illustrative bounds. The app requires at least two observations for its separate assessment, so this is not a final diagnosis. See [RESEARCH.md](RESEARCH.md) for prior art and product assumptions.

## Public research-building context

The optional **Show measured day summaries** control reads a bundled extract locally. It shows 384 temperature readings across four days from the public DOE Curated Test Fault Data Set, measured in an unoccupied research facility with baseline and deliberately induced infiltration. It sends no readings to Meta. Weather and operating conditions differ, so daily means do not establish a fault effect, and these data do not validate the simulator's actions or diagnostic accuracy. See [FIELD-DATA.md](FIELD-DATA.md) for attribution, the original data, reproducibility, and discrepancies in its published documentation.

## The fault that disappears: condition coverage

A separate fixed, local training exercise illustrates a limitation of checking equipment under conditions that do not match a reported symptom. Its invented complaint mentions high demand; the first invented reading is normal at low demand. Two invented hypotheses both fit that reading within a made-up ±0.10 deviation-unit bound, so the exercise identifies high demand as unobserved rather than clearing the fault. A second, invented high-demand reading is compatible with the conditional-fault hypothesis and incompatible with the no-fault hypothesis under the stated bounds. The two models' low/high predictions and observations are displayed, together with a condition-aware evidence handoff. Other, unmodeled causes remain possible; compatibility is not a probability. This scenario is independent of the thermal simulation, models no physical equipment, and is not a validation or a recommendation to operate equipment. It sends no data to Meta and performs no external network request.
