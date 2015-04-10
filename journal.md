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



## October 3

Finished adding all commands, clocked in a conversion of Ubuntu 13.10 with packages at: 11:40

## October 8
Finished conversion of live processes (tentative). Yet to be tested exhaustively


## October 21
Finished live conversion for real and merged into master

Really interesting hacker news thread here worth monitoring:
https://news.ycombinator.com/item?id=8483102
https://medium.com/@kelseyhightower/optimizing-docker-images-for-static-binaries-b5696e26eb07
http://jonathan.bergknoff.com/journal/building-good-docker-images

The idea of separating build and and runtime environments is very interesting to follow

## October 23
Exploring alternatives to rsync. It looks like rsync typically does a rolling hash, but because we are executing on the
same host into an alternative directory, this feature (mentioned below) is obviously not used.
http://en.wikipedia.org/wiki/Rsync#Determining_which_parts_of_a_file_have_changed

Let's try instead to use rdiff instead. It actually looks like Dropbox uses rdiff, so we are on the right track.

Unfortunately hard links aren't supported, and bad signatures don't raise errors, so just keep this in mind.

upgraded to docker 1.3 and boot2docker 1.3, which automatically enabled TLS and broke everything. YAY! Here's my workaround:
http://blog.sequenceiq.com/blog/2014/10/17/boot2docker-tls-workaround/
$(docker run sequenceiq/socat)

Yes this works, but is abysmally slow. For tomorrow, let's come up with a progress bar indicator or something

## November 4

Met with adviser, time to start structuring the paper around collecting data

Note, none of these capacities consist at all of compression. We save that for a separate discussion, and assume all can
be compressed. We are focusing on the raw size.


Data tables we want:




Table 1 from proposal for Ubuntu

#Ubuntu 12.04
Original filesystem
1125.77 MB

Base image:
99.13 MB

no package management:
rsync diff
996.65 MB

5645 modifications + additions (942.88 MB of additions)

116 deletions (0.216 MB of deletions)

rest are modifications

rdiffdir
974.35 MB


205 ---> 67 packages culled
including package management:

packages installed total 185MB

new "base" including packages is 326.41 MB


rsync
902.15 MB

12306 modificaitons + additions (773.603 MB of additions)
312 deletions (29.642 MB of deletion)

rest are modifications

rdiffdir
810.94 MB


#Ubuntu 12.04.5
Original filesystem
1062.71 MB

Base image:
99.13 MB

no package management:
rsync diff
915.26 MB

4081 modifications + additions (880.92 MB of additions)

112 deletions (0.2135 MB of deletions)

rest are modifications

rdiffdir
905.13 MB


204 ---> 66 packages culled
including package management:

packages installed total 184MB

new "base" including packages is 325.44 MB


rsync
769.58 MB

8292 modificaitons + additions (712.31 MB of additions)
215 deletions (29.58 MB of deletion)

rest are modifications

rdiffdir
736.46 MB


# Ubuntu 13.04
Original filesystem
876.36 MB

Base image:
160.41 MB

no package management:
rsync diff
710.87 MB

2356 modifications + additions (708.93 MB of additions)

123 deletions (67.739 MB of deletions)

rest are modifications

rdiffdir
718.24 MB


226 ---> 129 packages culled
including package management:

packages installed total 237MB

ERRRRORRR updating sources

# Ubuntu 13.10
Original filesystem
1157.45 MB

Base image:
114.76 MB

no package management:
rsync diff
982.38 MB

2340 modifications + additions (967.727 MB of additions)

122 deletions (70.78 MB of deletions)

rest are modifications

rdiffdir
987.28 MB


248 ---> 147 packages culled
including package management:

packages installed total 237MB

new "base" including packages is 447.697 MB


rsync
767.73

12021 modificaitons + additions (676.34 MB of additions)
2067 deletions (15.10 MB of deletion)

rest are modifications

rdiffdir
708.148 MB




# Ubuntu 14.04
Original filesystem
1212.22 MB

Base image:
192.02 MB

no package management:
rsync diff
1008.85 MB

5657 modifications + additions (943.55 MB of additions)

135 deletions (0.2572 MB of deletions)

rest are modifications

rdiffdir
971.215 MB


183 ---> 109 packages culled
including package management:

packages installed total 161MB

new "base" including packages is 386.95 MB


rsync
894.85 MB

10729 modificaitons + additions (796.51 MB of additions)
187 deletions (23.08 MB of deletion)

rest are modifications

rdiffdir
829.01 MB



# Ubuntu 14.10

Original filesystem
1132.17 MB

Base image:
196.89 MB

no package management:
rsync diff
876.35 MB

4163 modifications + additions (856.60 MB of additions)

144 deletions (0.2716 MB of deletions)

rest are modifications

rdiffdir
872.52 MB


245 ---> 144 packages culled
including package management:

packages installed total 229MB

new "base" including packages is 468.57 MB


rsync
687.56 MB

