# Minimal makefile for Sphinx documentation
#

ifeq ($(VERBOSE),1)
  Q =
  SPHINXOPTS ?= -v
else
  Q = @
endif

# You can set these variables from the command line.
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = "SOF Project"
SOURCEDIR     = .
BUILDDIR      = _build
ERROROPTS	  = -W --keep-going

DOC_TAG      ?= development
RELEASE      ?= latest
PUBLISHDIR    = ../thesofproject.github.io/$(RELEASE)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo ""
	@echo "make publish"
	@echo "   publish generated html to thesofproject.github.io site:"
	@echo "   specify RELEASE=name to publish as a tagged release version"
	@echo "   and placed in a version subfolder.  Requires repo merge permission."

.PHONY: help apidocs html clean


# Generate the doxygen xml (for Sphinx) and copy the doxygen html to the
# api folder for publishing along with the Sphinx-generated API docs.
# Keep doxygen optional not to burden "drive-by" .rst contributors with
# extra dependencies.

APIS_CMAKE := ../sof/doc/build.ninja
apidocs:
ifeq (${APIS_CMAKE},$(wildcard ${APIS_CMAKE}))
	ninja -C ../sof/doc $${VERBOSE:+-v} doc
else
	# To build doxygen APIs too run this first:
	#   cmake -GNinja -S ../sof/doc -B ../sof/doc
endif

html: apidocs
	$(Q)$(SPHINXBUILD) -t $(DOC_TAG) -b html -d $(BUILDDIR)/doctrees $(SOURCEDIR) $(BUILDDIR)/html $(SPHINXOPTS) $(O)
	# Reminder: to see _all_ warnings you must "make clean" first.


# Remove generated content (Sphinx and doxygen)

clean:
	rm -fr $(BUILDDIR)
ifeq (${APIS_CMAKE},$(wildcard ${APIS_CMAKE}))
	ninja -C ../sof/doc $${VERBOSE:+-v} doc-clean clean
endif

# Copy material over to the GitHub pages staging repo
# along with a README

publish:
	cd $(PUBLISHDIR)/..; git pull origin master
	mkdir -p $(PUBLISHDIR)
	rm -fr $(PUBLISHDIR)/*
	cp -r $(BUILDDIR)/html/* $(PUBLISHDIR)
	cp scripts/publish-README.md $(PUBLISHDIR)/../README.md
	cp scripts/publish-index.html $(PUBLISHDIR)/../index.html
	cd $(PUBLISHDIR)/..; git add -A; git commit -s -m "publish $(RELEASE)"; git push origin master;


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile doxy
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
