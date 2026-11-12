"""Parse an Ianseo qualification export (semicolon-delimited .txt or URL) into archer records."""

import pandas as pd

# Columns that follow the score columns; tie-break columns sit between "Hits" and this column.
TB_START_COLUMN = "Hits"
TB_END_COLUMN = "Category Rank"


def default_tiebreak_columns(columns):
    """Return the default tie-break column names.

    Args:
        columns (list[str]): header names of the export, in file order.
    Returns:
        list[str]: names from `Hits` up to (excluding) `Category Rank`, in file order.
    """
    start = columns.index(TB_START_COLUMN)
    end = columns.index(TB_END_COLUMN)
    return list(columns[start:end])


def parse_class(class_code):
    """Split an Ianseo class code into experience and gender category.

    Order within the code is not assumed: E/N/A is experience, O/F is gender.

    Args:
        class_code (str): e.g. "EO", "NF", "AO".
    Returns:
        tuple[str | None, str | None]: (experience in E/N/A, gender in O/F); None if absent.
    """
    code = str(class_code).strip().upper()
    experience = next((c for c in code if c in "ENA"), None)
    gender = next((c for c in code if c in "OF"), None)
    return experience, gender


def parse_quali_export(source, tiebreak_columns=None):
    """Read an Ianseo qualification export.

    Args:
        source (str | Path): path or URL of the semicolon-delimited export.
        tiebreak_columns (list[str] | None): header names to use as tie-breaks, in priority
            order. None uses every column from `Hits` to before `Category Rank`.
    Returns:
        tuple[list[dict], list[str]]: archers and the tie-break column names used. Each archer
            dict has: name (str), club (str), division (str), experience (str), gender (str), class (str, e.g. "EO"),
            score (int), tiebreaks (tuple[int, ...]).
    """
    df = pd.read_csv(source, sep=";", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    tb_cols = tiebreak_columns or default_tiebreak_columns(list(df.columns))
    missing = [c for c in tb_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Tie-break columns not in export: {missing}. Available: {list(df.columns)}")

    def to_int(value):
        """Convert an export cell to int, treating blank/non-numeric as 0."""
        value = str(value).strip()
        return int(value) if value.lstrip("-").isdigit() else 0

    archers = []
    for _, row in df.iterrows():
        experience, gender = parse_class(row["Class"])
        club = row["Country"].strip()
        if not club or experience is None or gender is None:
            continue
        archers.append(
            {
                "name": f"{row['GivenName'].strip()} {row['FamilyName'].strip()}",
                "club": club,
                "division": row["Division"].strip().upper(),
                "experience": experience,
                "class": f"{experience}{gender}",
                "gender": gender,
                "score": to_int(row["Score"]),
                "tiebreaks": tuple(to_int(row[c]) for c in tb_cols),
            }
        )
    return archers, list(tb_cols)
