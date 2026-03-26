"""Patient data — served via AssertionRepository (assertion-centric schema).

Demographics, vitals, and family history are stored as assertion rows
with category = 'vital_sign', 'family_history', etc. Use AssertionRepository
for all patient-related queries.
"""
