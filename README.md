# Scrollable Multichannel Plot (EEG + ECG)

This project provides a **scrollable, zoomable multichannel time-series plot** for EEG and ECG signals using Python and Plotly.  
It was built as a solution for the *QUASAR Coding Screener*.

---

## Features
- **Loads CSV** files while ignoring metadata lines (`#`).
- **Plots EEG channels** (µV) on the primary axis.
- **Plots ECG channels** (mV → converted to µV) on a secondary axis.
- **Plots CM reference channel** on a third overlaid axis.
- **Interactive exploration**:
  - Scroll/zoom/pan with Plotly.
  - Range slider under the plot.
  - Toggle channels on/off via legend click.
- **Optional usability flags**:
  - `--downsample N`: stride rows for speed on large datasets.
  - `--normalize`: per-trace min-max normalization to [-1, 1].
  - `--no-ecg` / `--no-cm`: skip plotting those channels.
  - `--html-out plot.html`: export interactive plot to HTML.

---

## Installation
It’s recommended to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate    # Windows
```

Install dependencies:

```bash
pip install pandas plotly
```

---

## Usage

Basic run:
```bash
python plot.py --csv data.csv
```

Save interactive HTML output (recommended for sharing):
```bash
python plot.py --csv data.csv --html-out plot.html
```

Speed up with downsampling and normalization:
```bash
python plot.py --csv data.csv --downsample 2 --normalize
```

Hide CM channel:
```bash
python plot.py --csv data.csv --no-cm
```

---

## Design Choices
- **Scaling**: ECG is typically in mV (≈ thousands of µV). To keep EEG (µV) visible, ECG traces are scaled ×1000 and placed on a **secondary y-axis**.
- **CM**: Plotted separately on a tertiary axis because its amplitude is large and not directly comparable to EEG/ECG.
- **Ignored columns**: `X3`, `Trigger`, `Time_Offset`, `ADC_Status`, `ADC_Sequence`, `Event`, `Comments` are dropped by default.
- **Interactivity**: Plotly was chosen for its built-in range slider, panning, zooming, and legend toggling.

---

## Future Work
- Add a GUI (e.g., **Streamlit/Dash**) for channel selection, unit switching, and normalization toggles.

---

## Notes on AI Assistance
The core implementation was developed independently. AI assistance was used for enhancement suggestions, particularly for improving the visual presentation (color schemes, styling) and code organization and documentation. 

---

## Example Screenshot
![Plot](screenshot.png)

---
