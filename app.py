import streamlit as st
import pandas as pd
from utils.google_sheets import (
      get_google_sheets_service,
      verificar_o_crear_hoja,
      agregar_o_actualizar_datos, # Usamos la nueva función
      obtener_nombres_hojas,
      leer_datos_hoja,
      actualizar_flag_wsp,
      ENCABEZADOS # Importar encabezados para usarlos en la visualización
  )
from utils.data_processing import (
      leer_excel_subido,
      preparar_datos_para_hoja
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
if 'service' not in st.session_state:
      st.session_state.service = None
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
          # Intentar obtener el servicio de sheets al loguearse
          st.session_state.service = get_google_sheets_service()
          if not st.session_state.service:
               st.warning("Login exitoso, pero hubo un problema al conectar con Google Sheets.")
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
          st.session_state.service = None # Limpiar servicio al salir
          st.experimental_rerun() # Recargar la app para volver al login

      # Verificar conexión a Google Sheets
      if not st.session_state.service:
           st.error("No se pudo establecer conexión con Google Sheets. Verifica las credenciales y la conexión a internet.")
           st.stop() # Detener la ejecución si no hay servicio
      if not st.session_state.spreadsheet_id:
           st.error("El ID de la Hoja de Cálculo no está configurado en secrets.toml ([google_sheets] > spreadsheet_id).")
           st.stop()

      spreadsheet_id = st.session_state.spreadsheet_id
      service = st.session_state.service

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
                      key=f"company_name_{uploaded_file.id}" # Clave única por archivo
                  )
                  if nombre: # Solo procesar si el usuario ingresó un nombre
                       nombres_companias[uploaded_file] = nombre.strip()
                       
              if st.button("Procesar Archivos Cargados", disabled=(len(nombres_companias) != len(uploaded_files))):
                  if len(nombres_companias) == 0:
                       st.warning("Asegúrate de asignar un nombre de Compañía/Hoja a cada archivo subido.")
                  else:
                      st.markdown("---")
                      st.subheader("Resultados del Procesamiento:")
                      
                      grand_total_agregados = 0
                      grand_total_actualizados = 0

                      for uploaded_file, nombre_hoja in nombres_companias.items():
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
                                           
                      elif len(datos_crudos) == 1 and datos_crudos[0] == ENCABEZADOS:
                           st.info("La hoja contiene solo los encabezados. Aún no hay datos de clientes.")
                      else:
                           st.info(f"No se encontraron datos de clientes en la hoja '{hoja_seleccionada}'.")
                  else:
                      st.error(f"No se pudieron cargar los datos de '{hoja_seleccionada}'.")

      # --- Modo: Enviar Mensajes (Placeholder) ---
      elif app_mode == "Enviar Mensajes (Próximamente)":
          st.title(" Envío de Mensajes Personalizados (WhatsApp)")
          st.image("https://img.freepik.com/free-vector/coming-soon-display-background-with-focus-light_1017-33741.jpg", width=400)
          st.info("Esta funcionalidad está en desarrollo.")
          st.markdown("""
          **Próximos pasos:**
          *   Integración con una API de WhatsApp (como Twilio, Meta Cloud API, o alternativas).
          *   Selección de clientes (filtrando por 'Mensaje_WSP_Enviado' = FALSE).
          *   Plantillas de mensajes personalizables (usando datos del cliente como Nombre, Póliza, etc.).
          *   Actualización automática del flag 'Mensaje_WSP_Enviado' a TRUE tras envío exitoso.
          *   Manejo de errores y logs de envío.
          """)