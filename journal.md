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
48.9% space reductions on the installed packages


This brings up the tradeoff of this approach vs the other. Our lineage of layers is going to take up more space than before! :(

Is this acceptable?

I argue yes, but it is worth discussing, because the alternative way of adding packages after does not suffer the same problem


## September 9

Test on a different OS with different package management tool.

Let's try CentOS 7 and the YUM package management tool

Downloaded 3 different builds:

CentOS7:
Minimal, DVD, and everything

Initial results show that the diff size is the exact same size as the original VM. Need to debug to figure out why...

## September 10

After removing the X option from rsync (extended attributes), the diff seems to be working again. (phew)

Depending on the OS, there are probably different disk-level attributes that are supported. They were likely not
supported in Ubuntu, so adding this option did nothing. In CentOS7, they were supported enough such that it didn't think
 two files were the same when they were, likely because they weren't pointing to the same inode or something like that.

 Preliminary results for CentOS 7 show:

 Original VM: 727 MB
 Base Image: 213 MB
 Diff: 583.54 MB

 % of possible: 67.35%


 Now on to package management:

 fixed a bug where I wasn't passing in the root to the VM / base image to the rpm command. That made it think all packages
 were the same.

 Since RPM provides really in depth and verbose package names / versions, it may make sense to cater to this.

 - Isolate out the package names that are the same
 - Any packages that are the same, figure out whether upgrade or downgrade is needed
 - Perform desired operation, or alternatively do nothing, just don't do an unnecessary uninstall then install


Install  162 Packages (+1 Dependent package)
Total download size: 125 M
Installed size: 399 M

Diff 356.81 MB

Added 399 MB to the intermediate image to save a total of 226.73 MB on the diff
56.8% savings on the package


Added in dependency filtering to cut down 162 to 67 packages


## September 11

Brainstorming ways of localizing the conversion process on the host itself.

Running the script on the host itself has the following dependencies:

- Python, pip, rest of the python packages in requirements.txt
- rsync
- tar
- docker client command line
- Commands used for get_installed and get_dependencies functions, which could be implemented in bash instead of python
to limit dependencies


Making use of Docker for a sandbox-like environment immediately comes to mind

Theoretical design can be a script written in C on host computer.

The C script can listen on a particular socket for RPCs.

The RPCs are stubs that, when hit, should fire off a subprocess (with fork) that performs the desired operation and
returns the result in the socket.

the desired stubs are:

get_dependencies(pkg)
- execute the corresponding shell script, depending on the current OS, and return the result as a string

get_filesystem()
- tar up the entire filesystem and send the resulting tar across the socket
- might involve an intermediate rsync to a subdirectory if tar doesn't accept our initial command
- then delete/clean up the results

get_installed()
- execute the corresponding shell script, depending on the current OS, to get a list of all the packages installed,
along with their versions and architectures if available


some additional stubs for getting the running processes/ bound ports might come into play


Finally, we may want the agent to somehow advertise itself to the other server, rather than the other server needing
to manually pass in the path to the agent. Either approach works.

The agent should bind itself to an unused port so that connections can take place remotely

Pros/Cons:
+ Very few dependencies
+ Most architectures should be able to run the agent natively
- Central bottleneck still exists because all logic is being executed on central machine


Check out this:

https://www.cs.utah.edu/~swalton/listings/sockets/programs/part2/chap6/simple-server.c

as well as the code in 6.858 for the simple web server.


## September 12

Started the coding for our C-based agent that runs on the host and communicates via a socket connection


In the future, we may want a nifty command line argument parser like this one:

https://github.com/hypersoft/nargv

But for now, our commands seem to only need at most one argument, so we'll just do that.

## September 15

Use swig as a compiler tool to convert c pre-processor defines to a python file without having to define in more than one spot

http://www.swig.org
http://stackoverflow.com/a/12147822


Got it up and running after some difficulty. Hooray for having a single file of definitions that's compatible
with different languages.


For introduction, look into other container technologies such as OpenVZ and parallels and whether or not they exist
for Windows.

## September 16

Started socket logic for buffering results


## September 17

Finished ringbuffer, implemented some tests, started logic on C-side of things


## September 18

Plan to support multiple OS's:

Have a get_dependencies_cmd function and a get_installed_cmd function that are included in during compile time
depending on which OS we are compiling for

## September 26

Seems like the socket-based tool is finally complete. Is working for Ubuntu 13.10 with optional compression for
sending the filesystem over the wire.

Compression is ESSENTIAL. Talk about this in the paper. Even a simple gzip compression cuts down the tar from > 1 GB
to 387.6MB

Now that it is functioning, we now want to consider 3 more things:

1. How to detect the processes that are running on the VM to put those in the configuration file
    - Other configuration such as VM size / memory / processor could also go here
2. Other ways of computing the filesystem diff
    - Block-based tools might be interesting to mess with
    - Hash-based approach to detect if a file is there (above a certain threshold size) but was actually just moved to a
    different path. This could potentially be a big winner
3. A verification tool. It'd be nice to have a proof of correctness tool that compares the final built docker image
with the original VM and makes sure that they are the same. This can be run optionally

4. So far we've been focusing on size-based performance metrics. We might want to also consider time-based to see
how long a typical conversion takes. My experience shows potentially up to 10 minutes?


## September 29

Did a lot of work refactoring the diff process. Now the entire diff logic and cmd generation is laid out in diff.py.

This makes it a lot easier to come up with other strategies for diff in the future, without wreaking havoc on filesystem.py

Simple observation about differences in virtual sizes of built Docker containers, depending on if package management is enabled or not

- For Ubuntu 13.10, we are looking at 1.349 GB vs 1.24 GB. This is the added weight of 109 MB, which can be attributed
to the extra space used to keep the packages-only layer, that is eventually discarded because isn't directly used in
the final container.


## September 30

Commands to get running processes:

{PID} is the PID of the given process


/proc/{PID}/cmdline - cmd used to start the process
/proc/{PID}/cwd - current working directory of command executed (symlink)
/proc/{PID}/exe - executable running (symlink)

The question now becomes how to identify the PID's of interest.

Thinking the easiest thing might be to tar up the /proc/ directory and send it over the wire to be processed on the
other side.


Also need to find specific ports being bound to. Two options:

$ lsof -i TCP
$ netstat -lntp

for each, we'll have to grep the process ID


also, need to get user who started each process, and then make sure to start it again under the given user's UID




