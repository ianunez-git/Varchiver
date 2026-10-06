# Valorant Archiver

Aplicación personal para organizar, subtitular y archivar clips de
Valorant grabados mediante Outplayed / Overwolf.

El objetivo principal es conservar partidas y momentos antiguos en
YouTube, reduciendo el espacio ocupado por clips individuales en el
disco.

------------------------------------------------------------------------

## Objetivo del proyecto

El flujo general es:

Outplayed ↓ Clips de Valorant ↓ Organización por partida ↓ Subtitle
Edit + Whisper ↓ Valorant Archiver ↓ Video final + subtítulos ↓ YouTube

Los clips originales nunca deben modificarse ni eliminarse
automáticamente.

------------------------------------------------------------------------

# Herramientas utilizadas

## Outplayed / Overwolf

Origen de los clips.

Los archivos normalmente tienen nombres similares a:

Valorant_09-24-2024_3-4-53-632.mp4

El nombre contiene:

-   Fecha
-   Hora
-   Minuto
-   Segundo
-   Milisegundos

Una carpeta de Outplayed NO necesariamente representa una sola partida.

Una misma carpeta puede contener clips de varias partidas.

------------------------------------------------------------------------

## Subtitle Edit

Utilizado para generar y revisar los subtítulos.

Configuración actualmente recomendada:

Engine: Whisper CPP

Backend: cuBLAS

Idioma: Spanish

Modelo: Large

VAD: Activado

Post processing: Activado

Translate to English: Desactivado

Hardware probado:

CPU: AMD Ryzen 7 5700X

GPU: NVIDIA GeForce RTX 4060

RAM: 16 GB

El uso de cuBLAS permite utilizar la GPU NVIDIA y reduce
considerablemente el tiempo de transcripción.

------------------------------------------------------------------------

# Flujo de subtítulos

Para cada clip:

clip.mp4 clip.srt

Ejemplo:

Valorant_09-24-2024_3-4-53-632.mp4 Valorant_09-24-2024_3-4-53-632.srt

Whisper genera una primera transcripción.

Después se recomienda revisar rápidamente:

-   Frases mal reconocidas
-   Español chileno / modismos
-   Callouts de Valorant
-   Nombres de agentes
-   Voces del propio juego
-   Subtítulos falsos provocados por sonidos
-   Errores importantes de sincronización

No es necesario que los subtítulos sean perfectos.

El objetivo es conservar las conversaciones y momentos relevantes.

------------------------------------------------------------------------

# FFmpeg

FFmpeg se utiliza para unir los clips sin recodificarlos.

Esto permite:

-   Evitar pérdida adicional de calidad
-   Procesar los videos rápidamente
-   Mantener los archivos originales intactos

La operación utilizada internamente es equivalente a:

ffmpeg -f concat -safe 0 -i lista.txt -c copy salida.mp4

FFprobe se utiliza para obtener la duración exacta de cada clip.

------------------------------------------------------------------------

# Valorant Archiver

Aplicación desarrollada en Python.

Versión de Python utilizada durante el desarrollo:

Python 3.12.10

Interfaz:

Tkinter

Dependencias externas:

-   FFmpeg
-   FFprobe

No se requieren actualmente librerías adicionales de Python.

------------------------------------------------------------------------

# Funcionalidad validada

## v0.1

-   Detectar clips MP4.
-   Reconocer nombres de Outplayed.
-   Ordenar clips por hora.
-   Detectar archivos SRT correspondientes.

## v0.2

-   Obtener duración mediante FFprobe.
-   Concatenar clips mediante FFmpeg.
-   Combinar múltiples archivos SRT.
-   Recalcular automáticamente los timestamps.
-   Mantener sincronización entre video y subtítulos.

## v0.3

Interfaz gráfica inicial.

Permite:

-   Seleccionar una carpeta de Outplayed.
-   Detectar clips.
-   Mostrar clips encontrados.
-   Comprobar existencia de SRT.
-   Procesar una partida mediante un botón.
-   Mostrar progreso.
-   Generar MP4 final.
-   Generar SRT final.
-   Avisar antes de reemplazar resultados existentes.

Prueba validada:

4 clips 32 subtítulos combinados

Resultado:

Video y subtítulos sincronizados correctamente.

------------------------------------------------------------------------

# Problema descubierto

Inicialmente se asumió:

1 carpeta Outplayed = 1 partida

Esto NO siempre es correcto.

Ejemplo real:

Valorant_09-06-2026_23-28-7-379

Contiene:

27 clips

Dentro de la misma carpeta existen al menos:

Partida 1: - Ascent - Phoenix - 13 clips

Partida 2: - Split - Sage - 14 clips

