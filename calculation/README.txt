CALCULATION PACKAGE
Basalt-Derived Calcium for Lower Carbon Portland Cement
A Carbon Budget for Process Development
Brad Pierce | 21 October 2026 | Public package 1.0
Associated record DOI: 10.5281/zenodo.23547373

PURPOSE

Reproduce the paper's paired carbon budgets, numerical tables, sensitivity
grids and four figures. The associated paper and calculation supplement PDFs
are supplied separately in the same record. Their exact SHA-256 hashes are
listed in publication-tables.json.

These are calculated engineering scenarios, not experimental plant data.
The development target is 10–20% lower total cement-manufacturing emissions.
All coproduct credits, carbon-removal credits and allocation of necessary
burdens away from cement are zero. The principal cases assume no kiln-energy
saving. A selected operating point is a specification to test, not a claim
that the complete circuit has been demonstrated.

QUICK START — CALCULATIONS

Extract the ZIP, open a terminal in this folder, and run:

    python3 calculate_paired.py
    python3 verify_paired.py
    python3 verify_publication.py

On Windows, use py -3 in place of python3 if appropriate.
Python 3.10 or later is required. Numerical calculations and verification
use only the Python standard library and require no network connection.
The scripts find inputs relative to their own locations. Retain the folder
structure, including legacy/; calculate_paired.py imports its recovery model.

verify_paired.py reports PASS for 38 paired checks and 30 recovery-model
checks. verify_publication.py additionally checks every numeric row in
Tables 2, S1 and S2, independently recomputes the worked-case equations,
checks the reported thresholds and comparisons, verifies all supplied
paired results byte for byte after rebuilding, and checks package hashes.
It writes results/publication-verification.json. Failed checks raise an
error and return a nonzero process status.

MAIN RESULTS

At 30 g CO2e/kWh, the matched conventional inventory is 756.93 kg CO2e/t
cement and the selected basalt route is 636.048287 kg CO2e/t: a 15.97%
reduction. Avoided carbonate emissions are 456 kg/t; added recovery burdens
are 335.118287 kg/t. At 20 and 40 g/kWh the reductions are 19.4% and 12.5%.
At 50 g/kWh the reduction is 9.1%, below the development target. Combined
process penalties can eliminate the benefit. These outcomes include zero
coproduct credits.

FILES TO READ

paired-inputs.json
    Paired plant inventory, supply scenarios, recovery designs and stresses.
effective-inputs.json
    Fully expanded inputs for each named paired design, including inherited
    recovery parameters. Documentation only; the model reads the JSON files
    named in the supplement.
paired-input-inventory.csv and legacy/input_inventory.csv
    Source anchors, selected assumptions, units and evidence limits.
    The paired input inventory overrides the corresponding recovery-model
    reference settings. In particular, the principal multiplier is 1.30.
references.json
    Numbered references corresponding to the paper.
claim-map.json
    Exact numerical values and result-row selectors for the paper.
publication-tables.json
    Displayed table values and identities of the associated publication PDFs.
DATA-DICTIONARY.txt
    Definitions, units and conventions for the supplied data.
results/
    Main paired model outputs. These are the datasets supporting the paper.
figures/
    The four original SVG figures supplied with the paper and supplement.
figure-alt-text.json
    Descriptions of the four figures.
MANIFEST.sha256
    Integrity hashes for all fixed package payloads.

FIGURE REPRODUCTION — OPTIONAL

Install the pinned plotting dependencies into a Python environment:

    python3 -m pip install -r requirements-plots.txt
    python3 plot_revision.py

The verified environment uses Matplotlib 3.11.2 and NumPy 2.5.4 with
Python 3.12.14. Installing these optional dependencies may require a network
connection; plotting itself is offline. Some pinned releases may require a
newer Python than the minimum needed for numerical calculations.
The script writes all four figures as SVG and also generates PNG convenience
copies. The SVG originals are the vector artwork used in the publication
PDFs. PNG files are not needed for numerical reproduction or publication.

MODEL AND DATA CONVENTIONS

One tonne of equivalent cement at the factory gate is the functional unit.
Both routes use the same clinker fraction, required product performance and
energy-supply scenario. All necessary recovery burdens are charged to cement.
Shared plant operations cancel in absolute savings but affect the percentage
denominator. Electricity factors are kg CO2e/kWh in data files; multiply by
1000 to obtain the g CO2e/kWh labels used in the paper. Fractions in CSV files
are fractions, not percentages. Full precision is retained in result files;
rounding occurs only for display.

Source-reported values, author-selected assumptions and derived quantities
are distinguished in the inventories. The paired model does not replace the
selected common inventory with an EPD headline total. It reconstructs the
comparison from explicit components. Site-specific assays, recovery,
reagent demand, utilities and residual-treatment inventories should replace
the selected assumptions when measurements become available.

legacy/ supplies the recovery calculation and its diagnostic checks. Its
standalone outputs use a separate fixed 919 kg/t reference and include an
explicitly labeled optional kiln-energy sensitivity. Those auxiliary outputs
are not the paper's paired main cases. Only the distinct fixed-inventory
comparison discussed in the supplement uses that reference basis. Use
results/paired-scenarios.csv for the main paired conclusions. The directory
name is retained because it is the dependency path specified in the supplement.

To explore assumptions, make a working copy of the package before changing
inputs. Run calculate_paired.py again. Changed inputs will intentionally fail
the fixed-publication integrity and displayed-result checks; those checks
test reproduction of this paper, not the validity of alternative scenarios.

AUTHORSHIP AND RIGHTS

This report was developed by Brad Pierce with substantial assistance from an
AI model. He established the research objectives and editorial direction and
retains responsibility for the claims, source attributions, and decisions
about publication.

© 2026 Brad Pierce · CC BY-NC 4.0
See LICENSE.txt. External publications are cited, not redistributed.
