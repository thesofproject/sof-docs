# -*- coding: utf-8 -*-
#
# Project SOF documentation build configuration file, created by
# sphinx-quickstart on Wed Jan 10 20:51:29 2018.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('.'))


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['breathe', 'sphinx.ext.graphviz', 'sphinxcontrib.plantuml',
              'sphinx.ext.todo', 'sphinx.ext.extlinks', 'sphinxcontrib.blockdiag'
]


graphviz_output_format='svg'
graphviz_dot_args=[
   '-Nfontname=verdana',
   '-Gfontname=verdana',
   '-Efontname=verdana']


plantuml = 'java -jar ' + os.path.join(os.path.abspath('.'), 'scripts/plantuml.jar') \
    + ' -config ' + os.path.join(os.path.abspath('.'), 'scripts/plantuml.cfg')

# More than half of the time building from scratch is consumed by the
# sphinx extension "breathe" that converts doxygen XML. Most of the rest
# is consumed by plantUML here. So you can set the variable below to
# 'none' for an _almost instant_ sphinx build! (with zero UML diagram
# and no doxygen). 'none' requires sphinxcontrib.plantuml>=0.11 but
# pre-0.11 errors can be ignored.  (of course don't disable UML when
# you're touching UML stuff)
plantuml_output_format = 'svg'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# Fixes "WARNING: Error when parsing function declaration."
c_id_attributes = ["__sparse_cache"]
# Not clear why Sphinx thinks some C files are C++
cpp_id_attributes = c_id_attributes
# cpp_paren_attributes = ["_ALIAS_OF", "__printf_like"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'SOF Project'
copyright = u'2022, SOF Project'
author = u'SOF Project developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

version = release = "2.2"

#
# The short X.Y version.
# version = u'0.1'
# The full version, including alpha/beta/rc tags.
# release = u'0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build','.tox' ]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos =False

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
try:
    import sphinx_rtd_theme
except ImportError:
    html_theme = 'alabaster'
    # This is required for the alabaster theme
    # refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
    html_sidebars = {
        '**': [
            'relations.html',  # needs 'show_related': True theme option to display
            'searchbox.html',
            ]
        }
    sys.stderr.write('Warning: sphinx_rtd_theme missing. Use pip to install it.\n')
else:
    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    html_theme_options = {
        'canonical_url': '',
        'analytics_id': 'GTM-M4BL5NF',
        'logo_only': False,
        'display_version': True,
        'prev_next_buttons_location': 'None',
        # Toc options
        'collapse_navigation': False,
        'sticky_navigation': True,
        'navigation_depth': 4,
    }


# Here's where we (manually) list the document versions maintained on
# the published doc website.  On a daily basis we publish to the
# /latest folder but when releases are made, we publish to a /<relnum>
# folder (specified via RELEASE=name on the make command).

if tags.has('release'):
   current_version = version
else:
   version = current_version = "latest"

html_context = {
   'current_version': current_version,
   'versions': ( ("latest", "/latest/"),
#                 ("0.1-rc4", "/0.1-rc4/"),
               )
    }


# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

html_logo = 'images/logo_sof_white_200w.png'
html_favicon = 'images/sof-favicon-16x16.png'

numfig = True
#numfig_secnum_depth = (2)
numfig_format = {'figure': 'Figure %s', 'table': 'Table %s', 'code-block': 'Code Block %s'}

SOF_GIT = 'https://github.com/thesofproject'

# "/sof/tree/branch/dir" is for directories and "/sof/blob/branch/file" is
# for files. Fortunately github automatically redirects one to the other
# as required.
extlinks = {
    'git-sof-mainline':
       (SOF_GIT + '/sof/tree/master/%s', None),
    'git-sof-docs-mainline':
       (SOF_GIT + '/sof-docs/tree/master/%s', None),
    'git-sof-kconfig':
       (SOF_GIT + '/kconfig/tree/master/%s', None),
    'git-alsa':
    ('https://git.alsa-project.org/?p=%s.git', None),
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

def setup(app):
# add_stylesheet() was renamed to add_css_file() in sphinx 1.8 released
# in September 2018. add_stylesheet() will be removed in sphinx 4.0
    try:
        app.add_css_file('sof-custom.css')
    except AttributeError:
        app.add_stylesheet('sof-custom.css')

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# -- Options for HTMLHelp output ------------------------------------------


rst_epilog = """
.. include:: /substitutions.txt
"""


breathe_projects = {
   "SOF Project" : "../sof/doc/doxygen/xml",
}
breathe_default_project = "SOF Project"
breathe_default_members = ('members', 'undoc-members', 'content-only')

try:
    if "tox" not in exclude_patterns:
        exclude_patterns.append(".tox")
except:
    exclude_patterns = [".tox"]