Por lo tanto, Valorant Archiver debe permitir separar manualmente los
clips en distintas partidas.

------------------------------------------------------------------------

# Cambio de fecha / medianoche

Una carpeta puede contener clips correspondientes a dos fechas.

Ejemplo:

09-06-2026 23:59 ↓ 09-07-2026 00:01

Por lo tanto, NO se debe ordenar únicamente utilizando la hora.

El orden debe calcularse utilizando:

Fecha + Hora + Minuto + Segundo + Milisegundo

------------------------------------------------------------------------

# v0.4 - Próxima versión

Objetivos:

1.  Leer todos los clips de una carpeta.

2.  Extraer fecha y hora completas desde el nombre.

3.  Ordenarlos cronológicamente.

4.  Soportar correctamente sesiones que atraviesan medianoche.

5.  Permitir dividir los clips en múltiples partidas.

6.  Permitir asignar información opcional:

    -   Mapa
    -   Agente

7.  Generar un video y un SRT independiente para cada partida.

Ejemplo:

2026-09-06_23-37_Haven_Sage.mp4 2026-09-06_23-37_Haven_Sage.srt

2026-09-07_00-01_Ascent_Phoenix.mp4 2026-09-07_00-01_Ascent_Phoenix.srt

------------------------------------------------------------------------

# Diseño futuro de la interfaz

La aplicación debería mostrar una cronología similar a:

23:37:03 Clip 1 23:40:42 Clip 2 23:42:12 Clip 3 ...

--- NUEVA PARTIDA ---

00:01:11 Clip 15 00:08:56 Clip 16 ...

El usuario decidirá dónde comienza una nueva partida.

La aplicación podrá sugerir separaciones utilizando diferencias
temporales entre clips, pero la decisión final será manual.

------------------------------------------------------------------------

# Información de cada partida

Idealmente cada grupo podrá contener:

Fecha Hora aproximada Mapa Agente Cantidad de clips

Ejemplo:

Partida 1

Fecha: 06-09-2026

Hora: 23:37

Mapa: Haven

Agente: Sage

Clips: 14

------------------------------------------------------------------------

# Miniaturas

Mejora futura.

FFmpeg puede extraer un fotograma de cada clip.

Esto permitiría mostrar miniaturas dentro de Valorant Archiver para
facilitar la identificación de:

-   Mapa
-   Agente
-   Cambio de partida

Esta funcionalidad NO es necesaria para v0.4 inicial.

------------------------------------------------------------------------

# Principio de seguridad

Valorant Archiver debe mantener un comportamiento seguro y controlado.

Nunca debe:

-   Eliminar clips originales automáticamente al procesar.
-   Modificar MP4 originales.
-   Modificar SRT originales.
-   Mover archivos sin confirmación.
-   Sobrescribir resultados sin advertencia.
-   Eliminar una carpeta completa de Outplayed para liberar espacio.

La liberación de espacio es una acción manual y explícita.

Cuando el usuario utiliza `LIBERAR ESPACIO`:

-   Solo se consideran los clips registrados para la partida
    seleccionada.
-   Se muestra una vista previa de los archivos afectados.
-   Se requieren dos confirmaciones.
-   Los archivos se envían a la Papelera de reciclaje de Windows.
-   El MP4 final no se elimina.
-   Los archivos JSON de configuración y catálogo no se eliminan.

La eliminación definitiva se realiza manualmente al vaciar la Papelera.

------------------------------------------------------------------------

# Resultado destinado a YouTube

Cada partida terminará idealmente como:

Partida.mp4 Partida.srt

El MP4 se sube normalmente a YouTube.

El SRT se añade como pista de subtítulos.

Esto permite que los subtítulos sean opcionales mediante CC y evita
tener que incrustarlos permanentemente en el video.

------------------------------------------------------------------------

# Objetivo futuro

Procesar una carpeta completa como:

Outplayed/Valorant/

Valorant Archiver debería detectar automáticamente todas las carpetas y
mostrar estados similares a:

LISTA FALTAN SRT YA PROCESADA REQUIERE SEPARAR PARTIDAS

De esta forma se podrán procesar grandes cantidades de clips antiguos
sin administrar manualmente cada archivo.

------------------------------------------------------------------------

# Filosofía del proyecto

Automatizar todo aquello que sea mecánico:

-   Ordenar clips
-   Calcular duraciones
-   Concatenar videos
-   Recalcular timestamps
-   Combinar subtítulos
-   Generar nombres

Mantener intervención humana donde aporta valor:

-   Identificar partidas
-   Identificar mapa
-   Identificar agente
-   Revisar conversaciones
-   Corregir subtítulos

## v0.4

Implementado y validado:

