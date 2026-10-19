# GitDoctor — Instrucciones para Copilot (Workspace & Agent Rules)

Este repositorio (`davidmmora/gitdoctor`, antes `repos-sync`) es el núcleo de diagnóstico clínico, salud, gobernanza y gestión multi-máquina de los proyectos de desarrollo de David M Mora.

---

## 🏗️ Arquitectura del Entorno

La estructura de carpetas es **completamente agnóstica de la unidad de disco y del nombre de la carpeta base**: el usuario designa libremente su carpeta raíz de proyectos donde prefiera (por ejemplo: `D:\Repos`, `C:\Proyectos`, `E:\Workspace` en Windows; o `~/Repos`, `~/Developer`, `~/Proyectos` en macOS/Linux). A esta carpeta contenedora la denominamos `<CarpetaRaiz>`.

* **Estructura en Windows (PC):** `<CarpetaRaiz>\<organizacion>\<nombre-del-repo>`
* **Estructura en macOS / Linux:** `<CarpetaRaiz>/<organizacion>/<nombre-del-repo>`

### 🩺 Ubicación de GitDoctor (Regla Estricta):
* GitDoctor (`davidmmora/gitdoctor`) reside **ÚNICA Y EXCLUSIVAMENTE en la raíz designada**:
  * `<CarpetaRaiz>/gitdoctor` (por ejemplo `D:\Repos\gitdoctor`, `C:\Proyectos\gitdoctor`, `~/Repos/gitdoctor` o `~/Developer/gitdoctor`).
* **NUNCA** clonar, mover ni ubicar GitDoctor dentro de `Personal` ni de ninguna de las 10 organizaciones. Está fuera de cualquier organización para evitar conflictos de gobernanza, dependencias circulares y duplicados. GitDoctor es el **único** repositorio permitido directamente en la raíz de `<CarpetaRaiz>`.

### 🏢 Las 10 Organizaciones Oficiales (para repositorios de proyectos):
1. `th-mex`: Proyectos empresariales y sistemas de THMEX.
2. `w-amarillo`: Proyectos de clientes y marcas (Omron, Festivales, Mabe, Nestlé, etc.).
3. `w-azul`: Plataformas internas, portales de clientes y sincronizadores.
4. `w-naranja`: Herramientas de telefonía y tareas (Smartsheets, Vicidial, etc.).
5. `interpec`: Aplicaciones avícolas y agropecuarias (Sabro, Aliamsa, etc.).
6. `w-pluma`: Sistemas avícolas (Sabropollo, Sabrohuevo, etc.).
7. `w-ic`: Servicios de sincronización (IcafSyncService).
8. `bf-agency`: Proyectos de BF Agency (w-tm).
9. `WeHubs-io`: Plataforma WeHubs (wehubs, Dixie, insta-photo).
10. `Personal`: Proyectos personales de David M Mora (`TranscriptAudio`, `pelusa`, `uveg`, etc.).

---

## ⚙️ Reglas para el Asistente

Cuando el usuario pida ayuda para crear, organizar o sincronizar proyectos:

1. **Ubicación estricta de GitDoctor:**
   * GitDoctor debe permanecer siempre en la raíz designada (`<CarpetaRaiz>/gitdoctor`).
   * Jamás moverlo o recrearlo dentro de `Personal/gitdoctor` ni en ninguna subcarpeta de organización.
2. **Estructura estricta para proyectos del catálogo:**
   * NUNCA crear o clonar proyectos normales/de código sueltos en la raíz de `<CarpetaRaiz>` (únicamente GitDoctor tiene permiso de estar en la raíz).
   * Todo proyecto de desarrollo debe pertenecer a una de las 10 organizaciones oficiales (`<CarpetaRaiz>/<organizacion>/<nombre-del-repo>`).
3. **Catálogo Maestro y Bóveda Privada (`repos.json` vs `repos.local.json`):**
   * `repos.json` en el repositorio público contiene **únicamente plantillas genéricas** para proteger la privacidad del usuario.
   * El inventario real y confidencial de clientes y proyectos vive en `repos.local.json` (ignorado por `.gitignore`).
   * Para sincronizar el catálogo confidencial entre múltiples máquinas (Windows y macOS) sin exponerlo en GitHub, se usa la **Bóveda Privada en GitHub Gist Secreto** (`gitdoctor /catalogo push` y `gitdoctor /catalogo pull`).
   * **NUNCA** commitear repositorios reales de clientes a `repos.json`.
4. **Repositorios en GitHub / GitLab / Multi-Proveedor:**
   * Al crear un nuevo repositorio, usar siempre GitHub CLI (`gh repo create <org>/<nombre> --private --source=<path> --remote=origin --push`).
5. **Comandos Oficiales del Ecosistema:**
   * `gitdoctor` (o `gitdoc`): Consola clínica con asistente IA, auditoría de Salud 360°, seguridad y Gitflow.
   * `gitdoctor /catalogo`: Gestiona la Bóveda Privada (Gist Secreto) para sincronizar repositorios entre Windows y Mac.
   * `gitdoctor /salud 360` (o `gitdoc /seguridad`): Diagnóstico profundo de secretos, llaves de API y ramas.
   * `gitdoctor /gitflow`: Audita e implementa la estrategia de ramas `develop`.
   * `gitdoctor /ia`: Alterna entre IA local offline (Ollama) y nube (Gemini).
   * `gitdoctor /perfiles`: Gestiona identidades Git (trabajo vs personal) por organización.
   * `gitdoctor --sync` (o alias `reposync`): Comprueba estado y descarga cambios limpios (`--ff-only`) en todos los repositorios.
6. **Seguridad:**
   * NUNCA subir archivos `.env` ni claves de API (como `GEMINI_API_KEY`) al repositorio.
   * Mantener siempre `.gitignore` actualizado.
