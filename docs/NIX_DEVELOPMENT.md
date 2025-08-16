# jsonshiatsu NixOS Development Environment

This project includes a comprehensive NixOS development environment using Nix flakes.

## Quick Start

### Prerequisites
- NixOS or Nix package manager with flakes enabled
- Optional: `direnv` for automatic environment loading

### Enter Development Environment

```bash
# Using flakes (recommended)
nix develop

# Or using direnv (automatically loads when entering directory)
direnv allow
```

### Development Commands

Once in the development shell, use the built-in script:

```bash
# Show all available commands
dev-scripts help

# Quick development workflow
dev-scripts install-dev    # Install in development mode
dev-scripts test-fast      # Run unit tests
dev-scripts format         # Format code
dev-scripts lint          # Run linting
dev-scripts all-checks    # Run all quality checks
```

## Available Commands

| Command | Description |
|---------|-------------|
| `dev-scripts test` | Run all tests with coverage |
| `dev-scripts test-fast` | Run unit tests only |
| `dev-scripts test-integration` | Run integration tests only |
| `dev-scripts format` | Format code with black and isort |
| `dev-scripts lint` | Run linting with flake8 and mypy |
| `dev-scripts security` | Run security checks with bandit |
| `dev-scripts clean` | Clean build artifacts |
| `dev-scripts build` | Build the package |
| `dev-scripts install-dev` | Install in development mode |
| `dev-scripts profile` | Run performance profiling |
| `dev-scripts benchmark` | Run performance benchmarks |
| `dev-scripts docs` | Build documentation |
| `dev-scripts all-checks` | Run all quality checks |

## Flake Apps

You can also run apps directly:

```bash
# Run tests
nix run .#test

# Run demo
nix run .#demo

# Run partial parsing demo
nix run .#partial-demo
```

## Development Tools Included

- **Python 3.11** with full development stack
- **Testing**: pytest, pytest-cov, pytest-xdist
- **Code Quality**: black, isort, flake8, mypy, bandit
- **Performance**: memory-profiler, line-profiler, cProfile
- **Documentation**: sphinx, sphinx-rtd-theme
- **Development**: ipython, ipdb, rich
- **Build Tools**: setuptools, wheel, build

## Directory Structure

The flake automatically sets up:
- `PYTHONPATH` to include current directory
- Development mode installation
- Useful aliases when using direnv:
  - `ff` → format code
  - `ft` → fast tests
  - `fl` → lint
  - `fc` → clean
  - `fa` → all checks

## For Systems Without Flakes

A fallback `shell.nix` is provided:

```bash
nix-shell
```

## Package Building

To build the jsonshiatsu package itself:

```bash
# Build package
nix build

# Build and install
nix profile install
```

## Environment Variables

The development environment sets:
- `jsonshiatsu_DEV=1` - Development mode flag
- `PYTHONPATH` - Includes current directory
- `PYTEST_ADDOPTS="--tb=short"` - Shorter test output

## Excluded from Packaging

These Nix development files are automatically excluded from package distribution:
- `flake.nix`
- `flake.lock`
- `shell.nix`
- `.envrc`
- `.direnv/`
- Development artifacts

## Performance Testing

```bash
# Run performance benchmarks
dev-scripts benchmark

# Profile a specific script
dev-scripts profile

# Memory profiling
python -m memory_profiler examples/demo.py
```

## Troubleshooting

1. **Flakes not enabled**: Add to `/etc/nixos/configuration.nix`:
   ```nix
   nix.settings.experimental-features = [ "nix-command" "flakes" ];
   ```

2. **direnv not working**: Install and configure:
   ```bash
   nix-env -i direnv
   echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
   ```

3. **Permission issues**: Ensure you have write access to the project directory

4. **Package not found**: Update nixpkgs channel:
   ```bash
   nix flake update
   ```

This development environment provides everything needed for productive jsonshiatsu development on NixOS!