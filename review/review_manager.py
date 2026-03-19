"""Simulation of human review decisions for flagged VAT record issues.

The prototype includes a lightweight review stage to emphasise that analytical
flags should be interpreted by a person before any downstream action is taken.
This module records simple confirm, reject, or ignore decisions to illustrate
that human oversight remains central to the workflow.
"""

import logging

import pandas as pd

LOGGER = logging.getLogger(__name__)


class ReviewManager:
    """Manage the prototype's simulated human review process.

    Notes
    -----
        The current implementation uses simple deterministic rules to mimic how a
        reviewer might respond to validation findings and anomalies. This keeps
        the demonstration reproducible while preserving the concept of explicit
        human judgement within the system design.
        """

    @staticmethod
    def _decide_outcome(item: dict) -> tuple[str, str]:
        """Return a simple prototype review outcome and supporting note.

        The rules are intentionally small and transparent:
        invalid or missing values are rejected, duplicate rows are ignored, and
        anomalies are confirmed only when their score is high enough to merit
        escalation.
        """
        issue_type = item.get("issue_type", "anomaly")
        score = item.get("anomaly_score", 0)

        if issue_type in {"missing_value", "invalid_date_format", "invalid_numeric_format", "missing_column"}:
            return "reject", "Record requires source spreadsheet correction."

        if issue_type == "duplicate_row":
            return "ignore", "Potential duplicate noted for user review."

        if issue_type == "anomaly":
            if score > 100:
                return "confirm", "Suspicious transaction retained for follow-up."
            return "ignore", "Low-severity anomaly not escalated."

        return "confirm", "Flag confirmed during prototype review."

    def review_issues(self, review_items: list[dict]) -> pd.DataFrame:
        """Generate a review log for flagged validation and anomaly items.

        Parameters
        ----------
        review_items : list of dict
            Combined list of issue records and anomaly records produced by
            earlier pipeline stages.

        Returns
        -------
        pandas.DataFrame
            Tabular log of review decisions, including the row index, issue
            type, simulated decision, and supporting note.

        Notes
        -----
        The prototype records one of three outcomes for each reviewed item:
        ``confirm``, ``reject``, or ``ignore``. The purpose is to demonstrate
        the review workflow rather than prescribe real assurance practice.
        """
        LOGGER.info("Simulating human review decisions")
        decisions = []

        for item in review_items:
            issue_type = item.get("issue_type", "anomaly")
            decision, review_note = self._decide_outcome(item)
            LOGGER.debug(
                "Reviewed item for row %s with issue type %s -> %s",
                item.get("row_index"),
                issue_type,
                decision,
            )

            decisions.append(
                {
                    "row_index": item.get("row_index"),
                    "issue_type": issue_type,
                    "decision": decision,
                    "notes": item.get("message") or item.get("reason") or review_note,
                }
            )

        review_log = pd.DataFrame(decisions)
        LOGGER.info("Review simulation recorded %s decisions", len(review_log))
        return review_log
