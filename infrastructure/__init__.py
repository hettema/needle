"""Durable execution and storage: the store, the corpus on disk, the watcher.

This is the only package that touches a file system, a database or a clock.
It applies what `board/` decides and reads what `board/` needs.
"""
