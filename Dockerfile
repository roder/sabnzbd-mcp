FROM python:3.11-alpine

WORKDIR /app
COPY pyproject.toml .
COPY src/ ./src/

# Install the project locally so `sabnzbd-mcp` is available in PATH
RUN pip install --no-cache-dir .

# Command runs the MCP server via standard IO
ENTRYPOINT ["sabnzbd-mcp"]