-   Orden cronológico mediante fecha + hora completa.
-   Soporte para sesiones que atraviesan medianoche.
-   Apertura de clips mediante doble clic.
-   División manual de una carpeta en múltiples partidas.
-   Identificación visual mediante P1, P2, P3...
-   Separadores visuales entre partidas.
-   Eliminación manual de divisiones.
-   Contador de partidas definidas.
-   Los archivos originales permanecen intactos.

Caso de prueba validado:

-   27 clips en una misma carpeta de Outplayed.
-   2 partidas diferentes.
-   Sesión atravesando medianoche.
-   División manual correcta entre ambas partidas.

------------------------------------------------------------------------

# Historial de versiones

## v0.5 --- División manual de partidas

### Nuevas funciones

-   Se agregó soporte para múltiples partidas dentro de una misma
    carpeta de Outplayed.
-   Los clips pueden dividirse manualmente utilizando "DIVIDIR AQUÍ".
-   Se agregó la opción "Quitar división".
-   Cada clip muestra a qué partida pertenece: P1, P2, P3, etc.
-   Se agregó un resumen con la cantidad de partidas detectadas.
-   Los clips pueden abrirse directamente desde Valorant Archiver.

### Metadatos por partida

Cada partida puede registrar:

-   Mapa
-   Agente

Ejemplo:

P1 - 13 clips - Ascent - Phoenix

P2 - 14 clips - Split - Sage

------------------------------------------------------------------------

## v0.6 --- Procesamiento de múltiples partidas

### Nuevas funciones

-   Cada partida definida puede procesarse independientemente.
-   Cada partida genera su propio archivo MP4.
-   Cada partida genera su propio archivo SRT combinado.
-   Los archivos originales no son modificados.
-   Se utilizan los metadatos de mapa y agente para generar nombres de
    salida.

Ejemplo:

2026-09-06_23-37_Ascent_Phoenix.mp4 2026-09-06_23-37_Ascent_Phoenix.srt

2026-09-07_00-08_Split_Sage.mp4 2026-09-07_00-08_Split_Sage.srt

### Subtítulos

Valorant Archiver detecta automáticamente los archivos SRT asociados a
cada MP4.

Actualmente muestra:

-   Cantidad total de clips.
-   Cantidad de SRT encontrados.
-   Clips que tienen SRT.
-   Clips que no tienen SRT.

------------------------------------------------------------------------

## v0.6.1 --- En desarrollo

### Cambio en el manejo de subtítulos

Los archivos SRT pasan a ser opcionales.

La ausencia de un SRT NO debe impedir procesar una partida.

Si un clip no tiene SRT:

1.  El MP4 se incluye normalmente en el video final.
2.  Su duración se suma al timeline.
3.  Durante ese fragmento simplemente no habrá subtítulos.
4.  Los subtítulos del siguiente clip deben mantener su sincronización.

Ejemplo:

Clip 1 + SRT Clip 2 + SRT Clip 3 SIN SRT Clip 4 + SRT

Resultado:

Video final: \[Clip 1\]\[Clip 2\]\[Clip 3\]\[Clip 4\]

SRT final: \[Subs 1\]\[Subs 2\]\[silencio\]\[Subs 4\]

### Interfaz

Si faltan subtítulos, el programa mostrará una advertencia:

"Falta X archivo(s) SRT. Los clips sin SRT se procesarán igualmente."

La advertencia será informativa y NO bloqueará el botón "PROCESAR
PARTIDAS".

### Selector de mapas y agentes

Pendiente mejorar el comportamiento de los desplegables.

Objetivo:

-   Abrir la lista normalmente.
-   Poder navegar con mouse o teclado.
-   Al escribir letras, saltar a la coincidencia correspondiente.
-   No utilizar autocompletado invasivo dentro del campo.

------------------------------------------------------------------------

# Próximas mejoras consideradas

## Persistencia de proyecto

Guardar automáticamente:

-   Divisiones P1, P2, P3...
-   Mapa de cada partida.
-   Agente de cada partida.

De esta manera, al volver a abrir una carpeta ya procesada, Valorant
Archiver podrá recuperar la organización anterior.

## Flujo esperado

Outplayed ↓ Clips MP4 ↓ Whisper / Subtitle Edit ↓ SRT individuales
(opcionales) ↓ Valorant Archiver ↓ Separación P1 / P2 / P3 ↓ Mapa +
Agente ↓ FFmpeg ↓ MP4 final por partida + SRT combinado por partida

------------------------------------------------------------------------

## v0.7 --- Simplificación del flujo de procesamiento

A partir de esta versión, Valorant Archiver se centra principalmente en
organizar y unir los clips de cada partida.

### Nuevo flujo principal

