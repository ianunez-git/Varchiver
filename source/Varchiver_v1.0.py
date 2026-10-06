from pathlib import Path
import subprocess
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import os
import json
import sys


# ============================================================
# VARIABLES GLOBALES
# ============================================================

videos_actuales = []
carpeta_actual = None

# Índices donde comienza una nueva partida.
# Ejemplo: {14} significa que el clip 15 inicia otra partida.
divisiones = set()

# Metadatos opcionales por partida.
# La clave es el índice del primer clip de cada partida.
metadatos_partidas = {}
variables_metadatos = {}

# Catálogo global de partidas procesadas.
# Se guarda junto al script para no depender de una carpeta concreta de Outplayed.
def directorio_aplicacion():
    """
    Carpeta persistente de Varchiver.

    - Desarrollo: carpeta del archivo .py.
    - Ejecutable PyInstaller: carpeta donde está Varchiver.exe.

    Los datos del usuario nunca se guardan dentro de _MEIPASS.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ARCHIVO_CATALOGO = directorio_aplicacion() / "valorant_archiver_catalogo.json"
catalogo_partidas = []

# ============================================================
# DETECCIÓN
# ============================================================

def obtener_fecha_hora(nombre):
    """
    Convierte un nombre de Outplayed como:

    Valorant_09-06-2026_23-59-8-0.mp4

    en un datetime:

    2026-09-06 23:59:08.000000

    Formato de Outplayed:
    MM-DD-YYYY_H-M-S-ms
    """

    patron = (
        r"^Valorant_"
        r"(\d{2})-(\d{2})-(\d{4})_"
        r"(\d+)-(\d+)-(\d+)-(\d+)$"
    )

    coincidencia = re.match(
        patron,
        Path(nombre).stem
    )

    if not coincidencia:
        return None

    mes, dia, anio, hora, minuto, segundo, milisegundo = map(
        int,
        coincidencia.groups()
    )

    try:
        return datetime(
            anio,
            mes,
            dia,
            hora,
            minuto,
            segundo,
            milisegundo * 1000
        )

    except ValueError:
        return None


def obtener_fecha(nombre):

    coincidencia = re.match(
        r"^Valorant_(\d{2})-(\d{2})-(\d{4})_",
        nombre
    )

    if not coincidencia:
        return "desconocida"

    mes, dia, anio = coincidencia.groups()

    return f"{dia}-{mes}-{anio}"


def analizar_carpeta(carpeta):

    carpeta = Path(carpeta)

    videos = []

    for archivo in carpeta.glob("*.mp4"):

        if obtener_fecha_hora(archivo.name) is not None:
            videos.append(archivo)

    videos.sort(
    key=lambda video: obtener_fecha_hora(video.name)
)

    return videos


# ============================================================
# FFMPEG / FFPROBE
# ============================================================

def obtener_duracion(video):

    resultado = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return float(
        resultado.stdout.strip()
    )


def unir_videos(videos, salida):

    lista_path = (
        videos[0].parent /
        "_valorant_archiver_lista.txt"
    )

    try:

        with lista_path.open(
            "w",
            encoding="utf-8"
        ) as archivo:

            for video in videos:

                ruta = (
                    video.resolve()
                    .as_posix()
                    .replace("'", "'\\''")
                )

                archivo.write(
                    f"file '{ruta}'\n"
                )

        comando = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(lista_path),
            "-c", "copy",
            str(salida)
        ]

        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True
        )

        if resultado.returncode != 0:

            raise RuntimeError(
                resultado.stderr[-1500:]
            )

    finally:

        if lista_path.exists():
            lista_path.unlink()


# ============================================================
# SUBTÍTULOS
# ============================================================

def tiempo_a_ms(tiempo):

    horas, minutos, resto = tiempo.split(":")

    segundos, milisegundos = (
        resto.split(",")
    )

    return (
        int(horas) * 3600000
        + int(minutos) * 60000
        + int(segundos) * 1000
        + int(milisegundos)
    )


def ms_a_tiempo(ms):

    ms = max(
        0,
        round(ms)
    )

    horas = ms // 3600000
    ms %= 3600000

    minutos = ms // 60000
    ms %= 60000

    segundos = ms // 1000
    milisegundos = ms % 1000

    return (
        f"{horas:02}:"
        f"{minutos:02}:"
        f"{segundos:02},"
        f"{milisegundos:03}"
    )


def leer_srt(
    ruta_srt,
    desplazamiento_ms
):

    contenido = ruta_srt.read_text(
        encoding="utf-8-sig",
        errors="replace"
    )

    patron = re.compile(
        r"(\d{2}:\d{2}:\d{2},\d{3})"
        r"\s*-->\s*"
        r"(\d{2}:\d{2}:\d{2},\d{3})"
        r"(?:[^\r\n]*)\r?\n"
        r"(.*?)(?=\r?\n\r?\n|\Z)",
        re.DOTALL
    )

    subtitulos = []

    for coincidencia in patron.finditer(
        contenido
    ):

        inicio = tiempo_a_ms(
            coincidencia.group(1)
        )

        fin = tiempo_a_ms(
            coincidencia.group(2)
        )

        texto = (
            coincidencia.group(3)
            .strip()
        )

        subtitulos.append(
            (
                inicio + desplazamiento_ms,
                fin + desplazamiento_ms,
                texto
            )
        )

    return subtitulos


def guardar_srt(
    subtitulos,
    salida
):

    with salida.open(
        "w",
        encoding="utf-8-sig",
        newline="\n"
    ) as archivo:

        for numero, (
            inicio,
            fin,
            texto
        ) in enumerate(
            subtitulos,
            start=1
        ):

            archivo.write(
                f"{numero}\n"
            )

            archivo.write(
                f"{ms_a_tiempo(inicio)} --> "
                f"{ms_a_tiempo(fin)}\n"
            )

            archivo.write(
                f"{texto}\n\n"
            )


# ============================================================
# PERSISTENCIA DE PROYECTO
# ============================================================

ARCHIVO_CONFIG = ".valorant_archiver.json"


def ruta_configuracion():
    if carpeta_actual is None:
        return None
    return carpeta_actual / ARCHIVO_CONFIG


def guardar_configuracion():
    """
    Guarda divisiones y metadatos de la carpeta actual.

    v0.9.2:
    - Conserva los índices antiguos por compatibilidad.
    - Guarda además el nombre del clip que inicia cada partida.
    - Guarda metadatos asociados al clip inicial, no solo a su índice.
    - Guarda una instantánea de los clips presentes al momento de guardar.

    De esta forma, si posteriormente se eliminan clips anteriores, las
    divisiones no se desplazan accidentalmente.
    """
    ruta = ruta_configuracion()

    if ruta is None or not videos_actuales:
        return

    inicios = obtener_inicios_partidas()

    datos = {
        "version": "1.0",
        # Compatibilidad con versiones anteriores.
        "divisiones": sorted(divisiones),
        "partidas": {},
        # Esquema robusto v0.9.2.
        "clips_guardados": [video.name for video in videos_actuales],
        "divisiones_clips": [
            videos_actuales[indice].name
            for indice in sorted(divisiones)
            if 0 <= indice < len(videos_actuales)
        ],
        "partidas_por_clip": {}
    }

    for inicio in inicios:
        meta = metadatos_partidas.get(
            inicio,
            {"mapa": "", "agente": ""}
        )

        meta_limpia = {
            "mapa": meta.get("mapa", ""),
            "agente": meta.get("agente", "")
        }

        # Formato antiguo.
        datos["partidas"][str(inicio)] = dict(meta_limpia)

        # Formato robusto: el metadato sigue al primer clip de la partida.
        if 0 <= inicio < len(videos_actuales):
            datos["partidas_por_clip"][videos_actuales[inicio].name] = dict(
                meta_limpia
            )

    temporal = ruta.with_suffix(".tmp")

    try:
        temporal.write_text(
            json.dumps(
                datos,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )
        temporal.replace(ruta)
    except OSError as error:
        # La persistencia no debe impedir usar Archiver, pero el fallo
        # no debe quedar completamente oculto durante diagnóstico.
        print(
            f"[Valorant Archiver] No se pudo guardar la configuración "
            f"de la carpeta: {error}"
        )
        try:
            if temporal.exists():
                temporal.unlink()
        except OSError:
            pass


def _inferir_organizacion_desde_catalogo():
    """
    Intenta reconstruir divisiones y metadatos usando clips_origen del catálogo.

    Es especialmente útil para migrar configuraciones antiguas basadas solo
    en índices cuando algunos clips ya fueron eliminados.
    """
    if not videos_actuales or "catalogo_partidas" not in globals():
        return None

    # clip resuelto -> registro de catálogo
    propietario = {}

    for partida in catalogo_partidas:
        for ruta in partida.get("clips_origen", []):
            if not ruta:
                continue
            try:
                clave = str(Path(ruta).resolve()).lower()
            except OSError:
                clave = str(Path(ruta)).lower()
            propietario[clave] = partida

    grupos = []
    ultimo_id = None
    inicio_actual = None
    partida_actual = None

    for indice, video in enumerate(videos_actuales):
        try:
            clave = str(video.resolve()).lower()
        except OSError:
            clave = str(video).lower()

        partida = propietario.get(clave)
        if partida is None:
            # Si no conocemos algún clip, no hacemos inferencias parciales.
            return None

        identidad = partida.get("id") or partida.get("ruta_video") or id(partida)

        if identidad != ultimo_id:
            if inicio_actual is not None:
                grupos.append((inicio_actual, partida_actual))
            inicio_actual = indice
            partida_actual = partida
            ultimo_id = identidad

    if inicio_actual is not None:
        grupos.append((inicio_actual, partida_actual))

    if not grupos:
        return None

    nuevas_divisiones = {inicio for inicio, _ in grupos if inicio > 0}
    nuevos_metadatos = {}

    for inicio, partida in grupos:
        nuevos_metadatos[inicio] = {
            "mapa": str(partida.get("mapa", "")),
            "agente": str(partida.get("agente", ""))
        }

    return nuevas_divisiones, nuevos_metadatos


def cargar_configuracion():
    """
    Restaura divisiones y metadatos si existe una configuración válida.

    v0.9.2 prioriza identidad de clips sobre posiciones numéricas.
    """
    ruta = ruta_configuracion()

    if ruta is None or not ruta.exists():
        return False

    try:
        datos = json.loads(
            ruta.read_text(encoding="utf-8")
        )

        nombres_actuales = [video.name for video in videos_actuales]
        indice_por_nombre = {
            nombre: indice
            for indice, nombre in enumerate(nombres_actuales)
        }

        # --------------------------------------------------------
        # Formato robusto v0.9.2: divisiones ligadas al clip inicial.
        # --------------------------------------------------------
        if isinstance(datos.get("divisiones_clips"), list):
            divisiones_validas = {
                indice_por_nombre[nombre]
                for nombre in datos.get("divisiones_clips", [])
                if nombre in indice_por_nombre
                and indice_por_nombre[nombre] > 0
            }

            metadatos_validos = {}
            partidas_por_clip = datos.get("partidas_por_clip", {})

            if isinstance(partidas_por_clip, dict):
                for nombre, meta in partidas_por_clip.items():
                    if nombre not in indice_por_nombre or not isinstance(meta, dict):
                        continue

                    inicio = indice_por_nombre[nombre]

                    # Solo conservar metadatos de inicios reales.
                    if inicio not in ({0} | divisiones_validas):
                        continue

                    metadatos_validos[inicio] = {
                        "mapa": str(meta.get("mapa", "")),
                        "agente": str(meta.get("agente", ""))
                    }

            # Caso importante: si desapareció toda una partida anterior,
            # el primer clip restante puede haber sido una antigua división.
            # Al quedar ahora en índice 0, pasa naturalmente a ser P1.
            primer_nombre = nombres_actuales[0] if nombres_actuales else None
            if (
                primer_nombre
                and isinstance(partidas_por_clip, dict)
                and primer_nombre in partidas_por_clip
                and 0 not in metadatos_validos
            ):
                meta = partidas_por_clip[primer_nombre]
                if isinstance(meta, dict):
                    metadatos_validos[0] = {
                        "mapa": str(meta.get("mapa", "")),
                        "agente": str(meta.get("agente", ""))
                    }

            divisiones.clear()
            divisiones.update(divisiones_validas)
            metadatos_partidas.clear()
            metadatos_partidas.update(metadatos_validos)
            return True

        # --------------------------------------------------------
        # Migración de JSON antiguos.
        # Si cambió el conjunto de clips y el catálogo permite reconocer
        # exactamente a qué partida pertenece cada clip actual, usamos esa
        # información en vez de confiar ciegamente en índices antiguos.
        # --------------------------------------------------------
        inferida = _inferir_organizacion_desde_catalogo()
        if inferida is not None:
            divisiones_inferidas, metadatos_inferidos = inferida
            divisiones.clear()
            divisiones.update(divisiones_inferidas)
            metadatos_partidas.clear()
            metadatos_partidas.update(metadatos_inferidos)

            # Migrar inmediatamente al formato robusto.
            guardar_configuracion()
            return True

        # --------------------------------------------------------
        # Fallback legado: comportamiento anterior.
        # Solo se usa cuando el catálogo no permite una migración segura.
        # --------------------------------------------------------
        divisiones_guardadas = datos.get(
            "divisiones",
            []
        )

        divisiones_validas = {
            int(indice)
            for indice in divisiones_guardadas
            if str(indice).isdigit()
            and 0 < int(indice) < len(videos_actuales)
        }

        partidas_guardadas = datos.get(
            "partidas",
            {}
        )

        metadatos_validos = {}

        for clave, meta in partidas_guardadas.items():
            try:
                inicio = int(clave)
            except (TypeError, ValueError):
                continue

            if inicio not in ({0} | divisiones_validas):
                continue

            if not isinstance(meta, dict):
                continue

            metadatos_validos[inicio] = {
                "mapa": str(meta.get("mapa", "")),
                "agente": str(meta.get("agente", ""))
            }

        divisiones.clear()
        divisiones.update(divisiones_validas)

        metadatos_partidas.clear()
        metadatos_partidas.update(metadatos_validos)

        # Convertir también este archivo al formato v0.9.2 para que futuras
        # modificaciones de clips ya no dependan solo de índices.
        guardar_configuracion()
        return True

    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        # Si el JSON está dañado, Archiver abre la carpeta normalmente.
        return False


# ============================================================
# SELECTOR
# ============================================================

def seleccionar_carpeta():

    carpeta = filedialog.askdirectory(
        title="Seleccionar partida de Outplayed"
    )

    if not carpeta:
        return

    ruta_var.set(
        carpeta
    )

    analizar_partida(
        carpeta
    )


# ============================================================
# ANALIZAR PARTIDA
# ============================================================


def calcular_numero_partida(indice):
    """
    Determina a qué partida pertenece un clip
    según las divisiones existentes.
    """

    numero = 1

    for division in sorted(divisiones):
        if indice >= division:
            numero += 1

    return numero


def actualizar_lista_clips():
    """
    Reconstruye visualmente la lista mostrando
    las divisiones entre partidas.
    """

    lista.delete(0, tk.END)

    for indice, video in enumerate(videos_actuales):

        # Mostrar separación antes del clip
        if indice in divisiones:

            numero_partida = calcular_numero_partida(indice)

            lista.insert(
                tk.END,
                f"────────── PARTIDA {numero_partida} ──────────"
            )

        fecha_hora = obtener_fecha_hora(
            video.name
        )

        fecha_texto = fecha_hora.strftime(
            "%d-%m-%Y  %H:%M:%S"
        )

        srt = video.with_suffix(".srt")

        estado_srt = (
            "✓ SRT"
            if srt.exists()
            else "✗ Sin SRT"
        )

        numero_partida = calcular_numero_partida(
            indice
        )

        lista.insert(
            tk.END,
            f"P{numero_partida}  "
            f"{fecha_texto}   "
            f"{video.name}   "
            f"[{estado_srt}]"
        )


def obtener_indice_video_desde_lista():
    """
    Convierte la posición seleccionada de la Listbox
    al índice real dentro de videos_actuales.

    Es necesario porque ahora la lista también contiene
    líneas visuales de separación.
    """

    seleccion = lista.curselection()

    if not seleccion:
        return None

    posicion_lista = seleccion[0]

    contador_videos = -1

    for posicion in range(posicion_lista + 1):

        texto = lista.get(posicion)

        if not texto.startswith("──────────"):
            contador_videos += 1

    return contador_videos


def dividir_aqui():

    indice = obtener_indice_video_desde_lista()

    if indice is None:
        messagebox.showinfo(
            "Dividir partida",
            "Selecciona primero el clip que inicia "
            "la nueva partida."
        )
        return

    if indice == 0:
        messagebox.showinfo(
            "Dividir partida",
            "El primer clip ya corresponde al inicio "
            "de la primera partida."
        )
        return

    divisiones.add(indice)

    actualizar_lista_clips()

    actualizar_resumen_partidas()
    guardar_configuracion()


def quitar_division():
    """
    Elimina la división correspondiente a la partida
    del clip seleccionado.

    Se puede seleccionar cualquier clip de P2, P3, etc.
    """

    indice = obtener_indice_video_desde_lista()

    if indice is None:
        messagebox.showinfo(
            "Quitar división",
            "Selecciona un clip de la partida cuya "
            "división quieres eliminar."
        )
        return

    # Buscar la última división anterior o igual
    # al clip seleccionado.
    divisiones_anteriores = [
        division
        for division in divisiones
        if division <= indice
    ]

    if not divisiones_anteriores:
        messagebox.showinfo(
            "Quitar división",
            "La Partida 1 no tiene una división anterior."
        )
        return

    division_a_eliminar = max(
        divisiones_anteriores
    )

    divisiones.remove(
        division_a_eliminar
    )

    actualizar_lista_clips()
    actualizar_resumen_partidas()
    guardar_configuracion()


def actualizar_resumen_partidas():

    cantidad = len(divisiones) + 1

    partidas_var.set(
        f"Partidas definidas: {cantidad}"
    )

    reconstruir_panel_partidas()


def analizar_partida(carpeta):

    global videos_actuales
    global carpeta_actual
    global divisiones
    global metadatos_partidas

    # Eliminar divisiones pertenecientes
    # a la carpeta anteriormente seleccionada
    divisiones.clear()
    metadatos_partidas.clear()

    carpeta_actual = Path(
        carpeta
    )

    videos_actuales = analizar_carpeta(
        carpeta
    )

    # Restaurar organización previa de esta carpeta, si existe.
    cargar_configuracion()

    lista.delete(
        0,
        tk.END
    )

    if not videos_actuales:

        fecha_var.set(
            "Partida: No detectada"
        )

        clips_var.set(
            "Clips encontrados: 0"
        )

        srt_var.set(
            "Subtítulos: 0/0"
        )

        estado_var.set(
            "No se encontraron clips."
        )

        boton_procesar.config(
            state="disabled"
        )

        return

    fecha = obtener_fecha(
        videos_actuales[0].name
    )

    # ----------------------------------------
    # CONTAR SUBTÍTULOS
    # ----------------------------------------

    cantidad_srt = 0

    for video in videos_actuales:

        srt = video.with_suffix(
            ".srt"
        )

        if srt.exists():
            cantidad_srt += 1

    # ----------------------------------------
    # MOSTRAR CLIPS
    # ----------------------------------------

    actualizar_lista_clips()

    # Mostrar las divisiones restauradas o la configuración inicial.
    partidas_var.set(
        f"Partidas definidas: {len(divisiones) + 1}"
    )

    reconstruir_panel_partidas()

    # ----------------------------------------
    # INFORMACIÓN GENERAL
    # ----------------------------------------

    fecha_var.set(
        f"Partida: {fecha}"
    )

    clips_var.set(
        f"Clips encontrados: "
        f"{len(videos_actuales)}"
    )

    srt_var.set(
        f"Subtítulos: "
        f"{cantidad_srt}/"
        f"{len(videos_actuales)}"
    )

    # ----------------------------------------
    # ESTADO DE SUBTÍTULOS
    # ----------------------------------------

    if cantidad_srt == len(
        videos_actuales
    ):

        estado_var.set(
            "✓ Partida lista para procesar"
        )

        boton_procesar.config(
            state="normal"
        )

    else:

        faltantes = (
            len(videos_actuales)
            - cantidad_srt
        )

        estado_var.set(
            f"⚠ Faltan {faltantes} archivo(s) SRT · "
            f"se procesarán igualmente"
        )

        boton_procesar.config(
            state="normal"
        )


# ============================================================
# INFORMACIÓN DE PARTIDAS
# ============================================================

class SearchableCombobox(ttk.Combobox):
    """
    Selector con búsqueda por coincidencia.

    v0.9.2 revisión 3:
    - Permite escribir normalmente varias letras.
    - Filtra por coincidencia en cualquier parte del nombre.
    - No selecciona ni reemplaza automáticamente el texto escrito.
    - La lista puede abrirse con Flecha abajo o haciendo clic.
    - Al salir del campo valida el texto y conserva solo valores válidos.
    """

    def __init__(self, master=None, completion_list=None, **kwargs):
        self._lista_completa = list(completion_list or [])
        kwargs["values"] = self._lista_completa
        kwargs["state"] = "normal"
        super().__init__(master, **kwargs)

        self.bind("<KeyRelease>", self._buscar)
        self.bind("<<ComboboxSelected>>", self._seleccionado)
        self.bind("<FocusOut>", self._validar)
        self.bind("<Escape>", self._restaurar_lista)

    def _coincidencias(self, texto):
        texto = texto.strip().lower()

        if not texto:
            return self._lista_completa

        return [
            valor
            for valor in self._lista_completa
            if texto in valor.lower()
        ]

    def _buscar(self, event):
        # Las teclas de navegación no deben alterar el filtro.
        if event.keysym in {
            "Up", "Down", "Return", "Tab",
            "Left", "Right", "Home", "End",
            "Escape"
        }:
            return

        texto = self.get()
        coincidencias = self._coincidencias(texto)
        self["values"] = coincidencias

        # Importante: NO generar <Down> automáticamente.
        # En algunas versiones de Tk/Windows eso selecciona el primer
        # resultado y reemplaza el texto mientras el usuario escribe.

    def _seleccionado(self, _event=None):
        self["values"] = self._lista_completa

    def _validar(self, _event=None):
        valor = self.get().strip()

        if not valor:
            self.set("")
            self["values"] = self._lista_completa
            return

        # Aceptar diferencias de mayúsculas/minúsculas,
        # pero guardar el nombre oficial de la lista.
        for opcion in self._lista_completa:
            if opcion.lower() == valor.lower():
                self.set(opcion)
                self["values"] = self._lista_completa
                return

        # Si quedó texto parcial y existe UNA sola coincidencia,
        # podemos resolverla sin ambigüedad. Si hay varias, no elegimos
        # arbitrariamente la primera.
        coincidencias = self._coincidencias(valor)

        if len(coincidencias) == 1:
            self.set(coincidencias[0])
        elif valor not in self._lista_completa:
            self.set("")

        self["values"] = self._lista_completa

    def _restaurar_lista(self, _event=None):
        self["values"] = self._lista_completa


MAPAS_VALORANT = [
    "",
    "Abyss",
    "Ascent",
    "Bind",
    "Breeze",
    "Corrode",
    "Fracture",
    "Haven",
    "Icebox",
    "Lotus",
    "Pearl",
    "Split",
    "Sunset",
]

AGENTES_VALORANT = [
    "",
    "Astra",
    "Breach",
    "Brimstone",
    "Chamber",
    "Clove",
    "Cypher",
    "Deadlock",
    "Fade",
    "Gekko",
    "Harbor",
    "Iso",
    "Jett",
    "KAY/O",
    "Killjoy",
    "Neon",
    "Omen",
    "Phoenix",
    "Raze",
    "Reyna",
    "Sage",
    "Skye",
    "Sova",
    "Tejo",
    "Viper",
    "Vyse",
    "Waylay",
    "Yoru",
]


def obtener_inicios_partidas():
    """
    Devuelve los índices donde comienza cada partida.
    La primera siempre comienza en 0.
    """
    return [0] + sorted(divisiones)


def obtener_rangos_partidas():
    """
    Devuelve tuplas:
    (numero_partida, indice_inicio, indice_fin_exclusivo)
    """
    inicios = obtener_inicios_partidas()
    rangos = []

    for posicion, inicio in enumerate(inicios):

        if posicion + 1 < len(inicios):
            fin = inicios[posicion + 1]
        else:
            fin = len(videos_actuales)

        rangos.append(
            (posicion + 1, inicio, fin)
        )

    return rangos


def guardar_metadato(inicio, campo, variable):
    """
    Guarda inmediatamente los cambios escritos/elegidos
    en los campos Mapa y Agente.
    """
    if inicio not in metadatos_partidas:
        metadatos_partidas[inicio] = {
            "mapa": "",
            "agente": ""
        }

    metadatos_partidas[inicio][campo] = variable.get().strip()
    guardar_configuracion()


def reconstruir_panel_partidas():
    """
    Reconstruye el panel inferior con una fila por cada
    partida definida, conservando los datos ya ingresados
    cuando sea posible.
    """
    if "marco_partidas_contenido" not in globals():
        return

    for widget in marco_partidas_contenido.winfo_children():
        widget.destroy()

    variables_metadatos.clear()

    if not videos_actuales:
        tk.Label(
            marco_partidas_contenido,
            text="Selecciona una carpeta para definir las partidas.",
            fg="#666666"
        ).pack(
            anchor="w",
            padx=8,
            pady=8
        )
        return

    inicios_validos = set(obtener_inicios_partidas())

    # Eliminar metadatos de divisiones que ya no existen.
    for inicio in list(metadatos_partidas):
        if inicio not in inicios_validos:
            del metadatos_partidas[inicio]

    for numero, inicio, fin in obtener_rangos_partidas():

        datos = metadatos_partidas.setdefault(
            inicio,
            {
                "mapa": "",
                "agente": ""
            }
        )

        primer_video = videos_actuales[inicio]
        fecha_hora = obtener_fecha_hora(
            primer_video.name
        )

        fecha_texto = fecha_hora.strftime(
            "%d-%m-%Y %H:%M:%S"
        )

        cantidad = fin - inicio

        fila = tk.Frame(
            marco_partidas_contenido,
            bd=1,
            relief="groove"
        )

        fila.pack(
            fill="x",
            padx=5,
            pady=4
        )

        encabezado = tk.Frame(fila)
        encabezado.pack(
            fill="x",
            padx=8,
            pady=(6, 3)
        )

        tk.Label(
            encabezado,
            text=f"P{numero}",
            font=("Segoe UI", 10, "bold"),
            width=4,
            anchor="w"
        ).pack(
            side="left"
        )

        tk.Label(
            encabezado,
            text=f"{cantidad} clips  |  Inicio: {fecha_texto}",
            anchor="w"
        ).pack(
            side="left"
        )

        campos = tk.Frame(fila)
        campos.pack(
            fill="x",
            padx=8,
            pady=(0, 7)
        )

        mapa_var = tk.StringVar(
            value=datos.get("mapa", "")
        )

        agente_var = tk.StringVar(
            value=datos.get("agente", "")
        )

        variables_metadatos[inicio] = {
            "mapa": mapa_var,
            "agente": agente_var
        }

        tk.Label(
            campos,
            text="Mapa:"
        ).pack(
            side="left"
        )

        combo_mapa = SearchableCombobox(
            campos,
            completion_list=MAPAS_VALORANT,
            textvariable=mapa_var,
            width=18
        )

        combo_mapa.pack(
            side="left",
            padx=(5, 18)
        )

        tk.Label(
            campos,
            text="Agente:"
        ).pack(
            side="left"
        )

        combo_agente = SearchableCombobox(
            campos,
            completion_list=AGENTES_VALORANT,
            textvariable=agente_var,
            width=18
        )

        combo_agente.pack(
            side="left",
            padx=(5, 0)
        )

        mapa_var.trace_add(
            "write",
            lambda *_args, i=inicio, v=mapa_var:
                guardar_metadato(i, "mapa", v)
        )

        agente_var.trace_add(
            "write",
            lambda *_args, i=inicio, v=agente_var:
                guardar_metadato(i, "agente", v)
        )


# ============================================================
# PROCESAMIENTO
# ============================================================

def limpiar_nombre_archivo(texto):
    texto = texto.strip()
    caracteres_invalidos = '<>:"/\\|?*'

    for caracter in caracteres_invalidos:
        texto = texto.replace(caracter, "-")

    texto = "-".join(texto.split())
    return texto.strip(".-_")


def obtener_nombre_salida(numero, inicio):
    fecha_hora = obtener_fecha_hora(
        videos_actuales[inicio].name
    )

    fecha_base = fecha_hora.strftime(
        "%Y-%m-%d_%H-%M"
    )

    datos = metadatos_partidas.get(
        inicio,
        {}
    )

    mapa = limpiar_nombre_archivo(
        datos.get("mapa", "")
    )

    agente = limpiar_nombre_archivo(
        datos.get("agente", "")
    )

    partes = [fecha_base]

    if mapa:
        partes.append(mapa)

    if agente:
        partes.append(agente)

    if not mapa and not agente:
        partes.append(f"P{numero}")

    return "_".join(partes)


def procesar_partida():

    if not videos_actuales:
        return

    # Capturar cualquier texto actualmente escrito.
    for inicio, variables in variables_metadatos.items():
        guardar_metadato(
            inicio,
            "mapa",
            variables["mapa"]
        )
        guardar_metadato(
            inicio,
            "agente",
            variables["agente"]
        )

    rangos = obtener_rangos_partidas()
    salidas = []

    for numero, inicio, fin in rangos:
        nombre = obtener_nombre_salida(
            numero,
            inicio
        )

        salida_video = carpeta_actual / f"{nombre}.mp4"
        salida_srt = carpeta_actual / f"{nombre}.srt"

        salidas.append(
            (
                salida_video,
                salida_srt
            )
        )

    existentes = []

    for salida_video, salida_srt in salidas:
        if salida_video.exists():
            existentes.append(salida_video.name)

        if combinar_srt_var.get() and salida_srt.exists():
            existentes.append(salida_srt.name)

    if existentes:
        respuesta = messagebox.askyesno(
            "Archivos existentes",
            "Ya existen uno o más archivos de salida:\n\n"
            + "\n".join(existentes)
            + "\n\n¿Quieres reemplazarlos?"
        )

        if not respuesta:
            return

    boton_procesar.config(
        state="disabled"
    )

    boton_buscar.config(
        state="disabled"
    )

    barra["value"] = 0

    estado_var.set(
        "Procesando partidas..."
    )

    # Tkinter debe consultarse desde el hilo principal.
    # Capturamos la opción antes de iniciar el trabajo en segundo plano.
    combinar_srt = combinar_srt_var.get()

    hilo = threading.Thread(
        target=procesar_en_segundo_plano,
        args=(combinar_srt,),
        daemon=True
    )

    hilo.start()


def procesar_en_segundo_plano(combinar_srt):

    try:
        rangos = obtener_rangos_partidas()
        resultados = []
        total_partidas = len(rangos)

        for posicion, (
            numero,
            inicio,
            fin
        ) in enumerate(
            rangos,
            start=1
        ):
            clips = videos_actuales[inicio:fin]

            nombre = obtener_nombre_salida(
                numero,
                inicio
            )

            salida_video = (
                carpeta_actual /
                f"{nombre}.mp4"
            )

            salida_srt = (
                carpeta_actual /
                f"{nombre}.srt"
            )

            subtitulos_finales = []
            desplazamiento_ms = 0
            total_clips = len(clips)

            # En v0.7 el video es el flujo principal.
            # Solo analizamos duración/SRT si el usuario lo pidió.
            if combinar_srt:
                for indice, video in enumerate(
                    clips,
                    start=1
                ):
                    actualizar_estado(
                        f"P{numero}: preparando subtítulos "
                        f"{indice}/{total_clips}..."
                    )

                    duracion = obtener_duracion(
                        video
                    )

                    srt = video.with_suffix(
                        ".srt"
                    )

                    if srt.exists():
                        subtitulos = leer_srt(
                            srt,
                            desplazamiento_ms
                        )

                        subtitulos_finales.extend(
                            subtitulos
                        )

                    # La duración se suma incluso si falta el SRT.
                    desplazamiento_ms += round(
                        duracion * 1000
                    )

                    fraccion_partida = (
                        (indice / total_clips) * 0.35
                    )

                    progreso = (
                        (
                            (posicion - 1)
                            + fraccion_partida
                        )
                        / total_partidas
                    ) * 100

                    actualizar_progreso(
                        progreso
                    )

            actualizar_estado(
                f"P{numero}: uniendo clips con FFmpeg..."
            )

            unir_videos(
                clips,
                salida_video
            )

            cantidad_subtitulos = 0
            srt_generado = None

            if combinar_srt:
                actualizar_estado(
                    f"P{numero}: combinando SRT existentes..."
                )

                guardar_srt(
                    subtitulos_finales,
                    salida_srt
                )

                cantidad_subtitulos = len(
                    subtitulos_finales
                )
                srt_generado = salida_srt

            resultados.append(
                (
                    numero,
                    len(clips),
                    salida_video,
                    srt_generado,
                    cantidad_subtitulos,
                    inicio
                )
            )

            actualizar_progreso(
                (
                    posicion /
                    total_partidas
                ) * 100
            )

        ventana.after(
            0,
            procesamiento_completado_multiple,
            resultados
        )

    except Exception as error:
        ventana.after(
            0,
            procesamiento_error,
            str(error)
        )


def procesamiento_completado_multiple(resultados):

    estado_var.set(
        "✓ Procesamiento completado"
    )

    boton_procesar.config(
        state="normal"
    )

    boton_buscar.config(
        state="normal"
    )

    lineas = [
        f"Se procesaron {len(resultados)} partida(s).",
        ""
    ]

    for (
        numero,
        cantidad_clips,
        video,
        srt,
        cantidad_subtitulos,
        inicio
    ) in resultados:

        lineas.extend([
            f"P{numero} — {cantidad_clips} clips",
            f"Video: {video.name}"
        ])

        if srt is not None:
            lineas.extend([
                f"Subtítulos: {srt.name}",
                f"Entradas SRT: {cantidad_subtitulos}"
            ])
        else:
            lineas.append(
                "Subtítulos: no generados (opción desactivada)"
            )

        lineas.append("")

    registrar_resultados_catalogo(resultados)

    messagebox.showinfo(
        "Proceso completado",
        "\n".join(lineas).strip()
        + "\n\n✓ Partidas registradas en el historial."
    )


# ============================================================
# CATÁLOGO / HISTORIAL v0.8
# ============================================================

def cargar_catalogo():
    global catalogo_partidas
    if not ARCHIVO_CATALOGO.exists():
        catalogo_partidas = []
        return
    try:
        datos = json.loads(ARCHIVO_CATALOGO.read_text(encoding="utf-8"))
        catalogo_partidas = datos if isinstance(datos, list) else []
    except (OSError, json.JSONDecodeError):
        catalogo_partidas = []


def guardar_catalogo():
    temporal = ARCHIVO_CATALOGO.with_suffix(".tmp")
    try:
        temporal.write_text(
            json.dumps(catalogo_partidas, ensure_ascii=False, indent=4),
            encoding="utf-8"
        )
        temporal.replace(ARCHIVO_CATALOGO)
    except OSError as error:
        # El historial sigue siendo utilizable aunque falle la escritura,
        # pero dejamos una señal visible para diagnóstico.
        print(
            f"[Valorant Archiver] No se pudo guardar el catálogo: {error}"
        )
        try:
            if temporal.exists():
                temporal.unlink()
        except OSError:
            pass


def registrar_resultados_catalogo(resultados):
    """Registra/actualiza cada MP4 generado sin duplicarlo."""
    ahora = datetime.now().isoformat(timespec="seconds")
    for numero, cantidad_clips, video, srt, cantidad_subtitulos, inicio in resultados:
        meta = metadatos_partidas.get(inicio, {})
        fecha_hora = obtener_fecha_hora(videos_actuales[inicio].name)
        registro = {
            "id": str(video.resolve()).lower(),
            "fecha_partida": fecha_hora.isoformat(timespec="seconds") if fecha_hora else "",
            "mapa": meta.get("mapa", ""),
            "agente": meta.get("agente", ""),
            "clips": cantidad_clips,
            "video": video.name,
            "ruta_video": str(video.resolve()),
            "carpeta_origen": str(carpeta_actual.resolve()),
            "clips_origen": [
                str(video_origen.resolve())
                for video_origen in videos_actuales[
                    inicio:(
                        obtener_rangos_partidas()[numero - 1][2]
                    )
                ]
            ],
            "procesado": ahora,
            "srt": srt.name if srt is not None else "",
            "estado_publicacion": "Procesado",
            "estado_almacenamiento": "Local"
        }

        existente = next(
            (i for i, item in enumerate(catalogo_partidas)
             if item.get("id") == registro["id"]),
            None
        )
        if existente is None:
            catalogo_partidas.append(registro)
        else:
            anterior = catalogo_partidas[existente]
            registro["estado_publicacion"] = anterior.get(
                "estado_publicacion",
                "Subido a YouTube"
                if anterior.get("estado") == "Subido a YouTube"
                else "Procesado"
            )
            registro["estado_almacenamiento"] = anterior.get(
                "estado_almacenamiento",
                "Clips eliminados"
                if anterior.get("estado") == "Eliminado localmente"
                else (
                    "Respaldado"
                    if anterior.get("estado") == "Respaldado"
                    else "Local"
                )
            )
            catalogo_partidas[existente] = registro

    catalogo_partidas.sort(
        key=lambda x: x.get("fecha_partida", ""),
        reverse=True
    )
    guardar_catalogo()
    actualizar_historial()


def formatear_tamano(bytes_total):
    if bytes_total is None:
        return "—"
    unidades = ["B", "KB", "MB", "GB", "TB"]
    valor = float(bytes_total)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            if unidad == "B":
                return f"{int(valor)} {unidad}"
            return f"{valor:.2f} {unidad}"
        valor /= 1024


def analizar_almacenamiento_partida(partida):
    """Analiza solo archivos conocidos; nunca elimina nada."""
    rutas_clips = [
        Path(ruta)
        for ruta in partida.get("clips_origen", [])
        if ruta
    ]

    clips_existentes = [ruta for ruta in rutas_clips if ruta.is_file()]
    bytes_clips = 0
    for ruta in clips_existentes:
        try:
            bytes_clips += ruta.stat().st_size
        except OSError:
            pass

    ruta_video = Path(partida.get("ruta_video", ""))
    video_existe = ruta_video.is_file()
    bytes_video = 0
    if video_existe:
        try:
            bytes_video = ruta_video.stat().st_size
        except OSError:
            pass

    return {
        "clips_total": len(rutas_clips),
        "clips_existentes": len(clips_existentes),
        "bytes_clips": bytes_clips,
        "video_existe": video_existe,
        "bytes_video": bytes_video
    }


def enviar_a_papelera_windows(ruta):
    """
    Envía un archivo a la Papelera de reciclaje usando la API nativa
    de Windows. No realiza eliminación permanente.
    """
    import ctypes
    from ctypes import wintypes

    ruta = Path(ruta)

    if not ruta.is_file():
        return False

    # SHFileOperation requiere una cadena terminada en doble NUL.
    origen = str(ruta.resolve()) + "\0\0"

    FO_DELETE = 0x0003
    FOF_SILENT = 0x0004
    FOF_NOCONFIRMATION = 0x0010
    FOF_ALLOWUNDO = 0x0040
    FOF_NOERRORUI = 0x0400

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    operacion = SHFILEOPSTRUCTW()
    operacion.hwnd = None
    operacion.wFunc = FO_DELETE
    operacion.pFrom = origen
    operacion.pTo = None
    operacion.fFlags = (
        FOF_ALLOWUNDO
        | FOF_NOCONFIRMATION
        | FOF_SILENT
        | FOF_NOERRORUI
    )
    operacion.fAnyOperationsAborted = False
    operacion.hNameMappings = None
    operacion.lpszProgressTitle = None

    resultado = ctypes.windll.shell32.SHFileOperationW(
        ctypes.byref(operacion)
    )

    if resultado != 0:
        raise RuntimeError(
            f"Windows devolvió el código {resultado} al intentar "
            f"enviar a la Papelera:\n{ruta.name}"
        )

    if operacion.fAnyOperationsAborted:
        raise RuntimeError(
            f"La operación fue cancelada por Windows:\n{ruta.name}"
        )

    # Confirmar que el archivo ya no continúa en su ubicación original.
    if ruta.exists():
        raise RuntimeError(
            f"Windows informó éxito, pero el archivo continúa "
            f"en su ubicación original:\n{ruta.name}"
        )

    return True


def obtener_archivos_liberables(partida, incluir_srt=False):
    clips = [
        Path(ruta)
        for ruta in partida.get("clips_origen", [])
        if ruta and Path(ruta).is_file()
    ]

    archivos = list(clips)

    if incluir_srt:
        for clip in clips:
            srt = clip.with_suffix(".srt")
            if srt.is_file():
                archivos.append(srt)

    # Evitar duplicados accidentalmente.
    unicos = []
    vistos = set()
    for ruta in archivos:
        clave = str(ruta.resolve()).lower()
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(ruta)

    return unicos


def liberar_espacio_historial():
    partida = obtener_partida_historial()

    if not partida:
        messagebox.showinfo(
            "Seleccionar partida",
            "Selecciona una partida del historial primero."
        )
        return

    if not partida.get("clips_origen"):
        messagebox.showwarning(
            "Información insuficiente",
            "Esta partida no tiene registrada la lista exacta de clips de origen.\n\n"
            "Reprocésala con v0.8.2 o superior antes de liberar espacio."
        )
        return

    incluir_srt = eliminar_srt_var.get()
    archivos = obtener_archivos_liberables(partida, incluir_srt)

    if not archivos:
        messagebox.showinfo(
            "Sin archivos para liberar",
            "No se encontraron clips originales disponibles para esta partida."
        )
        actualizar_detalle_almacenamiento()
        actualizar_historial()
        return

    total_bytes = 0
    for ruta in archivos:
        try:
            total_bytes += ruta.stat().st_size
        except OSError:
            pass

    clips_mp4 = [r for r in archivos if r.suffix.lower() == ".mp4"]
    srts = [r for r in archivos if r.suffix.lower() == ".srt"]

    vista = "\n".join(f"• {r.name}" for r in archivos[:12])
    if len(archivos) > 12:
        vista += f"\n• ... y {len(archivos) - 12} archivo(s) más"

    texto = (
        f"Partida: {partida.get('mapa', '')} / {partida.get('agente', '')}\n\n"
        f"Clips MP4: {len(clips_mp4)}\n"
        f"SRT: {len(srts)}\n"
        f"Tamaño total: {formatear_tamano(total_bytes)}\n\n"
        "Los siguientes archivos serán enviados a la Papelera de reciclaje:\n\n"
        f"{vista}\n\n"
        "El MP4 final procesado, el catálogo y .valorant_archiver.json "
        "NO serán eliminados.\n\n"
        "¿Deseas continuar?"
    )

    if not messagebox.askyesno("Liberar espacio", texto):
        return

    # Segunda confirmación para una operación destructiva, aunque recuperable.
    if not messagebox.askyesno(
        "Confirmar envío a Papelera",
        f"Se enviarán {len(archivos)} archivo(s) a la Papelera "
        f"({formatear_tamano(total_bytes)}).\n\n"
        "Podrás recuperarlos desde la Papelera mientras no la vacíes.\n\n"
        "¿Confirmas?"
    ):
        return

    enviados = 0
    errores = []

    for ruta in archivos:
        try:
            if enviar_a_papelera_windows(ruta):
                enviados += 1
        except Exception as error:
            errores.append(str(error))

    # Estado automático solo cuando ya no queda ningún clip fuente.
    info = analizar_almacenamiento_partida(partida)
    if info["clips_total"] > 0 and info["clips_existentes"] == 0:
        migrar_estados_partida(partida)
        partida["estado_almacenamiento"] = (
            "Clips eliminados"
            if info["video_existe"]
            else "Todo eliminado"
        )
        guardar_catalogo()

    actualizar_historial()
    actualizar_detalle_almacenamiento()

    if errores:
        messagebox.showwarning(
            "Liberación parcial",
            f"Se enviaron {enviados}/{len(archivos)} archivo(s) a la Papelera.\n\n"
            "Algunos archivos no pudieron procesarse:\n\n"
            + "\n\n".join(errores[:5])
        )
    else:
        messagebox.showinfo(
            "Espacio liberado",
            f"Se enviaron {enviados} archivo(s) a la Papelera.\n\n"
            f"Espacio trasladado: {formatear_tamano(total_bytes)}\n\n"
            "El MP4 final se mantuvo intacto."
        )


def actualizar_detalle_almacenamiento(event=None):
    if "almacenamiento_detalle_var" not in globals():
        return

    partida = obtener_partida_historial()
    if not partida:
        almacenamiento_detalle_var.set(
            "Selecciona una partida para analizar sus archivos."
        )
        return

    info = analizar_almacenamiento_partida(partida)

    if not partida.get("clips_origen"):
        almacenamiento_detalle_var.set(
            "Esta entrada fue creada antes de v0.8.2 y no contiene la lista "
            "exacta de clips de origen. Reprocesa la partida una vez para "
            "habilitar el análisis seguro de sus clips."
        )
        return

    estado_video = (
        formatear_tamano(info["bytes_video"])
        if info["video_existe"]
        else "no encontrado"
    )

    almacenamiento_detalle_var.set(
        f"Clips originales disponibles: "
        f'{info["clips_existentes"]}/{info["clips_total"]}'
        f"   ·   Espacio potencialmente recuperable: "
        f'{formatear_tamano(info["bytes_clips"])}'
        f"   ·   MP4 final: {estado_video}"
    )


ESTADOS_PUBLICACION = [
    "Procesado",
    "Subido a YouTube"
]

ESTADOS_ALMACENAMIENTO = [
    "Local",
    "Respaldado",
    "Clips eliminados",
    "Todo eliminado",
    "Archivo no encontrado"
]


def migrar_estados_partida(partida):
    """Compatibilidad con catálogos v0.8.x."""
    if "estado_publicacion" not in partida:
        viejo = partida.get("estado", "Procesado")
        partida["estado_publicacion"] = (
            "Subido a YouTube" if viejo == "Subido a YouTube" else "Procesado"
        )

    if "estado_almacenamiento" not in partida:
        viejo = partida.get("estado", "")
        if viejo == "Respaldado":
            almacenamiento = "Respaldado"
        elif viejo == "Eliminado localmente":
            ruta_video = Path(partida.get("ruta_video", ""))
            almacenamiento = (
                "Clips eliminados" if ruta_video.is_file() else "Todo eliminado"
            )
        else:
            almacenamiento = "Local"
        partida["estado_almacenamiento"] = almacenamiento

    partida.pop("estado", None)


def sincronizar_disponibilidad(partida):
    migrar_estados_partida(partida)

    ruta_video = Path(partida.get("ruta_video", ""))
    video_existe = ruta_video.is_file()
    info = analizar_almacenamiento_partida(partida)
    clips_conocidos = bool(partida.get("clips_origen"))
    clips_existen = info["clips_existentes"] > 0 if clips_conocidos else True
    estado = partida.get("estado_almacenamiento", "Local")

    # Solo detectar ausencia automáticamente; nunca inventar si fue borrado,
    # movido o respaldado.
    if not video_existe and estado not in ("Todo eliminado", "Respaldado"):
        partida["estado_almacenamiento"] = "Archivo no encontrado"
    elif video_existe and clips_conocidos and not clips_existen and estado in (
        "Local", "Archivo no encontrado"
    ):
        partida["estado_almacenamiento"] = "Clips eliminados"


def actualizar_historial(*_args):
    if "historial_tree" not in globals():
        return

    for item in historial_tree.get_children():
        historial_tree.delete(item)

    texto = historial_busqueda_var.get().strip().lower() if "historial_busqueda_var" in globals() else ""
    mapa_filtro = historial_mapa_var.get() if "historial_mapa_var" in globals() else "Todos"
    agente_filtro = historial_agente_var.get() if "historial_agente_var" in globals() else "Todos"
    pub_filtro = historial_publicacion_var.get() if "historial_publicacion_var" in globals() else "Todos"
    alm_filtro = historial_almacenamiento_var.get() if "historial_almacenamiento_var" in globals() else "Todos"

    visibles = 0
    hubo_cambios = False

    for i, partida in enumerate(catalogo_partidas):
        antes = dict(partida)
        sincronizar_disponibilidad(partida)
        if partida != antes:
            hubo_cambios = True

        mapa = partida.get("mapa", "")
        agente = partida.get("agente", "")
        publicacion = partida.get("estado_publicacion", "Procesado")
        almacenamiento = partida.get("estado_almacenamiento", "Local")
        video = partida.get("video", "")
        fecha_original = partida.get("fecha_partida", "")

        if mapa_filtro != "Todos" and mapa != mapa_filtro:
            continue
        if agente_filtro != "Todos" and agente != agente_filtro:
            continue
        if pub_filtro != "Todos" and publicacion != pub_filtro:
            continue
        if alm_filtro != "Todos" and almacenamiento != alm_filtro:
            continue

        searchable = " ".join([
            fecha_original, mapa, agente, publicacion, almacenamiento, video
        ]).lower()
        if texto and texto not in searchable:
            continue

        fecha = fecha_original
        try:
            fecha = datetime.fromisoformat(fecha).strftime("%d-%m-%Y %H:%M")
        except (ValueError, TypeError):
            pass

        info = analizar_almacenamiento_partida(partida)
        if almacenamiento in ("Clips eliminados", "Respaldado"):
            etiqueta_estado = "estado_ok"
        elif almacenamiento == "Archivo no encontrado":
            etiqueta_estado = "estado_atencion"
        elif almacenamiento == "Todo eliminado":
            etiqueta_estado = "estado_ausente"
        else:
            etiqueta_estado = ""

        historial_tree.insert(
            "", "end", iid=str(i),
            values=(
                fecha, mapa, agente, partida.get("clips", ""),
                publicacion, almacenamiento,
                formatear_tamano(info["bytes_clips"]) if partida.get("clips_origen") else "—",
                formatear_tamano(info["bytes_video"]) if info["video_existe"] else "—",
                video
            ),
            tags=(etiqueta_estado,) if etiqueta_estado else ()
        )
        visibles += 1

    if hubo_cambios:
        guardar_catalogo()

    historial_resumen_var.set(
        f"Partidas registradas: {len(catalogo_partidas)}  ·  Mostrando: {visibles}"
    )


def obtener_partida_historial():
    seleccion = historial_tree.selection()
    if not seleccion:
        return None
    try:
        return catalogo_partidas[int(seleccion[0])]
    except (ValueError, IndexError):
        return None


def cambiar_estados_historial():
    partida = obtener_partida_historial()
    if not partida:
        messagebox.showinfo("Seleccionar partida", "Selecciona una partida del historial primero.")
        return

    pub = historial_nueva_publicacion_var.get()
    alm = historial_nuevo_almacenamiento_var.get()

    if pub in ESTADOS_PUBLICACION:
        partida["estado_publicacion"] = pub
    if alm in ESTADOS_ALMACENAMIENTO:
        partida["estado_almacenamiento"] = alm

    guardar_catalogo()
    actualizar_historial()


def limpiar_filtros_historial():
    historial_busqueda_var.set("")
    historial_mapa_var.set("Todos")
    historial_agente_var.set("Todos")
    historial_publicacion_var.set("Todos")
    historial_almacenamiento_var.set("Todos")
    actualizar_historial()


def localizar_video_historial(partida=None):
    """
    Permite localizar nuevamente el MP4 final.
    Si recibe una partida, reutiliza directamente esa referencia para evitar
    perder la selección cuando el historial se refresca.
    """
    if partida is None:
        partida = obtener_partida_historial()

    if not partida:
        messagebox.showinfo(
            "Seleccionar partida",
            "Selecciona una partida del historial primero."
        )
        return

    ruta_anterior = Path(partida.get("ruta_video", ""))
    carpeta_inicial = None

    # Intentar abrir el selector en la carpeta donde se esperaba el MP4.
    if ruta_anterior.parent.is_dir():
        carpeta_inicial = str(ruta_anterior.parent)
    else:
        carpeta_origen = Path(partida.get("carpeta_origen", ""))
        if carpeta_origen.is_dir():
            carpeta_inicial = str(carpeta_origen)

    opciones = {
        "title": "Localizar MP4 final",
        "filetypes": [
            ("Video MP4", "*.mp4"),
            ("Todos los archivos", "*.*")
        ]
    }
    if carpeta_inicial:
        opciones["initialdir"] = carpeta_inicial

    ruta = filedialog.askopenfilename(**opciones)

    if not ruta:
        return

    nuevo = Path(ruta)
    partida["ruta_video"] = str(nuevo.resolve())
    partida["video"] = nuevo.name

    if partida.get("estado_almacenamiento") == "Archivo no encontrado":
        # Si todavía existen clips fuente, sigue siendo material local.
        info = analizar_almacenamiento_partida(partida)
        partida["estado_almacenamiento"] = (
            "Local" if info["clips_existentes"] > 0 else "Clips eliminados"
        )

    guardar_catalogo()
    actualizar_historial()
    actualizar_detalle_almacenamiento()

    messagebox.showinfo(
        "MP4 localizado",
        "La nueva ubicación del MP4 fue registrada correctamente.\n\n"
        f"{nuevo.name}"
    )


def declarar_video_eliminado(partida=None):
    if partida is None:
        partida = obtener_partida_historial()

    if not partida:
        messagebox.showinfo(
            "Seleccionar partida",
            "Selecciona una partida del historial primero."
        )
        return

    if not messagebox.askyesno(
        "Registrar MP4 eliminado",
        "Esto NO eliminará ningún archivo.\n\n"
        "Solo registrará en el historial que el MP4 final ya fue eliminado.\n\n"
        "¿Continuar?"
    ):
        return

    partida["estado_almacenamiento"] = "Todo eliminado"
    guardar_catalogo()
    actualizar_historial()
    actualizar_detalle_almacenamiento()


def abrir_video_historial(event=None):
    partida = obtener_partida_historial()
    if not partida:
        return
    ruta = Path(partida.get("ruta_video", ""))
    if not ruta.exists():
        partida["estado_almacenamiento"] = "Archivo no encontrado"
        guardar_catalogo()
        actualizar_historial()

        respuesta = messagebox.askyesnocancel(
            "Archivo no encontrado",
            "El MP4 final ya no existe en su ubicación registrada.\n\n"
            "Sí = localizar el archivo en otra ubicación\n"
            "No = registrar que fue eliminado\n"
            "Cancelar = no hacer nada por ahora"
        )

        if respuesta is True:
            localizar_video_historial(partida)
        elif respuesta is False:
            declarar_video_eliminado(partida)
        return
    try:
        os.startfile(ruta)
    except Exception as error:
        messagebox.showerror("Error", f"No se pudo abrir el video:\n\n{error}")


def abrir_carpeta_historial():
    partida = obtener_partida_historial()
    if not partida:
        return
    ruta_video = Path(partida.get("ruta_video", ""))
    carpeta = ruta_video.parent
    if not carpeta.exists():
        carpeta = Path(partida.get("carpeta_origen", ""))
    if not carpeta.exists():
        messagebox.showwarning(
            "Carpeta no encontrada",
            "La carpeta registrada ya no existe en esta ubicación."
        )
        return
    try:
        os.startfile(carpeta)
    except Exception as error:
        messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n\n{error}")


# ============================================================
# ACTUALIZAR GUI DESDE THREAD
# ============================================================

def actualizar_estado(texto):

    ventana.after(
        0,
        estado_var.set,
        texto
    )


def actualizar_progreso(valor):

    ventana.after(
        0,
        lambda: barra.config(
            value=valor
        )
    )


# ============================================================
# RESULTADO
# ============================================================

def procesamiento_completado(
    video,
    srt,
    cantidad_subtitulos
):

    estado_var.set(
        "✓ Procesamiento completado"
    )

    boton_procesar.config(
        state="normal"
    )

    boton_buscar.config(
        state="normal"
    )

    messagebox.showinfo(
        "Proceso completado",
        "La partida fue procesada correctamente.\n\n"
        f"Video:\n{video.name}\n\n"
        f"Subtítulos:\n{srt.name}\n\n"
        f"Subtítulos combinados: "
        f"{cantidad_subtitulos}"
    )


def procesamiento_error(error):

    estado_var.set(
        "✗ Error durante el procesamiento"
    )

    boton_procesar.config(
        state="normal"
    )

    boton_buscar.config(
        state="normal"
    )

    messagebox.showerror(
        "Error",
        "Ocurrió un error:\n\n"
        f"{error}"
    )



def abrir_clip(event=None):

    indice = obtener_indice_video_desde_lista()

    if indice is None:
        return

    if indice < 0 or indice >= len(videos_actuales):
        return

    video = videos_actuales[indice]

    try:
        os.startfile(video)

    except Exception as error:

        messagebox.showerror(
            "Error",
            f"No se pudo abrir el clip:\n\n{error}"
        )




# ============================================================
# INTERFAZ
# ============================================================

def ruta_recurso(nombre):
    """Resuelve recursos en desarrollo y en un futuro ejecutable PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / nombre


