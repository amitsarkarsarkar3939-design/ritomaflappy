use std::env;
use std::io::{self, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode, Stdio};
use std::thread;
use std::time::Duration;

const GAME_URL: &str = "http://127.0.0.1:8000/";
const TERMINAL_COMMAND: &str = "bix-V open k0ns0le--";

struct PythonLauncher {
    program: String,
    prefix: Vec<String>,
}

fn project_directory() -> PathBuf {
    if let Ok(directory) = env::current_dir() {
        if directory.join("terminal.py").is_file() {
            return directory;
        }
    }

    if let Ok(executable) = env::current_exe() {
        if let Some(directory) = executable.parent() {
            if directory.join("terminal.py").is_file() {
                return directory.to_path_buf();
            }
        }
    }

    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn python_launchers() -> Vec<PythonLauncher> {
    let mut launchers = Vec::new();

    if let Ok(program) = env::var("PYTHON") {
        if !program.trim().is_empty() {
            launchers.push(PythonLauncher {
                program,
                prefix: Vec::new(),
            });
        }
    }

    if cfg!(windows) {
        launchers.push(PythonLauncher {
            program: "python".to_string(),
            prefix: Vec::new(),
        });
        launchers.push(PythonLauncher {
            program: "py".to_string(),
            prefix: vec!["-3".to_string()],
        });
    } else {
        launchers.push(PythonLauncher {
            program: "python3".to_string(),
            prefix: Vec::new(),
        });
        launchers.push(PythonLauncher {
            program: "python".to_string(),
            prefix: Vec::new(),
        });
    }

    launchers
}

fn game_server_is_running() -> bool {
    let address = SocketAddr::from(([127, 0, 0, 1], 8000));
    TcpStream::connect_timeout(&address, Duration::from_millis(250)).is_ok()
}

fn launch_game(directory: &Path) -> Result<(), String> {
    if game_server_is_running() {
        println!("Collect Ricoins is already running at {GAME_URL}");
        return Ok(());
    }

    let launcher = directory.join("run_app.py");
    if !launcher.is_file() {
        return Err(format!(
            "Could not find {}. Run this launcher from the Collect Ricoins game folder.",
            launcher.display()
        ));
    }

    for python in python_launchers() {
        let mut command = Command::new(&python.program);
        command
            .args(&python.prefix)
            .arg(&launcher)
            .current_dir(directory);

        match command.spawn() {
            Ok(mut process) => {
                thread::sleep(Duration::from_millis(400));
                if let Some(status) = process
                    .try_wait()
                    .map_err(|error| format!("Could not check the game launcher: {error}"))?
                {
                    if status.success() && game_server_is_running() {
                        println!("Collect Ricoins is running at {GAME_URL}");
                        return Ok(());
                    }
                    return Err(format!(
                        "The game launcher stopped before the game became available ({status})."
                    ));
                }
                println!("Launching Collect Ricoins at {GAME_URL}");
                return Ok(());
            }
            Err(error) if error.kind() == io::ErrorKind::NotFound => continue,
            Err(error) => {
                return Err(format!("Could not start the game launcher: {error}"));
            }
        }
    }

    Err("Python 3 was not found. Install Python or set PYTHON to its executable.".to_string())
}

fn open_game_in_browser() -> Result<(), String> {
    let result = if cfg!(windows) {
        Command::new("cmd")
            .args(["/C", "start", "", GAME_URL])
            .spawn()
    } else if cfg!(target_os = "macos") {
        Command::new("open").arg(GAME_URL).spawn()
    } else {
        Command::new("xdg-open").arg(GAME_URL).spawn()
    };

    result
        .map(|_| ())
        .map_err(|error| format!("Could not open the game in a browser: {error}"))
}

fn open_game_terminal(directory: &Path) -> Result<(), String> {
    let terminal_script = directory.join("terminal.py");
    if !terminal_script.is_file() {
        return Err(format!(
            "Could not find {}.",
            terminal_script.display()
        ));
    }

    for python in python_launchers() {
        let mut command = Command::new(&python.program);
        command
            .args(&python.prefix)
            .arg(&terminal_script)
            .arg("--cli")
            .current_dir(directory)
            .stdin(Stdio::piped())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit());

        let mut process = match command.spawn() {
            Ok(process) => process,
            Err(error) if error.kind() == io::ErrorKind::NotFound => continue,
            Err(error) => {
                return Err(format!("Could not open the game terminal: {error}"));
            }
        };
        let mut terminal_input = process
            .stdin
            .take()
            .ok_or_else(|| "Could not connect to the game terminal input.".to_string())?;
        let console_input = io::stdin();
        let mut line = String::new();

        loop {
            line.clear();
            let bytes = console_input
                .read_line(&mut line)
                .map_err(|error| format!("Could not read terminal input: {error}"))?;
            if bytes == 0 {
                let _ = terminal_input.write_all(b"exit\n");
                break;
            }

            let command = line.trim();
            if command.eq_ignore_ascii_case("back") {
                terminal_input
                    .write_all(b"exit\n")
                    .and_then(|_| terminal_input.flush())
                    .map_err(|error| format!("Could not close the game terminal: {error}"))?;
                break;
            }

            terminal_input
                .write_all(line.as_bytes())
                .and_then(|_| terminal_input.flush())
                .map_err(|error| format!("Could not send a command to the game terminal: {error}"))?;

            if command.eq_ignore_ascii_case("exit") || command.eq_ignore_ascii_case("quit") {
                break;
            }
        }

        drop(terminal_input);
        let status = process
            .wait()
            .map_err(|error| format!("Could not close the game terminal: {error}"))?;
        println!("\nTerminal closed. You are back at the game launcher ({status}).");
        return Ok(());
    }

    Err("Python 3 was not found. Install Python or set PYTHON to its executable.".to_string())
}