Outplayed ↓ Clips MP4 ↓ Valorant Archiver ↓ Separación P1 / P2 / P3... ↓
Mapa + Agente ↓ FFmpeg ↓ MP4 final por partida ↓ Subtitle Edit
(opcional) ↓ Generación/revisión de subtítulos solo cuando sea necesario

### Cambio en el manejo de subtítulos

Los subtítulos dejan de ser un requisito para procesar una partida.

Se agregó la opción:

-   [ ] Combinar SRT existentes

Esta opción está desactivada por defecto.

Con la opción desactivada:

-   Los clips se unen normalmente.
-   Se genera solamente el MP4 final de cada partida.
-   No se procesan ni combinan los SRT individuales.

Con la opción activada:

-   Se mantiene disponible la funcionalidad desarrollada anteriormente.
-   Los SRT existentes se combinan.
-   Los clips sin SRT siguen formando parte del video.

### Motivo del cambio

La combinación de múltiples SRT individuales puede producir pequeños
desfases entre clips.

Se decidió simplificar el flujo y generar subtítulos directamente sobre
el MP4 final utilizando Subtitle Edit + Whisper/cuBLAS cuando sea
necesario.

Esto reduce:

-   Complejidad del procesamiento.
-   Posibles problemas de sincronización.
-   Cantidad de archivos que necesitan transcripción.
-   Trabajo manual innecesario.

------------------------------------------------------------------------

## v0.7.1 --- Persistencia de partidas

### Nueva función: configuración persistente

Valorant Archiver ahora recuerda cómo fue organizada una carpeta.

Al trabajar con una carpeta se crea automáticamente:

.valorant_archiver.json

Este archivo se almacena dentro de la misma carpeta de clips.

### Información almacenada

El archivo guarda:

-   Divisiones entre partidas.
-   Mapa seleccionado para cada partida.
-   Agente seleccionado para cada partida.

Ejemplo:

P1 - 13 clips - Ascent - Phoenix

P2 - 14 clips - Split - Sage

### Recuperación automática

Al volver a abrir una carpeta previamente configurada, Valorant Archiver
lee automáticamente `.valorant_archiver.json`.

Se restauran:

-   P1 / P2 / P3...
-   Posición de las divisiones.
-   Mapa.
-   Agente.

Por lo tanto, ya no es necesario volver a organizar manualmente una
carpeta cada vez que se inicia el programa.

### Guardado automático

No es necesario utilizar un botón "Guardar".

La configuración se actualiza automáticamente cuando:

-   Se crea una división.
-   Se elimina una división.
-   Se modifica el mapa.
-   Se modifica el agente.

### Seguridad

El archivo de configuración:

-   No modifica los MP4 originales.
-   No modifica los SRT originales.
-   Solo afecta a la carpeta seleccionada.
-   No recorre otras carpetas de Outplayed.
-   No afecta clips de otros videojuegos.

Si el archivo JSON no existe, Valorant Archiver funciona normalmente
como una carpeta nueva.

------------------------------------------------------------------------

# Historial reciente de versiones

## v0.7.2 --- Búsqueda en desplegables

Se mejoraron los selectores de Mapa y Agente.

Ahora permiten:

-   Escribir parte del nombre.
-   Buscar por coincidencia, no solamente por prefijo.
-   Mostrar las coincidencias en el desplegable.
-   Mantener únicamente valores válidos del catálogo.

Ejemplos:

-   `pho` → Phoenix
-   `ill` → Killjoy
-   `asc` → Ascent
-   `spl` → Split

La funcionalidad fue validada correctamente.

------------------------------------------------------------------------

## v0.8.0 --- Historial de partidas

Se incorporó una pestaña `Historial`.

Cada partida procesada registra:

-   Fecha y hora.
-   Mapa.
-   Agente.
-   Cantidad de clips.
-   Nombre del MP4 final.
-   Ruta del MP4.
-   Carpeta de origen.

El catálogo se almacena en:

`valorant_archiver_catalogo.json`

El historial permanece disponible después de cerrar y volver a abrir
Valorant Archiver.

También permite:

-   Abrir el MP4.
-   Abrir su carpeta.
-   Abrir el MP4 mediante doble clic.

------------------------------------------------------------------------

## v0.8.1 --- Estados, búsqueda y filtros

Se incorporó inicialmente un estado de gestión por partida.

También se agregaron:

-   Búsqueda libre.
-   Filtro por mapa.
-   Filtro por agente.
-   Filtro por estado.
-   Persistencia de los estados.
-   Conservación del estado al reprocesar una partida.

Esta estructura fue posteriormente reemplazada en v0.9 por estados
separados de publicación y almacenamiento.

