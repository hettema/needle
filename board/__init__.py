"""What happens: the board's rules, pure over typed inputs.

Nothing in this package touches a file, a database, a clock or a process. A
function here takes domain values and returns domain values, so every rule
the board has can be tested without a corpus on disk and can never become
the thing that runs. A ratchet refuses `subprocess` and its kin here.
"""
