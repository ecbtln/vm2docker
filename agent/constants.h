// size is technically an unsigned long (%lu), but we make it %s for portability with the python
// regular expression side of things
#define SEND_FILE_HEADER_FMT "Size: %s, Filename: %s"

// RPC commands
#define GET_DEPS_CMD 		    "get_dependencies"
#define GET_FS_CMD 			    "get_filesystem"
#define GET_INSTALLED_CMD 	    "get_installed"
#define EXIT_CMD			    "exit"
#define GET_BOUND_SOCKETS_CMD   "get_bound_sockets"
#define GET_PROC_CMD            "get_active_processes"
#define GET_PS_CMD              "get_ps"
#define GET_PID_CMD             "get_pid"


// responses
#define UNKNOWN_CMD "UNKNOWN_CMD"


// socket
#define DEFAULT_AGENT_PORT	49153


// now we also need the GET_INSTALLED_CMD that is actually executed for each OS to be bridged over
// this is because we need to execute it in the Docker image itself, to detect packages
// that are installed directly in the base image
// we'll establish the convention of <OS_NAME>__GET_INSTALLED_CMD as the name of the cmd
#define UBUNTU__GET_INSTALLED_CMD "dpkg --get-selections"
#define CENTOS__GET_INSTALLED_CMD "rpm -qa --queryformat '%{NAME}\n'"
#define MAGEIA__GET_INSTALLED_CMD CENTOS__GET_INSTALLED_CMD

