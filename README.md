# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

---
This project focuses on student experiences and research opportunities in the Computer Science department at the University of Illinois Chicago (UIC). The system combines unofficial student discussions from Reddit with official information from UIC research laboratories and research-area pages.

This knowledge is valuable because official university websites describe research areas, laboratories, and faculty members, but they do not explain how students actually find research positions, communicate with professors, join research groups, or experience lab culture. Students often share this practical information through online discussions and community forums, making it difficult to find through official channels.

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| #  | Source                                          | Type             | URL or file path                                                                                                                                                                                               |
| -- | ----------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Research in the CS at UIC                       | Reddit           | [https://www.reddit.com/r/uichicago/comments/15fzeez/research_in_the_cs_at_uic/](https://www.reddit.com/r/uichicago/comments/15fzeez/research_in_the_cs_at_uic/)                                               |
| 2  | How to Get Into Research?                       | Reddit           | [https://www.reddit.com/r/uichicago/comments/met23h/how_to_get_into_research/](https://www.reddit.com/r/uichicago/comments/met23h/how_to_get_into_research/)                                                   |
| 3  | How Do I Get Into Research?                     | Reddit           | [https://www.reddit.com/r/uichicago/comments/1e95n83/how_do_i_get_into_research/](https://www.reddit.com/r/uichicago/comments/1e95n83/how_do_i_get_into_research/)                                             |
| 4  | UIC Computer Science Research                   | Reddit           | [https://www.reddit.com/r/uichicago/comments/1j5cgjx/uic_computer_science_research/](https://www.reddit.com/r/uichicago/comments/1j5cgjx/uic_computer_science_research/)                                       |
| 5  | Classes or Research Labs You Loved              | Reddit           | [https://www.reddit.com/r/uichicago/comments/hkziru/all_majors_what_are_some_classes_or_research_labs/](https://www.reddit.com/r/uichicago/comments/hkziru/all_majors_what_are_some_classes_or_research_labs/) |
| 6  | High School Research Opportunities              | Reddit           | [https://www.reddit.com/r/uichicago/comments/16a8kqs/high_school_research_opportunities/](https://www.reddit.com/r/uichicago/comments/16a8kqs/high_school_research_opportunities/)                             |
| 7  | UIC Artificial Intelligence Laboratory Projects | Official Website | [https://ai.uic.edu/projects/](https://ai.uic.edu/projects/)                                                                                                                                                   |
| 8  | DBMC Moving Objects Databases Project           | Official Website | [https://dbmc.lab.uic.edu/projects/moving-objects-databases/](https://dbmc.lab.uic.edu/projects/moving-objects-databases/)                                                                                     |
| 9  | About EVL                                       | Official Website | [https://www.evl.uic.edu/about/](https://www.evl.uic.edu/about/)                                                                                                                                               |
| 10 | UIC Research Areas                              | Official Website | [https://cs.uic.edu/cs-research/research-areas-2/](https://cs.uic.edu/cs-research/research-areas-2/)                                                                                                           |


---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size: 400 characters**

**Overlap: 75 characters**

**Why these choices fit your documents:**
My document collection contains short Reddit discussions and medium-length laboratory descriptions. Using very large chunks would combine multiple unrelated topics into a single embedding, while very small chunks would lose context. I used paragraph-aware chunking with a target size of 400 characters and 75 characters of overlap. This preserves complete ideas such as student advice, research opportunities, and laboratory descriptions while maintaining enough context for semantic retrieval.

Before chunking, I removed page markers, Reddit navigation text, HTML artifacts, repeated whitespace, and other boilerplate content that was not relevant to the domain.

**Final chunk count: 19**

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** all-MiniLM-L6-v2 from Sentence Transformers.

**Production tradeoff reflection:**
I selected all-MiniLM-L6-v2 because it is lightweight, free, runs locally, and performs well for small semantic search applications. For a production system, I would compare larger embedding models with stronger semantic understanding, longer context windows, better multilingual support, and higher retrieval accuracy. I would also consider latency, infrastructure cost, and whether embeddings should be generated locally or through a hosted API.
---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
Answer the user's question using only the retrieved document context below. Do not use outside knowledge. If the context does not contain enough information, say "I don't have enough information in the documents to answer that."

The retrieved chunks are passed to the model as context. The model is instructed to answer only from that context and to decline questions that are not supported by the retrieved documents.

**How source attribution is surfaced in the response:**

Source attribution is generated programmatically rather than relying on the language model. The retrieval system collects the filenames of the retrieved documents and displays them separately in the user interface. This guarantees that every answer includes the document sources used during retrieval.
---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question                                                                        | Expected answer                                                                                 | System response (summarized)                                                                     | Retrieval quality  | Response accuracy |
| - | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------ | ----------------- |
| 1 | How do UIC students recommend getting involved in undergraduate research?       | Contact professors, show interest, apply for opportunities.                                     | Recommended contacting professors, applying broadly, showing commitment, and preparing a resume. | Relevant           | Accurate          |
| 2 | What advice do students give when emailing professors about research positions? | Send personalized emails and show genuine interest.                                             | Recommended avoiding generic emails and referencing specific research interests.                 | Relevant           | Accurate          |
| 3 | What is EVL?                                                                    | EVL is the Electronic Visualization Laboratory focused on visualization and advanced computing. | Correctly identified EVL and summarized its mission and research focus.                          | Relevant           | Accurate          |
| 4 | What research areas are available in the AI Lab?                                | Machine learning, data mining, intelligent systems, text summarization.                         | Returned "I don't have enough information in the documents to answer that."                      | Partially relevant | Inaccurate        |
| 5 | Which UIC faculty are listed for computer vision?                               | Sathya Ravi and Wei Tang.                                                                       | Correctly identified Sathya Ravi and Wei Tang.                                                   | Relevant           | Accurate          |


**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
What research areas are available in the AI Lab?

**What the system returned:**
"I don't have enough information in the documents to answer that."

**Root cause (tied to a specific pipeline stage):**

The retrieval stage returned AI-related documents, but the chunking process split the relevant project descriptions into chunks that did not contain enough complete context for the language model to confidently answer the question. As a result, the grounding prompt caused the model to decline the question.

**What you would change to fix it:**

I would increase chunk size for the AI Lab project pages, add more AI Lab source documents, and experiment with retrieving additional chunks (top-k = 7 or 8) to provide more complete context.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
The planning document provided a clear structure for the project. Defining the domain, chunking strategy, retrieval approach, and evaluation questions before writing code made it easier to implement each stage of the RAG pipeline incrementally and verify that the implementation matched the intended design.
**One way your implementation diverged from the spec, and why:**
My original plan targeted a larger number of chunks, but after inspecting the document collection I found that the sources were relatively short. Rather than artificially increasing chunk count, I prioritized chunk quality and retrieval relevance. This resulted in fewer chunks than initially expected while still producing accurate retrieval results.
---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* The Domain, Documents, and Chunking Strategy sections from planning.md.
- *What it produced:* A document ingestion and paragraph-aware chunking pipeline.
- *What I changed or overrode:*I reduced the chunk size from the initial implementation and improved cleaning rules to remove Reddit navigation text and page markers.

**Instance 2**

- *What I gave the AI:*The Retrieval Approach section and architecture diagram.
- *What it produced:*Sentence Transformer embedding code, ChromaDB integration, retrieval functions, and Gradio interface code.
- *What I changed or overrode:* modified the retrieval logic to return source filenames separately and enforced programmatic source attribution instead of relying on the language model to cite sources.

## Demo Video

[Watch Demo Video](demo/recording.mp4)