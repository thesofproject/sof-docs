# Minimal makefile for Sphinx documentation
#
# You can override these defaults from the command line.

ifeq ($(VERBOSE),1)
  Q =
  SPHINXOPTS ?= -v
else
  Q = @
endif

# Locate SOF firmware repository: check SOF_ROOT, or candidate directories
ifeq ($(SOF_ROOT),)
  SOF_ROOT := $(firstword $(wildcard ../sof-dox-work ../sof ../sof-tgl/sof /home/lrg/work/sof-dox-work))
endif
SOF_DOC_BUILD ?= $(if $(SOF_ROOT),$(SOF_ROOT)/build_doxygen,_build_doxygen)
SOF_HAS_DOC := $(wildcard $(SOF_ROOT)/doc/CMakeLists.txt)

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


# Generate the doxygen xml (for Sphinx Breathe) and copy the doxygen html
# for publishing along with the Sphinx-generated API docs.
apidocs:
ifneq ($(SOF_HAS_DOC),)
	@if [ ! -f "$(SOF_DOC_BUILD)/build.ninja" ]; then \
		echo "Configuring Doxygen build with CMake in $(SOF_DOC_BUILD)..."; \
		cmake -GNinja -S "$(SOF_ROOT)/doc" -B "$(SOF_DOC_BUILD)"; \
	fi
	@echo "Building Doxygen documentation in $(SOF_DOC_BUILD)..."
	ninja -C "$(SOF_DOC_BUILD)" $${VERBOSE:+-v} doc
else
	@echo "Note: SOF firmware source tree (doc/CMakeLists.txt) not found."
	@echo "      Specify SOF_ROOT=/path/to/sof to generate live C API documentation."
endif

PYTHON ?= python3

generate_data:
	$(PYTHON) scripts/generate_matrices.py

html: generate_data apidocs
	$(SPHINXBUILD) -j auto -t $(DOC_TAG) -b html               \
		-d $(BUILDDIR)/doctrees $(SOURCEDIR) $(BUILDDIR)/html $(SPHINXOPTS)    \
		$(if $(wildcard $(SOF_DOC_BUILD)/doxygen/xml),-D breathe_projects.'SOF Project'="$(abspath $(SOF_DOC_BUILD)/doxygen/xml)",) \
		$(ERROROPTS) $(O)
	@if [ -d "$(SOF_DOC_BUILD)/doxygen/html" ]; then \
		echo "Copying raw Doxygen HTML to $(BUILDDIR)/html/doxygen..."; \
		mkdir -p $(BUILDDIR)/html/doxygen; \
		cp -r $(SOF_DOC_BUILD)/doxygen/html/* $(BUILDDIR)/html/doxygen/; \
	fi
	# Reminder: to see _all_ warnings you must "make clean" first.


# Remove generated content (Sphinx and doxygen)

clean:
	rm -fr $(BUILDDIR)
ifneq ($(SOF_HAS_DOC),)
	@if [ -f "$(SOF_DOC_BUILD)/build.ninja" ]; then \
		ninja -C "$(SOF_DOC_BUILD)" $${VERBOSE:+-v} doc-clean clean; \
	fi
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
