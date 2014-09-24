#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "constants.h"

// TODO: consider not using grep at all to limit dependencies
// TODO: consider using a macro to be able to inline the get_installed_cmd
char * get_installed_cmd() {
    char *c = UBUNTU__GET_INSTALLED_CMD;
    const int len = strlen(c) + 1;
    char *cmd = malloc(len);
    strncpy(cmd, c, len);
    return cmd;
}

char * get_dependencies_cmd(char *pkg) {
    char *c = "apt-cache depends %s | grep \"Depends:\"";
    const int len = strlen(c) + 1 - 2 + strlen(pkg);
    char *cmd = malloc(len);
    snprintf(cmd, len, c, pkg);
    return cmd;
}