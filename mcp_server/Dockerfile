FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir mcp httpx

COPY . .

# Run MCP server
CMD ["python", "-m", "mcp_server.server"]
