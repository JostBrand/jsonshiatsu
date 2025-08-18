{
  description = "jsonshiatsu - Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    pre-commit-hooks.url = "github:cachix/git-hooks.nix";
  };

  outputs = { self, nixpkgs, flake-utils, pre-commit-hooks }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        pre-commit-check = pre-commit-hooks.lib.${system}.run {
          src = ./.;
          hooks = {
            black.enable = true;
            isort.enable = true;
            flake8.enable = true;
            mypy.enable = true;
          };
        };
        
        python = pkgs.python313;
        pythonWithPkgs = python.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
          pytest
          pytest-cov
          black
          isort
          flake8
          autopep8
          mypy
          build
          # Add core dependencies to avoid pip externally managed errors
        ]);
        
        devScripts = pkgs.writeScriptBin "dev-scripts" ''
          #!/usr/bin/env bash
          
          case "$1" in
            "test")
              echo "Running tests..."
              PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -v --cov=jsonshiatsu --cov-report=html --cov-report=term
              ;;
            "test-fast")
              echo "Running fast tests..."
              PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/unit/ -v
              ;;
            "test-integration")
              echo "Running integration tests..."
              PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/integration/ -v
              ;;
            "format")
              echo "Formatting code..."
              black jsonshiatsu/ tests/ examples/
              isort jsonshiatsu/ tests/ examples/
              ;;
            "lint")
              echo "Linting code..."
              flake8 jsonshiatsu/ tests/ examples/
              mypy jsonshiatsu/
              ;;
            "clean")
              echo "Cleaning build artifacts..."
              rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/ .coverage
              find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
              ;;
            "build")
              echo "Building package..."
              python -m build
              ;;
            "install-dev")
              echo "Setting up development environment..."
              echo "PYTHONPATH configured to use local source directory"
              echo "jsonshiatsu is ready for development!"
              ;;
            "profile")
              echo "Running performance profile..."
              PYTHONPATH="$(pwd):$PYTHONPATH" python -m cProfile -o profile.stats examples/demo.py
              ;;
            "benchmark")
              echo "Running benchmarks..."
              PYTHONPATH="$(pwd):$PYTHONPATH" python simple_perf_test.py
              ;;
            "all-checks")
              echo "Running all checks..."
              $0 format
              $0 lint
              $0 test
              ;;
            *)
              echo "jsonshiatsu Development Scripts"
              echo ""
              echo "Usage: dev-scripts <command>"
              echo ""
              echo "Development commands (using Nix-provided Python 3.13):"
              echo "  test           - Run all tests with coverage"
              echo "  test-fast      - Run unit tests only"
              echo "  test-integration - Run integration tests only"
              echo "  format         - Format code with black and isort"
              echo "  lint           - Run linting with flake8 and mypy"
              echo "  clean          - Clean build artifacts"
              echo "  build          - Build the package"
              echo "  install-dev    - Install in development mode"
              echo "  profile        - Run performance profiling"
              echo "  benchmark      - Run performance benchmarks"
              echo "  all-checks     - Run all quality checks"
              echo ""
              echo "Quick start:"
              echo "  1. dev-scripts install-dev    # Install jsonshiatsu in development mode"
              echo "  2. dev-scripts test-fast      # Run unit tests"
              echo ""
              echo "💡 All dependencies are provided by Nix, no virtual environment needed!"
              echo "   Uses Python $(python --version | cut -d' ' -f2) with pre-installed packages."
              ;;
          esac
        '';

      in
      {
        checks = {
          inherit pre-commit-check;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonWithPkgs
            
            git
            curl
            jq
            ruff
            
            gnumake
            tree
            valgrind
            devScripts
          ] ++ pre-commit-check.enabledPackages;

          shellHook = pre-commit-check.shellHook + ''
            echo "🤲 jsonshiatsu Development Environment"
            echo "======================================"
            echo ""
            echo "Python: $(python --version)"
            echo "Location: $(pwd)"
            echo ""
            echo "🎯 Ready to use! All dependencies included via Nix."
            echo ""
            echo "📚 Available commands:"
            echo "  dev-scripts install-dev    # Install jsonshiatsu in development mode"
            echo "  dev-scripts test-fast      # Run unit tests"
            echo "  dev-scripts test           # Run all tests with coverage"
            echo "  dev-scripts format         # Format code with black and isort"
            echo "  dev-scripts lint           # Run linting"
            echo "  dev-scripts                # Show all available commands"
            echo ""
            echo "💡 No virtual environment needed! Python 3.13 + dev tools provided by Nix."
            echo "   This completely avoids 'pip externally managed environment' errors."
            echo ""
            
            # Set up development environment variables
            export JSONSHIATSU_DEV=1
            export PYTEST_ADDOPTS="--tb=short"
            export PYTHONPATH="$(pwd):$PYTHONPATH"
            
            # Create necessary directories
            mkdir -p {logs,tmp,build}
            
            # Add common ignore patterns to gitignore if it doesn't exist
            if [ ! -f .gitignore ] || ! grep -q "^*.egg-info" .gitignore; then
              echo "*.egg-info/" >> .gitignore
              echo "__pycache__/" >> .gitignore
              echo ".pytest_cache/" >> .gitignore
              echo "htmlcov/" >> .gitignore
              echo ".coverage" >> .gitignore
              echo "build/" >> .gitignore
              echo "dist/" >> .gitignore
            fi
          '';

          NIX_SHELL_PRESERVE_PROMPT = 1;
        };

        # Package definition (for building jsonshiatsu itself)
        packages.default = pkgs.python313Packages.buildPythonPackage rec {
          pname = "jsonshiatsu";
          version = "0.1.0";
          
          src = ./.;
          
          format = "pyproject";
          
          nativeBuildInputs = with pkgs.python313Packages; [
            setuptools
            wheel
          ];
          
          propagatedBuildInputs = with pkgs.python313Packages; [
            # Add runtime dependencies here if any
          ];
          
          checkInputs = with pkgs.python313Packages; [
            pytest
            pytest-cov
          ];
          
          checkPhase = ''
            python -m pytest tests/unit/ -v
          '';
          
          meta = with pkgs.lib; {
            description = "A therapeutic JSON parser that gently massages malformed JSON into shape";
            homepage = "https://github.com/yourusername/jsonshiatsu";
            license = licenses.agpl3Only;
            maintainers = [ ];
          };
        };

        apps = {
          test = flake-utils.lib.mkApp {
            drv = pkgs.writeShellScriptBin "jsonshiatsu-test" ''
              ${pythonWithPkgs}/bin/python -m pytest tests/ -v
            '';
          };
          
          demo = flake-utils.lib.mkApp {
            drv = pkgs.writeShellScriptBin "jsonshiatsu-demo" ''
              export PYTHONPATH="$(pwd):$PYTHONPATH"
              ${pythonWithPkgs}/bin/python examples/demo.py
            '';
          };
          
          partial-demo = flake-utils.lib.mkApp {
            drv = pkgs.writeShellScriptBin "jsonshiatsu-partial-demo" ''
              export PYTHONPATH="$(pwd):$PYTHONPATH"
              ${pythonWithPkgs}/bin/python examples/partial_parsing_demo.py
            '';
          };
        };

        formatter = pkgs.nixpkgs-fmt;
      });
}
