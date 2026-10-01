# Processes

One file per kind of work that repeats (for example `weekly-status-update.md`). The `save` skill
writes these as it notices them. A skill is built from a process file only if you agree.

Each process file has:

    # <Process name>
    skill-offer: not-yet        # not-yet · offered-accepted · offered-declined
    skill: none                 # or the path to the skill built from this

    ## Steps (as actually done)
    ## Inputs and sources
    ## Output and format
    ## Corrections and preferences
    ## Occurrences
    - YYYY-MM-DD: <one line on this time>
