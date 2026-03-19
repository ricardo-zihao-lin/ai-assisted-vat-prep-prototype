"""Utilities for loading tabular VAT records into a pandas DataFrame.

This module provides the ingestion layer for the prototype pipeline. Its role
is intentionally narrow: accept a spreadsheet-like input file, read it with
pandas, and standardise column naming conventions so that downstream modules can
operate on a predictable schema. The implementation favours transparency over
aggressive preprocessing because the prototype is designed to support review of
financial records rather than silently reshape them.
"""

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)


def normalize_column_name(column_name: str) -> str:
    """Convert a source column heading into a normalised internal name.

    Parameters
    ----------
    column_name : str
        Raw column label extracted from the input spreadsheet.

    Returns
    -------
    str
        Lower-case column name with surrounding whitespace removed and spaces
        converted to underscores.

    Notes
    -----
    Column normalisation provides a lightweight contract between external files
    and the rest of the prototype. This keeps later processing stages focused
    on validation and review rather than defensive handling of naming variants.
    """
    LOGGER.debug("Normalising column name: %s", column_name)
    normalized = column_name.strip().lower().replace(" ", "_")
    return normalized


def load_spreadsheet(file_path: str | Path) -> pd.DataFrame:
    """Load spreadsheet data and return a normalised VAT records table.

    Parameters
    ----------
    file_path : str or pathlib.Path
        Path to a CSV or Excel workbook containing VAT transaction records.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the loaded records with normalised column names.

    Raises
    ------
    ValueError
        Raised when the provided file extension is not supported by the
        prototype ingestion layer.

    Notes
    -----
    The loader deliberately performs minimal transformation. It reads the file
    and harmonises column headings, leaving substantive data checks to the
    validation and anomaly detection modules.
    """
    path = Path(file_path)
    LOGGER.info("Loading spreadsheet data from %s", path)

    if path.suffix.lower() == ".csv":
        # CSV input is expected for the prototype dataset used in the demo.
        dataframe = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        # Excel support is included to reflect likely small-business workflows.
        dataframe = pd.read_excel(path)
    else:
        LOGGER.error("Unsupported spreadsheet format requested: %s", path.suffix)
        raise ValueError(f"Unsupported file type: {path.suffix}")

    # Normalised headings give downstream modules a stable schema to target.
    dataframe.columns = [normalize_column_name(column) for column in dataframe.columns]
    LOGGER.debug("Loaded dataframe with shape %s and columns %s", dataframe.shape, list(dataframe.columns))
    return dataframe
