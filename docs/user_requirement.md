# User Requirements

- Run the experiment fully on-device on mobile.
- Prefer a 1.5B model. A larger model is acceptable if quantization lets it run within 1.5B-class resource limits.
- This is a RAG system. Answers must come from the provided documents.
- If the model is not grounded in the documents or does not know the answer, it must say so instead of giving a false answer.
- Latency must be considered.
- Choose a language and stack that suit on-device mobile inference.
- Target iOS first.
- The same solution must also work on Android.
- When giving an answer, highlight the source passage it came from.
- There are about 15 documents.
- Refer sample questions in @C:\Users\PK\Desktop\projects\mobile_rag\data\questions\FrontlineAI_100_Clinically_Grounded_QA_Benchmark.json

Experimental Setup
-----------------
Use python - But when building we need to keep in mind this should work in mobile
OpenRouter for models

