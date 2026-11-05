# Research-facility data extract

`data/ornl_infiltration_subset.csv` is an **observational extract**, included for inspection and context. It is not a TwinLab diagnosis, benchmark, replay of the simulator's interventions, or evidence of field performance. The records come from an unoccupied research facility; conditions such as weather, controls, and schedules can differ between days. Daily temperature differences do not establish a causal effect or justify a diagnostic conclusion.

## Source, credit and license

Kim, Janghyun; Leach, Matt; and Im, Piljae (2019), National Renewable Energy Laboratory / U.S. Department of Energy, [Curated Test Fault Data Set](https://doi.org/10.25984/1862682) ([catalog record](https://catalog.data.gov/dataset/curated-test-fault-data-set); [source description PDF](https://data.openei.org/files/909/curateddatasetdetaildescription.pdf); [source archive](https://data.openei.org/files/909/dataset.zip)). Experiments were performed at Oak Ridge National Laboratory's Flexible Research Platform. The catalog identifies the dataset license as [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). This extract retains four source filenames, timestamps, and three columns; other columns and scenarios are omitted and temperatures are converted to Celsius only for reporting. No endorsement by the dataset publishers is implied.

The source documentation's experiment schedule and its filename convention identify December 7 and 14, 2017 as 20% and 40% increased effective leakage area, and December 9 and 10 as baseline dates. Window openings were used to achieve the target leakage levels, with rooms 106 and 204 involved. The source PDF's Table 5 lists the baseline dates as 2019, inconsistent with its schedule and source filenames; this extract follows the source filenames and schedule, and the discrepancy remains unresolved. The source table lists daily average ambient temperatures of 3.8°C and 0.6°C for the two fault days; the simple averages of the 96 extracted `T_out_Avg` values are 4.26°C and 2.25°C, respectively. The reason for this difference is not established. Do not treat those summaries as interchangeable.

## Reproduce the extract

On 29 October 2026, the archive downloaded through the catalog's linked source had SHA-256 `1e6cd3df991abf865f7567e6cc0ac246968299eb02dfe9464d887727f930dde0`. Running the command below produced a byte-for-byte match with the checked-in CSV: all 384 records and selected fields match that downloaded archive. This digest is a local integrity check, not a publisher-signed checksum. If the publisher changes the archive, the script intentionally rejects it pending review.

```bash
python field_replay.py --extract /path/to/dataset.zip --output /tmp/ornl-extract.csv
cmp data/ornl_infiltration_subset.csv /tmp/ornl-extract.csv
python field_replay.py
```

The last command reports descriptive means; `python -m unittest discover -s tests -p 'test_field_replay.py' -v` checks extraction, conversion, invalid data handling, and the current file's shape. Those tests do not independently authenticate the source. Timestamp interpretation, weather normalization, measurements outside the three selected fields, and equipment or site variation have not been evaluated.
