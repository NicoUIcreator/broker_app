import streamlit as st
import os
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Encabezados estándar para cada nueva hoja de compañía
ENCABEZADOS = [
    'ID_Cliente_Unico', 'Nombre_Apellido', 'Numero_Identificacion',
    'Tipo_Identificacion', 'Numero_Telefono_1', 'Numero_Telefono_2',
    'Email_Principal', 'ID_Cliente_Compania', 'Fecha_Ultima_Actualizacion',
    'Mensaje_WSP_Enviado', 'Notas'
]

@st.cache_resource # Cachear el recurso para no reconstruirlo en cada interacción
def get_google_sheets_service():
    """Autentica y devuelve el objeto de servicio de Google Sheets."""
    try:
        # Intenta cargar desde Streamlit secrets (para despliegue)
        creds_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        st.success("Autenticación con Google Sheets (Secrets) exitosa.")
    except KeyError:
        # Si falla, intenta cargar desde el archivo local (para desarrollo)
        local_creds_path = 'credentials.json'
        if os.path.exists(local_creds_path):
            creds = Credentials.from_service_account_file(local_creds_path, scopes=SCOPES)
            st.info("Autenticación con Google Sheets (Archivo local) exitosa.")
        else:
            st.error("Error: No se encontraron credenciales de Google Sheets ni en secrets ni como 'credentials.json'.")
            return None
    except Exception as e:
        st.error(f"Error inesperado durante la autenticación de Google Sheets: {e}")
        return None

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error al construir el servicio de Google Sheets: {e}")
        return None

def verificar_o_crear_hoja(service, spreadsheet_id, nombre_hoja):
    """Verifica si una hoja existe, si no, la crea con los encabezados. Devuelve True si éxito."""
    if not service:
        st.error("Servicio de Google Sheets no disponible.")
        return False
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        nombres_hojas_existentes = [s.get("properties", {}).get("title", "") for s in sheets]

        if nombre_hoja in nombres_hojas_existentes:
            st.info(f"La hoja '{nombre_hoja}' ya existe.")
            return True
        else:
            st.warning(f"La hoja '{nombre_hoja}' no existe. Creando...")
            body = {'requests': [{'addSheet': {'properties': {'title': nombre_hoja}}}]}
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            st.success(f"Hoja '{nombre_hoja}' creada.")
            
            # Añadir encabezados
            time.sleep(1) # Pausa prudencial
            encabezados_body = {'values': [ENCABEZADOS]}
            range_encabezados = f"'{nombre_hoja}'!A1" # Comillas por si nombre tiene espacios
            
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=range_encabezados,
                valueInputOption='USER_ENTERED', body=encabezados_body
            ).execute()
            st.success(f"Encabezados añadidos a la hoja '{nombre_hoja}'.")
            return True

    except HttpError as error:
        st.error(f"Error de API al verificar/crear hoja '{nombre_hoja}': {error}")
        st.error(f"Detalles: {error.content}")
        return False
    except Exception as e:
        st.error(f"Error inesperado en verificar_o_crear_hoja para '{nombre_hoja}': {e}")
        return False

def agregar_datos_a_hoja(service, spreadsheet_id, nombre_hoja, datos):
    """Agrega filas de datos al final de la hoja especificada."""
    if not service:
        st.error("Servicio de Google Sheets no disponible.")
        return False
    if not datos:
        st.warning(f"No hay datos para agregar a la hoja '{nombre_hoja}'.")
        return True # No es un error, solo no hay nada que hacer

    try:
        range_to_append = f"'{nombre_hoja}'!A:A" # Comillas por si nombre tiene espacios
        body = {'values': datos}
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=range_to_append,
            valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS', body=body
        ).execute()
        rows_added = result.get('updates', {}).get('updatedRows', 0)
        st.success(f"Se agregaron {rows_added} filas a la hoja '{nombre_hoja}'.")
        return True

    except HttpError as error:
        st.error(f"Error de API al agregar datos a la hoja '{nombre_hoja}': {error}")
        st.error(f"Detalles: {error.content}")
        return False
    except Exception as e:
         st.error(f"Error inesperado al agregar datos a '{nombre_hoja}': {e}")
         return False
         
