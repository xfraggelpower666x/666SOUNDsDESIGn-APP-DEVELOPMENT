package main

import (
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
)

func launch(arguments []string) error {
	executable, err := os.Executable()
	if err != nil {
		return err
	}

	base := filepath.Dir(executable)
	checkout := filepath.Join(base, "checkout")
	runtime := filepath.Join(base, "runtime")
	python := filepath.Join(runtime, "python", "python.exe")
	git := filepath.Join(runtime, "git", "cmd")
	github := filepath.Join(runtime, "gh", "bin")
	// Die gebündelten Werkzeuge stehen auch den normalen CLI-Unterprozessen zur Verfügung.
	searchPath := git + ";" + github + ";" + filepath.Dir(python) + ";" + os.Getenv("PATH")
	app := filepath.Join(checkout, "windows-app", "app.py")
	command := exec.Command(python, append([]string{app}, arguments...)...)
	command.Dir = checkout
	command.Env = append(os.Environ(), "PATH="+searchPath)
	command.Stdin, command.Stdout, command.Stderr = os.Stdin, os.Stdout, os.Stderr
	return command.Run()
}

func main() {
	// Strg+C geht an beide Konsolenprozesse. Der Launcher wartet auf Python.
	interrupts := make(chan os.Signal, 1)
	signal.Notify(interrupts, os.Interrupt)
	defer signal.Stop(interrupts)
	if err := launch(os.Args[1:]); err != nil {
		if child, ok := err.(*exec.ExitError); ok {
			os.Exit(child.ExitCode())
		}
		fmt.Fprintln(os.Stderr, "666DEV:", err)
		os.Exit(1)
	}
}
