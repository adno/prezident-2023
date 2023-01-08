from collections import Counter
import json
import pandas as pd
import numpy as np
import math
import seaborn as sns
import matplotlib.pyplot as plt
import mpl_toolkits.axisartist as axisartist
from urllib.request import urlretrieve
import os


ANSWER2INT = {
    'no': -1,
    'dont_know': 0,
    'yes': 1
    }


def webdata2df(webdata):
    questions = {}
    candidates = {}
    questions2gists_tags = {}

    for i, qd in enumerate(webdata['questions'], 1):
        # id, name, title, gist, tags
        qt = qd['title']
        q = f'{i}. {qt}'
        questions[qd['id']] = q
        questions2gists_tags[q] = (qd['gist'], qd['tags'])

    for cd in webdata['candidates']:
        # id, name, motto, img_url
        candidates[cd['id']] = cd['name']

    df = pd.DataFrame(
        index=candidates.values(), columns=questions.values(),
        dtype='Int64'
        )

    comments = pd.DataFrame(
        index=candidates.values(), columns=questions.values(),
        dtype='str'
        )

    for ad in webdata['answers']:
        # "id", "candidate_id", "question_id",
        # "answer": "yes"/"no"/"dont_know",
        # Optional: "comment": "..."
        c = candidates[ad['candidate_id']]
        q = questions[ad['question_id']]
        a = ANSWER2INT[ad['answer']]
        comment = ad.get('comment')

        df.loc[c, q] = a
        if comment is not None:
            comments.loc[c, q] = comment

    return (df, comments, questions2gists_tags)


ODPOVEDNOST = {5, 12}
GROUP2QN_SIGN = {
    'Velké pravomoci a malá odpovědnost': [
        1, 8, -9, -10, 11, -23, 25, 26, 27, 29, -5, -12
        ],
    'pravomoci': [1, 8, -9, -10, 11, -23, 25, 26, 27, 29],
    'odpovědnost a stíhatelnost': [5, 12],
    'má prosazovat názory většiny společnosti': [15],
    'má prezentovat postoje vlády': [20],
    '-názory vláda, +názory občanů': [-20, 15],
    'Pro EU, Ukrajinu a lidská práva': [2, 4, -14, 18, 21, -22]
    }


CFILT = [
    'Petr Pavel',
    'Danuše Nerudová',
    'Marek Hilšer',
    'Pavel Fischer',
    'Andrej Babiš'
    ]

BIGFONT = dict(
    fontsize=12,
    fontweight='bold'
    )
SMALLFONT = dict(
    fontsize=9,
    c='gray'
    )


DATA_PATH = 'downloads/pro-kazdeho.json'
DATA_URL = (
    'https://www.volebnikalkulacka.cz/data/'
    'kalkulacka/prezidentske-2023/pro-kazdeho.json'
    )

def get_data():
    if not os.path.exists(DATA_PATH):
        urlretrieve(DATA_URL, filename=DATA_PATH)
    with open(DATA_PATH) as f:
        wd = json.load(f)
    return webdata2df(wd)


def save_fig(filename):
    plt.savefig(filename, bbox_inches='tight', pad_inches=0.3, dpi=300)


def plot_corr(df, filename=None):
    plt.figure(figsize=(6, 5))

    plt.title(
        'Korelace mezi odpověďmi kandidátů (celá sada otázek)',
        y=1.1,
        **BIGFONT
        )

    plt.gcf().text(
        -0.1, -0.25,
        'Zdroj dat: www.volebnikalkulacka.cz',
        **SMALLFONT
        )

    corr = df.T.corr().round(2)

    sns.heatmap(corr, annot=True, vmin=-1, vmax=1, center=0, cmap='bwr')

    if filename is not None:
        save_fig(filename)
    else:
        plt.show()


def get_group_signs(df, group):
    cols_signs = [
        (df.columns[abs(n)-1], math.copysign(1, n))
        for n in GROUP2QN_SIGN[group]
        ]
    cols = [c for c, __ in cols_signs]
    return (df[cols], dict(cols_signs))


def group_with_signs(df, group, odpo=False):
    df, signs = get_group_signs(df, group)
    odpovednost = [abs(n) in ODPOVEDNOST for n in GROUP2QN_SIGN[group]]
    signed = {}
    for c, o in zip(df.columns, odpovednost):
        data = df[c]
        if signs[c] < 0:
            data = -1*data
            c = f'NE: {c}'
        else:
            c = f'ANO: {c}'
        if o:
            c = f'[odpovědnost] {c}'
        signed[c] = data
    return pd.DataFrame(signed)


