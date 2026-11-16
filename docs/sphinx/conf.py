"""Налаштування Sphinx для API-довідника (крок 5 лабораторної роботи №6).

Довідник збирається з docstring-ів початкового коду розширенням `autodoc`.
Окремого тексту про кожну функцію тут немає й бути не повинно: інакше опис
розійшовся б із кодом при першій же правці, а саме цього крок 9 роботи й
шукає.

Збірка:

    python -m sphinx -b html docs/sphinx docs/sphinx/_build/html
    python -m sphinx -b singlehtml docs/sphinx docs/sphinx/_build/single
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

project = "Інформаційна система обліку витрат на харчування"
author = "Майстренко Ілля Ігорович, група КН-32"
copyright = "2026, Майстренко Ілля Ігорович"
version = "1.1.0"
release = "1.1.0"

language = "uk"

extensions = [
    "sphinx.ext.autodoc",
    # Розбирає секції Args, Returns, Raises у стилі Google (docs/docstring-tags.md).
    "sphinx.ext.napoleon",
    # Додає посилання на початковий код кожного описаного елемента.
    "sphinx.ext.viewcode",
    # Зводить усі згадані вимоги в один перелік: див. directive `todo` нижче.
    "sphinx.ext.autosummary",
]

autosummary_generate = False

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
    # Службові поля, які Pydantic додає до кожної схеми. До предметної
    # області не стосуються, а в довіднику повторювалися б 7 разів.
    "exclude-members": "model_config,model_fields,model_computed_fields",
}

# Анотації типів беруться з сигнатури; у docstring-ах типи не дублюються.
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_examples = True
# Секція Attributes подається полем усередині опису класу, а не окремими
# директивами. Інакше для кожного поля dataclass виходить два описи —
# один із docstring-а, другий із самої анотації — і Sphinx попереджає про
# дублювання.
napoleon_use_ivar = True

# Залежності, які не потрібні для складання довідника.
autodoc_mock_imports = ["uvicorn"]

templates_path = []
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_title = "API-довідник системи обліку витрат на харчування"
html_static_path = []
html_show_sourcelink = True

# Попередження вважати помилками не можна: autodoc попереджає про
# відсутні описи параметрів у сторонніх бібліотеках. Власні попередження
# перевіряються окремо, під час збірки.
nitpicky = False

# --- Збірка PDF ----------------------------------------------------------
# Потрібна для подання довідника одним файлом. Двигун саме XeLaTeX: pdflatex
# без додаткових пакетів не набирає кирилицю.
latex_engine = "xelatex"
latex_documents = [
    (
        "index",
        "api-reference.tex",
        "API-довідник системи обліку витрат на харчування",
        author,
        "manual",
    ),
]
latex_elements = {
    "papersize": "a4paper",
    "pointsize": "11pt",
    "babel": r"\usepackage{babel}",
    "fontpkg": r"""
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}[Scale=0.85]
""",
    "preamble": r"\usepackage{microtype}",
}
