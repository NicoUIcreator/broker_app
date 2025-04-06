import streamlit as st
import pandas as pd
from utils.google_sheets import (
      get_google_sheets_service,
      verificar_o_crear_hoja,
      agregar_o_actualizar_datos, # Usamos la nueva función
      obtener_nombres_hojas,
      leer_datos_hoja,
      actualizar_flag_wsp,
      ENCABEZADOS, # Importar encabezados para usarlos en la visualización
      # Nuevas importaciones para Drive
      get_google_drive_service,
      upload_csv_to_drive
  )
from utils.data_processing import (
      leer_excel_subido,
      preparar_datos_para_hoja
  )
# Import WhatsApp utility functions
from utils.whatsapp_messaging import (
    initialize_whatsapp_client,
    send_whatsapp_message,
    format_message
)

  # --- Configuración de la Página ---
st.set_page_config(
      page_title="Gestor Clientes Broker",
      page_icon="📊",
      layout="wide" # Usar ancho completo
  )

  # --- Estado de Sesión ---
if 'logged_in' not in st.session_state:
      st.session_state.logged_in = False
if 'service' not in st.session_state: # Servicio de Sheets
      st.session_state.service = None
if 'drive_service' not in st.session_state: # Servicio de Drive
      st.session_state.drive_service = None
if 'whatsapp_client' not in st.session_state: # Nuevo: Cliente WhatsApp
      st.session_state.whatsapp_client = None
if 'spreadsheet_id' not in st.session_state:
       # Cargar desde secrets si está disponible
       try:
           st.session_state.spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
       except KeyError:
           st.session_state.spreadsheet_id = None # O un valor por defecto si prefieres

  # --- Función de Login ---
def check_login():
      """Verifica las credenciales ingresadas con las de secrets.toml."""
      try:
          stored_username = st.secrets["login"]["username"]
          stored_password = st.secrets["login"]["password"]
      except KeyError:
          st.error("Error: No se encontraron credenciales de login en la configuración (secrets.toml).")
          return False

      if (st.session_state["username"] == stored_username and
          st.session_state["password"] == stored_password):
          st.session_state.logged_in = True
          # Limpiar contraseña del estado después de verificar
          del st.session_state["password"] 
          # Intentar obtener los servicios de Google al loguearse
          st.session_state.service = get_google_sheets_service() # Sheets
          st.session_state.drive_service = get_google_drive_service() # Drive
          st.session_state.whatsapp_client = initialize_whatsapp_client() # WhatsApp (Placeholder)

          # Verificar servicios y configuraciones
          if not st.session_state.service:
               st.warning("Login exitoso, pero hubo un problema al conectar con Google Sheets.")
          if not st.session_state.drive_service:
               st.warning("Login exitoso, pero hubo un problema al conectar con Google Drive.")
          if not st.session_state.spreadsheet_id:
               st.warning("Login exitoso, pero no se configuró el SPREADSHEET_ID en secrets.toml.")

      else:
          st.session_state.logged_in = False
          st.error("Usuario o contraseña incorrectos.")

  # --- Pantalla de Login ---
if not st.session_state.logged_in:
      st.title("Inicio de Sesión - Gestor de Clientes")
      st.text_input("Usuario", key="username")
      st.text_input("Contraseña", type="password", key="password")
      st.button("Ingresar", on_click=check_login)
      st.info("Utiliza las credenciales definidas en el archivo .streamlit/secrets.toml")

  # --- Aplicación Principal (si está logueado) ---
