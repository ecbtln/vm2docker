__author__ = 'elubin'



class FileSystemDiffTool(object):
    """
    The goal of this class is to be able to define the differences between two filesystems (files and their permissions)
    The possible changes are: addition, modification, deletion
    And a file is described both by its file contents and permissions, so modifications can take the form of permissions changes
    Future goals will be to potentially describe diffs of non-binary files in terms of the diff tool itself, but for now
    we will default to including the entire new file and replacing the old
    In addition to describing the diffs, the other goal of the class will be to deploy these changes. In other words, given a diff,
    it should be able to apply the diff between two filesystems from one to get the other.
    Ultimately, this tool will be used in a Dockerfile, along with the diff itself (persisted to a file), to take a given image, and
    convert it to the desired image.


    ALTERNATIVELY: we can just wrap an existing tool!
    """
    pass



# Tools to check out:

# rsync
# beyond compare: http://www.scootersoftware.com
# rdiff: http://rdiff-backup.nongnu.org
# dirdiff: http://freecode.com/projects/dirdiff/


# existing tools:
# Here are some tools that might help:
# CheckInstall
# http://asic-linux.com.mx/~izto/checkinstall/
#
#
# Installwatch
# http://asic-linux.com.mx/~izto/checkinstall/installwatch.html
#
#
# instmon
# http://freecode.com/projects/instmon
#
#
# sinstall
# http://sourceforge.net/projects/sinstall/
#
#
# slacktrack
# http://freecode.com/projects/slacktrack
#
#
# strace Analyzer
# http://en.community.dell.com/techcenter/high-performance-computing/w/wiki/2264.aspx
# http://preview.tinyurl.com/7c7hf79
#
