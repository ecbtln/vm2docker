#include <string.h>
#include <stdlib.h>
#include <stdio.h>

// TODO: consider not using grep at all to limit dependencies

char * get_installed_cmd() {
    char *c = "dpkg --get-selections | grep -v deinstall";
    char *cmd = malloc(strlen(c) + 1);
    strcpy(cmd, c);
    return cmd;
}

char * get_dependencies_cmd(char *pkg) {
    char *c = "apt-cache depends %s | grep \"Depends:\"";
    char *cmd = malloc(strlen(c) + 1 - 2 + strlen(pkg));
    sprintf(cmd, c, pkg);
    return cmd;
}