ventana = tk.Tk()

ventana.title(
    "Valorant Archiver"
)

# Identidad visual Varchiver.
# Si los recursos faltan, la aplicación sigue funcionando normalmente.
try:
    ruta_icono = ruta_recurso("varchiver.ico")
    if ruta_icono.exists():
        ventana.iconbitmap(default=str(ruta_icono))
except (tk.TclError, OSError):
    pass

try:
    ruta_logo = ruta_recurso("varchiver_logo.png")
    if ruta_logo.exists():
        _logo_icono_tk = tk.PhotoImage(file=str(ruta_logo))
        ventana.iconphoto(True, _logo_icono_tk)
    else:
        _logo_icono_tk = None
except (tk.TclError, OSError):
    _logo_icono_tk = None

ventana.geometry(
    "1180x860"
)

ventana.minsize(
    920,
    700
)

# Paleta visual v0.9.3. Se mantiene Tk/ttk nativo para no introducir
# dependencias externas antes de v1.0.
COLOR_FONDO = "#F4F5F7"
COLOR_PANEL = "#FFFFFF"
COLOR_TEXTO = "#1F2937"
COLOR_SECUNDARIO = "#667085"
COLOR_PRIMARIO = "#2563EB"
COLOR_PRIMARIO_ACTIVO = "#1D4ED8"
COLOR_PELIGRO = "#B42318"
COLOR_PELIGRO_ACTIVO = "#912018"

