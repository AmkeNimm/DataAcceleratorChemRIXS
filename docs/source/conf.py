# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Path setup --------------------------------------------------------------

import os
import sys
from io import StringIO

from docutils import nodes, statemachine
from sphinx.util.docutils import SphinxDirective


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath("../../"))

import reduceFuncs_chemRIXS

readme_file = os.path.join(os.path.abspath("../../"), "README.md")
index_file = os.path.join(os.path.abspath("../../docs"), "index.rst")
#skymodel_file = os.path.join(os.path.abspath("../../docs"), "skymodel.rst")




# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'chemRIXSDataAccelerator'
copyright = '2025, Amke Nimmrich'
author = 'Amke Nimmrich'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
   # "sphinx.ext.autodoc"
    "sphinx.ext.napoleon",
]

# set this to properly handle multiple input params with the same type/shape
napoleon_use_param = False

# set this to handle returns section more uniformly
napoleon_use_rtype = False

# use this to create custom sections
# currently used for the SkyModel.read method
#napoleon_custom_sections = [
#    ("GLEAM", "params_style"),
#    ("FHD", "params_style"),
#    ("VOTable", "params_style"),
#    ("SkyH5", "params_style")
#]

# turn off alphabetical ordering in autodoc
autodoc_member_order = "bysource"



templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'furo'
html_static_path = ['_static']
