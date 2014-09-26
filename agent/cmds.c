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
#define FILESYSTEM_NAME "filesystem.tar.gz"

void send_msg(int clientfd, char *msg);
void exec_and_send(int clientfd, char *cmd);

// TODO: this is very time sensitive. Consider sending keep alive messages to the host while the tar is generated so that the host doesn't time out waiting for the msg
// This can be combined with a progress-bar of sorts for sending the tar over the wire. 1GB takes a lot of time!
void get_filesystem(char *compression, int clientfd) {
    // http://man7.org/linux/man-pages/man2/sendfile.2.html
    // allow the caller to specify any other arguments to the char command (used for compression)
    // i'm well aware a malicious user could pass in a semicolon and execute an arbitrary command
    // for now, we don't care


    char *filename = FILESYSTEM_NAME;
    // remove the tar if it already exists
    remove(filename); // this should work. if it doesn't exist that's fine it will silently fail
    // 1: tar up the filesystem
    char *cmd = "tar -C / --exclude=sys --exclude=proc -c . %s -f %s";

    int cmd_length = strlen(cmd) + strlen(filename);
    if (compression != NULL) {
        cmd_length += strlen(compression);
    }
    char *formatted_cmd = malloc(cmd_length);

    if (compression == NULL) {
        compression = "";
    }
    snprintf(formatted_cmd, cmd_length, cmd, compression, filename);

    printf("EXEC: %s\n", formatted_cmd);
    int ret = system(formatted_cmd);
    if (ret != 0) {
        perror("Error: Unable to create filesystem archive");
    }
    free(formatted_cmd);


    // first, send the file header
    const int buff_size = 1000;
    char buffer[buff_size]; // TODO:, don't need this big buffer
    char final_buffer[buff_size];
    char *fmt_str = SEND_FILE_HEADER_FMT;


    off_t nbytes;
    // First, convert the %s to their correct modifiers
    snprintf(buffer, buff_size, fmt_str, "%lu", "%s");



    // now, send the file
    int fd = open(filename, O_RDONLY);
    struct stat st;

    fstat(fd, &st);
    nbytes = st.st_size;
    // TODO: does this work for big files
    snprintf(final_buffer, buff_size, buffer, nbytes, filename);
    send_msg(clientfd, final_buffer);


    int n_sent = sendfile(clientfd, fd, NULL, nbytes);
    printf("Sent %d/%zd bytes successfully\n", n_sent, nbytes);
    close(fd);
    remove(filename);
}

void get_installed(int clientfd) {
    char *cmd;
    get_installed_cmd(&cmd);
    exec_and_send(clientfd, cmd);
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