ventana.configure(bg=COLOR_FONDO)

estilo = ttk.Style()
try:
    estilo.theme_use("vista")
except tk.TclError:
    pass

estilo.configure("TNotebook", background=COLOR_FONDO, borderwidth=0)
estilo.configure(
    "TNotebook.Tab",
    font=("Segoe UI", 10, "bold"),
    padding=(16, 8)
)
estilo.configure(
    "Treeview",
    rowheight=27,
    font=("Segoe UI", 9)
)
estilo.configure(
    "Treeview.Heading",
    font=("Segoe UI", 9, "bold")
)


# ---------------- PESTAÑAS v0.8 ----------------

notebook = ttk.Notebook(ventana)
notebook.pack(fill="both", expand=True)

tab_procesar = tk.Frame(notebook, bg=COLOR_FONDO)
tab_historial = tk.Frame(notebook, bg=COLOR_FONDO)

notebook.add(tab_procesar, text="Procesar clips")
notebook.add(tab_historial, text="Historial")

# ---------------- TÍTULO ----------------

tk.Label(
    tab_procesar,
    text="VALORANT ARCHIVER",
    font=("Segoe UI", 22, "bold"),
    fg=COLOR_TEXTO,
    bg=COLOR_FONDO
).pack(
    pady=(25, 3)
)


