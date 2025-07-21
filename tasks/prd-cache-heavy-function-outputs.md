# Product Requirements Document (PRD): Cache Heavy Function Outputs in Database

## 1. Introduction/Overview

This feature will update the database schema to store the outputs of computationally expensive ("heavy") functions directly in the `posts` table. By caching these outputs, the system can avoid re-analyzing posts on every run, significantly improving performance for repeated analyses and queries.

## 2. Goals

- Reduce redundant computation by persisting heavy function outputs.
- Improve performance of data analysis and search features.
- Ensure outputs are available for internal use without exposing them externally.

## 3. User Stories

- As a developer, I want to store the results of heavy analysis functions in the database so that I can reuse them without recalculating each time.
- As a system, I want to retrieve cached analysis results for a post if available, to speed up processing.

## 4. Functional Requirements

1. The system must identify which heavy function outputs are suitable for caching (e.g., word frequency, sentiment analysis, custom metrics).
2. The database schema must be updated to add new columns to the `posts` table, one for each selected heavy function output.
3. Each column must store the output in a format appropriate for the metric (e.g., integer, float, or short string; avoid blobs unless necessary).
4. The system must provide a mechanism to generate and store these outputs on-demand (i.e., when a function is called and the value is not already present).
5. Once stored, the outputs must not be updated unless the post itself changes (write-once policy).
6. The system must use the cached value if present, otherwise compute and store the value.
7. The cached outputs must not be exposed via any public API or UI.
8. The implementation must use SQLAlchemy for all database interactions.
9. All changes must be covered by appropriate unit tests.

## 5. Non-Goals (Out of Scope)

- Exposing cached outputs to end users or external systems.
- Caching outputs for tables other than `posts`.
- Supporting updates to cached outputs unless the post data changes.

## 6. Design Considerations (Optional)

- Column names should clearly indicate the cached metric (e.g., `cached_word_freq`, `cached_sentiment`).
- Consider the impact on database size and query performance.
- Use Alembic for schema migrations.

## 7. Technical Considerations (Optional)

- Ensure backward compatibility with existing data.
- Use SQLAlchemy models and migrations for all schema changes.
- Avoid storing large blobs; prefer compact representations.
- Ensure that caching logic is modular and easy to extend for new metrics.

## 8. Success Metrics

- Reduction in average processing time per post for repeated analyses.
- No increase in error rates or data integrity issues.
- All relevant unit tests pass.

## 9. Open Questions

- Which specific heavy function outputs should be prioritized for caching?
- Are there any size limits for the new columns?
- Should there be a mechanism to invalidate or refresh cached values if needed in the future?

---
