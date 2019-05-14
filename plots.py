import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import uuid
from itertools import chain
import numpy as np


def pie_plot(ax, colors, data, title=None):
    if title:
        ax.set_title(title)
    ax.pie(data.values(), labels=data.keys(), colors=colors, startangle=90, autopct='%.1f%%')


def pie_lots(data):
    colors = [[34, 108, 120], [78, 205, 196], [255, 107, 107], [255, 230, 109]]
    colors_01 = [tuple(cc/255 for cc in c) for c in colors]
    plt.figure(figsize=(7, 2.2), dpi=200)
    gs = gridspec.GridSpec(1, 3)
    gs.update(wspace=0., hspace=0.)
    for g, d in zip(gs, data):
        ax = plt.subplot(g)
        pie_plot(ax, colors_01, **d)
    _id = str(uuid.uuid4())
    filename = f"static/{_id}.png"
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    return filename


def bar_plots(data):
    colors = [[34, 108, 120],[78, 205, 196],[255, 107, 107]]
    colors_01 = [tuple(cc/255 for cc in c) for c in colors]
    options = set(chain.from_iterable(d['data'].keys() for d in data))

    N = len(options)

    fig, ax = plt.subplots(figsize=(7, 7/4 * N), dpi=200)

    ind = np.arange(N)    # the x locations for the groups
    width = 0.30

    shift = [width, 0, -width]

    p = []
    for d, c, s in zip(data, colors_01, shift):
        values = [d['data'].get(o, 0) for o in options]
        pos = ind + s
        print(pos, values)
        p.append(ax.barh(pos, values, width, color=c))
        for i, v in zip(pos, values):
            ax.text(
                1, i-0.08, '{:3.0f} %'.format(v), fontsize=16, color=('w' if v > 8 else 'black'), weight='bold')
    ax.set_yticks(ind)
    ax.set_yticklabels(options, rotation=90, fontsize=16, ha='right', va='center')

    ax.legend(p, [d['title'] for d in data], frameon=False, fontsize='large')
    ax.get_xaxis().set_visible(False)
    ax.tick_params(axis='y', which='both',length=0)
    plt.box(False)
    _id = str(uuid.uuid4())
    filename = f"static/{_id}.png"
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    return filename


