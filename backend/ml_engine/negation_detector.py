"""ConText/NegEx deterministic negation detection.

Adapted from ra-training-data-factory's context_tagger.py.
Implements the 6-status negation model with configurable trigger lists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple


@dataclass
class NegationResult:
    """Result of negation detection for a clinical text span."""

    polarity: str  # active | negated | resolved | historical | family_history | uncertain
    triggers: List[str] = field(default_factory=list)
    trigger_positions: List[Tuple[int, int]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Trigger word lists
# ---------------------------------------------------------------------------

# Pre-negation triggers — modify text AFTER the trigger
PRE_NEGATION_TRIGGERS = [
    "no evidence of", "no sign of", "no signs of", "no symptoms of",
    "denies", "denied", "denying", "deny",
    "negative for", "not", "no", "without",
    "rules out", "rule out", "ruled out", "r/o",
    "never had", "never", "absence of", "absent",
    "free of", "free from",
    "no history of", "no h/o",
    "no further", "no current", "no active",
    "no evidence", "no indication of",
    "fails to reveal", "failed to reveal",
    "unremarkable for", "unremarkable",
    "not demonstrate", "not feel", "not complain",
    "patient does not have", "does not have",
    "no complaint of", "no complaints of",
    "test negative", "tested negative",
    "with no", "shows no",
]

# Post-negation triggers — modify text BEFORE the trigger
POST_NEGATION_TRIGGERS = [
    "is ruled out", "has been ruled out", "was ruled out",
    "is excluded", "is unlikely", "is absent",
    "was negative", "is negative", "are negative",
    "not found", "not seen", "not identified", "not present",
    "not detected", "not observed",
]

# Historical triggers
HISTORICAL_TRIGGERS = [
    "history of", "h/o", "hx of", "hx:",
    "prior", "previous", "previously",
    "past history of", "past medical history",
    "status post", "s/p",
    "years ago", "months ago",
    "in \\d{4}", "back in",
    "former", "childhood",
    "remote history",
]

# Family history triggers
FAMILY_TRIGGERS = [
    "family history of", "family history significant for",
    "family history", "family hx of", "fh:",
    "fhx:", "family history:",
    "mother had", "father had", "sibling had",
    "brother had", "sister had", "parent had",
    "mother with", "father with",
    "maternal", "paternal",
    "runs in family", "runs in the family",
    "family member", "family members",
]

# Uncertain / hypothetical triggers
UNCERTAIN_TRIGGERS = [
    "possible", "possibly", "probable", "probably",
    "suspected", "suspect", "suspicious",
    "questionable", "question of",
    "consider", "considered", "considering",
    "differential", "differential includes",
    "cannot exclude", "cannot rule out",
    "may have", "might have", "could have",
    "versus", "vs", "vs.",
    "uncertain", "unclear",
    "evaluate for", "evaluated for",
    "concern for", "concerning for",
    "worry about", "worried about",
    "likely", "unlikely",
    "appears to be", "seems to be",
    "r/o",
]

# Resolved triggers
RESOLVED_TRIGGERS = [
    "resolved", "resolution of",
    "cleared", "clear of",
    "improved and discontinued",
    "no longer present", "no longer active",
    "in remission", "remission",
    "recovered from", "recovery from",
    "cured", "status post treatment",
    "was treated and resolved",
    "previously treated",
]

# Scope-breaking conjunctions
SCOPE_BREAKERS = {"but", "however", "although", "except", "yet", "nevertheless", "still"}


class NegationDetector:
    """Deterministic ConText/NegEx negation detector.

    Assigns one of 6 polarity statuses to a clinical text span:
    active, negated, resolved, historical, family_history, uncertain.
    """

    def __init__(self, scope_window: int = 20) -> None:
        self.scope_window = scope_window

    def detect(self, target_text: str, context_text: str) -> NegationResult:
        """Detect negation status for a target text within its context.

        Args:
            target_text: The diagnosis/finding text to check.
            context_text: Surrounding clinical text for context.

        Returns:
            NegationResult with polarity and trigger information.
        """
        if not target_text or not context_text:
            return NegationResult(polarity="active")

        target_lower = target_text.lower().strip()
        context_lower = context_text.lower()

        # Find the target in context
        target_pos = context_lower.find(target_lower)
        if target_pos == -1:
            # Target not found in context — check target text itself
            return self._check_text_only(target_lower)

        # Extract scope window around target
        scope_start = max(0, target_pos - self.scope_window * 8)  # ~8 chars per word
        scope_end = min(len(context_lower), target_pos + len(target_lower) + self.scope_window * 8)
        scope_text = context_lower[scope_start:scope_end]

        # Check in priority order (most specific first)
        triggers: List[str] = []

        # 1. Family history
        for trigger in FAMILY_TRIGGERS:
            if self._trigger_in_scope(trigger, scope_text, target_lower):
                triggers.append(trigger)
                return NegationResult(polarity="family_history", triggers=triggers)

        # 2. Resolved
        for trigger in RESOLVED_TRIGGERS:
            if self._trigger_in_scope(trigger, scope_text, target_lower):
                triggers.append(trigger)
                return NegationResult(polarity="resolved", triggers=triggers)

        # 3. Historical
        for trigger in HISTORICAL_TRIGGERS:
            if self._trigger_in_scope(trigger, scope_text, target_lower):
                triggers.append(trigger)
                return NegationResult(polarity="historical", triggers=triggers)

        # 4. Negation (pre-triggers)
        for trigger in PRE_NEGATION_TRIGGERS:
            if self._pre_trigger_match(trigger, scope_text, target_lower, target_pos - scope_start):
                triggers.append(trigger)
                return NegationResult(polarity="negated", triggers=triggers)

        # 5. Negation (post-triggers)
        for trigger in POST_NEGATION_TRIGGERS:
            if self._post_trigger_match(trigger, scope_text, target_lower, target_pos - scope_start):
                triggers.append(trigger)
                return NegationResult(polarity="negated", triggers=triggers)

        # 6. Uncertain
        for trigger in UNCERTAIN_TRIGGERS:
            if self._trigger_in_scope(trigger, scope_text, target_lower):
                triggers.append(trigger)
                return NegationResult(polarity="uncertain", triggers=triggers)

        # Default: active
        return NegationResult(polarity="active")

    def _check_text_only(self, text: str) -> NegationResult:
        """Check the target text itself for negation cues."""
        for trigger in PRE_NEGATION_TRIGGERS[:10]:  # Check common ones
            if trigger in text:
                return NegationResult(polarity="negated", triggers=[trigger])
        for trigger in HISTORICAL_TRIGGERS[:5]:
            if trigger in text:
                return NegationResult(polarity="historical", triggers=[trigger])
        return NegationResult(polarity="active")

    def _trigger_in_scope(self, trigger: str, scope: str, target: str) -> bool:
        """Check if a trigger appears in the scope near the target."""
        pattern = re.escape(trigger).replace(r"\\d\{4\}", r"\d{4}")
        match = re.search(pattern, scope)
        if not match:
            return False

        # Check for scope-breaking conjunctions between trigger and target
        trigger_pos = match.start()
        target_pos = scope.find(target)
        if target_pos == -1:
            return True

        between = scope[min(trigger_pos, target_pos):max(trigger_pos, target_pos)]
        for breaker in SCOPE_BREAKERS:
            if f" {breaker} " in between:
                return False

        return True

    def _pre_trigger_match(self, trigger: str, scope: str, target: str, target_rel_pos: int) -> bool:
        """Check if a pre-trigger appears BEFORE the target within scope."""
        trigger_pos = scope.find(trigger)
        if trigger_pos == -1:
            return False
        if trigger_pos >= target_rel_pos:
            return False  # Trigger must be before target

        between = scope[trigger_pos + len(trigger):target_rel_pos]
        word_count = len(between.split())
        if word_count > self.scope_window:
            return False

        for breaker in SCOPE_BREAKERS:
            if f" {breaker} " in between:
                return False

        return True

    def _post_trigger_match(self, trigger: str, scope: str, target: str, target_rel_pos: int) -> bool:
        """Check if a post-trigger appears AFTER the target within scope."""
        after_target = scope[target_rel_pos + len(target):]
        trigger_pos = after_target.find(trigger)
        if trigger_pos == -1:
            return False

        word_count = len(after_target[:trigger_pos].split())
        return word_count <= self.scope_window
