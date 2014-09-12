# This Makefile is set up to build in one of two modes.
# In debug mode, the C compiler does virtually no optimizations
# (-O0) and embeds a bunch of debugging symbols to make work with GDB easier.
# In release mode, the compiler will do every optimization it can (-O3) and keep
# debugging symbols out; this should decrease the size of the final binary and
# make it perform better.
#
# To compile in debug mode, type "make DEBUG=1".  To to compile in release
# mode, type "make DEBUG=0" or simply "make".
#
# If you type "make prof", Make will instrument the output for profiling with
# gprof.  Be sure you run "make clean" first!
#
# If everything gets wacky and you need a sane place to start from, you can
# type "make clean", which will remove all compiled code.
#
# If you want to do something wacky with your compiler flags--like enabling
# debug symbols but keeping optimizations on--you can specify CXXFLAGS or
# LDFLAGS on the command line.  If you want to use a predefined mode but augment
# the predefined CXXFLAGS or LDFLAGS, you can specify EXTRA_CXXFLAGS or
# EXTRA_LDFLAGS on the command line.


# The sources we're building
HEADERS = $(wildcard *.h)
PRODUCT_SOURCES = $(filter-out agent.c, $(wildcard *.c))

# What we're building
PRODUCT_OBJECTS = $(PRODUCT_SOURCES:.c=.o)
PRODUCT = agent

# What we're building with
CXX = gcc
CXXFLAGS = -std=gnu99 -Wall # -fcilkplus
LDFLAGS = -lm #-lrt -lcilkrts
PARAMS :=

# Determine which profile--debug or release--we should build against, and set
# CFLAGS appropriately.
#
# At this time, we also update the .buildmode stamp, which records if the last
# build was in debug or release mode.  This is a bit hackish--we set all C
# compiler outputs to depend on .buildmode, and then we touch .buildmode if it
# should change.  Touching .buildmode invalidates all the compiler outputs, so
# they all get built again in the correct mode.  Credit to Ceryen Tan and Marek
# Olszewski, who developed this code for 6.197 back in the day.
OLD_MODE = $(shell cat .buildmode 2> /dev/null)
ifeq ($(DEBUG),1)
# We want debug mode.
CXXFLAGS += -g -O0 -gdwarf-3
ifneq ($(OLD_MODE),debug)
$(shell echo debug >.buildmode)
endif
else
# We want release mode.
CXXFLAGS += -O3 -DNDEBUG -fgnu89-inline
ifneq ($(OLD_MODE),release)
$(shell echo release >.buildmode)
endif
endif


# By default, make the product.
all:		$(PRODUCT)

# How to clean up
clean:
	$(RM) $(PRODUCT) *.o *.out


# How to compile a C file
%.o:		%.c $(HEADERS) .buildmode
	$(CXX) $(PARAMS)  $(CXXFLAGS) $(EXTRA_CXXFLAGS) -o $@ -c $<

# How to link the product
$(PRODUCT): LDFLAGS += #-lXext -lX11
$(PRODUCT):	$(PRODUCT_OBJECTS) agent.o .buildmode
	$(CXX) $(PARAMS) $(LDFLAGS) $(EXTRA_LDFLAGS) -o $@ $(PRODUCT_OBJECTS) agent.o
