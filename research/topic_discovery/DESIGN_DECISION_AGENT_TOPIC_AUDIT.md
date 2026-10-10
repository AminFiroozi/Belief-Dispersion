# Design Decision: Agent Audit With Human Verification

Date: 2026-10-10
Status: adopted for topic-family and topic-discourse validation

## Decision

Topic-family membership and same-topic-discourse judgments will use one blinded
Codex machine audit followed by explicit human verification. The human reviewer
will accept, correct, or mark each agent judgment unclear. This replaces the
earlier plan for two complete independent human topic audits.

This decision applies only to topic identity. Market-implication sentiment is
more subjective and remains subject to independent human validation before a
production labeling model is selected.

## Rationale

The topic task is principally definitional: does a headline belong to one of the
predeclared continuing discourses, and do two headlines contribute to the same
discourse? A capable language model can perform a useful first pass, while a
human verifier can focus effort on disagreements and boundary cases.

The procedure reduces annotation burden without treating the agent as ground
truth. Because the human sees the agent answer, the result is an adjudicated
human-verified reference, not an estimate of independent human-model agreement.

## Procedure

1. The agent reads only the blinded rater-1 headline and pair files plus the
   frozen rater guide.
2. The agent does not inspect hidden keys, machine assignments, rater-2 files,
   sources, dates, market data, or market outcomes.
3. The completed agent files are checksummed and preserved.
4. Separate verification sheets display the agent judgment and provide
   `human_decision`: `accept`, `correct`, or `unclear`.
5. For `correct`, the human supplies the corrected topic/relation and
   confidence. For `accept`, correction fields remain blank.
6. Hidden keys remain closed until human verification is complete and
   checksummed.
7. Final labels are derived deterministically from accepted agent judgments and
   explicit human corrections.

## Reporting

Report agent acceptance rate, correction rate, unclear rate, and correction
confusion by topic. Do not report Cohen kappa or characterize this workflow as
two independent raters. Any unreviewed agent label remains a machine label, not
human-validated ground truth.
