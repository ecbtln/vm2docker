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
void send_fs(char *compression, char *target_name, char *target, char *exclude, char *to_tar, int clientfd) {
    // remove the tar if it already exists
    remove(target_name); // this should work. if it doesn't exist that's fine it will silently fail
    // 1: tar up the filesystem

    if (to_tar == NULL) {
        to_tar = ".";
    }
    if (compression == NULL) {
        compression = "";
    }

    char *cmd = "tar -C %s %s -c %s %s -f %s";

    int cmd_length = strlen(cmd) + strlen(target_name) + strlen(exclude) + strlen(target) + strlen(compression) + strlen(to_tar);
    char *formatted_cmd = malloc(cmd_length);

    snprintf(formatted_cmd, cmd_length, cmd, target, exclude, to_tar, compression, target_name);

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
    int fd = open(target_name, O_RDONLY);
    struct stat st;

    fstat(fd, &st);
    nbytes = st.st_size;
    // TODO: does this work for big files??
    snprintf(final_buffer, buff_size, buffer, nbytes, target_name);
    send_msg(clientfd, final_buffer);


    int n_sent = sendfile(clientfd, fd, NULL, nbytes);
    printf("Sent %d/%zd bytes successfully\n", n_sent, nbytes);
    close(fd);
    remove(target_name);
}


void get_filesystem(char *compression, int clientfd) {
    char *exclude = "--exclude=sys --exclude=proc";
    char *target = "/";

    send_fs(compression, FILESYSTEM_NAME, target, exclude, NULL, clientfd);
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

void get_bound_sockets(int clientfd) {
    exec_and_send(clientfd, "netstat -lntp");
}

void get_active_processes(char *pids, int clientfd) {
    send_fs(NULL, "processes.tar", "/proc", NULL, pids, clientfd);
}

void get_ps(int clientfd) {
    char *cmd = "ps -ao pid,cmd";
    char *fmt = "%s | grep -v \"%s\"";
    int size = strlen(fmt) + 2 * strlen(cmd);
    char buffer[size];
    sprintnf(buffer, size, fmt, cmd, cmd);
    exec_and_send(clientfd, buffer);
}

void get_pid(int clientfd) {
    char buffer[11];
    pid_t pid = getpid();
    snprintf(buffer, sizeof(buffer), "%ld", (long)pid);

    // send one more than the length of the string so that the null character is sent
    send(clientfd, buffer, strlen(buffer) + 1, 0);
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
