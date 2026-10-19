# 🩺 GitDoctor AI — Suite Clínica, Gobernanza y Salud de Repositorios Git

**GitDoctor** (`gitdoctor` / `gitdoc`) es la suite clínica y asistente DevOps integral que audita la salud de tus repositorios, previene fuga de secretos, implementa buenas prácticas como Gitflow, sincroniza código en paralelo y asiste a desarrolladores entre múltiples equipos (**Windows, macOS y Linux**).

Diseñado con un enfoque agnóstico y profesional:
* **Multi-IA:** Funciona tanto con **Google Gemini Cloud** como con **IA Local Privada y Offline** vía [Ollama](https://ollama.com) (cero fugas de código, 100% privado y sin límites de cuota).
* **Multi-Proveedor & Multi-Trabajo:** Soporta **GitHub, GitLab, Bitbucket y Azure DevOps**, permitiendo identidades de Git separadas (nombre y correo corporativo vs personal) por cada organización.
* **Onboarding Inteligente:** Diagnostica carpetas preexistentes en tu disco y te ayuda a organizarlas en la arquitectura oficial sin desorden.

---

## 🛠️ Comandos Globales de Terminal

Una vez instalado, tienes disponibles los comandos desde cualquier terminal:

| Comando | Alias Corto | Descripción |
| :--- | :---: | :--- |
| `gitdoctor` | `gitdoc` | Abre la consola clínica interactiva con IA y herramientas DevOps. |
| `gitdoctor /catalogo` | `gitdoc /boveda` | **Bóveda Privada (Gist Secreto):** Sincroniza tu catálogo confidencial entre Windows y Mac. |
| `gitdoctor /salud 360` | `gitdoc /seguridad` | **Auditoría de Salud 360°:** Secretos, API keys, Gitflow, higiene e integridad. |
| `gitdoctor /gitflow` | `gitdoc /gitflow` | Audita y crea la rama `develop` para estructurar Gitflow en tus repositorios. |
| `gitdoctor /ia` | `gitdoc /ia` | Alterna entre IA Local Offline (Ollama) y Nube (Gemini Cloud). |
| `gitdoctor /perfiles` | `gitdoc /perfiles` | Configura identidades de commit (trabajo vs personal) por organización. |
| `gitdoctor --sync` | `reposync` | Sincronización ultrarrápida multihilo con pull lineal (`--ff-only`). |

---

## 📂 ¿Cómo está estructurado?

GitDoctor organiza automáticamente el código por **Organización o Grupo**, garantizando cero repositorios de código sueltos en la raíz:

```text
<Tu_Carpeta_De_Proyectos>/         <-- (Ej. D:\Repos, C:\Proyectos, ~/Developer, ~/Repos)
|
+-- gitdoctor/                     <-- NÚCLEO DE GITDOCTOR (Únicamente en la raíz, fuera de toda org)
|   +-- agent.py                   <-- Consola clínica GitDoctor AI y motor multihilo
|   +-- onboarding.py              <-- Asistente de diagnóstico y reorganización inicial
|   +-- repos.json                 <-- Catálogo público / plantilla de ejemplo
|   +-- repos.local.json           <-- (Privado) Catálogo maestro de tus repositorios reales
|   +-- config.local.json          <-- (Privado) Configuración local y motor de IA
|   +-- sync.ps1 / sync.sh         <-- Motores de sincronización paralela y auto-reajuste
|   +-- setup-windows.bat/.ps1     <-- Instalador y configurador para Windows
|   +-- setup-mac.sh               <-- Instalador y configurador para macOS
|   +-- docs/                      <-- Documentación y planes de evolución
|   +-- run-*.bat / .command       <-- Lanzadores directos
|
+-- Personal/                      <-- Proyectos personales y herramientas
|   +-- mi-libreria/
|   +-- web-app/
|
+-- organizacion-1/                <-- Repositorios de tu empresa / trabajo principal
|   +-- proyecto-a/
|   +-- proyecto-b/
|
+-- organizacion-2/                <-- Repositorios de clientes o agencia
    +-- proyecto-c/
```

> **Regla de Gobernanza:** GitDoctor reside **exclusivamente en la raíz** de tu carpeta principal de proyectos para evitar dependencias circulares, conflictos de sincronización o duplicados fantasma. Todos los proyectos de desarrollo se distribuyen dentro de sus respectivas organizaciones oficiales.
>
> 💡 **Libertad Total de Unidad y Ruta:** Puedes crear y designar tu carpeta raíz de proyectos donde prefieras (`D:\Repos`, `C:\Proyectos`, `E:\Workspace`, `~/Developer`, `~/Repos`, etc.). GitDoctor detecta automáticamente su ubicación relativa respecto a su carpeta contenedora y la almacena en `config.local.json`. Si en cualquier momento deseas mover o redefinir tu raíz, puedes usar el comando interactivo `gitdoctor /dir [nueva_ruta]`.

---

## ⚡ Instalación Inicial (1-Clic)

Elige la carpeta raíz donde deseas tener tus proyectos (en cualquier unidad o ruta, ej: `D:\Repos`, `C:\Proyectos`, `~/Developer`, `~/Repos`) y clona GitDoctor **directamente en esa raíz**:

### En Windows (PC)
1. Abre tu terminal (PowerShell o CMD) en tu carpeta de repositorios (ej: `D:\Repos` o `C:\Proyectos`):
   ```cmd
   git clone https://github.com/davidmmora/gitdoctor.git gitdoctor
   cd gitdoctor
   setup-windows.bat
   ```

### En macOS (Mac)
1. Abre la Terminal en tu carpeta de repositorios (ej: `~/Repos` o `~/Developer`):
   ```bash
   git clone https://github.com/davidmmora/gitdoctor.git gitdoctor
   cd gitdoctor
   bash setup-mac.sh
   ```

*(El instalador configurará automáticamente los comandos globales en tu terminal, creará los 5 accesos directos en tu Escritorio y calibrará las rutas de tus repositorios).*

---

## 🔒 Privacidad y Auto-Reajuste Transparente

* **Catálogo Público vs Privado:**  
  * `repos.json` contiene únicamente plantillas de ejemplo genéricas, permitiendo que GitDoctor sea público y colaborativo.  
  * `repos.local.json` almacena de forma privada y local el inventario de todos tus repositorios y clientes reales, protegido por `.gitignore`.
* **Auto-Reajuste Silencioso (Self-Healing):**  
  Cada vez que ejecutas `sync.sh` o `sync.ps1` (o mediante el alias `reposync`), GitDoctor descarga automáticamente las últimas actualizaciones con `git pull --ff-only` y reajusta permisos, accesos directos del Escritorio y comandos globales en tu terminal sin requerir ninguna reinstalación manual.

---

## 🖥️ 5 Accesos Directos de Escritorio (Windows & Mac)

Al finalizar la instalación, se crearán automáticamente **5 accesos directos listos en tu Escritorio** para operar con doble clic:

| Acceso Directo (Windows / Mac) | Icono | Función |
| :--- | :---: | :--- |
| **GitDoctor - Consola & IA** | 🩺 | Abre la consola clínica GitDoctor AI con motor antierrores y soporte multi-IA. |
| **GitDoctor - Salud 360** | 🛡️ | Ejecuta el escáner completo de seguridad, secretos, Gitflow e higiene. |
| **GitDoctor - Sincronizar** | 🔄 | Sincroniza y descarga actualizaciones en paralelo con `git pull --ff-only`. |
| **GitDoctor - Vigilante** | 👁️ | Inicia el monitoreo continuo en segundo plano con **notificaciones nativas**. |
| **GitDoctor - Salida Segura** | 🛫 | Auditoría pre-flight de 2 segundos antes de apagar; sube tus commits automáticamente. |

---

## 🛡️ Capacidades Clínicas de GitDoctor AI

### 1. 🚨 Escáner de Fuga de Secretos y API Keys
Detecta credenciales comprometidas antes de que toquen GitHub:
* Google / Gemini API Keys (`AIzaSy...`)
* OpenAI Keys (`sk-...`, `sk-proj-...`)
* AWS Keys (`AKIA...`)
* GitHub Personal Access Tokens (`ghp_...`, `github_pat_...`)
* Archivos `.env` rastreados en Git o presentes sin regla en `.gitignore`.
* Certificados o llaves privadas (`.pem`, `.key`, `id_rsa`).

### 2. 🌿 Estrategia de Ramas Gitflow Asistida (`/gitflow`)
* Identifica proyectos que solo tienen rama `main`/`master` plana.
* Te permite crear la rama `develop`, subirla a GitHub y dejarla como rama de trabajo activa con un solo Enter.

### 3. 🧠 Motor Multi-IA: Nube + IA Local Privada (`/ia`)
* **Google Gemini Cloud:** Inferencia conversacional con Function Calling.
* **Ollama Local Offline:** Detección automática en `localhost:11434`. Cero fugas de código, 100% privado y sin límites de cuota por minuto.

### 4. 👥 Gestión Multi-Trabajo y Multi-Proveedor (`/perfiles`)
* Configura identidades de commit independientes (`user.name` y `user.email`) para cada organización o cliente, asegurando que nunca envíes un commit corporativo con tu correo personal ni viceversa.
* Detección de remotos GitHub, GitLab, Bitbucket y Azure DevOps.
* Si aceptas con **Enter**, lo descarga inmediatamente en la carpeta correcta y lo registra en tu catálogo.

### 2. ⚡ Diagnóstico de Salud Ultra-Rápido (~1 segundo)
Audita el estado de todos tus repositorios en paralelo con multihilo (`ThreadPoolExecutor`). Te muestra un puntaje visual de salud (`[Salud: 98%]`) identificando proyectos limpios, con cambios sin commit o pendientes de push.

### 3. 🎯 Motor Antierrores y Autocorrector de Comandos
* **Sin barra `/` obligatoria:** Puedes escribir `salud`, `code amps`, `sync`, `push`, `limpiar`, `disco`, `apagar` sin necesidad de poner la barra.
* **Autocorrección difusa de typos:** Si te equivocas al escribir (ej. `/saldu`, `/synk`, `/clonn`), el agente detecta lo que querías decir, te sugiere la corrección y la ejecuta con solo pulsar Enter.
* **Guía interactiva:** Si olvidas escribir el nombre del proyecto al usar `code` o `clone`, el asistente te pregunta amigablemente en lugar de arrojar un error de sintaxis.

### 4. 💻 Apertura Directa en Visual Studio Code (`code <repo>`)
Escribe `code <nombre>` o `abrir <nombre>`. El agente busca el repositorio por coincidencia difusa y lo abre al instante en VS Code. Si el proyecto aún no está clonado en ese equipo, te ofrece descargarlo y abrirlo en un solo paso.

### 5. 🛡️ Modo Vigilante con Notificaciones Nativas del SO
Al escribir `vigilante`, el agente monitorea en bucle tus carpetas mientras programas. Si detecta archivos modificados sin guardar o commits pendientes de subir, emite una **notificación nativa del sistema operativo**:
* **En Windows:** Notificación Toast nativa en la bandeja del sistema.
* **En macOS:** Notificación en el Centro de Notificaciones de Mac.
* **En Linux:** Notificación de escritorio vía `notify-send`.

### 6. 🧹 Higiene y Limpieza Automática (`limpiar`)
Detecta archivos de caché no deseados (`.firebase/`, `.DS_Store`, `Thumbs.db`, `.vscode/`, `*.log`), los retira del seguimiento de Git sin borrarlos del disco, agrega las reglas a su `.gitignore` local y crea el commit de limpieza.

### 7. 💽 Gestor de Espacio en Disco (`disco` o `prune`)
Analiza carpetas pesadas regenerables (`node_modules`, `.next`, `dist`, `build`, `.venv`, `.cache`) en todos tus repositorios y te permite purgarlas con confirmación previa para liberar decenas de gigabytes en equipos livianos.

### 8. 🛫 Pre-Flight Check de Salida Segura (`apagar`)
Antes de apagar el equipo o cambiar de máquina, escribe `apagar`. Audita que todo esté en orden y te ofrece subir los commits pendientes a GitHub para que puedas cerrar sesión con 100% de tranquilidad.

### 9. 🤖 Chat Conversacional con Gemini AI (Copiloto Protector)
Si tienes configurada tu `GEMINI_API_KEY` (configúrala fácilmente escribiendo `/set-key`), puedes hablar con el guardián en lenguaje natural (incluso con modismos, abreviaturas o faltas de ortografía):
* **Auto-Descubrimiento Dinámico de Modelos:** Consulta en tiempo real los modelos disponibles en la API de Google (priorizando `gemini-3.8-flash`, `gemini-3.5-flash`, etc.) adaptándose automáticamente a cambios de versión o lanzamientos futuros de Google sin romperse.
* **Function Calling Bidireccional:** La IA no solo responde dudas, sino que ejecuta acciones reales en tu computadora (`check_health`, `clean_hygiene`, `open_in_vscode`, `clone_repo_or_org`, etc.) y te explica el resultado en español claro.
* **Ejemplos de interacción:**
  * *"¿Cómo está la salud de mis proyectos?"*
  * *"Abre el proyecto mi-proyecto en VS Code"*
  * *"Limpia los archivos de caché de Firebase"*
  * *"Sube mis cambios pendientes a GitHub"*
  * *"Descarga el repositorio tal"*

---

## 📋 Tabla de Referencia de Comandos

Todos los comandos se pueden escribir con barra (`/comando`) o sin barra (`comando`), y en minúsculas o mayúsculas:

| Comando | Sinónimos aceptados | Qué hace | Ejemplo |
| :--- | :--- | :--- | :--- |
| **`/code`** | `code`, `abrir`, `vscode` | Abre un repositorio en Visual Studio Code | `code mi-proyecto` |
| **`/salud`** | `salud`, `status`, `estado` | Auditoría de salud local en ~1 segundo | `salud` o `salud fetch` |
| **`/sync`** | `sync`, `sincronizar`, `pull` | Descarga cambios remotos lineales (`--ff-only`) | `sync` o `sync mi-organizacion` |
| **`/push`** | `push`, `subir` | Sube a GitHub los commits locales pendientes | `push` |
| **`/commit`** | `commit`, `guardar` | Crea commit y push de un proyecto específico | `/commit mi-proyecto feat: nuevo feature` |
| **`/orgs`** | `orgs`, `organizaciones` | Activa/desactiva organizaciones en este equipo | `orgs` |
| **`/nuevos`** | `nuevos`, `check-github` | Detecta repos creados por colegas en GitHub | `nuevos` |
| **`/clone`** | `clone`, `clonar`, `descargar` | Descarga bajo demanda un repo u organización | `clone mi-libreria` |
| **`/disponibles`** | `disponibles`, `faltantes` | Lista repositorios que aún no tienes clonados | `disponibles` |
| **`/limpiar`** | `limpiar`, `clean`, `higiene` | Limpia archivos de caché/logs y actualiza `.gitignore` | `limpiar` |
| **`/disco`** | `disco`, `prune`, `espacio` | Analiza y purga carpetas pesadas (`node_modules`, etc.) | `disco` |
| **`/apagar`** | `apagar`, `checkout`, `salida` | Auditoría de salida segura antes de apagar o salir | `apagar` |
| **`/vigilante`** | `vigilante`, `watchdog` | Monitoreo en bucle con notificaciones nativas | `vigilante 300` |
| **`/github`** | `github`, `gh`, `perfil` | Ver usuario activo, cuentas guardadas y organizaciones | `github` |
| **`/login`** | `login`, `auth` | Inicia sesión con cualquier cuenta de GitHub | `login` |
| **`/switch`** | `switch`, `cambiar-cuenta` | Cambia entre cuentas de GitHub guardadas en el equipo | `switch` |
| **`/logout`** | `logout`, `desconectar` | Cierra sesión de una cuenta de GitHub | `logout` |
| **`/git-id`** | `git-id`, `identidad` | Configura `user.name` y `user.email` para Git | `git-id "Juan Perez" juan@empresa.com` |
| **`/dir`** | `dir`, `carpeta` | Ver o cambiar la carpeta raíz de repositorios | `dir D:\MisProyectos` |
| **`/catalogo`**| `catalogo`, `boveda`, `vault` | Sincroniza tu catálogo privado vía GitHub Gist Secreto | `/catalogo push` o `/catalogo pull` |
| **`/importar-github`**| `mis-repos`, `descubrir` | Descarga todos tus repos de GitHub a tu catálogo personal | `mis-repos` |
| **`/set-key`** | `set-key`, `key` | Configura tu API Key privada de Gemini AI | `set-key` |
| **`/ayuda`** | `ayuda`, `help` | Muestra la guía interactiva en consola | `ayuda` |
| **`/salir`** | `salir`, `exit`, `quit` | Cierra el asistente | `salir` |

---

## 🔒 Seguridad y Privacidad Garantizadas

* **Claves Privadas Protegidas:** Tu `GEMINI_API_KEY` se guarda de forma local y privada en `.env`. Este archivo está estrictamente ignorado por Git en `.gitignore`.
* **Configuración por Máquina Aislada:** `config.local.json` y `repos.local.json` están excluidos de Git para que cada máquina conserve sus propias carpetas, organizaciones y proyectos sin generar conflictos entre desarrolladores.
* **Cero Fugas:** En pantalla las claves siempre se ofuscan (`AIza...****`) y los mensajes de error limpian cualquier token antes de imprimirse.
* **Modo Offline:** Si no tienes API Key de Gemini o estás sin internet, todo el sistema opera al 100% en modo local con los comandos rápidos.

---

## 📖 Documentación Adicional
* Registro histórico de cambios y roadmap de arquitectura: [docs/PLAN_Y_HISTORIAL.md](./docs/PLAN_Y_HISTORIAL.md)
