package main

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"runtime"
)

type pythonLauncher struct {
	name   string
	prefix []string
}

func launch(python pythonLauncher) error {
	args := append(append([]string{}, python.prefix...), "terminal.py", "--cli")
	command := exec.Command(python.name, args...)
	command.Stdin = os.Stdin
	command.Stdout = os.Stdout
	command.Stderr = os.Stderr
	return command.Run()
}

func launchers() []pythonLauncher {
	if runtime.GOOS == "windows" {
		return []pythonLauncher{
			{name: "python"},
			{name: "py", prefix: []string{"-3"}},
		}
	}
	return []pythonLauncher{
		{name: "python3"},
		{name: "python"},
	}
}

func main() {
	for _, python := range launchers() {
		if _, err := exec.LookPath(python.name); err != nil {
			continue
		}

		err := launch(python)
		var exitError *exec.ExitError
		if errors.As(err, &exitError) {
			os.Exit(exitError.ExitCode())
		}
		if err != nil {
			fmt.Fprintln(os.Stderr, "Could not run the Bix game terminal:", err)
			os.Exit(1)
		}
		return
	}

	fmt.Fprintln(os.Stderr, "Python 3 was not found. Install Python or run terminal.py directly.")
	os.Exit(127)
}
