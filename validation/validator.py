"""Validation routines for identifying basic VAT data quality issues.

The validation layer captures structural and formatting issues that commonly
appear in spreadsheet-based bookkeeping workflows. The checks are intentionally
simple and interpretable so that they can support a human reviewer without
introducing opaque automated corrections.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from review.issue_interpreter import RawIssueSignal, interpret_signal
from review.models import (
    DeterminismType,
    Issue,
    IssueStatus,
    ReviewState,
    RiskLevel,
    build_issue_id,
    build_record_id,
    utc_now_iso,
)

LOGGER = logging.getLogger(__name__)

EXPECTED_COLUMNS = ["date", "description", "net_amount", "vat_amount"]
NUMERIC_COLUMNS = ["net_amount", "vat_amount"]
VAT_RATE_STANDARD = Decimal("0.20")
VAT_RATE_ALTERNATIVES = (Decimal("0.05"), Decimal("0.00"))
VAT_RATE_TOLERANCE = Decimal("0.01")
MIN_NET_THRESHOLD = Decimal("1.00")
VAT_RATE_RULE_ID = "VR021"
ISO_DATE_PATTERN = r"\d{4}-\d{2}-\d{2}"


def _column_has_any_non_missing(dataframe: pd.DataFrame, column: str) -> bool:
    if column not in dataframe.columns:
        return False
    return bool((~dataframe[column].map(_is_missing_cell)).any())


def _source_column_is_present(dataframe: pd.DataFrame, column: str) -> bool:
    mapping = dataframe.attrs.get("source_mapping", {})
    if isinstance(mapping, dict):
        return mapping.get(column) is not None
    return column in dataframe.columns


def _optional_review_column_enabled(dataframe: pd.DataFrame, column: str) -> bool:
    """Enable optional-field prompts only when the source file meaningfully uses the column."""
    return _source_column_is_present(dataframe, column) and _column_has_any_non_missing(dataframe, column)

def _normalise_scalar(value: Any) -> Any:
    """Convert pandas scalars into plain Python values for issue serialisation."""
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def _to_decimal_exact(value: Any) -> Decimal | None:
    """Convert a numeric-looking value to Decimal without inheriting float noise."""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, Decimal):
        return abs(value)

    try:
        return abs(Decimal(str(value).strip()))
    except (InvalidOperation, AttributeError, ValueError):
        return None


def _format_rate(rate: Decimal) -> str:
    """Render a rate as a compact percentage string for review text."""
    percentage = (rate * Decimal("100")).normalize()
    if percentage == percentage.to_integral():
        return f"{int(percentage)}%"
    formatted = format(percentage.quantize(Decimal("0.01")), "f").rstrip("0").rstrip(".")
    return f"{formatted}%"


def _normalise_vat_code(value: Any) -> str | None:
    """Normalise VAT code labels into a compact uppercase token."""
    if value is None or pd.isna(value):
        return None
    token = str(value).strip().upper()
    return token or None


def _parse_transaction_dates(date_values: pd.Series) -> pd.Series:
    """Parse ISO dates first, then fall back to day-first parsing for non-ISO strings."""
    parsed_dates = pd.Series(pd.NaT, index=date_values.index, dtype="datetime64[ns]")
    if pd.api.types.is_string_dtype(date_values) or date_values.dtype == "object":
        text_values = date_values.astype("string").str.strip()
    else:
        text_values = date_values.astype("string")

    iso_mask = text_values.str.fullmatch(ISO_DATE_PATTERN, na=False)
    if iso_mask.any():
        parsed_dates.loc[iso_mask] = pd.to_datetime(
            text_values.loc[iso_mask],
            format="%Y-%m-%d",
            errors="coerce",
        )

    fallback_mask = ~iso_mask & text_values.notna() & text_values.ne("")
    if fallback_mask.any():
        parsed_dates.loc[fallback_mask] = pd.to_datetime(
            text_values.loc[fallback_mask],
            errors="coerce",
            dayfirst=True,
        )

    return parsed_dates


def _rate_matches(observed_rate: Decimal, target_rate: Decimal) -> bool:
    return abs(observed_rate - target_rate) <= VAT_RATE_TOLERANCE


def _build_tax_rate_issue(
    dataframe: pd.DataFrame,
    row_index: int,
    *,
    detected_rate: Decimal,
    matched_rate: Decimal | None,
    issue_type: str,
    status: IssueStatus,
    risk_level: RiskLevel,
    determinism_type: DeterminismType,
    detection_summary: str,
    why_it_matters: str,
    recommended_manual_check: str,
    possible_vat_review_impact: str | None = None,
) -> Issue:
    """Create a direct Issue object for VAT-rate review outcomes."""
    source_snapshot = _build_source_snapshot(dataframe, row_index)
    net_value = _normalise_scalar(dataframe.at[row_index, "net_amount"]) if row_index in dataframe.index else None
    vat_value = _normalise_scalar(dataframe.at[row_index, "vat_amount"]) if row_index in dataframe.index else None

    expected_value: dict[str, Any] = {
        "standard_rate": float(VAT_RATE_STANDARD),
        "tolerance": float(VAT_RATE_TOLERANCE),
        "observed_rate": float(detected_rate),
        "allowed_rates": [float(VAT_RATE_STANDARD), *[float(rate) for rate in VAT_RATE_ALTERNATIVES]],
    }
    if matched_rate is not None:
        expected_value["matched_rate"] = float(matched_rate)
        expected_value["match_band"] = _format_rate(matched_rate)

    return Issue(
        issue_id=build_issue_id(VAT_RATE_RULE_ID, row_index, ("net_amount", "vat_amount")),
        rule_id=VAT_RATE_RULE_ID,
        record_id=build_record_id(row_index),
        issue_type=issue_type,
        category="VAT rate review",
        status=status,
        risk_level=risk_level,
        determinism_type=determinism_type,
        detection_summary=detection_summary,
        why_it_matters=why_it_matters,
        possible_vat_review_impact=possible_vat_review_impact or why_it_matters,
        recommended_manual_check=recommended_manual_check,
        review_state=ReviewState.OPEN,
        detected_at=utc_now_iso(),
        row_index=row_index,
        field_names=("net_amount", "vat_amount"),
        detected_value={
            "net_amount": net_value,
            "vat_amount": vat_value,
            "observed_rate": float(detected_rate),
        },
        expected_value=expected_value,
        evidence_expected="Invoice, receipt, or supporting VAT evidence",
        source_snapshot=source_snapshot,
    )


def _detect_vat_rate_issue(dataframe: pd.DataFrame, row_index: int, net_amount: Any, vat_amount: Any) -> Issue | None:
    """Return a VAT-rate issue when the observed rate does not fit the heuristic bands."""
    net_decimal = _to_decimal_exact(net_amount)
    vat_decimal = _to_decimal_exact(vat_amount)
    if net_decimal is None or vat_decimal is None:
        return None

    if net_decimal < MIN_NET_THRESHOLD:
        return None

    if net_decimal == 0:
        return None

    observed_rate = vat_decimal / net_decimal
    declared_vat_code = _normalise_vat_code(dataframe.at[row_index, "vat_code"]) if "vat_code" in dataframe.columns else None

    if declared_vat_code in {"SR", "STANDARD", "STANDARD_RATE"} and _rate_matches(observed_rate, VAT_RATE_STANDARD):
        return None
    if declared_vat_code in {"ZR", "ZERO", "ZERO_RATE", "ZERO_RATED", "EXEMPT"} and _rate_matches(
        observed_rate,
        Decimal("0.00"),
    ):
        return None
    if declared_vat_code in {"RR", "REDUCED", "REDUCED_RATE", "REDUCED_RATED"} and _rate_matches(
        observed_rate,
        Decimal("0.05"),
    ):
        return None

    if _rate_matches(observed_rate, VAT_RATE_STANDARD):
        return None

    for alternative_rate in VAT_RATE_ALTERNATIVES:
        if _rate_matches(observed_rate, alternative_rate):
            observed_rate_text = _format_rate(observed_rate)
            matched_rate_text = _format_rate(alternative_rate)
            detection_summary = (
                f"The transaction tax rate is {observed_rate_text}, which is not the 20% standard rate. "
                f"It is close to the {matched_rate_text} band and should be manually confirmed."
            )
            why_it_matters = (
                f"The VAT amount is arithmetically plausible, but the record appears to use a {matched_rate_text} "
                "treatment that may require business-specific justification."
            )
            recommended_manual_check = (
                f"Check the source invoice, contract, or VAT treatment note to confirm whether the {matched_rate_text} "
                "rate is applicable."
            )
            return _build_tax_rate_issue(
                dataframe,
                row_index,
                detected_rate=observed_rate,
                matched_rate=alternative_rate,
                issue_type="vat_rate_review_prompt",
                status=IssueStatus.REVIEW_REQUIRED,
                risk_level=RiskLevel.MEDIUM,
                determinism_type=DeterminismType.PARTLY_DETERMINISTIC,
                detection_summary=detection_summary,
                why_it_matters=why_it_matters,
                recommended_manual_check=recommended_manual_check,
                possible_vat_review_impact=(
                    "The amount can still be valid, but the selected VAT treatment should be confirmed against the source evidence."
                ),
            )

    observed_rate_text = _format_rate(observed_rate)
    allowed_rates_text = ", ".join(_format_rate(rate) for rate in (VAT_RATE_STANDARD, *VAT_RATE_ALTERNATIVES))
    detection_summary = (
        f"The transaction tax rate is {observed_rate_text}, which does not match the standard or fallback VAT bands."
    )
    why_it_matters = (
        "The VAT ratio is not consistent with the prototype's baseline tax-rate heuristic, so the row may contain a "
        "calculation error or an unsupported VAT treatment."
    )
    recommended_manual_check = (
        "Recalculate the VAT treatment from the source evidence and confirm whether the entry should be corrected or "
        "documented as a special case."
    )
    issue = _build_tax_rate_issue(
        dataframe,
        row_index,
        detected_rate=observed_rate,
        matched_rate=None,
        issue_type="math_inconsistent",
        status=IssueStatus.NON_COMPLIANT,
        risk_level=RiskLevel.HIGH,
        determinism_type=DeterminismType.DETERMINISTIC,
        detection_summary=detection_summary,
        why_it_matters=why_it_matters,
        recommended_manual_check=recommended_manual_check,
        possible_vat_review_impact=(
            "The VAT ratio is outside the supported heuristic bands and should be treated as a probable calculation or treatment error."
        ),
    )
    issue.expected_value["allowed_rates_text"] = allowed_rates_text
    return issue


def _build_source_snapshot(dataframe: pd.DataFrame, row_index: int) -> dict[str, Any] | None:
    """Capture a lightweight row snapshot for traceability."""
    if row_index < 0 or row_index not in dataframe.index:
        return None

    row = dataframe.loc[row_index]
    return {column: _normalise_scalar(value) for column, value in row.items()}


def _is_missing_cell(value: Any) -> bool:
    """Treat nulls and blank strings as missing values."""
    if value is None or pd.isna(value):
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _build_signal(
    dataframe: pd.DataFrame,
    row_index: int,
    column: str,
    issue_type: str,
    value: Any,
    *,
    rule_id: str,
    category: str,
    expected_value: Any = None,
    evidence_expected: str | None = None,
) -> RawIssueSignal:
    """Create a raw signal for later interpretation into an issue object."""
    field_names = (column,) if column != "row" else ()
    return RawIssueSignal(
        rule_id=rule_id,
        row_index=row_index,
        issue_type=issue_type,
        category=category,
        field_names=field_names,
        detected_value=_normalise_scalar(value),
        expected_value=expected_value,
        evidence_expected=evidence_expected,
        source_snapshot=_build_source_snapshot(dataframe, row_index),
    )


def validate_vat_data(dataframe: pd.DataFrame) -> dict:
    """Perform baseline validation checks on the VAT transaction dataset.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Input VAT records table produced by the ingestion stage.

    Returns
    -------
    dict
        Dictionary containing a list of structured issue records and a summary
        issue count.

    Notes
    -----
    The validator focuses on high-value, low-complexity checks suitable for a
    research prototype: missing values, duplicated rows, unparseable dates, and
    invalid numeric entries. Findings are reported rather than corrected so that
    the financial record remains under user control.
    """
    LOGGER.info("Running validation checks on VAT dataset")
    issues: list[Issue] = []
    parsed_numeric_columns: dict[str, pd.Series] = {}

    def append_issue(issue: Issue, *, log_message: str | None = None, log_args: tuple[Any, ...] = ()) -> None:
        if log_message:
            LOGGER.warning(log_message, *log_args)
        issues.append(issue)

    if not isinstance(dataframe, pd.DataFrame):
        LOGGER.error("Validation received an invalid input type: %s", type(dataframe).__name__)
        issues.append(
            interpret_signal(
                RawIssueSignal(
                    rule_id="VR900",
                    row_index=-1,
                    issue_type="invalid_input",
                    category="Required field presence",
                    field_names=("dataframe",),
                    detected_value=type(dataframe).__name__,
                )
            )
        )
        return {
            "issues": issues,
            "issue_count": len(issues),
        }

    for column in EXPECTED_COLUMNS:
        if column not in dataframe.columns:
            LOGGER.warning("Expected column missing from dataset: %s", column)
            issues.append(
                interpret_signal(
                    _build_signal(
                        dataframe,
                        -1,
                        column,
                        "missing_column",
                        None,
                        rule_id="VR901",
                        category="Required field presence",
                        expected_value="A dataset containing all required review columns.",
                    )
                )
            )

    # Missing values are surfaced explicitly because absent bookkeeping fields
    # can undermine both tax calculations and later anomaly screening.
    missing_mask = dataframe.apply(lambda column_series: column_series.map(_is_missing_cell))
    for row_index, row in missing_mask.iterrows():
        for column, is_missing in row.items():
            if is_missing:
                if column == "date":
                    append_issue(
                        interpret_signal(
                            _build_signal(
                                dataframe,
                                row_index,
                                column,
                                "missing_transaction_date",
                                dataframe.at[row_index, column],
                                rule_id="VR001",
                                category="Required field presence",
                                expected_value="A valid transaction date.",
                                evidence_expected="Invoice, receipt, or ledger export",
                            )
                        ),
                        log_message="Missing value detected at row %s, column %s",
                        log_args=(row_index, column),
                    )
                elif column == "net_amount":
                    append_issue(
                        interpret_signal(
                            _build_signal(
                                dataframe,
                                row_index,
                                column,
                                "missing_net_amount",
                                dataframe.at[row_index, column],
                                rule_id="VR004",
                                category="Required field presence",
                                expected_value="A valid numeric net amount.",
                                evidence_expected="Invoice, receipt, or ledger export",
                            )
                        ),
                        log_message="Missing value detected at row %s, column %s",
                        log_args=(row_index, column),
                    )
                elif column == "vat_amount":
                    append_issue(
                        interpret_signal(
                            _build_signal(
                                dataframe,
                                row_index,
                                column,
                                "missing_vat_amount",
                                dataframe.at[row_index, column],
                                rule_id="VR006",
                                category="Required field presence",
                                expected_value="A valid numeric VAT amount or a confirmed zero value.",
                                evidence_expected="Invoice, receipt, or ledger export",
                            )
                        ),
                        log_message="Missing value detected at row %s, column %s",
                        log_args=(row_index, column),
                    )
                elif column == "description":
                    append_issue(
                        interpret_signal(
                            _build_signal(
                                dataframe,
                                row_index,
                                column,
                                "blank_description",
                                dataframe.at[row_index, column],
                                rule_id="VR013",
                                category="Digital record completeness",
                                expected_value="A short descriptive transaction narrative.",
                                evidence_expected="Invoice, receipt, or transaction note",
                            )
                        ),
                        log_message="Missing value detected at row %s, column %s",
                        log_args=(row_index, column),
                    )
                elif column == "invoice_reference":
                    if _optional_review_column_enabled(dataframe, "invoice_reference"):
                        append_issue(
                            interpret_signal(
                                _build_signal(
                                    dataframe,
                                    row_index,
                                    column,
                                    "missing_required_review_field",
                                    dataframe.at[row_index, column],
                                    rule_id="VR017",
                                    category="Digital record completeness",
                                    expected_value="A transaction reference used consistently within this dataset.",
                                    evidence_expected="Source spreadsheet, invoice copy, or supporting transaction evidence",
                                )
                            ),
                            log_message="Missing value detected at row %s, column %s",
                            log_args=(row_index, column),
                        )
                elif column == "gross_amount":
                    if _optional_review_column_enabled(dataframe, "gross_amount"):
                        append_issue(
                            interpret_signal(
                                _build_signal(
                                    dataframe,
                                    row_index,
                                    column,
                                    "missing_required_review_field",
                                    dataframe.at[row_index, column],
                                    rule_id="VR017",
                                    category="Digital record completeness",
                                    expected_value="A gross amount field where the dataset uses one for review support.",
                                    evidence_expected="Source spreadsheet or supporting transaction evidence",
                                )
                            ),
                            log_message="Missing value detected at row %s, column %s",
                            log_args=(row_index, column),
                        )
                elif column == "counterparty_ref":
                    if _optional_review_column_enabled(dataframe, "counterparty_ref"):
                        append_issue(
                            interpret_signal(
                                _build_signal(
                                    dataframe,
                                    row_index,
                                    column,
                                    "missing_counterparty_reference",
                                    dataframe.at[row_index, column],
                                    rule_id="VR012",
                                    category="Reference and evidence traceability",
                                    expected_value="A supplier, customer, or counterparty reference.",
                                    evidence_expected="Invoice, supplier statement, customer record, or source ledger export",
                                )
                            ),
                            log_message="Missing value detected at row %s, column %s",
                            log_args=(row_index, column),
                        )
                elif column == "document_reference":
                    if _optional_review_column_enabled(dataframe, "document_reference"):
                        append_issue(
                            interpret_signal(
                                _build_signal(
                                    dataframe,
                                    row_index,
                                    column,
                                    "missing_evidence_reference",
                                    dataframe.at[row_index, column],
                                    rule_id="VR014",
                                    category="Reference and evidence traceability",
                                    expected_value="A document or evidence reference linked to the transaction.",
                                    evidence_expected="Invoice number, receipt reference, attachment name, or evidence file identifier",
                                )
                            ),
                            log_message="Missing value detected at row %s, column %s",
                            log_args=(row_index, column),
                        )
                elif column == "category":
                    if _optional_review_column_enabled(dataframe, "category"):
                        append_issue(
                            interpret_signal(
                                _build_signal(
                                    dataframe,
                                    row_index,
                                    column,
                                    "missing_transaction_category_support_field",
                                    dataframe.at[row_index, column],
                                    rule_id="VR019",
                                    category="Digital record completeness",
                                    expected_value="A transaction type or category label used by this review workflow.",
                                    evidence_expected="Source spreadsheet classification or supporting transaction evidence",
                                )
                            ),
                            log_message="Missing value detected at row %s, column %s",
                            log_args=(row_index, column),
                        )
                elif column == "vat_code":
                    if _optional_review_column_enabled(dataframe, "vat_code"):
                        append_issue(
                            interpret_signal(
                                _build_signal(
                                    dataframe,
                                    row_index,
                                    column,
                                    "missing_required_review_field",
                                    dataframe.at[row_index, column],
                                    rule_id="VR017",
                                    category="Digital record completeness",
                                    expected_value="A VAT code where the dataset uses one for review support.",
                                    evidence_expected="Source spreadsheet or supporting transaction evidence",
                                )
                            ),
                            log_message="Missing value detected at row %s, column %s",
                            log_args=(row_index, column),
                        )
                else:
                    append_issue(
                        interpret_signal(
                            _build_signal(
                                dataframe,
                                row_index,
                                column,
                                "missing_required_review_field",
                                dataframe.at[row_index, column],
                                rule_id="VR017",
                                category="Digital record completeness",
                                evidence_expected="Source spreadsheet or supporting transaction evidence",
                            )
                        ),
                        log_message="Missing value detected at row %s, column %s",
                        log_args=(row_index, column),
                    )

    # Duplicate rows are preserved but flagged, as duplicates may indicate
    # accidental re-entry of transactions rather than legitimate repetition.
    duplicate_mask = dataframe.duplicated(keep=False)
    duplicate_indices = list(dataframe.index[duplicate_mask])
    if duplicate_indices:
        LOGGER.warning("Duplicate row pattern detected in %s row(s)", len(duplicate_indices))
    for row_index in duplicate_indices:
        issues.append(
            interpret_signal(
                    _build_signal(
                        dataframe,
                        row_index,
                        "row",
                        "exact_duplicate_row",
                        None,
                        rule_id="VR008",
                        category="Duplicate transaction risk",
                        evidence_expected="Original spreadsheet export or source transaction evidence",
                    )
            )
        )

    # Date parsing is deferred to pandas so the check remains concise and
    # aligned with the prototype's spreadsheet-oriented workflow.
    if "date" in dataframe.columns:
        date_values = dataframe["date"]
        parsed_dates = _parse_transaction_dates(date_values)
        invalid_date_mask = ~dataframe["date"].apply(_is_missing_cell) & parsed_dates.isna()
        invalid_date_indices = list(dataframe.index[invalid_date_mask])
        if invalid_date_indices:
            LOGGER.warning("Invalid date format detected in %s row(s)", len(invalid_date_indices))
        for row_index in invalid_date_indices:
            issues.append(
                interpret_signal(
                        _build_signal(
                            dataframe,
                            row_index,
                            "date",
                            "invalid_date_format",
                        dataframe.at[row_index, "date"],
                        rule_id="VR002",
                        category="Date validity and period review",
                        expected_value="A valid parseable date.",
                        evidence_expected="Invoice, receipt, or ledger export",
                    )
                )
            )

    for column in NUMERIC_COLUMNS:
        if column not in dataframe.columns:
            continue

        # Numeric coercion is used only for validation; the source values remain
        # intact so the record can still be reviewed in its original form.
        numeric_values = pd.to_numeric(dataframe[column], errors="coerce")
        parsed_numeric_columns[column] = numeric_values
        invalid_numeric_mask = ~dataframe[column].apply(_is_missing_cell) & numeric_values.isna()
        invalid_numeric_indices = list(dataframe.index[invalid_numeric_mask])
        if invalid_numeric_indices:
            LOGGER.warning("Invalid numeric format detected in %s row(s) for column %s", len(invalid_numeric_indices), column)
        for row_index in invalid_numeric_indices:
            if column == "net_amount":
                rule_id = "VR005"
                category = "Numeric validity"
                issue_type = "non_numeric_net_amount"
            else:
                rule_id = "VR007"
                category = "Numeric validity"
                issue_type = "non_numeric_vat_amount"
            issues.append(
                interpret_signal(
                    _build_signal(
                        dataframe,
                        row_index,
                        column,
                        issue_type,
                        dataframe.at[row_index, column],
                        rule_id=rule_id,
                        category=category,
                        expected_value="A valid numeric amount.",
                        evidence_expected="Invoice, receipt, or ledger export",
                    )
                )
            )

    if "net_amount" in parsed_numeric_columns and "vat_amount" in parsed_numeric_columns:
        net_amounts = parsed_numeric_columns["net_amount"]
        vat_amounts = parsed_numeric_columns["vat_amount"]
        vat_rate_mask = net_amounts.notna() & vat_amounts.notna()
        if vat_rate_mask.any():
            for row_index in dataframe.index[vat_rate_mask]:
                tax_rate_issue = _detect_vat_rate_issue(
                    dataframe,
                    int(row_index),
                    dataframe.at[row_index, "net_amount"],
                    dataframe.at[row_index, "vat_amount"],
                )
                if tax_rate_issue is not None:
                    append_issue(
                        tax_rate_issue,
                        log_message="VAT rate check produced a review item at row %s",
                        log_args=(row_index,),
                    )

    if "net_amount" in parsed_numeric_columns:
        net_amounts = parsed_numeric_columns["net_amount"]
        negative_net_mask = net_amounts.notna() & (net_amounts < 0)
        negative_indices = list(dataframe.index[negative_net_mask])
        if negative_indices:
            LOGGER.warning("Negative or unusually low net amount detected in %s row(s)", len(negative_indices))
        for row_index in negative_indices:
            issues.append(
                interpret_signal(
                    _build_signal(
                        dataframe,
                        row_index,
                        "net_amount",
                        "negative_or_unusually_low_net_amount",
                        dataframe.at[row_index, "net_amount"],
                        rule_id="VR016",
                        category="Unusual transaction review",
                        expected_value="A non-negative net amount unless the record is a documented refund, credit, or reversal.",
                        evidence_expected="Invoice, credit note, refund record, or supporting transaction evidence",
                    )
                )
            )

    if "net_amount" in parsed_numeric_columns and "vat_amount" in parsed_numeric_columns:
        net_amounts = parsed_numeric_columns["net_amount"]
        vat_amounts = parsed_numeric_columns["vat_amount"]
        suspicious_zero_mask = (
            net_amounts.notna()
            & vat_amounts.notna()
            & net_amounts.eq(0)
            & vat_amounts.eq(0)
        )
        suspicious_zero_indices = list(dataframe.index[suspicious_zero_mask])
        if suspicious_zero_indices:
            LOGGER.warning("Suspicious zero-value amount combination detected in %s row(s)", len(suspicious_zero_indices))
        for row_index in suspicious_zero_indices:
            issues.append(
                interpret_signal(
                    _build_signal(
                        dataframe,
                        row_index,
                        "net_amount",
                        "suspicious_zero_value_amount_combination",
                        {
                            "net_amount": _normalise_scalar(dataframe.at[row_index, "net_amount"]),
                            "vat_amount": _normalise_scalar(dataframe.at[row_index, "vat_amount"]),
                        },
                        rule_id="VR018",
                        category="Unusual transaction review",
                        expected_value="A documented reason for retaining an all-zero amount record.",
                        evidence_expected="Source spreadsheet note or supporting transaction evidence",
                    )
                )
            )

    if _source_column_is_present(dataframe, "invoice_reference") and _column_has_any_non_missing(dataframe, "invoice_reference"):
        invoice_reference_series = dataframe["invoice_reference"].astype("string").str.strip()
        duplicate_invoice_mask = invoice_reference_series.notna() & invoice_reference_series.ne("")
        duplicate_invoice_mask &= invoice_reference_series.duplicated(keep=False)
        for row_index in dataframe.index[duplicate_invoice_mask]:
            LOGGER.warning("Duplicate invoice reference detected at row %s", row_index)
            issues.append(
                interpret_signal(
                    _build_signal(
                        dataframe,
                        row_index,
                        "invoice_reference",
                        "duplicate_invoice_reference",
                        dataframe.at[row_index, "invoice_reference"],
                        rule_id="VR009",
                        category="Duplicate transaction risk",
                        expected_value="A document reference that uniquely identifies the transaction unless a legitimate repeated use is documented.",
                        evidence_expected="Invoice copy, export detail, or supporting transaction evidence",
                    )
                )
            )

    if _source_column_is_present(dataframe, "gross_amount") and _column_has_any_non_missing(dataframe, "gross_amount"):
        gross_numeric = pd.to_numeric(dataframe["gross_amount"], errors="coerce")
        net_numeric = parsed_numeric_columns.get("net_amount", pd.Series(index=dataframe.index, dtype="float64"))
        vat_numeric = parsed_numeric_columns.get("vat_amount", pd.Series(index=dataframe.index, dtype="float64"))
        consistent_amount_mask = net_numeric.notna() & vat_numeric.notna() & gross_numeric.notna()

        inconsistent_totals_mask = consistent_amount_mask & ((net_numeric + vat_numeric - gross_numeric).abs() > 0.01)
        for row_index in dataframe.index[inconsistent_totals_mask]:
            LOGGER.warning("Inconsistent totals detected at row %s", row_index)
            issues.append(
                interpret_signal(
                    _build_signal(
                        dataframe,
                        row_index,
                        "gross_amount",
                        "inconsistent_totals",
                        {
                            "net_amount": _normalise_scalar(dataframe.at[row_index, "net_amount"]),
                            "vat_amount": _normalise_scalar(dataframe.at[row_index, "vat_amount"]),
                            "gross_amount": _normalise_scalar(dataframe.at[row_index, "gross_amount"]),
                        },
                        rule_id="VR011",
                        category="Amount consistency",
                        expected_value="Gross amount should reconcile with net amount plus VAT amount within tolerance.",
                        evidence_expected="Invoice, receipt, or source ledger export",
                    )
                )
            )

        sign_conflict_mask = consistent_amount_mask & (
            ((net_numeric > 0) & ((vat_numeric < 0) | (gross_numeric < 0)))
            | ((net_numeric < 0) & ((vat_numeric > 0) | (gross_numeric > 0)))
            | ((vat_numeric > 0) & (gross_numeric < 0))
            | ((vat_numeric < 0) & (gross_numeric > 0))
        )
        for row_index in dataframe.index[sign_conflict_mask]:
            LOGGER.warning("Conflicting amount sign pattern detected at row %s", row_index)
            issues.append(
                interpret_signal(
                    _build_signal(
                        dataframe,
                        row_index,
                        "gross_amount",
                        "conflicting_amount_sign_pattern",
                        {
                            "net_amount": _normalise_scalar(dataframe.at[row_index, "net_amount"]),
                            "vat_amount": _normalise_scalar(dataframe.at[row_index, "vat_amount"]),
                            "gross_amount": _normalise_scalar(dataframe.at[row_index, "gross_amount"]),
                        },
                        rule_id="VR020",
                        category="Amount consistency",
                        expected_value="Related amounts should follow a consistent sign pattern unless a documented exception applies.",
                        evidence_expected="Credit note, refund evidence, reversal record, or supporting transaction evidence",
                    )
                )
            )

    LOGGER.info("Validation completed with %s issues", len(issues))
    return {
        "issues": issues,
        "issue_count": len(issues),
    }
