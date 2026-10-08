# Duration estimates and learning
Resolve cognitive_modality_defaults.<modality>.multiplier in Memory, falling back to 1.00 for a
missing entry. Estimate round(base_minutes * multiplier). Do not multiply an already scaled estimate
again. Learn only from completed, valid timed sessions through audit, once per stable session identity.
The update is clamp(current + .10 * (actual/estimated - current), .20, 2.00), rounded to two decimals.
Invalid or zero estimates require review. No passive decay; pauses preserve all learned values.
