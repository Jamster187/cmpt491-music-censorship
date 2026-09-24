"""Presentation-only helpers: finite primary series, honest context, readable axes."""
from __future__ import annotations
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, ScalarFormatter
import numpy as np

VERSION = 'analytical-presentation-v1'
DPI = 300
RECORDS = []
COLORS = dict(zip(['Pop', 'Rock', 'Hip-Hop / Rap', 'R&B / Soul', 'Country'],
                  ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#8B6508']))


def setup():
    plt.rcParams.update({'font.size': 11, 'axes.titlesize': 13, 'axes.labelsize': 11,
        'xtick.labelsize': 10, 'ytick.labelsize': 10, 'legend.fontsize': 10,
        'figure.dpi': 100, 'savefig.dpi': DPI})


def finite(values):
    x = np.asarray(values, dtype=float).ravel()
    return x[np.isfinite(x)]


def score_limits(values):
    """8% padding, outward nice rounding; only a 1e-6 constant/noise guard."""
    x = finite(values)
    if not len(x):
        return 0., 1.
    lo, hi = float(x.min()), float(x.max())
    if lo < -1e-12 or hi > 1+1e-12:
        raise ValueError('Primary score outside classifier domain')
    span = max(hi-lo, 1e-6)
    lower, upper = max(0., lo-.08*span), min(1., hi+.08*span)
    if upper-lower < 1e-6:
        lower = max(0., min((lo+hi)/2-5e-7, 1-1e-6))
        upper = lower+1e-6
    step = 10. ** math.floor(math.log10(upper-lower)-1)
    return max(0., math.floor(lower/step)*step), min(1., math.ceil(upper/step)*step)


def numeric_axis(ax, axis='y'):
    obj = ax.yaxis if axis == 'y' else ax.xaxis
    obj.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 5, 10]))
    fmt = ScalarFormatter(useOffset=False)
    fmt.set_scientific(False)
    obj.set_major_formatter(fmt)


def reference(ax):
    import pandas as pd
    ax.axvline(pd.Timestamp('2020-01-01'), color='#888888', linestyle=':', linewidth=.9)
    ax.grid(alpha=.15)


def metrics(values, limits):
    x = finite(values)
    lo, hi = sorted(limits)
    if not len(x):
        return dict(primary_min=None, primary_max=None, primary_span=None,
                    axis_min=lo, axis_max=hi, axis_span=hi-lo, utilization_ratio=None)
    span = float(np.ptp(x))
    return dict(primary_min=float(x.min()), primary_max=float(x.max()), primary_span=span,
                axis_min=float(lo), axis_max=float(hi), axis_span=float(hi-lo),
                utilization_ratio=span/(hi-lo) if hi > lo else None)


def assert_contained(values, limits):
    x = finite(values)
    if len(x) and (x.min() < limits[0]-1e-12 or x.max() > limits[1]+1e-12):
        raise ValueError('Primary analytical series clipped')


def emit(fig, path, family, primary_series, panels, *, note='', reference_path='',
         context_clipped=0, action='', issue='', axis_dimension='y'):
    """Record the least-utilized primary panel; retain every panel's measurements."""
    import json
    panel_metrics=[]
    for ax, values in panels:
        limits=ax.get_ylim() if axis_dimension=='y' else ax.get_xlim()
        panel_metrics.append(metrics(values, limits))
    usable=[r for r in panel_metrics if r['utilization_ratio'] is not None]
    worst=min(usable, key=lambda r:r['utilization_ratio']) if usable else panel_metrics[0]
    scale=panels[0][0].get_yscale() if axis_dimension=='y' else panels[0][0].get_xscale()
    if scale != 'linear':
        for r in panel_metrics: r['utilization_ratio']=None
        worst['utilization_ratio']=None
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    # Explicitly check visible labels against the figure canvas, not data clipping.
    clipped=[]
    for ax in fig.axes:
        xlo,xhi=sorted(ax.get_xlim()); ylo,yhi=sorted(ax.get_ylim())
        ticks=([label for value,label in zip(ax.get_xticks(),ax.get_xticklabels()) if xlo<=value<=xhi]+
               [label for value,label in zip(ax.get_yticks(),ax.get_yticklabels()) if ylo<=value<=yhi])
        for t in [ax.title, ax.xaxis.label, ax.yaxis.label]+ticks:
            if not t.get_visible() or not t.get_text(): continue
            box=t.get_window_extent(renderer)
            if box.x0 < -1 or box.y0 < -1 or box.x1 > fig.bbox.width+1 or box.y1 > fig.bbox.height+1:
                clipped.append(t.get_text())
    if clipped:
        raise ValueError('Labels outside figure: '+repr(clipped))
    fig.savefig(path, dpi=DPI, metadata={'Software':VERSION})
    RECORDS.append(dict(figure_path=str(path), figure_family=family,
        primary_series=primary_series, axis_dimension=axis_dimension, axis_scale=scale, **worst,
        panels_json=json.dumps(panel_metrics,sort_keys=True), issue_detected=issue,
        action_taken=action, full_scale_reference_available=bool(reference_path),
        full_scale_reference=reference_path, context_points_clipped=context_clipped,
        context_note=note, labels_inside_canvas=True))
    plt.close(fig)
