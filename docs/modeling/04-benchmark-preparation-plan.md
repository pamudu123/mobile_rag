# Step 4: Skipped — use the existing Q&A

Status: skipped for now by user decision; no implementation planned.

Use `data/questions/Q_S1.json` and `data/questions/Q_S2.json` as the working benchmark with their existing reference answers and answerability labels. Their correctness is an explicit user-provided working assumption, not a new verification result.

Do not create `notebooks/04_benchmark_preparation.ipynb`, Step 4 annotation artifacts, a review queue, or a new development/test split in this phase. Do not change the original Q&A files. Basic loading/schema checks needed to run later experiments are implementation details of those experiments, not a reinstated preparation stage.

Keep Q&A reference answers outside the retrieval index and normal model prompts. Later reports should describe results as agreement with the supplied benchmark. Do not label it an independently reviewed gold set or claim an independent held-out evaluation when no such split was established. Metrics requiring annotated source spans remain unavailable until those annotations exist; do not fabricate them.

Step 5, passage/chunk and citation preparation, follows the combined Step 2. Existing step numbers remain unchanged. No code has been created by this decision.