tk.Label(
    tab_procesar,
    text="Organiza, procesa y conserva tus partidas de Outplayed · v1.0",
    font=("Segoe UI", 10),
    fg=COLOR_SECUNDARIO,
    bg=COLOR_FONDO
).pack(
    pady=(0, 20)
)


# ---------------- SELECTOR ----------------

selector = tk.Frame(tab_procesar, bg=COLOR_FONDO)

selector.pack(
    fill="x",
    padx=30
)


ruta_var = tk.StringVar()


tk.Entry(
    selector,
    textvariable=ruta_var,
    font=("Segoe UI", 10)
).pack(
    side="left",
    fill="x",
    expand=True,
    padx=(0, 10)
)


boton_buscar = tk.Button(
    selector,
    text="Buscar carpeta",
    command=seleccionar_carpeta,
    width=15
)

boton_buscar.pack(
    side="right"
)


# ---------------- INFORMACIÓN ----------------

info = tk.Frame(tab_procesar, bg=COLOR_FONDO)

info.pack(
    fill="x",
    padx=30,
    pady=(25, 10)
)


fecha_var = tk.StringVar(
    value="Partida: —"
)

clips_var = tk.StringVar(
    value="Clips encontrados: —"
)

srt_var = tk.StringVar(
    value="Subtítulos: —"
)


