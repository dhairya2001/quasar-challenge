"""
Scrollable Multichannel Plot for EEG + ECG (Plotly)

Key features:
- Ignores metadata lines starting with '#'.
- Auto-detects EEG, ECG (X1/X2), and CM channels.
- Keeps EEG (µV) readable by converting ECG (mV) -> µV and placing ECG on a secondary y-axis.
- CM plotted on a third overlaid axis (can be hidden with --no-cm).
- Built-in pan/zoom + range slider; legend click to toggle channels.
- Optional per-trace normalization (z-score-like min-max to [-1, 1] per channel) via --normalize.
- Optional downsampling (integer stride) for performance on very large files.
- Saves interactive HTML if --html-out is specified (recommended for submissions).

"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors as pc

EEG_COLORS = pc.qualitative.Set3
ECG_COLORS = ['#FF6B6B', '#4ECDC4'] 
CM_COLOR = '#9B59B6' 

# columns for EEG
EEG_CANDIDATES = [
    "Fz", "Cz", "P3", "C3", "F3", "F4", "C4", "P4",
    "Fp1", "Fp2", "T3", "T4", "T5", "T6", "O1", "O2",
    "F7", "F8", "A1", "A2", "Pz"
]

# columns to be ignored
IGNORE_EXACT = set([
    "Trigger", "Time_Offset", "ADC_Status", "ADC_Sequence", "Event", "Comments"
])

# This function is to set up command line options so user could customize how script runs
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Scrollable multichannel EEG+ECG plot with Plotly.")
    ap.add_argument("--csv", required=True, help="Path to CSV file (lines beginning with '#' are ignored)."
                   )
    ap.add_argument("--html-out", default=None,
                    help="Optional path to save an interactive HTML (e.g., plot.html)."
                    )
    ap.add_argument("--downsample", type=int, default=1,
                    help="Integer stride to downsample rows for speed (default: 1 = no downsample)."
                    )
    ap.add_argument("--no-ecg", action="store_true", help="Do not plot ECG channels (X1/X2)."
                    )
    ap.add_argument("--no-cm", action="store_true", help="Do not plot CM channel."
                    )
    ap.add_argument("--normalize", action="store_true",
                    help="Per-trace min-max normalization to [-1, 1] (EEG, ECG, CM separately)."
                    )
    return ap.parse_args()


def load_data(csv_path: str, downsample: int) -> pd.DataFrame:
    # comment="#" will ignore metadata lines
    try:
        df = pd.read_csv(csv_path, comment="#")
    except Exception as e:
        print(f"Failed to read CSV: {e}", file=sys.stderr)
        raise

    if downsample and downsample > 1:
        df = df.iloc[::downsample, :].reset_index(drop=True)

    # validation of time
    if "Time" not in df.columns:
        raise ValueError("CSV must include a 'Time' column in seconds.")
    return df


def detect_channels(df: pd.DataFrame, include_ecg: bool, include_cm: bool) -> Tuple[List[str], List[str], str]:
    # EEG channels are among EEG_CANDIDATES and present in df
    eeg_channels = [c for c in EEG_CANDIDATES if c in df.columns]

    # ECG are X1:LEOG and X2:REOG
    ecg_channels = []
    if include_ecg:
        if "X1:LEOG" in df.columns:
            ecg_channels.append("X1:LEOG")
        if "X2:REOG" in df.columns:
            ecg_channels.append("X2:REOG")

    cm_channel = None
    if include_cm and "CM" in df.columns:
        cm_channel = "CM"

    return eeg_channels, ecg_channels, cm_channel

# Check if column should be ignored during plotting.
def is_ignored_column(col: str) -> bool:
    if col in IGNORE_EXACT:
        return True
    # ignoring starting with X3
    if col.startswith("X3:") or col.lower().startswith("x3:"):
        return True
    return False

# Normalize series to [-1, 1] range with improved handling of edge cases.
def minmax_normalize(series: pd.Series) -> pd.Series:
    s_min = series.min()
    s_max = series.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
        return series * 0.0
    return 2.0 * (series - s_min) / (s_max - s_min) - 1.0


def build_figure(df, eeg_channels, ecg_channels, cm_channel, normalize):
    time = df["Time"]

    # Top row: EEG+ECG with a secondary y-axis; Bottom row: CM
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25],
        subplot_titles=("EEG + ECG", "CM Reference"),
        specs=[
            [{"secondary_y": True}], 
            [{"secondary_y": False}],
        ],
        vertical_spacing=0.08,
    )

    # EEG (µV) on primary y of row 1
    for i,ch in enumerate(eeg_channels):
        y = df[ch]
        if normalize:
            y = minmax_normalize(y)
            name = f"{ch} (norm)"
        else:
            name = ch
        fig.add_trace(
            go.Scatter(x=time, y=y, mode="lines", name=name, line=dict(width=0.8, color=EEG_COLORS[i % len(EEG_COLORS)]), opacity=0.6),
            row=1, col=1, secondary_y=False
        )

    # ECG (mV) -> convert to µV and put on secondary y of row 1
    for i,ch in enumerate(ecg_channels):
        y = df[ch] * 1000.0
        if normalize:
            y = minmax_normalize(y)
            name = f"{ch} (norm)"
        else:
            name = f"{ch} (µV)"
        fig.add_trace(
            go.Scatter(x=time, y=y, mode="lines", name=name, line=dict(width=1, color=ECG_COLORS[i % len(ECG_COLORS)]), opacity=0.9),
            row=1, col=1, secondary_y=True
        )

    # CM in row 2
    if cm_channel is not None:
        y = df[cm_channel]
        if normalize:
            y = minmax_normalize(y)
            name = f"{cm_channel} (norm)"
        else:
            name = cm_channel
        fig.add_trace(
            go.Scatter(x=time, y=y, mode="lines", name=name, line=dict(width=1, color=CM_COLOR), opacity=0.8),
            row=2, col=1
        )

    # Layout and axes
    fig.update_layout(
        title="EEG + ECG Scrollable Plot",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        margin=dict(l=70, r=70, t=60, b=60)
    )

    # Put range slider on the bottom x-axis only
    fig.update_xaxes(title_text="Time (s)", row=2, col=1, rangeslider=dict(visible=True))

    # Axis titles
    fig.update_yaxes(title_text="EEG (µV)" if not normalize else "EEG (normalized)", 
                     row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="ECG (µV)" if not normalize else "ECG (normalized)", 
                     row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="CM" if not normalize else "CM (normalized)", 
                     row=2, col=1)

    return fig


def main():
    args = parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = load_data(str(csv_path), args.downsample)

    # Drop ignored columns if present
    drop_cols = [c for c in df.columns if is_ignored_column(c)]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors="ignore")

    eeg_channels, ecg_channels, cm_channel = detect_channels(
        df,
        include_ecg=not args.no_ecg,
        include_cm=not args.no_cm
    )

    if not eeg_channels and not ecg_channels and cm_channel is None:
        print("No plottable channels detected. Please check your CSV headers.", file=sys.stderr)
        print("Columns found:", list(df.columns), file=sys.stderr)
        sys.exit(2)

    fig = build_figure(df, eeg_channels, ecg_channels, cm_channel, normalize=args.normalize)

    # Save HTML if requested
    if args.html_out:
        out = Path(args.html_out)
        fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
        print(f"Saved interactive HTML to: {out.resolve()}" )

    try:
        fig.show()
    except Exception as e:
        print(f"Unable to open viewer automatically: {e}", file=sys.stderr)
        print("Tip: open the --html-out file in your browser.")

if __name__ == "__main__":
    main()
