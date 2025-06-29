# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "langchain-prolog"
copyright = "2025, Antonio Pisani"
author = "Antonio Pisani"
release = "0.1.1.post12"

import os
import sys

os.environ["SPHINX_BUILD"] = "True"

sys.path.insert(0, os.path.abspath("../src"))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx_copybutton",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",  # Creates summary tables for modules/classes
    "sphinx_sitemap",  # Generates sitemap for search engines
    "sphinx_tabs.tabs",  # For tabbed code examples
]

# Configure autodoc
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "show-inheritance": True,
}

# Intersphinx configuration for external documentation
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "langchain": ("https://api.python.langchain.com/en/latest/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

intersphinx_disabled_domains = []
intersphinx_timeout = 30
intersphinx_cache_limit = 90  # days
intersphinx_disabled_reftypes = ["*"]

# Configure myst-parser
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
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
html_theme_options = {
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "style_nav_header_background": "#2980B9",
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "style_nav_header_background": "#2980B9",
}

# Reduce warning noise
nitpicky = False
suppress_warnings = [
    "myst.header",
    "ref.*",  # Suppress all reference warnings
]

# Configure autodoc to handle imports
# Autodoc settings
autodoc_mock_imports = [
    "janus_swi",
    "langchain_prolog._prolog_init.initialize_macos",
    "langchain_prolog._prolog_init.initialize_linux",
    "langchain_prolog._prolog_init.initialize_windows",
]
autoclass_content = "both"
autodoc_member_order = "bysource"

# For more complex mocking
from unittest.mock import MagicMock
class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()


MOCK_MODULES = [
    "janus_swi",
]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)