tk.Label(
    info,
    textvariable=fecha_var,
    font=("Segoe UI", 11, "bold")
).pack(
    anchor="w"
)


tk.Label(
    info,
    textvariable=clips_var
).pack(
    anchor="w",
    pady=(8, 0)
)


tk.Label(
    info,
    textvariable=srt_var
).pack(
    anchor="w"
)


# ---------------- LISTA ----------------

marco_lista = tk.Frame(tab_procesar, bg=COLOR_FONDO)

marco_lista.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=10
)


scrollbar = tk.Scrollbar(
    marco_lista
)

scrollbar.pack(
    side="right",
    fill="y"
)


lista = tk.Listbox(
    marco_lista,
    font=("Consolas", 9),
    yscrollcommand=scrollbar.set
)

lista.pack(
    fill="both",
    expand=True
)

lista.bind(
    "<Double-Button-1>",
    abrir_clip
)


scrollbar.config(
    command=lista.yview
)

# ---------------- DIVISIONES ----------------

marco_divisiones = tk.Frame(tab_procesar, bg=COLOR_FONDO)

marco_divisiones.pack(
    fill="x",
    padx=30,
    pady=(5, 10)
)


partidas_var = tk.StringVar(
    value="Partidas definidas: 1"
)


tk.Label(
    marco_divisiones,
    textvariable=partidas_var,
    font=("Segoe UI", 10, "bold")
).pack(
    side="left"
)


