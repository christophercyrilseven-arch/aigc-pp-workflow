# Local Web Worker

The local web worker is served by the Python package:

```bash
aigcpp serve --host 0.0.0.0 --port 8897 --workers 4 --token optional-token
```

It provides:

- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /artifact/{job_id}/{path}`

The worker runs generation on the user's own machine or server. If it is
exposed beyond a trusted network, use a token and a secure tunnel.
