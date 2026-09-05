# Collect human calibration labels

Start with [worksheet.md](worksheet.md), or use [worksheet.json](worksheet.json).
The twelve cases have 18 fixed subquestions, six topic groups and a pinned source
corpus. `manifest.json` identifies exact candidate and worksheet inputs. No human
labels or Hermes outcome labels have been collected. The prior Hermes review was
of the design, not these answers.

Candidate answers are deliberately authored calibration probes with mixed quality.
They are not real model/arm outputs, gold labels or evidence of system performance.
They include source-backed answers and potential omissions, unsupported authority,
misleading citations, lineage errors or inappropriate refusal for the reviewer to
judge. No author answer key or intended outcome classification appears in the
worksheet. Source cards are synthetic, and all cases remain exposed calibration.

Magnus can return labels by case ID using the worksheet fields. Save the returned
labels in a separate versioned record tied to the source/candidate/input hashes;
preserve the blank input artifacts. Never infer a label from silence or summarize
an unreviewed item as approved. If a source/question needs correction, version the
input and recollect affected labels rather than overwriting reviewed evidence.

After human labels exist, freeze a judge prompt/version and compare a fresh Hermes
pass without revealing those labels or author expectations. Log the actual model,
input/output digests and disagreements. Refer disagreements and critical findings
to Magnus. Human calibration on these authored probes can debug a rubric, but does
not establish judge reliability on real-model enterprise outputs; a later reviewed
representative sample is still needed. One-human quality conclusions remain
provisional. No A/B/C comparison or threshold acceptance follows from this worksheet.
