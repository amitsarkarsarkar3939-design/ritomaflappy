#include <stdio.h>

#ifdef _WIN32
#include <process.h>

int main(void) {
    const char *python_args[] = {"python", "terminal.py", "--cli", NULL};
    intptr_t result = _spawnvp(_P_WAIT, "python", python_args);
    if (result != -1) {
        return (int)result;
    }

    {
        const char *launcher_args[] = {"py", "-3", "terminal.py", "--cli", NULL};
        result = _spawnvp(_P_WAIT, "py", launcher_args);
    }
    if (result == -1) {
        fputs("Python 3 was not found. Install Python or run terminal.py directly.\n", stderr);
        return 127;
    }
    return (int)result;
}

#else
#include <errno.h>
#include <unistd.h>

int main(void) {
    char *python3_args[] = {"python3", "terminal.py", "--cli", NULL};
    char *python_args[] = {"python", "terminal.py", "--cli", NULL};

    execvp("python3", python3_args);
    if (errno != ENOENT) {
        perror("Could not start python3");
        return 127;
    }

    execvp("python", python_args);
    perror("Python 3 was not found");
    return 127;
}
#endif
