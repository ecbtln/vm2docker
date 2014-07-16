Layout of expected steps for conversion

1. Determine linux release + verify kernel is compatible
2. Clone filesystem
    - For now, we will just clone the entire filesystem and tar it and import in using docker import
    - In the future, we will want to minimize image size and take advantage of layering
        - Match OS with a given base image
            - It looks like only Ubuntu and CentOS are available on the public docker registry, so we will likely
            have to use a tool like [debootstrap](https://wiki.debian.org/Debootstrap) in conjunction with the 
            available contrib scripts ([here](https://github.com/dotcloud/docker/tree/master/contrib)).
            - This process would likely be used in conjunction with a private registry see:
                - [Building private registry](http://blog.docker.com/2013/07/how-to-use-your-own-registry/)
                - [Quay.io](https://quay.io)
            - Also see here for a [trusted](http://blog.docker.com/2013/11/introducing-trusted-builds/) build of 
            [ubuntu desktop](http://dockerfile.github.io/#/ubuntu-desktop) and
            [ubuntu](http://dockerfile.github.io/#/ubuntu) with some more stuff added.
        - Generate commands to reinstall any packages that are missing:
            - i.e. [Ubuntu apt-get autogeneration](http://kracekumar.com/post/70198562577/autogenerate-dockerfile-from-ubuntu-image)
        - Add the rest of the files using the ADD directive and shell scripts to move to the appropriate location
3. Determine init.d processes
    - This may require accessing the running VM over ssh
    - Or we could just prompt the user which one of the processes should be ported over
    - 1 container per process
    - Either ask user for port #'s, or get them from the running VM using netstat
    - See LINKS.md for some links containing a discussion of running multiple processes vs. 1 process in a container
4. Some interesting exceptions to think about
    - SSH daemon? is it needed? probably not, but depends on if it's also used for X11 or something
    - UI/desktop? this gets less useful with docker, but might be able to still be used with X11
    - Environmental variables, linking containers, and shared volumes
    - Determine if privileged mode is needed. Generally, some VMs might be doing things that containers don't support
5. Potential future abstractions
    - support VDI and VMDK filesystems
    - support for both kubernetes and fleet output files
    - Also read memory and processor allocation for VM, and reassign to container