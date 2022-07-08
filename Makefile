# Minimal makefile for Sphinx documentation
#
# You can override these defaults from the command line.

ifeq ($(VERBOSE),1)
  Q =
  SPHINXOPTS ?= -v
else
  Q = @
endif

SOF_DOC_BUILD = ../sof/build_doxygen/
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = "SOF Project"
SOURCEDIR     = .
BUILDDIR      = _build
ifneq ($(LAX),1)
ERROROPTS	  = -W --keep-going
endif

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

APIS_CMAKE := ${SOF_DOC_BUILD}/build.ninja
apidocs:
ifeq (${APIS_CMAKE},$(wildcard ${APIS_CMAKE}))
	ninja -C ${SOF_DOC_BUILD} $${VERBOSE:+-v} doc
else
	# To build doxygen APIs too run this first:
	#   cmake -GNinja -S ../sof/doc -B ${SOF_DOC_BUILD}
endif

html: apidocs
	$(SPHINXBUILD) -j auto -t $(DOC_TAG) -b html               \
-d $(BUILDDIR)/doctrees $(SOURCEDIR) $(BUILDDIR)/html $(SPHINXOPTS)    \
-D breathe_projects.'SOF Project'="${SOF_DOC_BUILD}"/doxygen/xml \
$(ERROROPTS) $(O)
	# Reminder: to see _all_ warnings you must "make clean" first.


# Remove generated content (Sphinx and doxygen)

clean:
	rm -fr $(BUILDDIR)
ifeq (${APIS_CMAKE},$(wildcard ${APIS_CMAKE}))
	ninja -C ${SOF_DOC_BUILD} $${VERBOSE:+-v} doc-clean clean
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
