# Deploying Flow2API to Vercel

This guide provides a complete checklist for deploying Flow2API to Vercel.

## Prerequisites

1.  **Vercel Account**: [Sign up](https://vercel.com/signup).
2.  **Git Repository**: The Flow2API code must be pushed to a Git provider (GitHub, GitLab, Bitbucket).
3.  **External Storage**:
    *   **Database**: Flow2API defaults to SQLite, which is ephemeral on Vercel (data resets on redeploy). For production, you must provision a PostgreSQL database (e.g., Vercel Postgres, Neon, Supabase) and update the application code to support it, OR accept that data is stateless.
    *   **Object Storage**: Generated images and videos are saved to `/tmp`. For persistent access, configure an Object Storage bucket (AWS S3, Cloudflare R2, Vercel Blob) and a CDN.

## Environment Variable Matrix

Configure these variables in your Vercel Project Settings.

| Config Key | Environment Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `global.api_key` | `API_KEY` | **Yes** | `han1234` | Master API Key for client access. **Keep Secret.** |
| `global.admin_username` | `ADMIN_USERNAME` | **Yes** | `admin` | Username for the Admin Dashboard. |
| `global.admin_password` | `ADMIN_PASSWORD` | **Yes** | `admin` | Password for the Admin Dashboard. **Keep Secret.** |
| `flow.labs_base_url` | `FLOW_LABS_BASE_URL` | No | `https://labs.google/fx/api` | Google Labs API Base URL. |
| `flow.api_base_url` | `FLOW_API_BASE_URL` | No | `https://aisandbox-pa.googleapis.com/v1` | Google AI Sandbox API Base URL. |
| `flow.timeout` | `FLOW_TIMEOUT` | No | `120` | Timeout for upstream API calls (seconds). |
| `server.host` | `SERVER_HOST` | No | `0.0.0.0` | Server host binding. |
| `server.port` | `SERVER_PORT` | No | `8000` | Server port (Vercel overrides this). |
| `debug.enabled` | `DEBUG_ENABLED` | No | `false` | Enable debug mode. |
| `proxy.proxy_enabled` | `PROXY_ENABLED` | No | `false` | Enable outbound proxy. |
| `proxy.proxy_url` | `PROXY_URL` | No | - | HTTP Proxy URL. |
| `generation.image_timeout` | `GENERATION_IMAGE_TIMEOUT` | No | `300` | Timeout for image generation tasks. |
| `generation.video_timeout` | `GENERATION_VIDEO_TIMEOUT` | No | `1500` | Timeout for video generation tasks. |
| `cache.enabled` | `CACHE_ENABLED` | No | `false` | Enable caching of generated assets. |
| `cache.base_url` | `CACHE_BASE_URL` | No | - | Public URL prefix for assets (e.g. CDN URL). |

## Deployment Checklist

### 1. Preparation

- [ ] **Fork/Clone** the repository.
- [ ] **Create `vercel.json`** (if not present) to configure the build and routes:
    ```json
    {
      "version": 2,
      "builds": [
        {
          "src": "api/index.py",
          "use": "@vercel/python",
          "config": {
            "maxDuration": 300,
            "runtime": "python3.11"
          }
        }
      ],
      "routes": [
        {
          "src": "/v1/(.*)",
          "dest": "api/index.py"
        },
        {
          "src": "/api/admin/(.*)",
          "dest": "api/index.py"
        },
        {
          "src": "/login",
          "dest": "api/index.py"
        },
        {
          "src": "/manage",
          "dest": "api/index.py"
        },
        {
          "src": "/static/(.*)",
          "dest": "/static/$1"
        },
        {
          "src": "/",
          "dest": "api/index.py"
        }
      ]
    }
    ```

### 2. Database & Storage Setup

- [ ] **Provision Postgres** (Recommended): Set up a Vercel Postgres instance.
- [ ] **Configure Object Storage**: Create an S3/Blob bucket for storing generated media.
- [ ] **Migration**: Flow2API runs a migration check on startup. Ensure the database credentials are correct.

### 3. Vercel Project Configuration

- [ ] Import the repository in Vercel.
- [ ] In **Settings > Environment Variables**, add all the variables from the matrix above.
- [ ] Set `PYTHON_VERSION` to `3.9` or `3.11` if needed.

### 4. Deploy

- [ ] Run `vercel deploy` (or push to main branch).
- [ ] Verify the deployment URL.

## Architecture & SSE Proxying

### SSE (Server-Sent Events)
Flow2API uses SSE for streaming chat completions (`/v1/chat/completions`) and generation status.
- **Vercel Support**: Vercel Serverless Functions support response streaming. Flow2API's FastAPI implementation is compatible.
- **Timeouts**: Vercel has a default timeout (10s on Hobby, 60s on Pro). Video generation may exceed this.
    - **Mitigation**: Use the "Stay Alive" mechanism or client-side polling if the connection drops.
    - **Proxying**: Ensure no buffering proxies (like standard Nginx defaults) sit between the client and Vercel. Vercel's Edge Network handles this automatically.

### Asset Serving
- **Ephemeral Storage**: `/tmp` is the only writable directory on Vercel.
- **CDN**: Configure `CACHE_BASE_URL` to point to your CDN.
- **Implementation**: Ensure the application uploads generated files from `/tmp` to your Object Storage, then returns the CDN URL.

## Local Development vs. Vercel

To keep local development compatible:
- Use `vercel dev` to simulate the Vercel environment locally.
- Use `.env` files locally (loaded by `python-dotenv` or Vercel CLI) instead of hardcoding `setting.toml`.

## Troubleshooting

### Cold Start Latency
**Symptom**: First request takes 3-5 seconds.
**Cause**: Python runtime booting up.
**Fix**: Use Vercel Edge Functions (if applicable) or keep functions warm (Pro feature).

### Storage Permission Errors
**Symptom**: `OSError: [Errno 30] Read-only file system`
**Cause**: Trying to write to `data/` or `config/`.
**Fix**: Ensure all file writes target `/tmp`. Check logs to see where the write is attempting to happen.

### Database Connectivity
**Symptom**: Connection timeouts or errors.
**Cause**: Network restrictions or missing drivers.
**Fix**:
- Ensure `requirements.txt` includes the necessary DB driver (e.g., `asyncpg`).
- Allowlist Vercel IP addresses in your Database firewall.
- Use a connection pooler (e.g. Supavisor) for serverless environments.

### Generation Timeouts
**Symptom**: 504 Gateway Timeout during video generation.
**Cause**: Processing exceeds Vercel's execution limit.
**Fix**:
- Upgrade to Vercel Pro (allows up to 300s).
- Offload generation to a background worker (outside Vercel) and use webhooks.