------------------------------------------------------------------------

## v0.8.2 --- Análisis de almacenamiento

Valorant Archiver comenzó a registrar la lista exacta de clips fuente
utilizados por cada partida.

Esto permite calcular:

-   Cantidad de clips originales disponibles.
-   Tamaño de los clips originales.
-   Tamaño del MP4 final.
-   Espacio potencialmente recuperable.

La identificación se realiza por partida y no por carpeta completa.

Esto es importante porque P1, P2, P3, etc. pueden compartir una misma
carpeta física de Outplayed.

------------------------------------------------------------------------

## v0.8.3 --- Liberación segura de espacio

Se incorporó `LIBERAR ESPACIO`.

Antes de realizar la operación se muestra:

-   Partida seleccionada.
-   Cantidad de MP4 originales.
-   Cantidad de SRT incluidos.
-   Tamaño total.
-   Vista previa de archivos.

Los SRT individuales son opcionales mediante una casilla independiente.

Se requieren dos confirmaciones antes de continuar.

El MP4 final, `.valorant_archiver.json` y
`valorant_archiver_catalogo.json` quedan fuera de la operación.

### v0.8.3.1 --- Hotfix de Papelera

La primera implementación utilizaba PowerShell y produjo un error al
intentar enviar archivos a la Papelera.

Se reemplazó ese mecanismo por la API nativa de Windows.

Resultado validado:

-   13 MP4 + 13 SRT enviados correctamente a la Papelera.
-   Aproximadamente 1.33 GB trasladados.
-   Los archivos de la otra partida permanecieron intactos.
-   El MP4 final permaneció intacto.
-   El historial detectó correctamente que los clips fuente ya no
    estaban disponibles.

------------------------------------------------------------------------

## v0.9.0 --- Ciclo de vida de las partidas

El estado único de v0.8 fue dividido en dos dimensiones independientes.

### Estado de publicación

-   Procesado.
-   Subido a YouTube.

### Estado de almacenamiento

-   Local.
-   Respaldado.
-   Clips eliminados.
-   Todo eliminado.
-   Archivo no encontrado.

Esto permite representar situaciones reales como:

``` text
Publicación:     Subido a YouTube
Almacenamiento: Clips eliminados
Clips origen:   0 B
MP4 final:      Disponible
```

Se agregó migración automática del catálogo generado por v0.8.x.

También se incorporaron filtros independientes por publicación y
almacenamiento.

### MP4 no encontrado

Si el MP4 final ya no existe en su ruta registrada, Valorant Archiver no
asume automáticamente qué ocurrió.

Puede:

-   Detectar el archivo como `Archivo no encontrado`.
-   Permitir localizarlo nuevamente.
-   Registrar que fue eliminado.
-   Mantener la advertencia pendiente.

------------------------------------------------------------------------

## v0.9.1 --- Mejora del flujo de relocalización

Se corrigió el flujo utilizado cuando un MP4 final no se encuentra.

Anteriormente, después de seleccionar `Sí` para localizar el archivo, el
historial podía perder la selección y solicitar que la partida se
seleccionara nuevamente.

Ahora:

``` text
MP4 no encontrado
        ↓
        Sí
        ↓
Selector de archivos de Windows
        ↓
Seleccionar MP4
        ↓
Actualizar ruta
        ↓
Historial actualizado
```

La partida ya identificada se conserva durante todo el proceso.

El selector intenta abrir inicialmente la ubicación anterior del MP4 o,
cuando sea posible, la carpeta de origen.

Esta funcionalidad fue validada correctamente.

------------------------------------------------------------------------

# Estado actual del proyecto

Versión estable actual:

**Valorant Archiver v0.9.1**

Funciones validadas:

-   Detección y orden cronológico de clips MP4.
-   Soporte para sesiones que atraviesan medianoche.
-   Apertura individual de clips.
-   División manual P1 / P2 / P3...
-   Eliminación manual de divisiones.
-   Metadatos de mapa y agente.
-   Búsqueda por coincidencia en los desplegables.
-   Persistencia automática mediante `.valorant_archiver.json`.
-   Recuperación automática de divisiones y metadatos.
-   Procesamiento independiente de cada partida.
-   Unión mediante FFmpeg.
-   Nombres de salida por fecha, hora, mapa y agente.
-   SRT opcionales.
-   Historial persistente de partidas.
-   Búsqueda y filtros en el historial.
-   Estados separados de publicación y almacenamiento.
-   Registro exacto de clips fuente por partida.
-   Cálculo de espacio utilizado y potencialmente recuperable.
-   Liberación segura de clips mediante Papelera de reciclaje.
-   Inclusión opcional de SRT en la liberación.
-   Detección de MP4 final ausente.
-   Relocalización manual de MP4.
-   Registro de MP4 eliminado.
-   Compatibilidad/migración del catálogo de versiones v0.8.x.

