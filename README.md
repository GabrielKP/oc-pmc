
<h1 align="center">Origin and Control of Persistent Mental Content</h1>

<p align="center">Code & data accompanying the paper by Kressin Palacios, G, Bellana, B, and Honey, C. J.</p>

<p align="center">
<a href="https://www.python.org/"><img alt="code" src="https://img.shields.io/badge/code-Python-blue?logo=Python"></a>
<a href="https://docs.astral.sh/ruff/"><img alt="Code style: Ruff" src="https://img.shields.io/badge/code%20style-Ruff-green?logo=Ruff"></a>
<a href="https://python-poetry.org/"><img alt="packaging framwork: Poetry" src="https://img.shields.io/badge/packaging-Poetry-lightblue?logo=Poetry"></a>
</p>

---

## Analyses & figures

```sh
git clone git@github.com:GabrielKP/oc-pmc.git
cd oc-pmc
```


## Conditions


### Psiturk-based: Intact, Suppress, and Suppress-no-button-press

The studies were hosted on AWS with [https://github.com/NYUCCL/psiTurk.git](psiTurk).

* Story relatedness ratings: [readme](conditions/psiturk-based/story-relatedness/README.md)
* Linger volition (internal names in parenthesis): Intact (button_press), Suppress (button_press_suppress), suppress (Suppress-no-button-press)


### Psyserver-based: All other conditions

The studies were hosted on AWS with [git@github.com:GabrielKP/psyserver.git](PsyServer).

Studies collected with psiturk (legacy code):

- carver_original/linger_volition (suppress, button_press, button_press_suppress)
- carver_original/linger_ocd


## Data

The data

### Psiturk-based studies



### Psyserver-based studies

### Bellana et al. (2022) data

1. Download raw data from: [https://osf.io/dmbx4/](https://osf.io/dmbx4/)
2. Unzip and place appropriately
3. In `.env` set `BELLANA_DIR="</path/to/unzipped/folder>"`


## Original repositories

This repository is the merger of many private and public repositories used for the project:

* Story relatedness ratings: https://github.com/GabrielKP/story-relatedness
* Volition studies



*Good luck on your adventures.*