def score_group(df, group):
    df = group_with_signs(df, group)
    score = df.T.sum()
    return score


def plot_groups(df, xgroup, ygroup, filename=None):
    score_df = pd.DataFrame({
        xgroup: score_group(df, xgroup),
        ygroup: score_group(df, ygroup)
        })

    plt.figure(figsize=(6, 4))
    plt.scatter(
        score_df[xgroup], score_df[ygroup],
        c=range(len(score_df.index))
        )
    ax = plt.subplot()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(color='grey', linestyle='-', linewidth=0.25, alpha=0.5)

    shift = Counter()

    for candidate, x, y in score_df.itertuples():
        pt = (round(x, 2), round(y, 2))
        s = shift[pt]
        plt.text(x+0.1, y+0.1+s*0.15, candidate, rotation=45, fontsize=12)
        shift[pt] += 1

    nx = len(GROUP2QN_SIGN[xgroup])
    ny = len(GROUP2QN_SIGN[ygroup])
    plt.xticks(np.arange(-nx, nx+1, 2))
    plt.yticks(np.arange(-ny, ny+1, 2))
    plt.xlabel(xgroup, **BIGFONT)
    plt.ylabel(ygroup, **BIGFONT)

    plt.gcf().text(
        0, -0.1,
        'Zdroj dat: www.volebnikalkulacka.cz',
        **SMALLFONT
        )

    if filename is not None:
        save_fig(filename)
    else:
        plt.show()


def col2n(col):
    return int(col.partition(': ')[2].partition('. ')[0])


def plot_group_map(
    df,
    group,
    break_title=False,
    sort_lower={},
    filename=None,
    odpo=False
    ):
    df = group_with_signs(df, group, odpo=odpo)
    rows = sorted(df.index, key=lambda r: df.loc[r].sum())
    cols = sorted(
        df.columns,
        key=lambda c: (col2n(c) in sort_lower, df[c].sum())
        )
    df = df.loc[rows, cols].T

    plt.figure(figsize=(7, 4))

    # All this just to right align left axis labels
    # (we need to adjust the rest to match the correlation heatmap look):
    ax = plt.subplot(axes_class=axisartist.Axes)
    for name in ('top', 'bottom', 'left', 'right'):
        ax.axis[name].line.set_visible(False)
        ax.axis[name].major_ticks.set_visible(name in {'left', 'bottom'})
        ax.axis[name].major_ticks.set_tick_out(True)
    ax.axis['right'].set_visible(False)
    ax.axis['left'].major_ticklabels.set_ha('left')
    ax.axis['bottom'].major_ticklabels.set_ha('right')
    ax.axis['bottom'].major_ticklabels.set_rotation('vertical')

    sns.heatmap(
        df.astype('float'), cmap='bwr', annot=True, fmt='+.0f',
        square=True, cbar=False
        )
    opt_break = '\n' if break_title else ' '
    plt.gcf().text(
        -0.85, 1,
        (
            f'Na ose „{group}“ kandidáti dostávají +1 bod za '
            f'odpověď uvedenou níže{opt_break}'
            f'VELKÝMI PÍSMENY a -1 bod za opačnou.'
            ),
        **BIGFONT
        )

    plt.gcf().text(
        -0.85, -0.2,
        'Zdroj dat: www.volebnikalkulacka.cz',
        **SMALLFONT
        )

    if filename is not None:
        save_fig(filename)
    else:
        plt.show()


def main():
    df, comments, questions2gists_tags = get_data()
    cs = sorted(df.index, key=lambda c: (c not in CFILT, c))
    dft = df.loc[cs].T
    # Output gists and tags
    # dft['gists'] = [questions2gists_tags[q][0] for q in qs]
    # dft['tags'] = [', '.join(questions2gists_tags[q][1]) for q in qs]
    dft.to_csv('output/answers.csv')

    for candidate in dft.columns:
        dft[candidate+'*'] = comments.loc[candidate]

    dft = dft[sorted(
            dft.columns,
            key=lambda c: (c.removesuffix('*') not in CFILT, c)
            )]
    dft.to_csv('output/answers-comments.csv')

    plot_groups(
        df, 'Velké pravomoci a malá odpovědnost',
        'Pro EU, Ukrajinu a lidská práva',
        filename='output/p1.png'
        )
    plot_group_map(
        df, 'Velké pravomoci a malá odpovědnost', filename='output/p2.png',
        break_title=True  # , sort_lower=ODPOVEDNOST
        )
    plot_group_map(
        df, 'Pro EU, Ukrajinu a lidská práva', filename='output/p3.png'
        )
    plot_corr(df, filename='output/pcorr.png')


if __name__ == '__main__':
    main()
