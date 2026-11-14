#!/usr/bin/env ruby

python_candidates =
  if RUBY_PLATFORM.match?(/mswin|mingw|cygwin/i)
    [ENV.fetch("PYTHON", "python"), "py"]
  else
    [ENV.fetch("PYTHON", "python3"), "python"]
  end

script = File.expand_path("terminal.py", Dir.pwd)
unless File.file?(script)
  warn "terminal.py was not found in #{Dir.pwd}."
  warn "Run terminal.rb from the game folder."
  exit 2
end

python_candidates.each do |python|
  begin
    next unless system(python, "--version", out: File::NULL, err: File::NULL)

    arguments = python == "py" ? ["-3", script, "--cli"] : [script, "--cli"]
    exec(python, *arguments)
  rescue Errno::ENOENT
    next
  end
end

warn "Python 3 was not found. Install Python or set the PYTHON environment variable."
exit 127
