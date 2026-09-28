# The rating prompt, verbatim

This is the complete instruction each rating instance received. Twenty instances
were run, ten per design. The text below is identical across all twenty except
for three substitutions, listed after it.

Nothing else was supplied: no system prompt was set beyond the platform default,
no examples were given beyond those the rubric itself carries, and no instance
saw another instance's output.

---

```
You are applying a fixed content-analysis rubric to Stack Overflow python questions. Work strictly from the rubric. Do not look for, infer, or reason about when any question was posted.

Read the rubric file verbatim first:
E:\智能体论文\P9b_OSF_复现包_20260920\01_panels_and_classification\CLASSIFY_RUBRIC.md

Then read this batch of questions:
E:\智能体论文\P9b_IPM_20260919\工作文档\R1_blind_batch_01.json

Each record has: id (an opaque token), title, tags, body.

For every record, assign:
- score: integer 0-4 per the rubric's 0-4 scale
- label: "GEN" if score >= 3 else "VER"
- why: at most 12 words

Rules:
- Judge the question's intrinsic type only: is a correct complete answer producible from the text alone by a capable model (higher score), or does it require this asker's specific runtime, data, environment, or a judgment call about their situation (lower score)?
- Ignore any date, version number, or year that happens to appear in the text. It is not evidence about the rubric.
- Use the full 0-4 range. Do not compress toward the middle.
- Score every record in the batch. Do not skip any.

Write the result as a JSON array to:
E:\智能体论文\P9b_IPM_20260919\工作文档\R1_labels_batch_01.json

Format: [{"id": "Qxxxx", "score": 0, "label": "VER", "why": "..."}, ...]

Before finishing, verify with a script that the output array length equals the input array length and that every input id appears exactly once in your output. Report the count you wrote and the verification result. Do not report anything else.
```

---

## The three substitutions

| Where | Uniform-draw design (10 instances) | Panel-subsample design (10 instances) |
|---|---|---|
| Input file | `R1_blind_batch_NN.json` | `R1c_blind_batch_NN.json` |
| Output file | `R1_labels_batch_NN.json` | `R1c_labels_batch_NN.json` |
| Token prefix in the format example | `"Qxxxx"` | `"Cxxxx"` |

`NN` runs 01 to 10 within each design.

The paths are the local paths as actually issued and are reproduced unaltered.
In this package the three files they refer to are:

| Path in the prompt | Path in this package |
|---|---|
| `…\01_panels_and_classification\CLASSIFY_RUBRIC.md` | `01_panels_and_classification/CLASSIFY_RUBRIC.md` |
| `…\工作文档\R1_blind_batch_NN.json` | `06_sampling_window_test/blind_batches/` |
| `…\工作文档\R1_labels_batch_NN.json` | `06_sampling_window_test/labels/` |

## What the prompt deliberately does not contain

- The hypothesis, the predicted direction, or any existing value.
- Any date, month label, stratum index, or real question identifier. The batch
  files themselves carry only `id` (an opaque token), `title`, `tags` and `body`.
- Any statement of which design a batch belonged to. An instance could not tell
  from its instructions whether it was scoring the uniform draw or the panel
  subsample; the file name differs by one character and carries no meaning.

The instruction "Ignore any date, version number, or year that happens to appear
in the text" is in the prompt because the question bodies were left unedited and
a small number of them mention a year or an AI model or vendor; their counts and
the sensitivities that remove them are in `results/R1_sensitivity_result.json`
(`ai_era_terms`, `R1d_organic_year_excluded`, `R1d_ai_era_excluded`).