------------------------------------------------------------------------

# Flujo actual

``` text
Outplayed
    ↓
Clips de Valorant
    ↓
Seleccionar carpeta
    ↓
Separar P1 / P2 / P3...
    ↓
Mapa + Agente
    ↓
FFmpeg
    ↓
MP4 final por partida
    ↓
Historial persistente
    ↓
Subtitle Edit / Whisper (opcional)
    ↓
YouTube
    ↓
Respaldo opcional
    ↓
Liberar clips originales
    ↓
Papelera de reciclaje
    ↓
Eliminación definitiva manual
```

Los subtítulos ya no forman parte obligatoria del procesamiento
principal.

Cuando son necesarios, se recomienda generarlos o revisarlos sobre el
MP4 final utilizando Subtitle Edit + Whisper/cuBLAS.

------------------------------------------------------------------------

# Camino hacia v1.0

El núcleo funcional del proyecto se considera prácticamente completo.

Antes de v1.0 se realizará una revisión general enfocada en:

1.  Probar Valorant Archiver con más carpetas y partidas reales.
2.  Detectar casos límite y errores de uso cotidiano.
3.  Revisar mensajes de advertencia y confirmación.
4.  Verificar comportamiento cuando faltan o se mueven archivos.
5.  Revisar persistencia y compatibilidad del catálogo.
6.  Evitar agregar funcionalidades que no aporten al objetivo principal.
7.  Realizar la etapa final de interfaz y presentación.
8.  Evaluar empaquetado como aplicación ejecutable de Windows.

------------------------------------------------------------------------

# Requerimientos no funcionales / mejoras estéticas pendientes

Estas mejoras se reservan para la etapa final y no tienen prioridad
sobre la estabilidad funcional.

## Identidad visual

-   Diseñar un logo para Valorant Archiver.
-   Incorporar un icono propio para la aplicación.
-   Utilizar el icono en la ventana y, posteriormente, en el ejecutable.

## Interfaz

-   Mejorar visualmente la separación entre `Procesar clips` e
    `Historial`.
-   Dar mayor jerarquía visual a las pestañas principales.
-   Uniformar márgenes, tamaños y espaciados.
-   Revisar tipografías y legibilidad.
-   Mejorar la presentación visual de los estados.
-   Diferenciar visualmente acciones normales de acciones sensibles como
    `LIBERAR ESPACIO`.
-   Mejorar la adaptación a distintos tamaños de ventana.
-   Mantener una interfaz simple y consistente.

## Experiencia de uso

-   Indicar de forma más visible cuando se recuperó una configuración
    existente.
-   Evaluar recordar la última carpeta utilizada.
-   Evaluar un acceso directo para abrir la carpeta de salida.
-   Revisar navegación mediante teclado.
-   Mantener diálogos y acciones con la menor cantidad posible de pasos
    innecesarios.

------------------------------------------------------------------------

# Posibles mejoras posteriores a v1.0

Estas funciones no son requisitos para completar la primera versión
estable:

-   Miniaturas de clips.
-   Sugerencias automáticas de separación según diferencias temporales.
-   Procesamiento masivo de múltiples carpetas.
-   Catálogo más avanzado.
-   Integración específica con respaldos externos.
-   Soporte para otros videojuegos de Outplayed.

Valorant continúa siendo el objetivo principal de la aplicación.

------------------------------------------------------------------------

# Objetivo de v1.0

Valorant Archiver v1.0 debe permitir completar de forma segura y
ordenada el ciclo:

**clips de Outplayed → organización por partida → MP4 final → historial
→ YouTube → liberación de almacenamiento**

La prioridad es mantener el programa simple, confiable y útil para el
flujo real de archivo de partidas.

## Estado actual --- Varchiver v1.0

**Varchiver v1.0** es la primera versión estable y empaquetable de
Valorant Archiver.

La aplicación permite organizar clips de Valorant generados por
Outplayed, dividir una carpeta en varias partidas, asignar mapa y
agente, fusionar los clips de cada partida en un MP4 final y mantener un
catálogo persistente de los videos procesados.

La versión 1.0 corresponde al núcleo funcional validado en la Release
Candidate v0.9.7. No se agregaron funciones nuevas entre el RC y v1.0:
el objetivo fue publicar como versión estable el flujo que ya había
superado las pruebas de uso real.

### Funciones principales

-   Selección de carpetas de Outplayed.
-   Detección y orden cronológico de clips mediante la fecha/hora del
    nombre.