tk.Button(
    marco_divisiones,
    text="✂ DIVIDIR AQUÍ",
    command=dividir_aqui,
    width=18
).pack(
    side="right"
)


tk.Button(
    marco_divisiones,
    text="Quitar división",
    command=quitar_division,
    width=18
).pack(
    side="right",
    padx=(0, 10)
)



# ---------------- INFORMACIÓN DE PARTIDAS ----------------

marco_info_partidas = tk.LabelFrame(
    tab_procesar,
    text="Información de partidas",
    font=("Segoe UI", 10, "bold")
)

marco_info_partidas.pack(
    fill="x",
    padx=30,
    pady=(0, 8)
)

marco_partidas_contenido = tk.Frame(
    marco_info_partidas
)

marco_partidas_contenido.pack(
    fill="x",
    padx=5,
    pady=5
)

tk.Label(
    marco_partidas_contenido,
    text="Selecciona una carpeta para definir las partidas.",
    fg="#666666"
).pack(
    anchor="w",
    padx=8,
    pady=8
)


# ---------------- OPCIONES DE PROCESAMIENTO ----------------

marco_opciones = tk.LabelFrame(
    tab_procesar,
    text="Opciones de procesamiento",
    font=("Segoe UI", 10, "bold")
)

marco_opciones.pack(
    fill="x",
    padx=30,
    pady=(0, 8)
)

