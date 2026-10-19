# 📋 RepoSync Guardian — Historial de Cambios y Plan de Evolución

Este documento registra la evolución del ecosistema **RepoSync**, el trabajo completado hasta la fecha y el plan de desarrollo para convertirlo en una herramienta colaborativa, selectiva y con monitoreo nativo en segundo plano.

---

## 📌 1. Visión y Estado Actual del Proyecto

GitDoctor es el núcleo de gestión, auditoría y sincronización de repositorios de desarrollo para entornos multi-equipo en Windows, macOS y Linux, agnóstico de la unidad de disco o ruta base elegida por el usuario (ej. `D:\Repos`, `C:\Proyectos`, `~/Developer`, `~/Repos`).

### 🏛️ Componentes Principales:
* **Catálogo Maestro (`repos.json`):** Inventario con 106 repositorios distribuidos originalmente en 10 organizaciones.
* **Motores de Sincronización:** `sync.ps1` (Windows) y `sync.sh` (macOS / Linux) con soporte de pull lineal (`--ff-only`) y clonación automática.
* **Instaladores y Lanzadores 1-Clic:** `setup-windows.ps1` / `.bat` y `setup-mac.sh` / `.command`, con generación automática de accesos directos en el Escritorio.
* **Auditoría y Reconciliación Inteligente (`reconcile.py`):** Previene pérdidas de código local y detecta carpetas renombradas para evitar descargas dobles.
* **RepoSync Guardian AI (`agent.py`):** Asistente conversacional con Gemini AI y herramientas CLI directas.

---

## ⏱️ 2. Historial de Trabajo Completado

### ✅ Hito 1: Optimización de Rendimiento Multihilo
* **Problema:** Auditar 106 repositorios uno por uno demoraba entre 35 y 45 segundos por el coste de invocar Git secuencialmente.
* **Solución:** Se implementó paralelización con `ThreadPoolExecutor` en Python y una única consulta combinada `git status -b --porcelain`.
* **Resultado:** El escaneo completo de los 106 repositorios se redujo a **~1.05 segundos**.

### ✅ Hito 2: Módulo de Higiene y Limpieza Automática (`/limpiar`)
* **Problema:** Archivos temporales y cachés de compilación (como `.firebase/`, logs de VS Code `vsce-debug.log`, `.vscode/`, `.DS_Store`) ensuciaban el estado de Git en varios repositorios.
* **Solución:** Función `clean_repo_hygiene()` que:
  1. Desvincula los archivos basura del índice de Git (`git rm --cached`) sin eliminarlos físicamente del disco.
  2. Inyecta automáticamente las reglas de exclusión al `.gitignore` local de cada proyecto.
  3. Registra el commit de limpieza con el trailer oficial de Copilot.
* **Resultado:** La salud del ecosistema subió de **95.3% a 98.1%** de manera instantánea.

### ✅ Hito 3: Seguridad Estricta de la API Key de Gemini
* **Problema:** Riesgo de filtración de claves privadas de Gemini en repositorios Git compartidos.
* **Solución:**
  1. Almacenamiento local aislado en `_sync/.env` (restringido por `.gitignore`).
  2. Entrada protegida con `getpass` para que no se muestre en pantalla.
  3. Visualización enmascarada (`AIza...****`).
  4. Modo Offline funcional al 100% si no hay clave configurada.
  5. Comando `/set-key` para actualizar la clave en cualquier momento.

### ✅ Hito 4: Soporte Multi-Cuenta de GitHub y Modo Colaborativo
* **Problema:** El sistema estaba acoplado a un solo usuario y organizaciones rígidas, dificultando su uso compartido con colegas.
* **Solución:**
  1. Integración con GitHub CLI (`gh`): Comandos `/login`, `/switch`, `/logout`, `/github` y `/git-id`.
  2. Detección dinámica de organizaciones (`gh api user/orgs`): Cualquier colega que inicie sesión ve automáticamente sus propias organizaciones y repositorios.
  3. Sincronización de identidad de Git (`user.name` y `user.email`).

