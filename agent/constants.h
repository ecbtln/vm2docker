// size is technically an unsigned long (%lu), but we make it %s for portability with the python
// regular expression side of things
#define SEND_FILE_HEADER_FMT "Size: %s, Filename: %s"

// commands
#define GET_DEPS_CMD 		"get_dependencies"
#define GET_FS_CMD 			"get_filesystem"
#define GET_INSTALLED_CMD 	"get_installed"
#define EXIT_CMD			"exit"

// responses
#define UNKNOWN_CMD "UNKNOWN_CMD"