#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static volatile sig_atomic_t child_pid;
static volatile sig_atomic_t pending_signal;

static void forward_signal(int signal_number) {
    pending_signal = signal_number;
    if (child_pid > 0) {
        kill((pid_t)child_pid, signal_number);
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: herdr-launchagent-supervisor COMMAND [ARG ...]\n");
        return 64;
    }

    struct sigaction action = {.sa_handler = forward_signal};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, NULL) != 0 || sigaction(SIGINT, &action, NULL) != 0) {
        fprintf(stderr, "could not install signal handlers: %s\n", strerror(errno));
        return 1;
    }

    pid_t pid;
    int error = posix_spawn(&pid, argv[1], NULL, NULL, &argv[1], environ);
    if (error != 0) {
        fprintf(stderr, "could not start %s: %s\n", argv[1], strerror(error));
        return 1;
    }
    child_pid = pid;
    if (pending_signal != 0) {
        kill(pid, pending_signal);
    }

    siginfo_t info;
    while (waitid(P_PID, (id_t)pid, &info, WEXITED | WNOWAIT) != 0) {
        if (errno != EINTR) {
            fprintf(stderr, "could not wait for %s: %s\n", argv[1], strerror(errno));
            return 1;
        }
    }

    sigset_t blocked, previous;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGTERM);
    sigaddset(&blocked, SIGINT);
    if (sigprocmask(SIG_BLOCK, &blocked, &previous) != 0) {
        fprintf(stderr, "could not block signals while reaping %s: %s\n", argv[1], strerror(errno));
        return 1;
    }

    int status;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) {
            fprintf(stderr, "could not reap %s: %s\n", argv[1], strerror(errno));
            return 1;
        }
    }
    child_pid = 0;
    if (sigprocmask(SIG_SETMASK, &previous, NULL) != 0) {
        fprintf(stderr, "could not restore signal mask: %s\n", strerror(errno));
        return 1;
    }

    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    return 1;
}
