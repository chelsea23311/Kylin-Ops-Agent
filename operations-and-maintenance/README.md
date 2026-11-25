# 前端

Vue 3 + Vite + Pinia + Element Plus。部署和模型配置请参阅[项目 README](../README.md)。

```bash
npm ci
npm run dev
```

默认通过 Vite 代理连接 `127.0.0.1:8000` 后端，所有业务页面使用真实接口。生产构建运行 `npm run build`，生成的 `dist/` 由后端同源托管。

如需分离部署，可通过 `VITE_API_BASE_URL` 指定后端地址，并在前端域名下正确转发 WebSocket。