-   División manual de una carpeta en múltiples partidas.
-   Persistencia de divisiones y metadatos mediante
    `.valorant_archiver.json`.
-   Identificación robusta de divisiones mediante los clips que inician
    cada partida, evitando divisiones fantasma cuando se eliminan
    archivos anteriores.
-   Selección y búsqueda de mapas y agentes.
-   Fusión de clips MP4 mediante FFmpeg.
-   Combinación opcional de SRT existentes.
-   Historial global de partidas procesadas.
-   Búsqueda y filtros por mapa, agente, publicación y almacenamiento.
-   Estados independientes de publicación y almacenamiento.
-   Análisis del espacio utilizado por clips originales y MP4 final.
-   Eliminación selectiva de clips originales mediante la Papelera de
    reciclaje de Windows.
-   Eliminación opcional de SRT individuales asociados a los clips.
-   Relocalización de un MP4 cuando fue renombrado o movido.
-   Interfaz visual con estados destacados y acciones sensibles
    diferenciadas.
-   Logo e icono propios de Varchiver.
-   Distribución como ejecutable de Windows mediante PyInstaller.

------------------------------------------------------------------------

## Flujo de uso recomendado

1.  Abrir **Varchiver.exe**.
2.  Seleccionar una carpeta de clips de Outplayed.
3.  Revisar el orden de los clips.
4.  Crear o quitar divisiones si la carpeta contiene más de una partida.
5.  Asignar mapa y agente a cada partida.
6.  Procesar las partidas.
7.  Revisar los MP4 generados.
8.  Consultar las partidas desde **Historial**.
9.  Cuando el MP4 final haya sido verificado, usar **LIBERAR ESPACIO**
    si se desea retirar los clips originales.
10. Vaciar manualmente la Papelera de reciclaje cuando se quiera
    recuperar definitivamente el espacio.

Varchiver nunca vacía automáticamente la Papelera de reciclaje.

------------------------------------------------------------------------

## Seguridad de archivos

El procesamiento normal no elimina los clips originales.

La acción **LIBERAR ESPACIO**:

-   actúa únicamente sobre los clips de origen registrados para la
    partida seleccionada;
-   permite incluir opcionalmente sus SRT individuales;
-   muestra una vista previa;
-   requiere confirmación;
-   envía los archivos a la Papelera de reciclaje;
-   no elimina el MP4 final;
-   no elimina `.valorant_archiver.json`;
-   no elimina `valorant_archiver_catalogo.json`;
-   no elimina clips pertenecientes a otra partida aunque compartan la
    misma carpeta física.

La eliminación permanente ocurre solamente cuando el usuario vacía
manualmente la Papelera de reciclaje de Windows.

------------------------------------------------------------------------

## Persistencia

Varchiver utiliza dos niveles de persistencia.

### Configuración por carpeta

Cada carpeta de Outplayed puede contener:

`.valorant_archiver.json`

Este archivo conserva divisiones y metadatos de las partidas de esa
carpeta.

Si se quiere conservar esa organización, no debe eliminarse.

### Catálogo global

El historial se almacena en:

`valorant_archiver_catalogo.json`

En la versión ejecutable, este archivo se guarda y busca en la misma
carpeta donde se encuentra `Varchiver.exe`.

Por esta razón se recomienda mantener:

``` text
ValorantArchiver/
├── Varchiver.exe
├── valorant_archiver_catalogo.json
└── README.md
```

Si se ejecuta Varchiver desde otra ubicación, esa ubicación se considera
su directorio de datos.

Desde v0.9.7, abrir el programa desde una carpeta sin catálogo no crea
un catálogo vacío solamente por iniciar la aplicación.

------------------------------------------------------------------------

## Estados del historial

### Publicación

-   `Procesado`
-   `Subido a YouTube`

### Almacenamiento

-   `Local`
-   `Respaldado`
-   `Clips eliminados`
-   `Todo eliminado`
-   `Archivo no encontrado`

Si el MP4 fue movido o renombrado, puede utilizarse **Localizar MP4**
para actualizar su ruta sin perder el historial.

------------------------------------------------------------------------

## Requisitos

### Para utilizar Varchiver.exe

-   Windows.
-   FFmpeg y FFprobe disponibles en `PATH`.
-   Acceso a las carpetas de clips de Outplayed.

El ejecutable generado con PyInstaller no necesita una instalación
independiente de Python.

### Para ejecutar el código fuente

-   Python 3.12 o compatible.
-   Tkinter.
-   FFmpeg / FFprobe en `PATH`.

### Para recompilar el ejecutable

-   Python.
-   PyInstaller.
-   `Varchiver_v1.0.py`
-   `Varchiver_v1.0.spec`
-   `varchiver_logo.png`
-   `varchiver.ico`

