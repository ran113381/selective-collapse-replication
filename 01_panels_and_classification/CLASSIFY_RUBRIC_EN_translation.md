# Rubric for classifying Stack Overflow questions by AI substitutability (component B)

> **English translation, prepared for readers of this package.** The operative
> instrument is the Chinese original, `CLASSIFY_RUBRIC.md`, in this directory.
> This translation was not given to any rater. Where the two differ, the
> original governs.

Assign each Stack Overflow python question an **AI-substitutability** score:
whether a capable LLM could give a complete, correct answer **from the question
text alone**, without the asker's specific runtime context, proprietary code, or
several rounds of back-and-forth.

## Scoring 0–4

- **4 = pure GENERATION**: a concept, an algorithm or a standard how-to; self-contained; has a single standard answer; ChatGPT gets it right in one go.
  Examples: "how to read three integers in one line", "why `300 is 301-1` returns True", "find all root-to-leaf paths of a tree", "the replacement for classmethod+property in 3.11".
- **3 = leaning generation**: a standard approach plus a little context.
  Examples: "merge several dataframes by suffix", "rename CSV columns according to a config", "pandas assignment under multiple conditions".
- **2 = mixed / leaning verification**: needs some judgment or the asker's specific setup.
  Examples: "my Dash callback is nearly written but something is missing", "mypy rejects my protocol implementation".
- **1 = VERIFICATION**: debugging the asker's specific error, code or environment; tuning performance on their data; specific to a production environment.
  Examples: "conda proxy fails on home Wi-Fi", "a merge pushes memory to 1.6 TB", "celery queue duplication under high load".
- **0 = pure verification**: entirely bound by context or judgment; cannot be answered from the text alone.

## Label

`label = "GEN" if score >= 3 else "VER"`

## Key principles

- Judge by the question's **intrinsic type** and **ignore when it was asked** (do not infer whether it was posted before or after ChatGPT).
- Look at title + tags + body_excerpt; `[CODE]`/`[code]` mark collapsed code blocks.
- The core judgment: is the answer "generating a piece of standard code or an explanation" (GEN), or "diagnosing or weighing this particular person's specific situation" (VER)?

## Output format

For each question output `{"question_id": <int>, "score": <0-4>, "label": "GEN"|"VER", "why": "<reason of at most 12 words>"}`, collected into one JSON array.
