//! oziwm: the OziOS window manager, a Wayland compositor built on Smithay.

mod anim;
mod bindings;
mod cursor;
mod deco;
mod grabs;
mod handlers;
mod input;
mod ipc;
mod keyboard;
mod placement;
mod render;
mod state;
mod theme;
mod title;
mod tty;
mod winit;

use smithay::reexports::{calloop::EventLoop, wayland_server::Display};

pub use state::OziWm;

const USAGE: &str = "\
oziwm: OziOS window manager

Usage: oziwm [--nested | --tty] [-c COMMAND]...

  --nested      run as a window inside the current desktop
  --tty         run on the screen directly (the default outside a desktop)
  -c COMMAND    start COMMAND once oziwm is ready (may be given more than once)
  --version     print the version
";

#[derive(Clone, Copy, PartialEq, Eq)]
enum Backend {
    Auto,
    Nested,
    Tty,
}

struct Args {
    commands: Vec<String>,
    backend: Backend,
}

fn parse_args() -> Result<Args, String> {
    let mut commands = Vec::new();
    let mut backend = Backend::Auto;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--nested" => backend = Backend::Nested,
            "--tty" => backend = Backend::Tty,
            "-c" | "--command" => commands.push(args.next().ok_or("-c needs a command")?),
            "--version" => {
                println!("oziwm {}", env!("CARGO_PKG_VERSION"));
                std::process::exit(0);
            }
            "-h" | "--help" => {
                print!("{USAGE}");
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument: {other}\n\n{USAGE}")),
        }
    }
    Ok(Args { commands, backend })
}

fn init_logging() {
    let filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("oziwm=info,smithay=warn"));
    tracing_subscriber::fmt().with_env_filter(filter).init();
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = match parse_args() {
        Ok(args) => args,
        Err(message) => {
            eprintln!("{message}");
            std::process::exit(2);
        }
    };
    init_logging();

    let mut event_loop: EventLoop<OziWm> = EventLoop::try_new()?;
    let display: Display<OziWm> = Display::new()?;
    let mut state = OziWm::new(&mut event_loop, display)?;

    let inside_a_desktop = std::env::var_os("WAYLAND_DISPLAY").is_some() || std::env::var_os("DISPLAY").is_some();
    let nested = match args.backend {
        Backend::Nested => true,
        Backend::Tty => false,
        Backend::Auto => inside_a_desktop,
    };
    if nested {
        winit::init_winit(&mut event_loop, &mut state)?;
    } else {
        tty::init_tty(&mut event_loop, &mut state)?;
    }
    tracing::info!(
        socket = ?state.socket_name,
        ipc = %state.ipc_path.display(),
        "oziwm {} ready",
        env!("CARGO_PKG_VERSION")
    );

    for command in &args.commands {
        state.spawn_shell(command);
    }

    let result = event_loop.run(None, &mut state, |_| {});
    let _ = std::fs::remove_file(&state.ipc_path);
    result?;
    tracing::info!("oziwm stopped");
    Ok(())
}
