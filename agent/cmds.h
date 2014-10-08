#include "constants.h"

void get_dependencies(char *pkg, int clientfd);
void get_filesystem(char *compression, int clientfd);
void get_installed(int clientfd);
void get_bound_sockets(int clientfd);
void get_active_processes(char *pids, int clientfd);
void get_ps(int clientfd);
void get_pid(int clientfd);
