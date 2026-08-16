"""Baysix Factory — venue-agnostic autonomous strategy factory.

The core is deliberately free of any platform. A venue is an adapter implementing
six verbs (`factory.venue.Venue`); the search, the objective, the pre-registration
and the adjudication never know which one is running.
"""

__version__ = "0.1.0"
