# GitDoctor — Instrucciones para Copilot (Workspace & Agent Rules)

Este repositorio (`davidmmora/gitdoctor`, antes `repos-sync`) es el núcleo de diagnóstico clínico, salud, gobernanza y gestión multi-máquina de los proyectos de desarrollo de David M Mora.

---

## 🏗️ Arquitectura del Entorno

Los proyectos están distribuidos en dos sistemas operativos:
* **En Windows (PC):** `D:\Repos\<organizacion>\<nombre-del-repo>`
* **En macOS:** `~/Repos/<organizacion>/<nombre-del-repo>`

### 🏢 Las 10 Organizaciones Oficiales:
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

1. **Estructura estricta:**
   * NUNCA crear o clonar proyectos sueltos en la raíz de `D:\Repos` o `~/Repos`.
   * Todo proyecto debe pertenecer a una de las 10 organizaciones oficiales (`D:\Repos\<organizacion>\<nombre-del-repo>`).
2. **Catálogo Maestro (`repos.json`):**
   * Cada vez que se agregue o modifique un repositorio, debe reflejarse en `_sync/repos.json` con su `name`, `group`, `path`, `url` y `defaultBranch`.
3. **Repositorios en GitHub / GitLab / Multi-Proveedor:**
   * Al crear un nuevo repositorio, usar siempre GitHub CLI (`gh repo create <org>/<nombre> --private --source=<path> --remote=origin --push`).
4. **Comandos Oficiales del Ecosistema:**
   * `gitdoctor` (o `gitdoc`): Consola clínica con asistente IA, auditoría de Salud 360°, seguridad y Gitflow.
   * `gitdoctor /salud 360` (o `gitdoc /seguridad`): Diagnóstico profundo de secretos, llaves de API y ramas.
   * `gitdoctor /gitflow`: Audita e implementa la estrategia de ramas `develop`.
   * `gitdoctor /ia`: Alterna entre IA local offline (Ollama) y nube (Gemini).
   * `gitdoctor /perfiles`: Gestiona identidades Git (trabajo vs personal) por organización.
   * `gitdoctor --sync` (o alias `reposync`): Comprueba estado y descarga cambios limpios (`--ff-only`) en todos los repositorios.
5. **Seguridad:**
   * NUNCA subir archivos `.env` ni claves de API (como `GEMINI_API_KEY`) al repositorio.
   * Mantener siempre `.gitignore` actualizado.
