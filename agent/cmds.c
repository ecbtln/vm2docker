#include <string.h>
#include <sys/socket.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/sendfile.h>
#include <stdlib.h>
#include <stdbool.h>

#define _FILE_OFFSET_BITS 64
#include <sys/types.h>
#include <sys/stat.h>

#include "cmds.h"
#include "os.h"


#define POPEN_BUFFER_SIZE 1024

void send_msg(int clientfd, char *msg);
void exec_and_send(int clientfd, char *cmd);

void get_filesystem(int clientfd) {
    // http://man7.org/linux/man-pages/man2/sendfile.2.html

    // first, send the file header
    const int buff_size = 1000;
    char buffer[buff_size]; // TODO:, don't need this big buffer
    char temp_buffer[buff_size];
    char *fmt_str = SEND_FILE_HEADER_FMT;


    off_t nbytes = 1000;
    char *filename = "filesystem.tar.gz";
    // First, convert the %s to their correct modifiers
    snprintf(buffer, buff_size, fmt_str, "%lu", "%s");
    snprintf(temp_buffer, buff_size, buffer, nbytes, filename);
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
    char *cmd = get_installed_cmd();
    exec_and_send(clientfd, cmd);
    free(cmd);
}

void get_dependencies(char *pkg, int clientfd) {
    char *cmd = get_dependencies_cmd(pkg);
    exec_and_send(clientfd, cmd);
    free(cmd);
}

void exec_and_send(int clientfd, char *cmd) {
    FILE *cmd_result = popen(cmd, "r");
    printf("EXEC_AND_SEND_OUTPUT: %s\n", cmd);

    // TODO: redirect stderr to stdout
    char buffer[POPEN_BUFFER_SIZE];
    int nbytes = 0;

    bool eof = false;
    // this will skip the error case that would break stuff if the popen command printed nothing
    *buffer = '\0';

    while (!eof) {
        // continue reading until the end of the file
        // since the string is null-terminated by fgets, we want to fill the buffer up to the last character
        while (nbytes < POPEN_BUFFER_SIZE - 1) {
            // continue writing to the buffer until it is full (or the end of file occurs)
            char *str = fgets(buffer + nbytes, POPEN_BUFFER_SIZE - nbytes, cmd_result);
            if (str == NULL) {
                // we reached the end of file
                eof = true;
                break;
            }
            nbytes += strlen(str);
        }
        // buffer is full, send it on over the socket and repeat
        send(clientfd, buffer, strlen(buffer), 0);
        nbytes = 0;
        // don't send a null terminator yet, we'll do that at the end
    }
    // null terminate the string
    send(clientfd, "\0", 1, 0);
    pclose(cmd_result);
}

void send_msg(int clientfd, char *msg) {
    printf("Writing to Socket: %s\n", msg);
    send(clientfd,  msg, strlen(msg) + 1, 0);
}
