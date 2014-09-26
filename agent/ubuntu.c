#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "constants.h"


// TODO: consider using a macro to be able to inline the get_installed_cmd
void get_installed_cmd(char **cmd) {
    *cmd = UBUNTU__GET_INSTALLED_CMD;
}

char * get_dependencies_cmd(char *pkg) {
    char *c = "apt-cache depends %s | grep \"Depends:\"";
    const int len = strlen(c) + 1 - 2 + strlen(pkg);
    char *cmd = malloc(len);
    snprintf(cmd, len, c, pkg);
    return cmd;
}