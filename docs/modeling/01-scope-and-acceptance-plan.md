# Step 1: Scope and acceptance definitions

Status: documentation and review only; no notebook or implementation required.

Step 1 records the experiment scope, requirements, clinical-error definitions, acceptance criteria, and open decisions. The earlier proposal to implement a scope notebook is withdrawn following review with the user.

The existing architecture documents provide this foundation:

- [Master plan, including Step 1](../architecture/06-step-by-step-plan.md)
- [Healthcare accuracy criteria](../architecture/05-healthcare-accuracy.md)
- [Evaluation definitions](../architecture/03-evaluation-and-delivery.md)
- [Model and mobile constraints](../architecture/02-model-and-mobile.md)

The fixed direction is Python experiments, Gemma through OpenRouter, model-free BM25 retrieval initially, grounded answers with exact source highlighting, and eventual offline iOS/Android validation. Device limits, clinical authority, and deployment suitability remain separate review decisions; documenting them does not establish approval.

The first executable notebook will support [Step 2: corpus inventory](02-corpus-inventory-plan.md). Do not create a Step 1 notebook or Step 1 machine artifacts.
