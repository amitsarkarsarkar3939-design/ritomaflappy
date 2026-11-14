use std::{io::{self, Write}, thread, time::Duration};

fn main() -> io::Result<()> {
    let frames = [
        "\x1b[2J\x1b[H  ____  _",
        "\x1b[2J\x1b[H  ____  _\n | __ )(_)",
        "\x1b[2J\x1b[H  ____  _\n | __ )(_)\n |  _ \\ |",
        "\x1b[2J\x1b[H  ____  _\n | __ )(_)\n |  _ \\ |\n | |_) || |",
        "\x1b[2J\x1b[H  ____  _\n | __ )(_)\n |  _ \\ |\n | |_) || |\n |____/ |_|",
    ];

    for frame in frames {
        print!("\x1b[32m{frame}\x1b[0m");
        io::stdout().flush()?;
        thread::sleep(Duration::from_millis(110));
    }
    println!("\n  Bix Terminal is ready.");
    Ok(())
}