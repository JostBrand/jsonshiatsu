# jsonshiatsu NixOS Dev Flake

For the nix folks a dev shell

## Quick Start


### Enter Development 

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

## Flake Runner

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

- **Python 3.13** with full development stack
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
