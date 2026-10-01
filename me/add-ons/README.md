# Add-ons

An add-on is one short markdown file describing a custom routine that runs automatically inside a
skill. Use one when you want something extra done every time a skill runs (for example "every catch-up,
pull the weekly numbers from this report into my metrics project").

- **Adding a routine** = adding a file here (for example `weekly-metrics.md`).
- **Retiring a routine** = setting `status: retired`, or deleting the file.

The `catch-up` and `save` skills run every add-on here whose `runs-in` includes them and whose `status`
is `active`, following the file's steps.

## Format

    ---
    runs-in: [catch-up]       # any of: catch-up, save, start
    status: active            # active or retired
    ends: 2026-12-31          # optional: a date or a condition, after which it should be retired
    ---

    # <Add-on name>

    ## What it does
    One or two lines.

    ## When
    Which part of the skill, and how often (every run, Mondays only, once a source has new items).

    ## Inputs
    Sources to read and files to use.

    ## Steps
    1. ...

    ## Output
    Where results go (a project's `STATE.md`, a `notes/` file, the briefing).

    ## Rules
    Anything it must always or never do.

When an add-on's `ends:` date passes or its condition is met, catch-up mentions it once under "Needs
you" in the briefing, so it can be retired.
