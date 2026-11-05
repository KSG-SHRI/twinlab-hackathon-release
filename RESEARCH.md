# Challenging diagnostic confidence

Research snapshot: 29 October 2026. This document proposes a product direction; it does not establish novelty, customer demand, or performance in real facilities.

## The idea

TwinLab asks not only “which explanation does this model favor?” but also “which explanations still fit if the model is wrong by an illustrative amount?” Its evidence ledger compares synthetic observations with predictions for every known cause. It highlights disagreement and shows a possible next simulated comparison. The underlying screen uses a fixed ±1°C allowance per reading, chosen for demonstration rather than measured from equipment. It is neither a calibrated probability nor a claim that the true fault is in the modeled list.

The inspiration combines diagnostic cross-checking with the practical problem of a technician arriving after a fault has disappeared. A normal measurement during different operating conditions might be uninformative. A separate fixed synthetic condition-coverage exercise now demonstrates this idea: an invented low-demand reading fits both modeled hypotheses, and a later invented high-demand reading distinguishes them within an illustrative tolerance. It supplies a condition-aware handoff but does not establish real-world utility. The original thermal room model has persistent faults and does **not** model intermittent failures; the fixed example is not a physical simulator or field validation.

## Why examine this problem?

- In a [building automation discussion](https://www.reddit.com/r/BuildingAutomation/comments/1ufs9st/sanity_check/), a practitioner describes days spent tracing intermittent issues. Another [discussion](https://www.reddit.com/r/BuildingAutomation/comments/1fat6hm) describes disagreement between controls and HVAC contractors over a system fault. These are individual anecdotes, not representative market evidence.
- [NIST](https://www.nist.gov/programs-projects/automated-fault-detection-and-diagnostics-mechanical-services-commercial-buildings) describes the complexity of identifying faults in building mechanical services, while its [simulation and laboratory testing](https://www.nist.gov/publications/results-simulation-and-laboratory-testing-air-handling-unit-and-variable-air-volume-box) notes that operating conditions and missing sensors can mask some faults.
- [NASA's diagnostic work](https://ntrs.nasa.gov/citations/20120014263) provides a cross-domain example of diagnostic support for complex systems; using competing explanations is not unique to buildings.

## Where the idea is not new

[Berkeley Lab's active multi-mode diagnosis](https://eta.lbl.gov/publications/active-multi-mode-data-analysis) already uses additional operating modes to narrow HVAC fault hypotheses. Its [work on modeling and measurement constraints](https://eta.lbl.gov/publications/modeling-and-measurement-constraints) considers imperfect models and measurements. A published [air-handling-unit study](https://www.sciencedirect.com/science/article/pii/S0378778821009932) examines bounded uncertainty. Commercial systems also offer fault diagnosis and work-order workflows. TwinLab's combination is an accessible prototype and a testable workflow hypothesis, not a claim to have invented those techniques.

## Counterarguments and next validation

1. A generous mismatch bound can leave every cause plausible; a narrow one may exclude the correct explanation. The demo has no evidence for choosing a real threshold.
2. Real faults can be simultaneous, intermittent, or absent from the model. Showing one matching known fault does not establish a diagnosis. Time, load, weather, occupancy, sensor quality and equipment details matter.
3. Existing diagnostic tools or experienced technicians may already provide a better process. The proposed buyer and willingness to pay have not been validated.
4. Compare the interface with normal technician case preparation using consented, appropriately anonymized episodes and a preregistered study. Measure unsupported claims, time to prepare a handoff, and whether the next evidence request is useful; compare against current practice. This work has not been done.
5. For retrospective data, only observations that actually occurred can be assessed. A simulated prediction is not proof of what a real intervention would have done.

The application runs entirely on synthetic observations for diagnostic and optional Meta requests. Public measured data shown separately is contextual and does not validate the simulator.
