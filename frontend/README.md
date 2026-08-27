# LegalIA Frontend

Frontend moderno y profesional para LegalIA, construido con React + TypeScript + Vite.

## Características

- **Autenticación**: Login y registro integrados con el backend FastAPI
- **Chat en tiempo real**: Interfaz conversacional intuitiva
- **Markdown**: Soporte completo para respuestas formateadas
- **Metadatos de verificación**: Visualización del estado de verificación y métricas de retrieval
- **Diseño moderno**: Tema oscuro profesional con gradientes amber
- **Responsive**: Funciona perfectamente en desktop y móvil
- **Sin dependencias pesadas**: Stack mínimo y rápido

## Desarrollo local

### Prerrequisitos

- Node.js 20+
- Backend de LegalIA corriendo en `http://localhost:8000`

### Instalación

```bash
cd frontend
npm install
```

### Ejecutar en modo desarrollo

```bash
npm run dev
```

El frontend estará disponible en `http://localhost:3000` con hot-reload automático.

### Build para producción

```bash
npm run build
```

Los archivos optimizados se generan en `frontend/dist/`.

### Preview del build

```bash
npm run preview
```

## Arquitectura

```
frontend/
├── src/
│   ├── components/
│   │   ├── Auth.tsx          # Pantalla de login/registro
│   │   ├── Auth.css
│   │   ├── Chat.tsx          # Interfaz principal de chat
│   │   └── Chat.css
│   ├── api.ts                # Cliente HTTP con refresh automático
│   ├── types.ts              # Tipos TypeScript
│   ├── App.tsx               # Componente raíz
│   ├── main.tsx              # Entry point
│   └── index.css             # Estilos globales
├── Dockerfile                # Build de producción con nginx
├── nginx.conf                # Configuración nginx para SPA
└── vite.config.ts            # Configuración Vite
```

## Características técnicas

### Autenticación

- JWT tokens almacenados en localStorage
- Refresh automático cuando el access token expira
- Verificación de sesión al cargar la app
- Logout limpio

### API Client

El cliente API (`api.ts`) maneja:

- Refresh automático de tokens
- Headers de autorización
- Manejo de errores tipado
- Proxy a través de Vite en desarrollo

### Componentes principales

**Auth**: Pantalla de autenticación con toggle entre login/registro.

**Chat**: Interfaz principal con:
- Lista de mensajes con scroll automático
- Input con soporte para Shift+Enter (nueva línea)
- Markdown rendering para respuestas del asistente
- Badges de metadata (verificación, chunks, etc.)
- Loading states con typing indicator
- Welcome screen con ejemplos

## Variables de entorno

No necesita variables de entorno. El proxy se configura en `vite.config.ts`:

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

En producción, nginx hace el proxy interno al contenedor `legalia-api:8000`.

## Docker

El Dockerfile usa build multi-stage:

1. **Builder**: instala deps y ejecuta `npm run build`
2. **Runtime**: nginx alpine con los archivos estáticos

El contenedor expone el puerto 80 y nginx hace proxy de `/api` al backend.

## Paleta de colores

Tema oscado profesional con accent amber:

- Background: `#0F1117` (slate-950)
- Cards: `#171A23` (slate-900)
- Borders: `#1E222E` (slate-800)
- Accent: `#F59E0B` → `#D97706` (amber gradient)
- Text: `#F3F4F6` (slate-100)
- Muted: `#6B7280` (slate-500)

## Stack tecnológico

- **React 18**: Framework UI
- **TypeScript**: Type safety
- **Vite**: Build tool y dev server
- **React Markdown**: Rendering de markdown
- **Nginx**: Servidor estático en producción
- **CSS nativo**: Sin frameworks CSS pesados

## Principios de diseño

- **Mínimo y rápido**: sin dependencias innecesarias
- **Type-safe**: TypeScript estricto
- **Accesible**: HTML semántico y ARIA labels
- **Responsive**: mobile-first con breakpoints
- **Professional**: diseño limpio y moderno para uso legal