else:
      st.sidebar.title(f"Bienvenido, {st.secrets['login']['username']}!")
      st.sidebar.markdown("---")
      
      # --- Opciones en Sidebar ---
      app_mode = st.sidebar.selectbox(
          "Selecciona una Acción",
          ["Cargar Datos desde Excel", "Ver/Gestionar Clientes", "Enviar Mensajes (Próximamente)"]
      )
      st.sidebar.markdown("---")
      if st.sidebar.button("Cerrar Sesión"):
          st.session_state.logged_in = False
          st.session_state.service = None # Limpiar servicio Sheets
          st.session_state.drive_service = None # Limpiar servicio Drive
          st.session_state.whatsapp_client = None # Limpiar cliente WhatsApp
          st.rerun() # Recargar la app para volver al login

      # Verificar conexiones a Google Sheets y Drive
      sheets_ok = True
      drive_ok = True
      if not st.session_state.service:
           st.error("No se pudo establecer conexión con Google Sheets. Verifica las credenciales y la conexión a internet.")
           sheets_ok = False
      if not st.session_state.drive_service:
           st.warning("No se pudo establecer conexión con Google Drive. La exportación a CSV no estará disponible.")
           drive_ok = False # Aún se puede usar la app sin Drive
      if not st.session_state.spreadsheet_id:
           st.error("El ID de la Hoja de Cálculo (spreadsheet_id) no está configurado en secrets.toml ([google_sheets]).")
           sheets_ok = False
           
      # Detener solo si Sheets falla, ya que es esencial
      if not sheets_ok:
           st.stop()

      spreadsheet_id = st.session_state.spreadsheet_id
      service = st.session_state.service # Servicio de Sheets
      drive_service = st.session_state.drive_service # Servicio de Drive (puede ser None)

      # --- Modo: Cargar Datos desde Excel ---
      if app_mode == "Cargar Datos desde Excel":
          st.title(" Cargar Nuevos Clientes desde Archivo Excel")
          st.markdown("Sube uno o más archivos Excel. El sistema intentará crear/actualizar una hoja por cada archivo.")

          uploaded_files = st.file_uploader(
              "Selecciona los archivos Excel",
              type=["xlsx", "xls"],
              accept_multiple_files=True
          )

          if uploaded_files:
              # Pedir nombre de compañía para cada archivo
              nombres_companias = {}
              for uploaded_file in uploaded_files:
                  # Sugerir nombre basado en el archivo (sin extensión)
                  suggested_name = uploaded_file.name.split('.')[0]
                  # Limpiar nombre sugerido (reemplazar caracteres no alfanuméricos)
                  suggested_name_clean = ''.join(e for e in suggested_name if e.isalnum() or e.isspace()).strip()
                  
                  nombre = st.text_input(
                      f"Nombre de la Compañía/Hoja para '{uploaded_file.name}'",
                      value=suggested_name_clean,
                      key=f"company_name_{uploaded_file.file_id}" # Clave única por archivo
                  )
                  if nombre: # Solo procesar si el usuario ingresó un nombre
                       # Usar file_id como clave y guardar nombre y objeto archivo
                       nombres_companias[uploaded_file.file_id] = {"name": nombre.strip(), "file": uploaded_file}

              if st.button("Procesar Archivos Cargados", disabled=(len(nombres_companias) != len(uploaded_files))):
                  if len(nombres_companias) == 0:
                       st.warning("Asegúrate de asignar un nombre de Compañía/Hoja a cada archivo subido.")
                  else:
                      st.markdown("---")
                      st.subheader("Resultados del Procesamiento:")
                      
                      grand_total_agregados = 0
                      grand_total_actualizados = 0

                      # Iterar sobre el diccionario usando file_id como clave
                      for file_id, data in nombres_companias.items():
                          uploaded_file = data["file"] # Obtener el objeto archivo
                          nombre_hoja = data["name"]   # Obtener el nombre de la hoja
                          st.markdown(f"**Procesando: {uploaded_file.name} para la hoja '{nombre_hoja}'**")

                          with st.spinner(f"Leyendo y procesando '{uploaded_file.name}'..."):
                              df_compania = leer_excel_subido(uploaded_file)

                          if df_compania is not None:
                              with st.spinner(f"Adaptando datos de '{nombre_hoja}'..."):
                                  datos_para_sheets = preparar_datos_para_hoja(df_compania, nombre_hoja)

                              if datos_para_sheets:
                                  with st.spinner(f"Verificando/Creando hoja '{nombre_hoja}'..."):
                                      hoja_lista = verificar_o_crear_hoja(service, spreadsheet_id, nombre_hoja)

                                  if hoja_lista:
                                      with st.spinner(f"Agregando/Actualizando datos en '{nombre_hoja}'..."):
                                          # Usar la función que agrega o actualiza
                                          agregados, actualizados = agregar_o_actualizar_datos(service, spreadsheet_id, nombre_hoja, datos_para_sheets)
                                          grand_total_agregados += agregados
                                          grand_total_actualizados += actualizados
                                  else:
                                      st.error(f"No se pudieron procesar los datos para '{nombre_hoja}' porque la hoja no pudo ser creada/verificada.")
                              else:
                                  st.warning(f"No se prepararon datos válidos del archivo '{uploaded_file.name}' para '{nombre_hoja}'.")
                          else:
                              st.error(f"No se pudo leer el archivo Excel: '{uploaded_file.name}'.")
                          st.markdown("---") # Separador entre archivos

                      st.subheader("Resumen Total:")
                      st.success(f"Proceso completado. Total de registros nuevos agregados: {grand_total_agregados}")
                      st.info(f"Total de registros existentes actualizados: {grand_total_actualizados}")

      # --- Modo: Ver/Gestionar Clientes ---
      elif app_mode == "Ver/Gestionar Clientes":
          st.title(" Ver y Gestionar Clientes por Compañía")

          nombres_existentes = obtener_nombres_hojas(service, spreadsheet_id)
          if not nombres_existentes:
              st.warning("Aún no se han cargado datos de ninguna compañía.")
          else:
              hoja_seleccionada = st.selectbox("Selecciona la Compañía (Hoja)", options=nombres_existentes)

              if hoja_seleccionada:
                  st.subheader(f"Clientes de: {hoja_seleccionada}")
                  with st.spinner(f"Cargando datos de '{hoja_seleccionada}'..."):
                       datos_crudos = leer_datos_hoja(service, spreadsheet_id, hoja_seleccionada)

                  if datos_crudos is not None:
                      if len(datos_crudos) > 1: # Si hay más que solo el encabezado (o si no hay encabezado)
                           # Crear DataFrame para mejor visualización y filtrado
                           # Usar ENCABEZADOS como columnas si la primera fila coincide, sino usar la primera fila como header
                           header = ENCABEZADOS if datos_crudos[0] == ENCABEZADOS else datos_crudos[0]
                           data_start_row = 1 if datos_crudos[0] == ENCABEZADOS else 1 # Siempre empezar desde la segunda fila si hay datos
                           
                           df_clientes = pd.DataFrame(datos_crudos[data_start_row:], columns=header)
                           
                           # Añadir columna con número de fila original para poder actualizar
                           df_clientes['__row_number__'] = range(data_start_row + 1, len(datos_crudos) + 1)

                           # --- Filtros ---
                           st.markdown("**Filtros:**")
                           col1, col2 = st.columns(2)
                           
                           # Filtrar por nombre/apellido
                           filtro_nombre = col1.text_input("Buscar por Nombre/Apellido")
                           # Filtrar por WSP Enviado
                           opcion_wsp = ["Todos", "Pendientes (FALSE)", "Enviados (TRUE)"]
                           filtro_wsp_sel = col2.selectbox("Filtrar por Estado WhatsApp", options=opcion_wsp)

                           # Aplicar filtros
                           df_filtrado = df_clientes.copy()
                           if filtro_nombre:
                               df_filtrado = df_filtrado[df_clientes['Nombre_Apellido'].str.contains(filtro_nombre, case=False, na=False)]
                           
                           if filtro_wsp_sel == "Pendientes (FALSE)":
                               # Asegurarse de comparar con strings 'FALSE' o vacíos
                               df_filtrado = df_filtrado[df_filtrado['Mensaje_WSP_Enviado'].str.upper().isin(['FALSE', ''])]
                           elif filtro_wsp_sel == "Enviados (TRUE)":
                               df_filtrado = df_filtrado[df_filtrado['Mensaje_WSP_Enviado'].str.upper() == 'TRUE']

                           st.markdown("---")
                           st.dataframe(df_filtrado.drop(columns=['__row_number__'])) # Ocultar columna auxiliar al mostrar

                           # --- Acción: Marcar como Enviado/Pendiente ---
                           st.markdown("**Actualizar Estado WhatsApp:**")
                           
                           # Usar el índice del dataframe filtrado para seleccionar cliente
                           clientes_para_actualizar = df_filtrado['Numero_Identificacion'] + " - " + df_filtrado['Nombre_Apellido']
                           cliente_seleccionado = st.selectbox(
                               "Selecciona cliente para cambiar estado WSP", 
                               options=[""] + clientes_para_actualizar.tolist() # Añadir opción vacía
                           )

                           if cliente_seleccionado:
                               num_id_seleccionado = cliente_seleccionado.split(" - ")[0]
                               # Encontrar el número de fila original del cliente seleccionado en el DF *filtrado*
                               fila_original_num = df_filtrado.loc[df_filtrado['Numero_Identificacion'] == num_id_seleccionado, '__row_number__'].iloc[0]

                               col_act1, col_act2 = st.columns(2)
                               if col_act1.button("Marcar como ENVIADO (TRUE)"):
                                   with st.spinner("Actualizando estado..."):
                                       if actualizar_flag_wsp(service, spreadsheet_id, hoja_seleccionada, fila_original_num, True):
                                           st.success("¡Estado actualizado! Refresca los datos si es necesario.")
                                           # Idealmente, refrescaríamos los datos aquí, pero requiere rerun o manejo más complejo
                                       else:
                                           st.error("No se pudo actualizar el estado.")
                                       
                               if col_act2.button("Marcar como PENDIENTE (FALSE)"):
                                   with st.spinner("Actualizando estado..."):
                                       if actualizar_flag_wsp(service, spreadsheet_id, hoja_seleccionada, fila_original_num, False):
                                           st.success("¡Estado actualizado! Refresca los datos si es necesario.")
                                       else:
                                           st.error("No se pudo actualizar el estado.")
                           
                           st.markdown("---")
                           # --- Acción: Exportar a CSV ---
                           st.markdown("**Exportar Datos a Google Drive:**")
                           # Opcional: Pedir ID de carpeta de Drive
                           # drive_folder_id = st.text_input("ID de Carpeta en Google Drive (opcional, dejar vacío para raíz)")
                           drive_folder_id = None # Por ahora, subir a la raíz

                           if st.button(f"Exportar '{hoja_seleccionada}' a CSV en Drive", disabled=(not drive_ok or not datos_crudos)):
                               if drive_service and datos_crudos:
                                   filename = f"Export_{hoja_seleccionada}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
                                   with st.spinner(f"Exportando '{filename}.csv' a Google Drive..."):
                                       file_id = upload_csv_to_drive(drive_service, datos_crudos, filename, drive_folder_id)
                                       if file_id:
                                           # Opcional: Mostrar enlace
                                           st.info(f"Archivo creado en Google Drive. Puedes buscarlo por el nombre '{filename}.csv'.")
                                       else:
                                           st.error("Falló la exportación a Google Drive.")
                               elif not drive_ok:
                                    st.error("La conexión con Google Drive no está disponible.")
                               else:
                                    st.warning("No hay datos para exportar.")

                      elif len(datos_crudos) == 1 and datos_crudos[0] == ENCABEZADOS:
                           st.info("La hoja contiene solo los encabezados. Aún no hay datos de clientes.")
                      else: # datos_crudos es [] o None
                           st.info(f"No se encontraron datos válidos en la hoja '{hoja_seleccionada}' para mostrar o exportar.")
                  else: # datos_crudos es None (error al leer)
                      st.error(f"No se pudieron cargar los datos de '{hoja_seleccionada}'.")

      # --- Modo: Enviar Mensajes ---
      elif app_mode == "Enviar Mensajes (Próximamente)": # Mantener nombre hasta que funcione
          st.title(" Envío de Mensajes Personalizados (WhatsApp)")

          # Verificar cliente WhatsApp (placeholder por ahora)
          whatsapp_client = st.session_state.whatsapp_client
          if not whatsapp_client:
              st.error("El cliente de WhatsApp no está inicializado. Verifica la configuración en secrets.toml (cuando implementes la API real).")
              st.stop()

          # 1. Seleccionar Compañía/Hoja
          nombres_existentes_wsp = obtener_nombres_hojas(service, spreadsheet_id)
          if not nombres_existentes_wsp:
              st.warning("Aún no se han cargado datos de ninguna compañía para enviar mensajes.")
              st.stop()

          hoja_seleccionada_wsp = st.selectbox(
              "Selecciona la Compañía (Hoja) para enviar mensajes",
              options=nombres_existentes_wsp,
              key="wsp_hoja_select"
          )

          if hoja_seleccionada_wsp:
              st.subheader(f"Enviar mensajes a clientes de: {hoja_seleccionada_wsp}")

              # 2. Cargar y filtrar clientes pendientes
              with st.spinner(f"Cargando clientes pendientes de '{hoja_seleccionada_wsp}'..."):
                  datos_crudos_wsp = leer_datos_hoja(service, spreadsheet_id, hoja_seleccionada_wsp)

              if datos_crudos_wsp is None or len(datos_crudos_wsp) <= 1:
                  st.info(f"No se encontraron datos de clientes o solo encabezados en '{hoja_seleccionada_wsp}'.")
                  st.stop()

              header_wsp = ENCABEZADOS if datos_crudos_wsp[0] == ENCABEZADOS else datos_crudos_wsp[0]
              data_start_row_wsp = 1 # Asumimos que siempre hay encabezado o queremos ignorar la fila 0 si no es el estándar

              df_clientes_wsp = pd.DataFrame(datos_crudos_wsp[data_start_row_wsp:], columns=header_wsp)
              # Añadir número de fila original (importante para actualizar el flag)
              df_clientes_wsp['__row_number__'] = range(data_start_row_wsp + 1, len(datos_crudos_wsp) + 1)

              # Filtrar por Mensaje_WSP_Enviado == FALSE o vacío
              df_pendientes = df_clientes_wsp[
                  df_clientes_wsp['Mensaje_WSP_Enviado'].str.upper().isin(['FALSE', ''])
              ].copy() # Usar .copy() para evitar SettingWithCopyWarning

              if df_pendientes.empty:
                  st.success(f"¡Todos los clientes de '{hoja_seleccionada_wsp}' ya tienen el mensaje marcado como enviado!")
                  st.stop()

              st.markdown(f"Se encontraron **{len(df_pendientes)}** clientes pendientes de envío.")

              # 3. Selección de Clientes
              st.markdown("**Selecciona los clientes a los que deseas enviar mensaje:**")
              # Crear identificadores únicos para el multiselect
              df_pendientes['display_name'] = df_pendientes['Nombre_Apellido'] + " (ID: " + df_pendientes['Numero_Identificacion'] + ", Tel: " + df_pendientes['Numero_Telefono_1'] + ")"
              
              clientes_seleccionados_display = st.multiselect(
                  "Clientes Pendientes",
                  options=df_pendientes['display_name'].tolist(),
                  # default=df_pendientes['display_name'].tolist() # Descomentar para seleccionar todos por defecto
              )

              # Obtener los datos completos de los clientes seleccionados
              df_seleccionados = df_pendientes[df_pendientes['display_name'].isin(clientes_seleccionados_display)]

              # 4. Plantilla de Mensaje
              st.markdown("**Escribe tu plantilla de mensaje:**")
              st.markdown("Puedes usar placeholders como `{Nombre_Apellido}`, `{Numero_Identificacion}`, etc., que se reemplazarán con los datos del cliente.")
              # Mostrar columnas disponibles como placeholders
              st.caption(f"Columnas disponibles: {', '.join(header_wsp)}")

              mensaje_template = st.text_area("Plantilla del Mensaje:", height=150, value="Hola {Nombre_Apellido}, te contactamos para...")

              # 5. Botón de Envío
              st.markdown("---")
              if st.button(f"Enviar {len(df_seleccionados)} Mensajes (Simulación)", disabled=(len(df_seleccionados) == 0)):
                  if not mensaje_template:
                      st.warning("Por favor, escribe un mensaje.")
                  else:
                      st.subheader("Resultados del Envío (Simulación):")
                      exitos = 0
                      fallos = 0
                      
                      # Barra de progreso
                      progress_bar = st.progress(0)
                      status_text = st.empty()

                      for i, (index, cliente) in enumerate(df_seleccionados.iterrows()):
                          nombre_cliente = cliente['Nombre_Apellido']
                          telefono_cliente = cliente['Numero_Telefono_1']
                          fila_original = cliente['__row_number__']
                          
                          # Convertir la fila del DataFrame a un diccionario para formatear
                          datos_cliente_dict = cliente.to_dict()

                          status_text.text(f"Procesando {i+1}/{len(df_seleccionados)}: {nombre_cliente}...")

                          # Formatear mensaje
                          mensaje_final = format_message(mensaje_template, datos_cliente_dict)
                          st.text_area(f"Mensaje para {nombre_cliente}:", value=mensaje_final, height=100, disabled=True, key=f"msg_{index}")

                          # Enviar mensaje (simulado)
                          enviado_ok = send_whatsapp_message(whatsapp_client, telefono_cliente, mensaje_final, nombre_cliente)

                          # Actualizar flag en Google Sheet si el envío fue exitoso
                          if enviado_ok:
                              actualizado_ok = actualizar_flag_wsp(service, spreadsheet_id, hoja_seleccionada_wsp, fila_original, True)
                              if actualizado_ok:
                                  st.caption(f"Flag actualizado a TRUE para {nombre_cliente} en Google Sheets.")
                                  exitos += 1
                              else:
                                  st.warning(f"Mensaje enviado (simulado) a {nombre_cliente}, pero falló la actualización del flag en Google Sheets.")
                                  # Considerar esto como fallo parcial o total? Por ahora cuenta como éxito de envío.
                                  exitos += 1 # O decidir si contar como fallo si el flag no se actualiza
                          else:
                              fallos += 1
                          
                          # Actualizar progreso
                          progress_bar.progress((i + 1) / len(df_seleccionados))
                          st.markdown("---") # Separador visual

                      status_text.text("Proceso de envío completado.")
                      st.subheader("Resumen del Envío (Simulación):")
                      st.success(f"Mensajes enviados exitosamente (simulado): {exitos}")
                      st.error(f"Mensajes fallidos: {fallos}")
                      st.info("Recuerda que esto es una simulación. Deberás configurar una API real y reemplazar las funciones en utils/whatsapp_messaging.py.")
                      # Podríamos añadir un botón para refrescar los datos de pendientes
