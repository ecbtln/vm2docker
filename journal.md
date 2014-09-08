log of observations / thoughts
==========


This log will hopefully make it easier to synthesize everything to a thesis when the time comes



## September 8

Working on verifying the results that the app packagement and post-diff is effective

Had the realization that the size measurement on the filesystem vs the uncompressed tar might make a difference, so
I need to be careful to be consistent or include all values

Experimented with different modifiers to rsync, (axHAX) is what we have been using which preserves extended attributes
and modification times, tried switching to (rlpgoDxH) to ditch the consistency of modification times.

This greatly decreased the number of modified files (by about 20% 12k to 10k), but the size of the diff for ubuntu 14.04
increased only 1 MB (maybe less). Makes me think that rsync's way of keeping track of modification times is smarter
than having to recopy the whole file with a different modification time. But I don't know if that's possible because
we are using rsync combined with tar, not separately.

Resolved to create a different method of outputting the results of an experiment, separate from the debug log. This is
written to a file in the /tmp directory and its path is written at the end of debug log to stdout. The logger's name is
'results' and messages with INFO level and above get sent to this file.


Now want to see the results of the filtering dependency logic to see if that works as expected, now that I've got
something to test it on.

- Running with the Ubuntu 14.04 LTS, 187 packages are cut down to 77 packages.

- But we also lose a few installs, apt-get log shows:
(from 181 MB to 169 MB), fetching 36.7 MB of archives, as compared to 38.1 MB of archives and 183 packages instead of
189 packages

Diff becomes:

10516 modifications and additions, 65 deletions
changes.tar: 957.48MB

as opposed to:

12840 modifications and additions, 69 deletions
changes.tar: 955.79MB

Missing packages are (perceived to be a dependency of another package, but never installed via apt-get):

language-pack-gnome-en-base
language-pack-gnome-en
language-pack-en
tasksel-data
tasksel
language-pack-en-base

now we will do a reverse dependency search and find which packages said they depended on this

it may be because certain packages have dependencies in the host repo (doing the conversion) but not the other?

this is a problem, and i think the only way to fix it would be to make sure to execute the apt-cache depends requests
in the context of the VM rather than the converting machine. TODO: revisit this problem once we have created a self
contained version of this that runs directly on the host

Another possible result is the idea cycles in the dependency graph, which I didn't realize was possible but would stem
from co-dependencies. Looking for nodes with an in-degree of 0 is not sufficient because it misses strongly connected
components!!

In addition to looking for nodes with in-degree 0, we want to look for strongly connected components with size greater
than 1.

Ran with 12.04.4 LTS, with and without filtered dependencies verified to be the same

Diff reduced from 894.37 MB to 798.87 MB, (95.5 MB reduction and 195 MB bigger footprint of intermediate image)


This brings up the tradeoff of this approach vs the other. Our lineage of layers is going to take up more space than before! :(

Is this acceptable?

I argue yes, but it is worth discussing, because the alternative way of adding packages after does not suffer the same problem