9958 modificaitons + additions (637.728 MB of additions)
160 deletions (19.52 MB of deletion)

rest are modifications

rdiffdir
655.02 MB

Special exceptions for CentOS

1. I use the repoquery command, but thats not installed by default we need to do a yum install yum-utils first
2. netstat apparently is not installed by default
3. firewall issues: http://stackoverflow.com/questions/24729024/centos-7-open-firewall-port

#CentOS 5
From size: 507888K	/tmp/tmperamm6/root_fs/

To size: 2604820K	/tmp/tmperamm6/vm_root/
Diff between parent and child contains:
12272 modifications and additions, 4758 deletions
Deletions total 2034820 bytes
Additions total 2148584251 bytes
Size of /tmp/tmp6C2aIa/modded.tar: 2190.02 MB

rdiffdir
2138.70 MB

#CentOS 6
http://wiki.centos.org/HowTos/Network/IPTables
From size: 241804K	/tmp/tmpLDeBk5/root_fs/

To size: 692196K	/tmp/tmpLDeBk5/vm_root/

Diff between parent and child contains:
9704 modifications and additions, 3864 deletions
Deletions total 3157967 bytes
Additions total 359666480 bytes
Size of /tmp/tmpQ7br1y/modded.tar: 478.06 MB

rdiffdir
416.72 MB

78 packages --> 54

242 MB packages installed

From size: 535096K	/tmp/tmpu42Vh3/packages_container/

To size: 692200K	/tmp/tmpu42Vh3/vm_root/

Diff between parent and child contains:
14044 modifications and additions, 6454 deletions
Deletions total 124725628 bytes
Additions total 208822404 bytes
Size of /tmp/tmpSuCbB2/modded.tar: 381.88 MB

rdiffdir
269.42MB


#CentOS 7 (minimal)

From size: 248972K	/tmp/tmpXLTUx4/root_fs/

To size: 902876K	/tmp/tmpXLTUx4/vm_root/

Diff between parent and child contains:
6879 modifications and additions, 294 deletions
Deletions total 1287663 bytes
Additions total 555414354 bytes
Size of /tmp/tmpvCb4qC/modded.tar: 704.10 MB

rdiff
621.71 MB


packages:

165 ---> 67
packages installed total 389MB

From size: 676068K	/tmp/tmpnNqRjh/packages_container/

To size: 902880K	/tmp/tmpnNqRjh/vm_root/

Diff between parent and child contains:
14579 modifications and additions, 3764 deletions
Deletions total 125321236 bytes
Additions total 280970580 bytes
Size of /tmp/tmpTkPzFE/modded.tar: 544.55 MB

rdiff
370.94 MB

#Fedora 20


#Fedora 21

#Mageia 3
root@bb5cb3c4f313:/src/chief# cat /tmp/vm2docker__1416360337OAe0Jt.txt
From size: 164292K	/tmp/tmpHG5Udm/root_fs/

To size: 756156K	/tmp/tmpHG5Udm/vm_root/

Diff between parent and child contains:
3681 modifications and additions, 105 deletions
Deletions total 7910849 bytes
Additions total 545874604 bytes
Size of /tmp/tmph61W0L/modded.tar: 595.09 MB


rdiffdir
580.95 MB


packages:

311 --> 46

root@ad0ac494a159:/src/chief# cat /tmp/vm2docker__1416368667aMoe5z.txt
From size: 721536K	/tmp/tmpTKvb6z/packages_container/

To size: 758140K	/tmp/tmpTKvb6z/vm_root/

Diff between parent and child contains:
14754 modifications and additions, 2917 deletions
Deletions total 319521459 bytes
Additions total 322839865 bytes
Size of /tmp/tmpU5t3cX/modded.tar: 535.86 MB

rdiffdir
417.74MB


#Mageia 4
From size: 178280K	/tmp/tmpZ0QI3_/root_fs/

To size: 2875760K	/tmp/tmpZ0QI3_/vm_root/

Diff between parent and child contains:
3343 modifications and additions, 69 deletions
Deletions total 5638077 bytes
Additions total 2605438592 bytes
Size of /tmp/tmpaKINCq/modded.tar: 2575.37 MB

some conclusions: take a look at the reduction in diff size after installing packages. clearly the total size increases, but the diff decreases
indicating some value of the layering

rdiffdir
2613.04 MB

### kernel files in /usr/src are 102.33 MB and can be removed

Another similar table for CentOS

Another table for one other OS, TBD

Redo package management numbers with new approach

Then redo all numbers with rdiffdir instead of rsync

semi or official
maybe busybux
debian?
fedora?
Mageia?

very unofficial
Gentoo also?
archlinux


Conversion times: (how long each component of the conversion takes, maybe a pie chart or something)

Quantify the tradeoff between increasing total virtual size of container, and what quantity of containers on a single host are needed
to make up for this temporary increase (consider both of the same and different containers)


package dependency filtering

