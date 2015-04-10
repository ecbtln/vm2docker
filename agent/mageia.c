#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "constants.h"


// TODO: consider using a macro to be able to inline the get_installed_cmd
void get_installed_cmd(char **cmd) {
    *cmd = MAGEIA__GET_INSTALLED_CMD;
}

void get_dependencies_fmt(char **fmt) {
    *fmt = "urpmq -d %s";
}