# --- NUEVA FUNCIONALIDAD: LEER DATOS DE UNA HOJA ---
def leer_datos_hoja(service, spreadsheet_id, nombre_hoja, rango='A:K'): # Ajusta el rango si tienes más columnas
    """Lee datos de una hoja específica y los devuelve como lista de listas."""
    if not service:
        st.error("Servicio de Google Sheets no disponible.")
        return None
    try:
        range_to_read = f"'{nombre_hoja}'!{rango}"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_to_read
        ).execute()
        values = result.get('values', [])
        if not values:
            st.info(f"No se encontraron datos en la hoja '{nombre_hoja}' (rango {rango}).")
            return [] # Devuelve lista vacía si no hay datos
        else:
            # st.success(f"Datos leídos de '{nombre_hoja}'.")
            return values
    except HttpError as error:
        # Podría ser que la hoja no exista aún, manejarlo como no encontrado
        if error.resp.status == 400 and 'Unable to parse range' in str(error.content):
             st.warning(f"La hoja '{nombre_hoja}' parece no existir o está vacía.")
             return []
        st.error(f"Error de API al leer datos de la hoja '{nombre_hoja}': {error}")
        st.error(f"Detalles: {error.content}")
        return None
    except Exception as e:
        st.error(f"Error inesperado al leer datos de '{nombre_hoja}': {e}")
        return None
        
# --- NUEVA FUNCIONALIDAD: ACTUALIZAR FLAG WSP ---
def actualizar_flag_wsp(service, spreadsheet_id, nombre_hoja, fila_numero, nuevo_valor):
    """Actualiza la columna 'Mensaje_WSP_Enviado' (columna J) para una fila específica."""
    if not service:
         st.error("Servicio de Google Sheets no disponible.")
         return False
    try:
        # La columna 'Mensaje_WSP_Enviado' es la 10ª, índice J
        columna_flag = 'J' 
        rango_actualizar = f"'{nombre_hoja}'!{columna_flag}{fila_numero}"
        
        body = {'values': [[str(nuevo_valor).upper()]]} # Sheets espera TRUE/FALSE en mayúsculas

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=rango_actualizar,
            valueInputOption='USER_ENTERED', body=body
        ).execute()
        st.success(f"Flag WSP actualizado a {nuevo_valor} para la fila {fila_numero} en '{nombre_hoja}'.")
        return True
        
    except HttpError as error:
        st.error(f"Error de API al actualizar flag WSP en fila {fila_numero}, hoja '{nombre_hoja}': {error}")
        st.error(f"Detalles: {error.content}")
        return False
    except Exception as e:
        st.error(f"Error inesperado al actualizar flag WSP: {e}")
        return False
        
# --- NUEVA FUNCIONALIDAD: OBTENER NOMBRES DE HOJAS ---
def obtener_nombres_hojas(service, spreadsheet_id):
    """Obtiene la lista de nombres de todas las hojas en el spreadsheet."""
    if not service:
        st.error("Servicio de Google Sheets no disponible.")
        return []
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        nombres = [s.get("properties", {}).get("title", "") for s in sheets]
        return nombres
    except HttpError as error:
        st.error(f"Error de API al obtener nombres de hojas: {error}")
        st.error(f"Detalles: {error.content}")
        return []
    except Exception as e:
        st.error(f"Error inesperado al obtener nombres de hojas: {e}")
        return []

