.. _development_tree:

Linux SOF drivers
#################

.. contents::
   :local:
   :depth: 3

Background
**********

Linux development is split by subsystems. All SOF contributions are
merged through the sound/system (maintained by Takashi Iwai) and the
sound/soc subsystem (maintained by Mark Brown).

All SOF patches merged by the two maintainers will be used for
linux-next (as a first pass of integration to detect conflicts with
other subsystems or compilation issues) and eventually merged in the
mainline by Linus Torvalds.

Instructions for SOF developers
*******************************

ABI changes
===========

One fundamental and non-negotiable premise of Linux kernel development
is "we don't break the userspace." More specifically, users may update
their kernels at any time while keeping the SOF firmware binary and
topology files stored in the root filesystem unchanged. The
expectation is that the SOF Linux driver does not generate any errors
and that audio functionality remains unchanged.

Conversely, when a capability is introduced in a new firmware release, the
expectation is that the kernel shall be updated as well. In other words,
a new firmware does not need to include any backwards-compatibility
code to interface with an older kernel.

When the ABI changes, the developer or maintainer shall tag it in
GitHub, and the ABI level change will be recorded in the official ABI
change tracker:

https://github.com/orgs/thesofproject/projects/2

The process for firmware ABI changes is documented in the :ref:`SOF_ABI_changes`.

When the ABI is not backwards-compatible, Pull Requests on the
kernel side shall include code that deals with older firmware and
topology files.

Development branch
==================

All SOF development takes place on the topic/sof-dev branch in the SOF tree:

``git@github.com:thesofproject/linux.git``

Developers are required to submit Pull Requests (PRs) against the
topic/sof-dev branch. The Continuous Integration (CI) runs a set
of static analysis, builds, and on-device testing.

Two approvers are required for each PR. SOF admins may in some
exceptions use their privileges to merge PRs, such as to restore
functionality and broken builds.

When a PR is submitted by an SOF admin, another admin must approve that PR.
The PRs are integrated into the SOF tree using the 'rebase-and-merge' method
which keeps the integrated patches in a linear order.

Rebasing tree
=============

In addition to the topic/sof-dev branch, the SOF project maintains a
parallel topic/sof-dev-rebase branch. This branch is not intended for
development, but to make upstream contributions easier to manage.
As its name indicates, commit SHA1s in topic/sof-dev-rebase are volatile
and should not be relied on. SHA1s in topic/sof-dev are immutable.

Upstream merges
===============

During Linux development, patches to the ALSA/ASoC cores, dependencies such
as audio codecs, or bug fixes may be contributed by the community. SOF Linux
maintainers will, on a regular basis (typically weekly), merge all upstream
contributions into the SOF tree.

.. _sof_drv_maintainer_list:

Development flow
****************

SOF Linux maintainers
=====================

+---------------+-------------------+---------------+
| Intel	        | Pierre Bossart    | @plbossart    |
+---------------+-------------------+---------------+
| Intel         | Ranjani Sridharan | @ranj063      |
+---------------+-------------------+---------------+
| Intel         | Kai Vehmanen      | @kv2019i      |
+---------------+-------------------+---------------+
| NXP           | Daniel Baluta     | @dbaluta      |
+---------------+-------------------+---------------+

SOF maintainers process
=======================

Mirror all SOF patches to topic/sof-dev-rebase
----------------------------------------------

This mirroring consists in doing a set of git "cherry-pick" operations
from topic/sof-dev to topic/sof-dev-rebase. Once all development
patches are applied, SOF maintainers will add the relevant
Signed-off-by and Reviewed-by tags.

In specific cases, incremental patches will be squashed to simplify
upstream reviews, commit messages will be made clearer, and the order of
patches will be changed, but in all cases the intent is that both
topic/sof-dev and topic/sof-dev-rebase provide the same code (as seen
with git diff or diff -r).

Upstream merge/rebase
---------------------

When the two branches are integrated, the SOF maintainer will create
an upstream baseline. This baseline is then merged locally on top of
topic/sof-dev, then pushed as a dedicated PR and run through the CI
tests. The merge may in some cases create conflicts that have to be
resolved locally by the maintainer. Once the PR is deemed suitable for
integration, the maintainer will use a 'Commit merge' operation (in
contrast to the 'rebase-and-merge' used for development).

In parallel, the topic/sof-dev-rebase branch is rebased on top of the
same baseline, and again compared to the topic/sof-dev branch. After
the two separate operations of merge and rebase on the two branches,
these two branches should again be identical. The net effect of the
rebase is that all patches already integrated by ALSA/ASoC maintainers
'disappear.' In other words, comparing sof-dev with sof-dev-rebase
shows all patches not currently merged upstream. This includes a limited
number of infrastructure changes that will never be merged upstream
such as github's CODEOWNERS file.

Upstream contributions
----------------------

The SOF maintainer generates patch sets and sends them with a cover
to the alsa-devel mailing list, with the maintainers in Cc:. In most
cases the patches are approved without issues, but the ALSA/ASoC
maintainers or members of the community may provide feedback and
request some changes. In those cases, the changes are applied on
topic/sof-dev, then mirrored and squashed on topic/sof-dev-rebase, and
submitted again. Under no circumstances should the SOF maintainer handle
changes to the topic/sof-dev-rebase directly.

Exceptions
----------

In very specific cases, such as for HDMI-related patches, it might be easier
for an SOF developer to submit the patches directly to alsa-devel. By
default, though, the process is that all patches are first submitted
to the SOF GitHub, CI-tested. Only when maintainers provide a written
agreement should developers submit SOF-related patches directly to the
alsa-devel mailing list.

To avoid disrupting the development and rewriting its history, all
upstream patches are integrated using the "Merge commit" option.

Development summary
*******************

::

      +----reject-----------+                      +--------merge----------------+
      |                     |                      |                             |
      v                     |                      v                             |
 +----+------+        +-----+-------+       +------+--------+           +--------+----------+
 | developer +------->+ SOF reviews +--ok-->+ topic/sof-dev |         +-+ upstream baseline |
 | PR        |        | CI tests    |       |               |         | |                   |
 +-----------+        +-----+-------+       +------+--------+         | +---------+---------+
                            |                      |                  |           ^
                            |                               +--rebase-+           |
                            |                      |        |             ALSA maintainers ok
                            |                      |        v                     |
                            |           +----------v--------+--+         +--------+----------+
                            |           | topic/sof-dev-rebase +-email-->+    alsa-devel     |
			    |           |                      |         |    mailing list   |
                            |           +----------------------+         +--------+----------+
                            |                                                     ^
                            |                                                     |
                            |                                                     |
                            +-----------------direct path (exceptions)------------+
