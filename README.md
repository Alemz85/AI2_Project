# AI2 Project

Collaborative repository for the project work in this repo.

## Project layout

- `code.ipynb`: main analysis notebook
- `data/raw/`: local raw dataset files (ignored by git by default)
- `data/processed/`: generated outputs and cleaned data (ignored by git by default)
- `scripts/`: reusable helper scripts

## Getting started

1. Clone the repository.
2. Install dependencies with either `pip install -r requirements.txt` or `conda env create -f environment.yml`.
3. If you used Conda, activate the environment with `conda activate ai2-project`.
4. Place the source data in `data/raw/`.
5. Open `code.ipynb` in Jupyter and start working.

## Git workflow notes

- The repository ignores notebook checkpoints, OS/editor clutter, virtual environments, and local data folders.
- If you decide to version large datasets, prefer Git LFS over regular git commits.
- Move reusable notebook code into `scripts/` as the project grows to make collaboration easier.
