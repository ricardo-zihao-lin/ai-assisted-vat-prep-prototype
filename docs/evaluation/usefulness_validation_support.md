# Usefulness Validation Support

## Purpose

This document describes the practical support assets used to validate whether
the prototype is more useful than a raw issue-list baseline for pre-submission
VAT review work.

The usefulness validation follows the goals in `evaluation_plan.md`,
especially:

- explainability and workflow evaluation
- practical usefulness for structured review
- bounded human-in-the-loop decision support

The intent is not to prove final legal or tax correctness. The intent is to
show that the enhanced prototype output helps a reviewer understand issues,
prioritise work, and identify the next manual check more effectively than a
minimal issue list.

## Included Assets

The usefulness validation support now includes:

- `data/evaluation/review_support_case.csv`
- `data/evaluation/decision_logging_case.csv`
- `data/evaluation/review_usefulness_comparison_template.csv`
- `scripts/build_usefulness_validation_pack.py`

When the script is run, it writes:

- `output/runs/evaluation/usefulness_validation_pack/<dataset>/raw_issue_list_baseline.csv`
- `output/runs/evaluation/usefulness_validation_pack/<dataset>/review_oriented_output.csv`
- `output/runs/evaluation/usefulness_validation_pack/<dataset>/usefulness_side_by_side.csv`
- `output/evidence/evaluation/usefulness_validation_pack/usefulness_validation_task_pack.csv`
- `output/evidence/evaluation/usefulness_validation_pack/usefulness_validation_manifest.csv`

The repository also records dissertation-ready result outputs:

- `output/evidence/evaluation/usefulness_validation_pack/usefulness_comparison_results.csv`
- `output/evidence/evaluation/usefulness_validation_pack/usefulness_comparison_summary.csv`

## How The Comparison Works

### Raw issue-list baseline

The baseline intentionally keeps only minimal information:

- row index
- rule identifier
- issue type
- checked field

This is meant to simulate a simpler issue list such as:

```text
row 5 | unusual_net_amount | net_amount
```

### Review-oriented output

The enhanced output keeps the fields that directly support reviewer judgement:

- status
- risk level
- finding summary
- why it matters
- possible VAT review impact
- recommended manual check
- fields to check
- suggested action

### Side-by-side output

The generated `usefulness_side_by_side.csv` file places the baseline and the
enhanced review support fields on the same row for the same issue. This makes
it easy to compare:

- whether the issue is easier to understand
- whether the review significance is clearer
- whether the next manual step is more obvious
- whether the user would be better positioned to record a confident decision

## Recommended Evaluation Use

### Scenario 1: Explainability and prioritisation

Use `review_support_case.csv`.

Recommended focus:

- blank description
- unusual amount signals
- invalid numeric amount
- duplicate rows

Ask the reviewer:

- Which output makes the issue easier to understand?
- Which output makes the next check more obvious?
- Which output better distinguishes a hard failure from a review-only signal?

### Scenario 2: Workflow and decision support

Use `decision_logging_case.csv`.

Recommended focus:

- invalid date correction
- unusual amount escalation
- exclusion of duplicate rows
- accepted-with-note handling

Ask the reviewer:

- Which output better supports a confident review decision?
- Which output better supports evidence-based logging?
- Which output better supports escalation versus correction choices?

## Suggested Small-Scale Validation Method

If participant access is limited, a realistic undergraduate approach is:

1. Use the generated side-by-side CSVs as a fixed comparison pack.
2. Ask 3 to 5 reviewers or peers to judge each comparison row.
3. Record simple outcomes such as:
   - baseline easier
   - enhanced output easier
   - no meaningful difference
4. Ask for one short note about why.

Recommended judgement criteria:

- clarity of the issue meaning
- clarity of why the issue matters
- clarity of the next manual check
- confidence in making a review decision

This is usually more defensible than claiming usefulness without a structured
comparison method.

## Data Strategy Guidance

For usefulness validation, the primary dataset choice should remain:

- small
- controlled
- explainable
- scenario-oriented

That is why the core usefulness comparison should rely on the current prepared
evaluation datasets rather than only on larger public transaction sources.

### Optional realism extension

If you want a more realistic public-facing dataset layer, you can add an
additional synthetic VAT transaction dataset generated from a public retail
transaction substrate plus public macro indicators.

A sensible route is:

1. start with a public transaction-level retail dataset
2. map product or category groups to synthetic VAT treatments
3. encode cancellations, refunds, and zero-rated cases explicitly
4. calibrate broad monthly or sector movement to public aggregate indicators
5. publish the generated dataset and the generation script together

This should be treated as a realism extension, not as the main usefulness
proof. The main usefulness proof should still come from controlled comparison
tasks where expected reviewer advantages can be explained clearly.

## Recorded Result

Using the fixed comparison criteria defined in the task pack, the current
recorded outcome is that the enhanced review-oriented output was judged more
useful than the raw issue-list baseline for every comparison row in the pack.
The comparison result files capture this explicitly at row level and dataset
level, and the dissertation summary now surfaces the same result directly.

## Command

Run:

```powershell
venv\Scripts\python.exe scripts\build_usefulness_validation_pack.py
```

This prepares the comparison outputs needed for dissertation evidence,
demonstration, or small-scale reviewer assessment.
