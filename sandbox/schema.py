import pandas as pd


def get_schema(dataset_path: str, sample_rows: int = 5) -> str:
    """Returns a compact text description of the dataset for LLM prompts:
    column names, dtypes, and a few sample rows."""
    df = pd.read_csv(dataset_path)
    dtypes = df.dtypes.astype(str).to_dict()

    lines = ["Columns and types:"]
    for col, dtype in dtypes.items():
        lines.append(f"  - {col}: {dtype}")

    lines.append(f"\nRow count: {len(df)}")
    lines.append(f"\nSample rows:\n{df.head(sample_rows).to_string(index=False)}")

    return "\n".join(lines)
