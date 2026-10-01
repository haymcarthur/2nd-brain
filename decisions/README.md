# Decisions

One file per decision, named `YYYY-MM-DD-short-slug.md`. Copy `_template.md`.

- **Never edit a decision to change its answer.** A new decision that replaces an old one carries
  `supersedes: <old slug>`. The old one gets `status: superseded` and `superseded_by: <new slug>`.
- **`status: proposed`**: still being discussed. It lists what it would replace, and the old decision stays active.
- **`status: active`**: decided. It needs a source: the user said so, or a meeting, email, or thread shows it landed.
- **`provenance`**: `decided` if the user said it (or a source shows it landed), `guessed` if it was inferred without that — for example during `get-set-up`'s backfill.

The `save` and `catch-up` skills handle all of this automatically.
