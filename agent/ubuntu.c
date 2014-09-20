#include <string.h>
#include <stdlib.h>
#include <stdio.h>

// TODO: consider not using grep at all to limit dependencies

char * get_installed_cmd() {
    char *c = "dpkg --get-selections | grep -v deinstall";
    const int len = strlen(c) + 1;
    char *cmd = malloc(len);
    strcpy(cmd, c, len);
    return cmd;
}

char * get_dependencies_cmd(char *pkg) {
    char *c = "apt-cache depends %s | grep \"Depends:\"";
    const int len = strlen(c) + 1 - 2 + strlen(pkg);
    char *cmd = malloc(len);
    snprintf(cmd, len, c, pkg);
    return cmd;
}