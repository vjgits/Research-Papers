# Building with LLM APIs — Study Reference (real subject, vendor-neutral)

General working knowledge about building applications on large language model APIs, written for this
study in the author's own words. It is not taken from any certification exam, course or provider
document, and it avoids provider-specific numbers. Solvers may already know this subject; that is
the point of including one real subject.

## Tools
- T1. A tool is described to the model by a name, a description and a schema for its inputs. The model decides whether to call it mainly from the description.
- T2. The model does not run tools itself. It returns a tool call; the application runs the tool and sends the result back in the next request.
- T3. Give an agent only the tools it needs. Removing an unused tool is more reliable than instructing the model not to use it.
- T4. A tool that returns large raw output should filter or aggregate it itself, so the model receives only what it needs.

## Prompt caching
- C1. Prompt caching reuses an already processed prompt prefix. It helps only when the start of the prompt is identical across requests.
- C2. A change early in the prompt invalidates the cache for everything after it, so stable content (instructions, tool definitions, long documents) goes first and variable content last.
- C3. Providers set a minimum prefix length for caching; a prefix shorter than that is not cached at all.
- C4. Cached prefixes expire after a period without use; the lifetime depends on the provider and settings.

## Prompt injection
- I1. Prompt injection is text inside untrusted content (web pages, emails, documents, tool results) that tries to act as instructions to the model.
- I2. Telling the model in its system prompt to ignore such instructions reduces the risk but does not remove it. Consequential actions need a check enforced outside the model, such as user confirmation.
- I3. Limiting an agent's permissions limits the damage a successful injection can do.

## Evaluation
- E1. Evaluate on a fixed held-out set that was not used while writing the prompt.
- E2. A grader model from the same family as the model being graded may favour its outputs; use an independent grader or human spot checks.
- E3. Outputs vary between runs, so compare versions on enough examples, with repeated samples, to separate a real change from noise.

## Batches, formats and context
- B1. Batch interfaces process many requests asynchronously at lower cost, with results arriving later; they suit work that needs no immediate answer.
- S1. Asking for JSON in the prompt does not guarantee valid JSON. Validate outputs, or use a structured-output feature where the provider offers one.
- X1. The context window limits input plus output for one request. The model keeps no memory between requests unless the application resends earlier messages.
- X2. Long contexts cost more and can bury key instructions; remove material the task does not need.

## Reliability and sampling
- R1. Rate-limit and overload errors are usually transient; retry them with exponential back-off rather than immediately.
- M1. Lowering temperature reduces variation between runs; it does not make answers more correct.
- M2. The maximum-output setting caps response length. A response that hits the cap is cut off, and the API reports that as the stop reason.
