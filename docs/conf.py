# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "langchain-prolog"
copyright = "2025, Antonio Pisani"
author = "Antonio Pisani"
release = "0.1.0"

import os
import sys


sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../.."))

LIBRARIES = [
    # "/Users/antonio/miniconda3/envs/prolog/lib/python3.12/site-packages/langchain",
    "/Users/antonio/miniconda3/envs/prolog/lib/python3.12/site-packages/langchain_core",
    "/Users/antonio/miniconda3/envs/prolog/lib/python3.12/site-packages/pydantic",
    # "/Users/antonio/miniconda3/envs/prolog/lib/python3.12/site-packages/pydantic_core",
    "/Users/antonio/miniconda3/envs/prolog/lib/python3.12/site-packages/janus_swi",
]

for lib in LIBRARIES:
    if lib not in sys.path:
        sys.path.append(lib)


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx_copybutton",
]

# Configure autodoc
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Configure myst-parser
myst_heading_anchors = 3

# Configure copybutton
copybutton_prompt_text = "$ "  # Remove terminal prompts
copybutton_prompt_is_regexp = True
copybutton_line_continuation_character = "\\"
copybutton_here_doc_delimiter = "EOT"

# Display todos by seeting to True
todo_include_todos = True

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