combinar_srt_var = tk.BooleanVar(
    value=False
)

tk.Checkbutton(
    marco_opciones,
    text=(
        "Combinar SRT existentes "
        "(opcional; recomendado dejar desmarcado)"
    ),
    variable=combinar_srt_var
).pack(
    anchor="w",
    padx=10,
    pady=7
)


# ---------------- PROGRESO ----------------

barra = ttk.Progressbar(
    tab_procesar,
    orient="horizontal",
    mode="determinate",
    maximum=100
)

barra.pack(
    fill="x",
    padx=30,
    pady=(10, 5)
)


# ---------------- ESTADO ----------------

estado_var = tk.StringVar(
    value="Selecciona una carpeta de partida."
)


tk.Label(
    tab_procesar,
    textvariable=estado_var,
    font=("Segoe UI", 11, "bold")
).pack(
    pady=10
)


# ---------------- BOTÓN ----------------

boton_procesar = tk.Button(
    tab_procesar,
    text="PROCESAR PARTIDAS",
    command=procesar_partida,
    state="disabled",
    font=("Segoe UI", 11, "bold"),
    width=25,
    height=2,
    bg=COLOR_PRIMARIO,
    fg="white",
    activebackground=COLOR_PRIMARIO_ACTIVO,
    activeforeground="white",
    relief="flat",
    cursor="hand2"
)

boton_procesar.pack(
    pady=(5, 25)
)



# ---------------- HISTORIAL / CATÁLOGO ----------------

tk.Label(
    tab_historial,
    text="HISTORIAL DE PARTIDAS",
    font=("Segoe UI", 22, "bold"),
    fg=COLOR_TEXTO,
    bg=COLOR_FONDO
).pack(pady=(25, 3))

tk.Label(
    tab_historial,
    text="Catálogo, publicación y almacenamiento de tus partidas · v1.0",
    font=("Segoe UI", 10),
    fg=COLOR_SECUNDARIO,
    bg=COLOR_FONDO
).pack(pady=(0, 18))

historial_resumen_var = tk.StringVar(value="Partidas registradas: 0")
tk.Label(
    tab_historial,
    textvariable=historial_resumen_var,
    font=("Segoe UI", 10, "bold")
).pack(anchor="w", padx=30, pady=(0, 8))

