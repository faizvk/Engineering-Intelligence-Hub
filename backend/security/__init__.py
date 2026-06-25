"""Authentication, row-level access control, and abuse prevention.

An assistant over private incident reports and internal code is a
data-exfiltration surface: only authenticated users reach the API, retrieval can
never surface a chunk the requester isn't entitled to, and callers are throttled.
"""