# --- FUNCIONALIDAD MEJORADA: AGREGAR O ACTUALIZAR DATOS ---
def agregar_o_actualizar_datos(service, spreadsheet_id, nombre_hoja, datos_nuevos):
    """
    Agrega nuevos clientes o actualiza los existentes basados en Numero_Identificacion.
    'datos_nuevos' es la lista de listas procesadas del Excel.
    Asume que Numero_Identificacion está en el índice 2 y Fecha_Actualizacion en el 8.
    """
    if not service:
        st.error("Servicio de Google Sheets no disponible.")
        return 0, 0 # Filas agregadas, filas actualizadas

    # 1. Leer datos existentes de la hoja
    datos_actuales = leer_datos_hoja(service, spreadsheet_id, nombre_hoja, rango='A:K') # Leer todas las columnas relevantes
    if datos_actuales is None: # Hubo un error al leer
        return 0, 0
        
    # 2. Crear un diccionario de los datos actuales para búsqueda rápida por Numero_Identificacion
    #    Guardamos la fila completa y el número de fila original (índice + 1 porque sheets es 1-based)
    #    Omitimos el encabezado si existe
    mapa_datos_actuales = {}
    encabezado = datos_actuales[0] if datos_actuales else []
    inicio_datos = 1 if encabezado == ENCABEZADOS else 0 # Empezar desde la fila 1 si hay encabezado válido
    
    for i, fila in enumerate(datos_actuales[inicio_datos:], start=inicio_datos + 1):
         if len(fila) > 2: # Asegurarse que la fila tiene al menos Numero_Identificacion
             num_id = fila[2] 
             if num_id: # Solo mapear si hay un número de identificación
                 mapa_datos_actuales[num_id] = {'row_data': fila, 'row_number': i}

    # 3. Procesar los datos nuevos
    filas_para_agregar = []
    filas_para_actualizar = [] # Guardará (numero_fila, nueva_fila_completa)
    cont_agregadas = 0
    cont_actualizadas = 0

    for fila_nueva in datos_nuevos:
        num_id_nuevo = fila_nueva[2]
        if not num_id_nuevo:
            st.warning(f"Registro omitido por no tener Numero_Identificacion: {fila_nueva[1]}")
            continue # Omitir si no hay identificador

        if num_id_nuevo in mapa_datos_actuales:
            # Cliente ya existe, preparar para actualizar
            fila_existente_info = mapa_datos_actuales[num_id_nuevo]
            # Mantener el ID único si ya existe y el flag WSP, actualizar el resto
            id_unico_existente = fila_existente_info['row_data'][0]
            flag_wsp_existente = fila_existente_info['row_data'][9] if len(fila_existente_info['row_data']) > 9 else 'FALSE'
            
            fila_actualizada = fila_nueva[:] # Copiar la fila nueva
            fila_actualizada[0] = id_unico_existente # Conservar ID único
           # Actualizar fecha
            fila_actualizada[9] = flag_wsp_existente # Conservar flag WSP
            
            # Podríamos añadir una lógica más compleja para decidir si realmente actualizar
            # (p.ej., si los datos son diferentes) pero por ahora actualizamos siempre
            filas_para_actualizar.append((fila_existente_info['row_number'], fila_actualizada))
            cont_actualizadas += 1
        else:
            # Cliente nuevo, preparar para agregar
            # Aquí podríamos generar un ID_Cliente_Unico si quisiéramos
            # fila_nueva[0] = generar_id_unico() 
            filas_para_agregar.append(fila_nueva)
            cont_agregadas += 1

    # 4. Realizar las operaciones en Google Sheets
    # a) Actualizar filas existentes (hacer esto ANTES de agregar para evitar problemas de índices)
    if filas_para_actualizar:
        updates_body = []
        for row_num, row_data in filas_para_actualizar:
             updates_body.append({
                 'range': f"'{nombre_hoja}'!A{row_num}", # Rango de la fila a actualizar
                 'values': [row_data] # La fila completa con los nuevos valores
             })
        
        try:
             body = {'valueInputOption': 'USER_ENTERED', 'data': updates_body}
             service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
             st.success(f"{len(filas_para_actualizar)} filas actualizadas en '{nombre_hoja}'.")
        except HttpError as error:
             st.error(f"Error de API al actualizar filas en '{nombre_hoja}': {error}")
             st.error(f"Detalles: {error.content}")
             # Podríamos revertir o marcar estas filas como no actualizadas
             cont_actualizadas = 0 # Asumimos fallo total por simplicidad

    # b) Agregar nuevas filas
    if filas_para_agregar:
        agregar_datos_a_hoja(service, spreadsheet_id, nombre_hoja, filas_para_agregar)
        # La función agregar_datos_a_hoja ya imprime el mensaje de éxito/error
    
    return cont_agregadas, cont_actualizadas # Devuelve cuentas reales