import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/route': 'http://localhost:8000',
            '/traffic': 'http://localhost:8000',
            '/graph': 'http://localhost:8000',
            '/compare': 'http://localhost:8000',
            '/simulation': 'http://localhost:8000',
            '/active-route': 'http://localhost:8000',
            '/dispatch': 'http://localhost:8000',
            '/updates': {
                target: 'ws://localhost:8000',
                ws: true,
            },
        },
    },
});
