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