### ✅ Hito 5: Motor Antierrores y Asistencia Inteligente
* **Problema:** Los usuarios y colegas pueden cometer faltas de ortografía, olvidar la barra `/` inicial, equivocarse de comando o no pasar los argumentos necesarios (ej: `salud`, `code proyecto`, `/synk`, `/saldu`, `/clonn`).
* **Solución:**
  1. **Comandos sin barra obligatoria:** Reconoce comandos naturales como `salud`, `sync`, `push`, `limpiar`, `code <repo>`, `disco`, `apagar` sin obligar a escribir `/`.
  2. **Corrector difuso interactivo:** Si se escribe un comando con error tipográfico (ej. `/saldu`), sugiere automáticamente la corrección (`¿Quisiste decir '/salud'?`) y permite ejecutarlo pulsando Enter.
  3. **Manejo amigable de argumentos:** Si se omite el argumento en `/code` o `/clone`, el agente pregunta de forma conversacional el nombre en lugar de fallar.
  4. **Copiloto Protector con Gemini AI:** Prompting antierrores que interpreta lenguaje coloquial, faltas ortográficas y previene pérdida de datos en ramas divergentes o conflictos.

---

## 🗺️ 3. Plan de Evolución (Nuevas Funcionalidades Solicitadas)

A continuación se detalla el plan de implementación para las nuevas capacidades requeridas:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          PLAN DE EVOLUCIÓN                             │
├────────────────────────────────────────────────────────────────────────┤
│ Fase 1: Sincronización Selectiva por Equipo (config.local.json)        │
│ Fase 2: Apertura Directa en VS Code (/code <repo>)                     │
│ Fase 3: Modo Vigilante Daemon con Notificaciones Nativas del SO        │
│ Fase 4: Gestor de Espacio en Disco & Prune de Dependencias             │
│ Fase 5: Buscador Difuso y Pre-Flight Check de Salida Segura            │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 🔹 Fase 1: Sincronización Selectiva por Equipo (`config.local.json`)
* **Objetivo:** Permitir que cada equipo (ej. una laptop liviana con disco SSD pequeño vs. una PC de escritorio con 2TB) sincronice únicamente las organizaciones que necesita.
* **Diseño Técnico:**
  * Crear archivo de configuración por máquina: `_sync/config.local.json` (ignorado por Git).
  * Estructura:
    ```json
    {
      "machine_name": "Laptop-MacBook",
      "enabled_orgs": ["Personal", "organizacion-1"],
      "disabled_orgs": ["organizacion-2", "organizacion-3"],
      "auto_clone_new": false
    }
    ```
  * **Comandos en el Agente:**
    * `/orgs`: Muestra las organizaciones activas y deshabilitadas en esta máquina con opción de activarlas/desactivarlas con un solo clic.
    * `/clone <repo>`: Permite descargar un repositorio puntual de una organización no sincronizada sin necesidad de clonar la organización entera.
    * `/sync <org>`: Sincroniza únicamente una organización específica.

---

### 🔹 Fase 2: Integración Directa con Visual Studio Code
* **Objetivo:** Abrir cualquier proyecto en VS Code al instante desde la terminal o mediante lenguaje natural.
* **Diseño Técnico:**
  * Búsqueda por coincidencia parcial: Si el usuario escribe `/code backend` o `/code web`, el agente resuelve `D:\Repos\organizacion-1\backend-api` o `D:\Repos\Personal\mi-web-personal`.
  * Invoca `code <ruta_absoluta>` en Windows o macOS.
  * Soporte conversacional con Gemini: *"Abre el proyecto insta-photo en VS Code"*.

---

### 🔹 Fase 3: Modo Vigilante Permanente con Notificaciones Nativas del SO
* **Objetivo:** Que el Vigilante pueda correr en segundo plano todo el tiempo y avisar mediante notificaciones del sistema operativo en lugar de solo imprimir en la consola.
* **Diseño Técnico:**
  * **Notificaciones en Windows:** Notificaciones Toast nativas del sistema operativo.
  * **Notificaciones en macOS:** Notificaciones nativas a través del Centro de Notificaciones con `osascript -e 'display notification ...'`.
  * **Notificaciones en Linux:** Integración con `notify-send`.
  * **Casos de Alerta del Vigilante:**
    * ⚠️ Alerta de Archivos Sucios: Si hay cambios sin commit tras X minutos de trabajo.
    * 🚀 Alerta de Commits Pendientes: Si tienes commits en local listos para subir a GitHub.
    * 📥 Alerta de Cambios Remotos: Si un colega subió código a la rama de trabajo.
  * Lanzadores dedicados en segundo plano para dejarlo activo sin molestar.

