# Grading: delivery metrics in code, content scoring via LLM.
# See spec §8.8.

FILLERS_NO = {"eh", "øh", "ehm", "liksom", "altså", "på en måte", "ikke sant", "sånn", "da", "jo", "vel", "egentlig"}
SOFT_FILLERS = {"altså", "da", "jo", "vel", "egentlig"}  # weight 0.5, never surfaced as errors