fn print_help() {
    println!("Collect Ricoins is open in your browser.");
    println!("Type {TERMINAL_COMMAND} to open the game terminal.");
    println!("Inside the terminal, type back or exit to return here.");
    println!("Type back here to reopen the game, or exit to close this launcher.");
}

fn main() -> ExitCode {
    let directory = project_directory();
    println!("Starting Collect Ricoins...");
    if let Err(error) = launch_game(&directory) {
        eprintln!("{error}");
        return ExitCode::FAILURE;
    }
    print_help();

    let console_input = io::stdin();
    let mut line = String::new();
    loop {
        print!("game launcher> ");
        if let Err(error) = io::stdout().flush() {
            eprintln!("Could not write the launcher prompt: {error}");
            return ExitCode::FAILURE;
        }

        line.clear();
        match console_input.read_line(&mut line) {
            Ok(0) => {
                println!("\nLauncher closed. The game remains open.");
                return ExitCode::SUCCESS;
            }
            Ok(_) => {}
            Err(error) => {
                eprintln!("Could not read a command: {error}");
                return ExitCode::FAILURE;
            }
        }

        let command = line.trim();
        if command.eq_ignore_ascii_case(TERMINAL_COMMAND) {
            if let Err(error) = open_game_terminal(&directory) {
                eprintln!("{error}");
            }
        } else if command.eq_ignore_ascii_case("back") || command.eq_ignore_ascii_case("game") {
            match open_game_in_browser() {
                Ok(()) => println!("Collect Ricoins is open. The launcher is still available."),
                Err(error) => eprintln!("{error}"),
            }
        } else if command.eq_ignore_ascii_case("help") || command == "?" {
            print_help();
        } else if command.eq_ignore_ascii_case("exit") || command.eq_ignore_ascii_case("quit") {
            println!("Launcher closed. Collect Ricoins remains open in your browser.");
            return ExitCode::SUCCESS;
        } else {
            println!("Unknown launcher command. Type help or {TERMINAL_COMMAND}.");
        }
    }
}
