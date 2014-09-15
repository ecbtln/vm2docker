# A helper file to build the python module that contains the constants included from the agent



CC = gcc

PYTHON_PATH = -I/usr/include/python2.7/
TARGET = agent
PATH_TO_INTERFACE = ../agent/
INTERFACE = $(PATH_TO_INTERFACE)interface.i
SWIG = swig

LD_SHARED = ld -shared

OUT_FILENAME = interface_wrap
BUILD_DIR = constants/
OUT_OBJ_FILE = $(OUT_FILENAME).o
OUT_OBJ_PATH = $(BUILD_DIR)$(OUT_OBJ_FILE)
CFLAGS = -o $(OUT_OBJ_PATH)
OUT_FILE = $(BUILD_DIR)$(OUT_FILENAME).c
SWIG_FLAGS = -outcurrentdir -o $(OUT_FILE)
OBJ_FILE = $(HEADER_FILE).gch
MODULE_FILE = $(BUILD_DIR)_$(TARGET).so
PYTHON_SO = _$(TARGET).so



all:
	$(SWIG) -python $(SWIG_FLAGS) $(INTERFACE)
	$(CC) -fPIC -c $(OUT_FILE) $(PYTHON_PATH) $(CFLAGS)
	$(LD_SHARED) $(OUT_OBJ_PATH) -o $(MODULE_FILE)


clean:
	rm -rf $(BUILD_DIR)__pycache__
	rm -f $(BUILD_DIR)*_wrap* $(BUILD_DIR)*~ $(BUILD_DIR).~* $(BUILD_DIR)mypython $(BUILD_DIR)*.pyc
	rm -f $(BUILD_DIR)core
	rm -f $(BUILD_DIR)*.o $(BUILD_DIR)*.bundle $(BUILD_DIR)$(PYTHON_SO)
	rm -f $(BUILD_DIR)$(TARGET).py