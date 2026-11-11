"""SentinelAI command-line interface.

The CLI has two independent modes:

* **Local** (``sentinel scan``) — runs the OWASP/parser/risk engines in-process.
  No server, database, or network required. This is the fastest way for a new
  developer to see the product work.
* **Remote** (``sentinel login|upload|scans|report``) — talks to a running API
  using a bearer token stored in ``~/.sentinelai/config.json``.
"""

__version__ = "1.0.0"