Compilación:

``` powershell
python -m PyInstaller --clean Varchiver_v1.0.spec
```

El resultado se genera en:

``` text
dist\Varchiver.exe
```

------------------------------------------------------------------------

## Archivos de distribución y desarrollo

### Uso cotidiano

Para utilizar la aplicación normalmente bastan:

``` text
Varchiver.exe
valorant_archiver_catalogo.json
README.md
```

Los archivos `.valorant_archiver.json` permanecen en sus respectivas
carpetas de Outplayed.

### Desarrollo / respaldo recomendado

Es recomendable conservar en una carpeta `source` o `backup`:

``` text
Varchiver_v1.0.py
Varchiver_v1.0.spec
varchiver.ico
varchiver_logo.png
BUILD_VARCHIVER_v1.0.txt
```

Las carpetas `build` y `dist` generadas por PyInstaller pueden
eliminarse después de comprobar que el ejecutable final funciona y de
conservar una copia de `Varchiver.exe`.

------------------------------------------------------------------------

## Historial de versiones finales

### v0.9.2

Versión de estabilización funcional.

-   Corrección de la estructura de la pestaña Procesar clips.
-   Mejora de seguridad entre Tkinter y el hilo de procesamiento.
-   Persistencia robusta de divisiones basada en identidad de clips.
-   Migración de configuraciones antiguas utilizando el catálogo cuando
    es posible.
-   Corrección del buscador de mapas y agentes.
-   Eliminación de divisiones fantasma después de retirar clips de una
    partida.

### v0.9.3

Primera renovación visual.

-   Jerarquía visual mejorada.
-   Acción principal de procesamiento destacada.
-   Acción LIBERAR ESPACIO diferenciada.
-   Estados de almacenamiento destacados en Historial.
-   Mejoras de espaciado y legibilidad.

### v0.9.4 Hotfix

-   Ajuste responsive de la zona inferior del Historial.
-   Corrección de un padding incompatible con Tkinter.

### v0.9.5

Identidad visual.

-   Logo oficial Varchiver.
-   Icono propio de la aplicación.
-   Preparación de recursos para empaquetado.

### v0.9.6

Primer ejecutable standalone.

-   Preparación para PyInstaller.
-   Catálogo persistente junto al ejecutable.
-   Recursos gráficos incluidos en el EXE.

### v0.9.7 RC

Release Candidate.

-   Pruebas completas del flujo real desde el ejecutable.
-   Protección para no crear un catálogo vacío solamente por iniciar
    Varchiver desde otra carpeta.
-   Validación de divisiones, procesamiento, liberación de espacio,
    persistencia y relocalización de MP4.

### v1.0

Primera versión estable.

Validada mediante un flujo real completo:

-   seleccionar carpeta;
-   crear y quitar divisiones;
-   asignar metadatos;
-   procesar partidas;
-   consultar historial;
-   liberar clips originales;
-   conservar MP4 final;
-   renombrar/mover el MP4;
-   relocalizarlo desde Varchiver;
-   cerrar y reabrir manteniendo la persistencia.

------------------------------------------------------------------------

## Decisiones de alcance de v1.0

Varchiver v1.0 se mantiene deliberadamente simple.

No intenta reemplazar Outplayed, Subtitle Edit, YouTube ni un editor de
video completo. Su responsabilidad principal es organizar, consolidar,
catalogar y ayudar a liberar espacio de los clips ya capturados.

La combinación de SRT se mantiene como una función opcional y se
recomienda dejarla desactivada cuando se prefiera transcribir
posteriormente el MP4 final.

FFmpeg no está integrado dentro del ejecutable v1.0; se utiliza la
instalación disponible en `PATH`.

------------------------------------------------------------------------

## Posibles mejoras posteriores a v1.0

Las siguientes ideas quedan fuera del alcance de la primera versión
estable y pueden evaluarse para futuras versiones 1.x:

-   instalador de Windows;
-   actualización automática o asistida;
-   configuración interna de la ruta de FFmpeg;
-   soporte ampliado para otros juegos;
-   mejoras adicionales de respaldo;
-   nuevas herramientas de catálogo;
-   integración más profunda con el flujo de publicación;
-   refinamientos visuales que no comprometan la simplicidad de la
    interfaz.

------------------------------------------------------------------------

## Estado del proyecto

**Varchiver v1.0 --- estable.**

El núcleo funcional, persistencia, administración de almacenamiento,
interfaz, identidad visual y ejecutable de Windows fueron probados
mediante uso real.

A partir de este punto, cualquier nueva funcionalidad debe considerarse
una evolución de la rama 1.x y no un requisito pendiente de v1.0.
