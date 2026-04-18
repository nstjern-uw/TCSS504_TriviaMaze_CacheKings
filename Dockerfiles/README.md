# Dockerfile — Nuovo Fresco Pipe Network (CLI)

Container build for the CLI version of the **Nuovo Fresco Pipe Network** trivia maze game
(`python3 main.py`). The Dockerfile clones this repository at build time, installs the
Python dependencies from `requirements.txt`, and launches the CLI as the default command.

## Contents

- `dockerfile` — image definition (Python 3.11 slim base, clones the repo, installs deps, runs `main.py`).
- `.dockerignore` — excludes local files (`.git`, caches, editor dirs) from the build context.

## Build the image

From the repository root:

```bash
cd Dockerfiles && docker build -t maze .
```

This tags the locally built image as `maze:latest`.

## Run the game

```bash
docker run --rm -it maze
```

- `--rm` removes the container when you exit.
- `-it` gives you an interactive TTY so the CLI prompts work (arrow keys / `n/s/e/w`,
  `a/b/c/d` for answers, `blast`, `save`, `load`, `quit`).

To exit the game, type `quit` at the prompt.

## Pre-built image on Docker Hub

The image is also published to Docker Hub:

**`nstjern/maze:v1`**

Pull and run it without building locally:

```bash
docker pull nstjern/maze:v1
docker run --rm -it nstjern/maze:v1
```

A rolling `nstjern/maze:latest` tag is also published.

## Notes

- The Qt GUI (`python3 main.py --qt`) is **not** the default entry point; running the Qt
  variant from a container requires extra host setup (e.g. X11 forwarding with
  `-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix`). The CLI runs fine out of the box.
- The image is built for `linux/arm64` on the publisher's machine. If you need
  `linux/amd64`, rebuild locally or use `docker buildx build --platform linux/amd64 ...`.
