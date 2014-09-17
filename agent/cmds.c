#include <string.h>
#include <sys/socket.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/sendfile.h>

#define _FILE_OFFSET_BITS 64
#include <sys/types.h>
#include <sys/stat.h>
#include "cmds.h"

uint64_t file_size( char * filename );

void get_dependencies(char *pkg, int clientfd) {
    char buffer[1000];
    strcpy(buffer, pkg);
    int n = strlen(pkg);
    buffer[n] = '\n';
    buffer[n+1] = '\n';
    char *msg = "pkg1\npkg2\npkg3\npkg4\n";

    strcpy(buffer + n + 2, msg);
    int total = n + 2 + strlen(msg);
    buffer[total] = '\0';
    printf("%s\n", buffer);
    send_msg(clientfd, buffer);
}

void get_filesystem(int clientfd) {
    // TODO: consider using the sendfile system call!
    // http://man7.org/linux/man-pages/man2/sendfile.2.html

    // first, send the file header
    char buffer[1000];
    char *fmt_str = SEND_FILE_HEADER_FMT;


    off_t nbytes = 1000;
    char *filename = "filesystem.tar.gz";
    sprintf(buffer, fmt_str, nbytes, filename);
    send_msg(clientfd, buffer);


    // now, send the file
    char * from_file = "/src/filesystem.tar.gz";
    int fd = open(from_file, O_RDONLY);
    struct stat st;

    fstat(fd, &st);
    nbytes = st.st_size;


    int n_sent = sendfile(clientfd, fd, NULL, nbytes);
    if (n_sent != nbytes) {
        printf("Only %d/%zd bytes sent successfully", n_sent, nbytes);
    }
    close(fd);
}

void get_installed(int clientfd) {

}


void send_msg(int clientfd, char *msg) {
    printf("Writing to Socket: %s\n", msg);
    send(clientfd,  msg, strlen(msg) + 1, 0);
}