---

### 🔹 Fase 4: Gestor de Espacio en Disco & Prune de Dependencias (`/prune`)
* **Objetivo:** Liberar gigabytes de almacenamiento en laptops o equipos con almacenamiento reducido.
* **Diseño Técnico:**
  * Comando `/disco` o `/prune`:
    * Calcula el tamaño en disco de cada organización.
    * Identifica carpetas voluminosas regenerables (`node_modules`, `.next`, `dist`, `.venv`, `.cache`).
    * Ofrece eliminarlas de proyectos inactivos con un solo enter, liberando decenas de gigabytes sin perder una sola línea de código.

---

### 🔹 Fase 5: Buscador Difuso y Pre-Flight Check de Salida Segura
* **Objetivo:** Garantizar que nunca te vayas de tu máquina sin respaldar y facilitar la búsqueda de proyectos.
* **Diseño Técnico:**
  * `/buscar <término>`: Búsqueda difusa de proyectos por cliente, tecnología o nombre.
  * `/checkout` o `/apagar`: Rutina de 3 segundos antes de apagar el equipo:
    1. Audita el estado general.
    2. Si hay commits locales, te ofrece subirlos todos automáticamente.
    3. Si hay cambios sin guardar, te alerta con nombre y rama.
    4. Muestra: *"¡Todo en orden! Puedes apagar el equipo o cambiar a tu Mac con total seguridad."*

---

## 📌 4. Registro de Versiones

| Versión | Fecha | Resumen de Cambios |
| :--- | :--- | :--- |
| **v1.0** | 18-Oct-2026 | Catálogo inicial de 106 repositorios y scripts base Windows/Mac. |
| **v1.5** | 18-Oct-2026 | Reconciliación para Mac y prevención de pérdida de datos. |
| **v2.0** | 19-Oct-2026 | Creación de RepoSync Guardian AI con Gemini conversacional y multihilo. |
| **v2.5** | 19-Oct-2026 | Módulo multi-cuenta de GitHub (`/login`, `/switch`), organizaciones dinámicas e higiene automática. |
| **v2.6** | 19-Oct-2026 | Resiliencia de Gemini AI: filtro anti-omni, detección de 429 Rate Limit, comando `/helpme` y cuenta regresiva de reposo interactiva. |
| **v3.0** | 19-Oct-2026 | Asistente de Onboarding Pre-Instalación (`onboarding.py`), Auditoría de Salud 360° con escáner de secretos/API keys y módulo interactivo de Gitflow (`/gitflow`). |
| **v3.5** | 19-Oct-2026 | **Evolución a GitDoctor:** Comandos CLI `gitdoctor` / `gitdoc`, Motor Multi-IA (Ollama Local Offline + Gemini Cloud), soporte Multi-Trabajo y Multi-Proveedor (GitHub, GitLab, Bitbucket, Azure). |
| **v3.6** | 19-Oct-2026 | **Regla Estricta de Ubicación:** Se establece como política inquebrantable que GitDoctor reside única y exclusivamente en la raíz (`~/Repos/gitdoctor` o `D:\Repos\gitdoctor`), fuera de toda organización. Limpieza automática de duplicados y blindaje de comandos globales. |
| **v3.7** | 19-Oct-2026 | **Bóveda Privada de Catálogo Multi-Equipo:** Sincronización confidencial de `repos.local.json` entre Windows y Mac mediante GitHub Gist Secreto (`/catalogo push`, `/catalogo pull`, `/catalogo status`). Zero fugas en el repositorio público y sincronización automática. |
| **v3.8** | 19-Oct-2026 | **Instalador Interactivo Universal y Blindaje de GitDoctor:** Asistente interactivo en `onboarding.py` para macOS y Windows. Conexión dinámica a GitHub para descubrir organizaciones y repositorios reales del usuario. Selección del alcance de descarga (descargar todo vs organizaciones selectivas vs catálogo bajo demanda). Eliminación total de borrado destructivo de carpetas de GitDoctor. Normalización del nombre canónico `gitdoctor` y resiliencia total de rutas. |
