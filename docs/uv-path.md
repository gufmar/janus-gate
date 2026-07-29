# uv PATH on Debian (bash)

The Astral installer places `uv` in `~/.local/bin` by default. If `uv` is installed but `uv: command not found`, the shell `PATH` is usually missing that directory.

`PATH` is not usually set in one global file for your user tools. On a typical Debian bash setup:

| File | When it runs |
| --- | --- |
| `~/.profile` | Login shells (common for SSH sessions). Debian’s default here already prepends `~/.local/bin` and `~/bin` when those dirs exist. |
| `~/.bashrc` | Interactive non-login bash shells (new terminal tabs, `bash` without login). Often sourced from `~/.profile` when bash is the login shell. |
| `/etc/environment` or `/etc/profile` | System-wide; prefer user files for `uv`. |

## Option A – rely on Debian’s default `~/.profile` (recommended)

Confirm these lines exist (stock Debian images usually already have them):

```bash
# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
```

Then either open a new SSH login session, or reload:

```bash
source ~/.profile
```

## Option B – also add it in `~/.bashrc`

Handy for non-login interactive shells:

```bash
# ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
```

Reload with `source ~/.bashrc`, or open a new shell.

## Quick checks

```bash
echo "$PATH"
which uv
ls -l "$HOME/.local/bin/uv"
```

## systemd

Service units do not load `~/.profile` or `~/.bashrc`. Prefer a full path in `ExecStart` (for example `/home/<user>/.local/bin/uv run ...`) or set `Environment=PATH=...` / an `EnvironmentFile` in the unit. See [deploy/janus-gate.service](../deploy/janus-gate.service).