# Filtros de historial
marco_filtros_historial = tk.LabelFrame(
    tab_historial,
    text="Buscar y filtrar"
)
marco_filtros_historial.pack(fill="x", padx=30, pady=(0, 10))

historial_busqueda_var = tk.StringVar()
historial_mapa_var = tk.StringVar(value="Todos")
historial_agente_var = tk.StringVar(value="Todos")
historial_publicacion_var = tk.StringVar(value="Todos")
historial_almacenamiento_var = tk.StringVar(value="Todos")

tk.Label(marco_filtros_historial, text="Buscar:").grid(
    row=0, column=0, padx=(10, 5), pady=8, sticky="w"
)
entrada_busqueda_historial = tk.Entry(
    marco_filtros_historial,
    textvariable=historial_busqueda_var,
    width=26
)
entrada_busqueda_historial.grid(
    row=0, column=1, padx=(0, 12), pady=8, sticky="ew"
)

tk.Label(marco_filtros_historial, text="Mapa:").grid(
    row=0, column=2, padx=(0, 5), pady=8
)
combo_filtro_mapa = ttk.Combobox(
    marco_filtros_historial,
    textvariable=historial_mapa_var,
    values=["Todos"] + MAPAS_VALORANT,
    state="readonly",
    width=15
)
combo_filtro_mapa.grid(row=0, column=3, padx=(0, 12), pady=8)

tk.Label(marco_filtros_historial, text="Agente:").grid(
    row=0, column=4, padx=(0, 5), pady=8
)
combo_filtro_agente = ttk.Combobox(
    marco_filtros_historial,
    textvariable=historial_agente_var,
    values=["Todos"] + AGENTES_VALORANT,
    state="readonly",
    width=15
)
combo_filtro_agente.grid(row=0, column=5, padx=(0, 12), pady=8)

tk.Label(marco_filtros_historial, text="Publicación:").grid(
    row=0, column=6, padx=(0, 5), pady=8
)
combo_filtro_publicacion = ttk.Combobox(
    marco_filtros_historial,
    textvariable=historial_publicacion_var,
    values=["Todos"] + ESTADOS_PUBLICACION,
    state="readonly",
    width=17
)
combo_filtro_publicacion.grid(row=0, column=7, padx=(0, 10), pady=8)

tk.Label(marco_filtros_historial, text="Almacenamiento:").grid(
    row=0, column=8, padx=(0, 5), pady=8
)
combo_filtro_almacenamiento = ttk.Combobox(
    marco_filtros_historial,
    textvariable=historial_almacenamiento_var,
    values=["Todos"] + ESTADOS_ALMACENAMIENTO,
    state="readonly",
    width=20
)
combo_filtro_almacenamiento.grid(row=0, column=9, padx=(0, 10), pady=8)

tk.Button(
    marco_filtros_historial,
    text="Limpiar",
    command=limpiar_filtros_historial,
    width=10
).grid(row=0, column=10, padx=(0, 10), pady=8)

marco_filtros_historial.columnconfigure(1, weight=1)

historial_busqueda_var.trace_add("write", actualizar_historial)
combo_filtro_mapa.bind("<<ComboboxSelected>>", actualizar_historial)
combo_filtro_agente.bind("<<ComboboxSelected>>", actualizar_historial)
combo_filtro_publicacion.bind("<<ComboboxSelected>>", actualizar_historial)
combo_filtro_almacenamiento.bind("<<ComboboxSelected>>", actualizar_historial)

marco_historial = tk.Frame(tab_historial)
marco_historial.pack(fill="both", expand=True, padx=30, pady=(0, 14))

columnas_historial = ("fecha", "mapa", "agente", "clips", "publicacion", "almacenamiento", "origen", "mp4", "video")
historial_tree = ttk.Treeview(
    marco_historial,
    columns=columnas_historial,
    show="headings",
    selectmode="browse"
)

historial_tree.heading("fecha", text="Fecha")
historial_tree.heading("mapa", text="Mapa")
historial_tree.heading("agente", text="Agente")
historial_tree.heading("clips", text="Clips")
historial_tree.heading("publicacion", text="Publicación")
historial_tree.heading("almacenamiento", text="Almacenamiento")
historial_tree.heading("origen", text="Clips origen")
historial_tree.heading("mp4", text="MP4")
historial_tree.heading("video", text="Video")

historial_tree.column("fecha", width=135, anchor="center")
historial_tree.column("mapa", width=110, anchor="center")
historial_tree.column("agente", width=110, anchor="center")
historial_tree.column("clips", width=55, anchor="center")
historial_tree.column("publicacion", width=120, anchor="center")
historial_tree.column("almacenamiento", width=140, anchor="center")
historial_tree.column("origen", width=90, anchor="center")
historial_tree.column("mp4", width=85, anchor="center")
historial_tree.column("video", width=280)

scroll_historial = ttk.Scrollbar(
    marco_historial,
    orient="vertical",
    command=historial_tree.yview
)
historial_tree.configure(yscrollcommand=scroll_historial.set)

scroll_historial.pack(side="right", fill="y")
historial_tree.pack(side="left", fill="both", expand=True)
historial_tree.bind("<Double-Button-1>", abrir_video_historial)
historial_tree.bind("<<TreeviewSelect>>", actualizar_detalle_almacenamiento)

# Estados visuales del historial. Los tags se aplican al refrescar la tabla.
historial_tree.tag_configure("estado_ok", background="#F0FDF4")
historial_tree.tag_configure("estado_atencion", background="#FFFBEB")
historial_tree.tag_configure("estado_ausente", background="#FEF2F2")

marco_almacenamiento = tk.LabelFrame(
    tab_historial,
    text="Almacenamiento"
)
marco_almacenamiento.pack(fill="x", padx=30, pady=(0, 10))

almacenamiento_detalle_var = tk.StringVar(
    value="Selecciona una partida para analizar sus archivos."
)
tk.Label(
    marco_almacenamiento,
    textvariable=almacenamiento_detalle_var,
    anchor="w",
    justify="left"
).pack(fill="x", padx=10, pady=(8, 4))

controles_almacenamiento = tk.Frame(marco_almacenamiento)
controles_almacenamiento.pack(fill="x", padx=10, pady=(0, 8))

eliminar_srt_var = tk.BooleanVar(value=False)

tk.Checkbutton(
    controles_almacenamiento,
    text="Incluir SRT individuales asociados a los clips",
    variable=eliminar_srt_var
).pack(side="left")

tk.Button(
    controles_almacenamiento,
    text="LIBERAR ESPACIO",
    command=liberar_espacio_historial,
    width=18,
    font=("Segoe UI", 9, "bold"),
    bg=COLOR_PELIGRO,
    fg="white",
    activebackground=COLOR_PELIGRO_ACTIVO,
    activeforeground="white",
    relief="flat",
    cursor="hand2"
).pack(side="right")

acciones_historial = tk.Frame(tab_historial)
acciones_historial.pack(fill="x", padx=30, pady=(0, 25))

tk.Button(
    acciones_historial,
    text="Abrir video",
    command=abrir_video_historial,
    width=16
).pack(side="left")

tk.Button(
    acciones_historial,
    text="Abrir carpeta",
    command=abrir_carpeta_historial,
    width=16
).pack(side="left", padx=(10, 0))

tk.Label(
    acciones_historial,
    text="Publicación:"
).pack(side="left", padx=(20, 5))

historial_nueva_publicacion_var = tk.StringVar(value="Procesado")
ttk.Combobox(
    acciones_historial,
    textvariable=historial_nueva_publicacion_var,
    values=ESTADOS_PUBLICACION,
    state="readonly",
    width=17
).pack(side="left")

tk.Label(
    acciones_historial,
    text="Almacenamiento:"
).pack(side="left", padx=(12, 5))

historial_nuevo_almacenamiento_var = tk.StringVar(value="Local")
ttk.Combobox(
    acciones_historial,
    textvariable=historial_nuevo_almacenamiento_var,
    values=ESTADOS_ALMACENAMIENTO,
    state="readonly",
    width=19
).pack(side="left")

tk.Button(
    acciones_historial,
    text="Guardar estados",
    command=cambiar_estados_historial,
    width=14
).pack(side="left", padx=(8, 0))

tk.Button(
    acciones_historial,
    text="Localizar MP4",
    command=localizar_video_historial,
    width=13
).pack(side="left", padx=(8, 0))

# Ayuda en una fila independiente para evitar que se superponga o
# se recorte cuando la ventana tiene menos ancho disponible.
ayuda_historial = tk.Label(
    tab_historial,
    text="Doble clic sobre una partida para abrir su MP4.",
    fg=COLOR_SECUNDARIO,
    bg=COLOR_FONDO,
    anchor="e",
    font=("Segoe UI", 9)
)
ayuda_historial.pack(fill="x", padx=30, pady=(0, 8))

# Cargar el catálogo persistente.
# v1.0: abrir Varchiver desde una carpeta sin catálogo ya no crea
# automáticamente un JSON vacío. El archivo se crea cuando realmente hay
# información que guardar.
_catalogo_existia = ARCHIVO_CATALOGO.exists()

cargar_catalogo()

_catalogo_antes_migracion = json.dumps(
    catalogo_partidas,
    ensure_ascii=False,
    sort_keys=True
)

for _partida in catalogo_partidas:
    migrar_estados_partida(_partida)

_catalogo_despues_migracion = json.dumps(
    catalogo_partidas,
    ensure_ascii=False,
    sort_keys=True
)

if (
    _catalogo_existia
    or catalogo_partidas
    or _catalogo_antes_migracion != _catalogo_despues_migracion
):
    guardar_catalogo()

actualizar_historial()

# ============================================================
# EJECUTAR
# ============================================================

ventana.mainloop()