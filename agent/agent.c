#include <stdio.h>
#include <errno.h>
#include <err.h>
#include <sys/socket.h>
#include <resolv.h>
#include <arpa/inet.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdbool.h>

#define MY_PORT		9999
#define MAXBUF		1024


void process_client(int clientfd, struct sockaddr_in * client_addr);
void process_cmd(char *cmd, int cmd_size, int clientfd);

int main(int argc, char *argv[]) {   
	int sockfd;
	struct sockaddr_in self;

	/*---Create streaming socket---*/
    if ( (sockfd = socket(AF_INET, SOCK_STREAM, 0)) < 0 )
	{
		perror("Socket");
		exit(errno);
	}

	memset(&self, 0, sizeof(self));
	self.sin_family = AF_INET;
	self.sin_port = htons(MY_PORT);
	self.sin_addr.s_addr = INADDR_ANY;

	/*---Assign a port number to the socket---*/
    if ( bind(sockfd, (struct sockaddr*)&self, sizeof(self)) != 0 )
	{
		perror("socket--bind");
		exit(errno);
	}

	/*---Make it a "listening socket"---*/
	if ( listen(sockfd, 20) != 0 )
	{
		perror("socket--listen");
		exit(errno);
	}

	/*---Forever... ---*/
	while (true) {	
		int clientfd;
		struct sockaddr_in client_addr;
		int addrlen = sizeof(client_addr);

		/*---accept a connection (creating a data pipe)---*/
		clientfd = accept(sockfd, (struct sockaddr*)&client_addr, (socklen_t*)&addrlen);

		// Only accept one client at a time, this is desired behavior
		process_client(clientfd, &client_addr);
		
		/*---Close data connection---*/
		close(clientfd);
	}

	/*---Clean up (should never get here!)---*/
	close(sockfd);
	return 0;
}



void process_client(int clientfd, struct sockaddr_in * client_addr) {
	char buffer[MAXBUF];

	printf("%s:%d connected\n", inet_ntoa(client_addr->sin_addr), ntohs(client_addr->sin_port));

	while (true) {
		// accept messages indefinitely until the client closes the connection
		ssize_t msg_sz = recv(clientfd, buffer, MAXBUF, 0);
		if (msg_sz == 0) {
			printf("%s:%d connection closed\n", inet_ntoa(client_addr->sin_addr), ntohs(client_addr->sin_port));
			break;
		}
		process_cmd(buffer, msg_sz, clientfd);
	}
}


void process_cmd(char *cmd, int cmd_size, int clientfd) {
	// temporary implementation that just returns what the client asked for
	send(clientfd, cmd, cmd_size, 0);
}
