#!/bin/bash
# build doc from sof
git clone https://github.com/thesofproject/sof
cmake -GNinja -S sof/doc -B _build_doxy

# TODO: change the (bad) default value for SOF_DOC_BUILD in
# sof-docs/Makefile and remove this command line override
# build sof-doc
make html VERBOSE=1 SOF_DOC_BUILD=_build_doxy
du -shc _build*/*
